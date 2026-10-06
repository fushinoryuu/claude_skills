"""Extract the structured findings block from model output."""

import json
import re

_FENCE = re.compile(r"```json[ \t]*\r?\n(.*?)```", re.DOTALL | re.IGNORECASE)


class ParseError(Exception):
    """No valid findings block in the output."""


def parse_findings(text: str) -> list[dict]:
    """Return the findings list from the last fenced json block that holds one.

    Earlier JSON in the explanation is ignored. Raises ParseError when no block
    parses to an object with a `findings` list of objects.
    """
    blocks = _FENCE.findall(text)
    if not blocks:
        raise ParseError("no fenced json block in output")
    for body in reversed(blocks):
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        findings = data.get("findings")
        if isinstance(findings, list) and all(isinstance(f, dict) for f in findings):
            return findings
    raise ParseError("no json block with a 'findings' list of objects")
