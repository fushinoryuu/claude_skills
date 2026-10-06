"""CLI: python -m evals.runner --skill pr-review [--case ID] [--runs N]"""

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
from evals.runner.report import RunMeta, format_summary, write_results
from evals.runner.run import prepare, run_skill


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m evals.runner", description="Run skill evals.")
    p.add_argument("--skill", required=True, help="skill folder name, e.g. pr-review")
    p.add_argument("--case", help="run only this case id")
    p.add_argument("--runs", type=int, default=1, help="runs per case (default 1)")
    p.add_argument("--threshold", type=float, default=0.5, help="a case passes when its pass rate is above this (default 0.5)")
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
    return args


def main(argv: list[str] | None = None, client: ModelClient | None = None) -> int:
    """Exit codes: 0 all cases passed, 1 some failed, 2 setup or API error."""
    load_dotenv()
    args = _parse_args(argv)

    try:
        if args.dry_run:
            _, cases, system, prompts = prepare(args.skills_dir, args.evals_dir, args.skill, args.case)
            print(f"=== SYSTEM ===\n{system}")
            for case in cases:
                print(f"\n=== USER ({case.id}) ===\n{prompts[case.id]}")
            return 0

        client = client or AnthropicClient(args.model, args.max_tokens, args.effort)
        meta = RunMeta(args.model, args.effort, args.runs, args.threshold, datetime.now(UTC))
        result = run_skill(
            args.skill,
            skills_dir=args.skills_dir,
            evals_dir=args.evals_dir,
            client=client,
            case_id=args.case,
            runs=args.runs,
            threshold=args.threshold,
            progress=lambda msg: print(msg, file=sys.stderr),
        )
    except EvalConfigError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except FatalModelError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    path = write_results(result, meta, args.results_dir or args.evals_dir / "results")
    print()
    print(format_summary(result, meta))
    print(f"\nresults: {path}")
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
