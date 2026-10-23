PR: #12
Title: FC-6: Add --exclude to filecount
State: OPEN
Base branch: main
Head branch: fc-6-exclude
Changed files: src/filecount/cli.py, tests/test_cli.py

Body:
Adds `--exclude PATTERN` to `filecount`.

- The pattern is a glob matched against the file name.
- The option can be repeated, and works with `--recursive`.
- It has help text, so it shows in `--help`.

Tests cover one pattern, several patterns, a pattern that matches nothing, and the command line.
