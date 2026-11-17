#!/usr/bin/env python3
"""Upgrade a customized Fedora template on a clone and migrate halted AppVMs."""

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path


def lookup(app, name):
    try:
        return app.domains[name]
    except KeyError:
        return None


def require_template(app, name):
    vm = lookup(app, name)
    if vm is None or vm.klass != "TemplateVM":
        raise ValueError(f"{name} must be an installed TemplateVM")
    return vm


def guest(vm, command):
    return subprocess.check_output(
        ["qvm-run", "-u", "root", "--pass-io", vm, command], text=True
    ).strip()


def prepare(app_factory, args):
    source, target = args.source, args.target
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", target):
        raise ValueError(f"Invalid clone name: {target}")
    app = app_factory()
    old = require_template(app, source)
    if old.get_power_state() != "Halted" or lookup(app, target) is not None:
        raise ValueError("The source must be halted and the clone name must be unused")
    subprocess.run(["qvm-clone", source, target], check=True)
    candidate = require_template(app_factory(), target)
    try:
        candidate.start()
        release = guest(target, "rpm -E %fedora")
        if not release.isdecimal() or not 0 < args.release - int(release) <= 2:
            raise ValueError(f"Expected a Fedora release one or two versions before {args.release}; got {release}")
        # Stream DNF output. Allow package erasures only after an explicit opt-in.
        command = ["dnf", f"--releasever={args.release}", "--best", "--assumeyes", "distro-sync"]
        if args.allow_erasing:
            command.append("--allowerasing")
        subprocess.run(["qvm-run", "-u", "root", "--pass-io", target, shlex.join(command)], check=True)
        subprocess.run(["qvm-shutdown", "--wait", target], check=True)
        candidate.start()
        guest(target, f'test "$(rpm -E %fedora)" = {args.release} && rpm -q qubes-core-agent && dnf check')
        subprocess.run(["qvm-shutdown", "--wait", target], check=True)
        candidate.features["template-name"] = target
        candidate.features["dom0-tools-upgraded-from"] = source
    except (Exception, KeyboardInterrupt):
        print(f"Preparation failed. Candidate {target} is available for inspection.", file=sys.stderr)
        raise
    print(f"Verified candidate {target} for Fedora {args.release}.")


def check_qube(vm, template):
    if vm is None or vm.klass != "AppVM":
        raise ValueError("Expected an existing AppVM")
    if vm.template.name != template:
        raise ValueError(f"{vm.name} uses {vm.template.name}, expected {template}")
    if vm.get_power_state() != "Halted":
        raise ValueError(f"{vm.name} must be halted")
    if vm.template_for_dispvms or vm.provides_network:
        raise ValueError(f"{vm.name} is a disposable template or network provider")


def build_plan(app, source, target, names):
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", target):
        raise ValueError(f"Invalid destination template name: {target}")
    if source == target:
        raise ValueError("Source and destination must differ")
    require_template(app, source)
    target_vm = lookup(app, target)
    if target_vm is not None:
        require_template(app, target)
    for name in names:
        vm = lookup(app, name)
        if vm is None:
            raise ValueError(f"Unknown qube: {name}")
        check_qube(vm, source)
    return {"source": source, "target": target, "qubes": list(dict.fromkeys(names))}


def save_journal(path, plan):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as journal:
        json.dump(plan, journal, indent=2)
        journal.write("\n")
        journal.flush()
        os.fsync(journal.fileno())


def switch(app_factory, plan, rollback=False):
    source, target = plan["source"], plan["target"]
    names = plan["qubes"]
    if rollback:
        source, target = target, source
        names = reversed(names)
    require_template(app_factory(), target)
    errors = []
    for name in names:
        try:
            app = app_factory()
            vm = lookup(app, name)
            if rollback and vm is not None and vm.klass == "AppVM":
                if vm.template.name == target:
                    continue
            check_qube(vm, source)
            vm.template = target
            updated = lookup(app_factory(), name)
            if updated is None or updated.template.name != target:
                raise ValueError("Could not verify the new template assignment")
            print(f"{name}: {source} -> {target}", flush=True)
        except Exception as error:
            if not rollback:
                raise
            errors.append(f"{name}: {error}")
    if errors:
        raise RuntimeError("Rollback incomplete:\n" + "\n".join(errors))


def main(app_factory, args):
    if args.action == "prepare":
        prepare(app_factory, args)
        return
    if args.action == "rollback":
        plan = json.loads(args.journal.read_text(encoding="utf-8"))
        switch(app_factory, plan, rollback=True)
        return

    plan = build_plan(app_factory(), args.source, args.target, args.qubes)
    candidate = require_template(app_factory(), args.target)
    if candidate.features.get("dom0-tools-upgraded-from") != args.source:
        raise ValueError("Destination must be a verified clone prepared from this source")
    if candidate.get_power_state() != "Halted":
        raise ValueError("The destination template must be halted")
    for name in plan["qubes"]:
        print(f"{name}: {args.source} -> {args.target}")
    if args.action == "plan":
        return

    save_journal(args.journal, plan)
    print(f"Rollback journal: {args.journal}", flush=True)
    try:
        switch(app_factory, plan)
    except (Exception, KeyboardInterrupt) as error:
        print(f"Migration stopped: {error}. Attempting rollback.", file=sys.stderr)
        switch(app_factory, plan, rollback=True)
        raise RuntimeError("Migration stopped and original assignments were restored") from error


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    command = commands.add_parser("prepare", help="clone, upgrade, and verify a Fedora template")
    command.add_argument("source")
    command.add_argument("target")
    command.add_argument("release", type=int)
    command.add_argument("--allow-erasing", action="store_true")
    for action in ("plan", "apply"):
        command = commands.add_parser(action)
        command.add_argument("source")
        command.add_argument("target")
        command.add_argument("qubes", nargs="+")
        if action == "apply":
            command.add_argument("--journal", required=True, type=Path)
    commands.add_parser("rollback").add_argument("journal", type=Path)
    args = parser.parse_args()

    try:
        if not Path("/etc/qubes-release").is_file():
            raise RuntimeError("Run this tool in Qubes dom0")
        import fcntl

        from qubesadmin.app import QubesLocal

        if args.action == "plan":
            main(QubesLocal, args)
        else:
            with (Path.home() / ".qubes-template-migrate.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                main(QubesLocal, args)
    except (Exception, KeyboardInterrupt) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
