"""Print a summary table and write the results JSON."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from evals.runner.run import SkillRun


@dataclass(frozen=True)
class RunMeta:
    model: str
    effort: str | None
    runs: int
    threshold: float
    started: datetime


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}"


def format_summary(result: SkillRun, meta: RunMeta) -> str:
    rows = [("case", "pass", "recall", "unexpected", "result")]
    for c in result.cases:
        passes = sum(r.score.passed for r in c.runs)
        rows.append(
            (
                c.case.id,
                f"{passes}/{len(c.runs)}",
                f"{c.mean_recall:.2f}",
                f"{c.unexpected_runs}/{len(c.runs)}",
                "PASS" if c.passed else "FAIL",
            )
        )
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    lines = ["  ".join(cell.ljust(w) for cell, w in zip(row, widths)).rstrip() for row in rows]

    s = result.summary
    lines += [
        "",
        f"skill: {result.skill}   model: {meta.model}   runs/case: {meta.runs}   threshold: >{meta.threshold}",
        (
            f"recall: {_pct(s.recall)}   false-positive rate: {_pct(s.false_positive_rate)}"
            f"   cases passed: {s.cases_passed}/{s.cases_total}"
        ),
        f"tokens: {result.input_tokens} in, {result.output_tokens} out",
    ]
    return "\n".join(lines)


def build_payload(result: SkillRun, meta: RunMeta) -> dict:
    s = result.summary
    return {
        "skill": result.skill,
        "model": meta.model,
        "effort": meta.effort,
        "date": meta.started.isoformat(),
        "runs_per_case": meta.runs,
        "threshold": meta.threshold,
        "summary": {
            "recall": s.recall,
            "false_positive_rate": s.false_positive_rate,
            "cases_passed": s.cases_passed,
            "cases_total": s.cases_total,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
        },
        "cases": [
            {
                "id": c.case.id,
                "tags": list(c.case.tags),
                "passed": c.passed,
                "pass_rate": c.pass_rate,
                "mean_recall": c.mean_recall,
                "runs": [
                    {
                        "passed": r.score.passed,
                        "recall": r.score.recall,
                        "matched": r.score.matched,
                        "expected": r.score.expected,
                        "total": r.score.total,
                        "unexpected": r.score.unexpected,
                        "forbidden": r.score.forbidden,
                        "invalid_categories": list(r.score.invalid_categories),
                        "error": r.score.error,
                        "output": r.output,
                    }
                    for r in c.runs
                ],
            }
            for c in result.cases
        ],
    }


def write_results(result: SkillRun, meta: RunMeta, results_dir: Path) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    path = results_dir / f"{meta.started.strftime('%Y%m%dT%H%M%SZ')}-{result.skill}.json"
    path.write_text(json.dumps(build_payload(result, meta), indent=2) + "\n", encoding="utf-8")
    return path
