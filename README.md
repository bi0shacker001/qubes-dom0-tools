# Qubes dom0 tools

Small tools for maintaining Qubes OS without installing QIM. Review the Python file in your browser qube and transfer it through your usual dom0 workflow. Run it in dom0 with Python 3 and the Qubes admin tools.

## Upgrade a customized Fedora template

Prepare a halted template by cloning it, applying Fedora's package transaction, restarting it, and checking the resulting Fedora release and package health. The original remains available for rollback. The clone needs enough space for the transaction. If a repository or dependency blocks the upgrade, inspect the candidate and the DNF output. Use `--allow-erasing` only if you accept DNF removing conflicting packages.

Choose your actual source and unused clone names. For example:

```sh
python3 qubes-template-upgrade.py prepare fedora-42-custom fedora-44-custom 44
```

Check your custom packages and services on the clone before migrating. Select the halted AppVMs to move. The tool rejects disposable templates and network providers.

```sh
python3 qubes-template-upgrade.py plan fedora-42-custom fedora-44-custom my-app
python3 qubes-template-upgrade.py apply fedora-42-custom fedora-44-custom my-app \
  --journal "$HOME/fedora44-migration.json"
```

Apply verifies each assignment and attempts to reverse the batch on failure. To reverse the assignments later, halt the migrated qubes and use the journal:

```sh
python3 qubes-template-upgrade.py rollback "$HOME/fedora44-migration.json"
```

Rollback changes template assignments. Keep separate backups of AppVM private data.

The Fedora package transaction follows the [Qubes Fedora template upgrade guide](https://doc.qubes-os.org/en/r4.3/user/templates/fedora/fedora-upgrade.html).
