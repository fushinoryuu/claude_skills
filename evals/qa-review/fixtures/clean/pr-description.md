PR: #42
Title: LFMT-12: Add a --sort option to listfmt
State: OPEN
Base branch: main
Head branch: lfmt-12-sort-option
Changed files: README.md, src/listfmt/cli.py, src/listfmt/core.py, tests/test_cli.py, tests/test_core.py

Body:
Adds `--sort {name,size}` to `listfmt`.

- `sort_entries` in `core.py` orders the entries by name or by size, smallest first. With no key the order is unchanged.
- The option uses argparse `choices`, so any other value prints the valid choices and exits with code 2.
- README option table updated.

Tests: sort by name and by size, no sort key, empty input, an unknown key, and the invalid value on the command line.
