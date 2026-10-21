Key: LFMT-12
Type: Story
Status: In QA
Summary: Add a --sort option to listfmt

Description:
Users want to list files in a stable order. Add a `--sort` option to the `listfmt` command so the output can be ordered by name or by size. Without the option the output stays in the order the paths were given.

Acceptance criteria:
1. `listfmt --sort name <paths>` prints the paths in alphabetical order.
2. `listfmt --sort size <paths>` prints the paths with the smallest file first.
3. Any other value for `--sort` prints an error that lists the valid choices, and the command exits with code 2.
4. The README documents the new option.

Linked issues: none

Comments:
- Dev (2026-03-02): PR 42 is up for QA.
