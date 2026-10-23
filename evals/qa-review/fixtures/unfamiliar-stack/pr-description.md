PR: #4
Title: WK-5: Add pluralize
State: OPEN
Base branch: main
Head branch: wk-5-pluralize
Changed files: README.md, src/wordkit.gleam

Body:
Adds `pluralize(count, word)` to wordkit.

- Exactly one gets the singular word. Every other count, including zero and negative numbers, gets the word with an "s".
- README documents it.

Tried it in `gleam shell` for 1, 0 and 3.
