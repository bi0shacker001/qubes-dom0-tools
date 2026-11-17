# Qubes dom0 tools

Small tools for maintaining Qubes OS without installing QIM.

## Install on Qubes OS 4.3

Download the [repository file](https://bi0shacker001.github.io/qubes-dom0-tools/qubes-dom0-tools.repo) and [RPM signing key](https://bi0shacker001.github.io/qubes-dom0-tools/RPM-GPG-KEY-qubes-dom0-tools) in an online qube. Check that the key fingerprint is `D991 110D ED5D A1A2 CBF8 580B CD01 871A 37BF 82C7` with:

```sh
gpg --show-keys --fingerprint RPM-GPG-KEY-qubes-dom0-tools
```

Transfer both files into dom0. From the directory containing them, run:

```sh
sudo install -m 0644 qubes-dom0-tools.repo /etc/yum.repos.d/qubes-dom0-tools.repo
sudo rpmkeys --import RPM-GPG-KEY-qubes-dom0-tools
sudo qubes-dom0-update --enablerepo=qubes-dom0-tools qubes-template-upgrade
```

The repo is disabled by default and scoped to this package. Repeat the final command to update it. Qubes downloads the package through its UpdateVM. [Qubes dom0 update mechanism](https://doc.qubes-os.org/en/r4.3/developer/services/dom0-secure-updates.html)

## Upgrade a customized Fedora template

Prepare a halted template by cloning it, applying Fedora's package transaction, restarting it, and checking the resulting Fedora release and package health. The original remains available for rollback. The clone needs enough space for the transaction. If a repository or dependency blocks the upgrade, inspect the candidate and the DNF output. Use `--allow-erasing` only if you accept DNF removing conflicting packages.

Choose your actual source and unused clone names. For example:

```sh
qubes-template-upgrade prepare fedora-42-custom fedora-44-custom 44
```

Check your custom packages and services on the clone before migrating. Select the halted AppVMs to move. The tool rejects disposable templates and network providers.

```sh
qubes-template-upgrade plan fedora-42-custom fedora-44-custom my-app
qubes-template-upgrade apply fedora-42-custom fedora-44-custom my-app \
  --journal "$HOME/fedora44-migration.json"
```

Apply verifies each assignment and attempts to reverse the batch on failure. To reverse the assignments later, halt the migrated qubes and use the journal:

```sh
qubes-template-upgrade rollback "$HOME/fedora44-migration.json"
```

Rollback changes template assignments. Keep separate backups of AppVM private data.

The Fedora package transaction follows the [Qubes Fedora template upgrade guide](https://doc.qubes-os.org/en/r4.3/user/templates/fedora/fedora-upgrade.html).
