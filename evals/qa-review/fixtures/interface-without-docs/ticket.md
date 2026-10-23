Key: FC-6
Type: Story
Status: In QA
Summary: Let filecount skip files by pattern

Description:
People want to count their source files without counting logs and temporary files. Add an option to leave out files whose names match a pattern.

Acceptance criteria:
1. `filecount --exclude PATTERN folder` does not count files whose name matches the glob pattern.
2. `--exclude` can be given more than once, and a file matching any pattern is skipped.
3. It works together with `--recursive`.
4. `filecount --help` lists the new option.

Linked issues: none

Comments:
- Dev (2026-03-20): PR 12 is up for QA.
