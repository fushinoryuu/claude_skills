"""CLI: python -m evals.runner --skill pr-review [--case ID] [--runs N] [--triggers]"""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

from evals.runner.client import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    AnthropicClient,
    FatalModelError,
    ModelClient,
)
from evals.runner.loader import EvalConfigError
from evals.runner.report import (
    RunMeta,
    format_summary,
    format_trigger_summary,
    write_results,
    write_trigger_results,
)
from evals.runner.run import prepare, run_skill
from evals.runner.triggers import build_router_prompt, prepare_triggers, run_triggers


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m evals.runner", description="Run skill evals.")
    p.add_argument("--skill", required=True, help="skill folder name, e.g. pr-review")
    p.add_argument("--triggers", action="store_true", help="run the trigger tests (triggers.yaml) instead of the cases")
    p.add_argument("--case", help="run only this case id")
    p.add_argument("--runs", type=int, default=1, help="runs per case or trigger prompt (default 1)")
    p.add_argument("--threshold", type=float, default=0.5, help="a case or prompt passes when its pass rate is above this (default 0.5)")
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"model id (default {DEFAULT_MODEL})")
    p.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"], help="output_config effort; omitted by default")
    p.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    p.add_argument("--dry-run", action="store_true", help="print the assembled prompts and exit without calling the model")
    p.add_argument("--skills-dir", type=Path, default=Path("skills"))
    p.add_argument("--evals-dir", type=Path, default=Path("evals"))
    p.add_argument("--results-dir", type=Path, help="default: <evals-dir>/results")
    args = p.parse_args(argv)
    if args.runs < 1:
        p.error("--runs must be at least 1")
    if not 0 <= args.threshold < 1:
        p.error("--threshold must be in [0, 1)")
    if args.triggers and args.case:
        p.error("--case cannot be combined with --triggers")
    return args


def _progress(msg: str) -> None:
    print(msg, file=sys.stderr)


def _dry_run(args: argparse.Namespace) -> None:
    if args.triggers:
        catalog, _, prompts = prepare_triggers(args.skills_dir, args.evals_dir, args.skill)
        print(f"=== SYSTEM ===\n{build_router_prompt(catalog)}")
        for prompt in prompts:
            kind = "should_trigger" if prompt.should_trigger else "should_not_trigger"
            print(f"\n=== USER ({kind}) ===\n{prompt.text}")
        return
    _, cases, system, user_messages = prepare(args.skills_dir, args.evals_dir, args.skill, args.case)
    print(f"=== SYSTEM ===\n{system}")
    for case in cases:
        print(f"\n=== USER ({case.id}) ===\n{user_messages[case.id]}")


def main(argv: list[str] | None = None, client: ModelClient | None = None) -> int:
    """Exit codes: 0 everything passed, 1 something failed, 2 setup or API error."""
    load_dotenv()
    args = _parse_args(argv)
    results_dir = args.results_dir or args.evals_dir / "results"

    try:
        if args.dry_run:
            _dry_run(args)
            return 0

        client = client or AnthropicClient(args.model, args.max_tokens, args.effort)
        meta = RunMeta(args.model, args.effort, args.runs, args.threshold, datetime.now(UTC))
        common = {
            "skills_dir": args.skills_dir,
            "evals_dir": args.evals_dir,
            "client": client,
            "runs": args.runs,
            "threshold": args.threshold,
            "progress": _progress,
        }
        if args.triggers:
            result = run_triggers(args.skill, **common)
            summary, path = format_trigger_summary(result, meta), write_trigger_results(result, meta, results_dir)
        else:
            result = run_skill(args.skill, case_id=args.case, **common)
            summary, path = format_summary(result, meta), write_results(result, meta, results_dir)
    except (EvalConfigError, FatalModelError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    print()
    print(summary)
    print(f"\nresults: {path}")
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
