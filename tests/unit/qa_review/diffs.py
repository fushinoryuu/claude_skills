"""Build small git diffs for the qa-review script tests."""


def make_diff(path, added=(), removed=(), before=(), after=(), new=False, deleted=False):
    """A one-hunk git diff for one file: unchanged lines before, removed lines, added lines, unchanged lines after."""
    old_count = len(before) + len(removed) + len(after)
    new_count = len(before) + len(added) + len(after)
    lines = [f"diff --git a/{path} b/{path}"]
    if new:
        lines.append("new file mode 100644")
    if deleted:
        lines.append("deleted file mode 100644")
    lines += [f"--- {'/dev/null' if new else 'a/' + path}", f"+++ {'/dev/null' if deleted else 'b/' + path}"]
    lines.append(f"@@ -{0 if new else 10},{old_count} +{0 if deleted else 10},{new_count} @@")
    lines += [f" {x}" for x in before] + [f"-{x}" for x in removed] + [f"+{x}" for x in added] + [f" {x}" for x in after]
    return "\n".join(lines) + "\n"
