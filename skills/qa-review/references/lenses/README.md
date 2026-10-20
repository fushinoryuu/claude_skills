# Lenses

A lens is a short, optional file of extra checks for a particular kind of change. The core checklist in `references/qa-core.md` always applies and never depends on a lens. A project with no matching lens gets the full core review.

The lenses in this folder (`service`, `api-spec`) are **examples** that show the pattern. Nothing requires them.

## Adding a lens

Drop one file in this folder. No other file needs editing.

1. Start the file with this frontmatter:

   ```yaml
   ---
   name: web-ui
   description: One line on what this lens adds beyond the core.
   applies_when:
     paths: ["**/*.tsx", "**/*.vue", "**/*.css"]
     touches: "user-facing screens or styles"
   ---
   ```

   - `paths` is a list of file globs. A lens is a candidate when a changed file matches one of them.
   - `touches` is one plain-language line describing the kind of change the lens is for. Use it to judge a lens whose paths did not match.

2. Group the checks under the same step names `SKILL.md` uses: **Step 4 (Requirements and implementation)**, **Step 5 (Test coverage)**, **Step 6 (Higher-level tests)**, and **Step 7 (Interfaces and documentation)**. Include only the steps the lens adds to.
3. Add only checks the core does not already cover, and never repeat a core item.
4. Say what evidence to look for, as the core does.

## How lenses are chosen

Lenses are chosen from what the change touches, never from a project label. Any number of lenses, including none, can apply to one review, and the report names each lens applied and why, or says "core only". The user can also name a lens, or ask for the core only.
