"""Trigger tests: would the model pick this skill from its name and description alone?"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import yaml

from evals.runner.client import FatalModelError, ModelClient, ModelError
from evals.runner.loader import EvalConfigError
from evals.runner.skills import SkillInfo, load_catalog

ROUTER_PREAMBLE = """\
You are the skill router for an agent. Below are the available skills, each with a name and a description. Given the user's message, decide which skill, if any, the agent should load to handle it. Pick a skill only when its description clearly covers the request; otherwise answer none."""

ROUTER_FORMAT = """\
You may think briefly. Then give your decision alone on the final line: the exact skill name, or none."""


@dataclass(frozen=True)
class TriggerPrompt:
    text: str
    should_trigger: bool


@dataclass(frozen=True)
class TriggerRecord:
    correct: bool
    picked: str | None = None
    error: str | None = None
    output: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class PromptResult:
    prompt: TriggerPrompt
    runs: tuple[TriggerRecord, ...]
    pass_rate: float
    passed: bool


@dataclass(frozen=True)
class TriggerRun:
    skill: str
    skill_name: str
    prompts: list[PromptResult]

    def _records(self, should_trigger: bool | None = None):
        return [
            r
            for p in self.prompts
            if should_trigger is None or p.prompt.should_trigger == should_trigger
            for r in p.runs
        ]

    @property
    def accuracy(self) -> float:
        records = self._records()
        return sum(r.correct for r in records) / len(records)

    @property
    def trigger_recall(self) -> float | None:
        """Of the prompts that should trigger the skill, how often it was picked."""
        records = self._records(True)
        return sum(r.picked == self.skill_name for r in records) / len(records) if records else None

    @property
    def false_trigger_rate(self) -> float | None:
        """Of the prompts that should not trigger the skill, how often it was picked anyway."""
        records = self._records(False)
        return sum(r.picked == self.skill_name for r in records) / len(records) if records else None

    @property
    def passed(self) -> bool:
        return all(p.passed for p in self.prompts)

    @property
    def input_tokens(self) -> int:
        return sum(r.input_tokens for r in self._records())

    @property
    def output_tokens(self) -> int:
        return sum(r.output_tokens for r in self._records())


def load_triggers(evals_dir: Path, skill: str) -> list[TriggerPrompt]:
    path = evals_dir / skill / "triggers.yaml"
    if not path.is_file():
        raise EvalConfigError(f"missing {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise EvalConfigError(f"{path}: invalid YAML: {e}") from e
    if not isinstance(data, dict):
        raise EvalConfigError(f"{path}: expected a mapping with should_trigger and should_not_trigger")

    prompts = []
    for key, should_trigger in (("should_trigger", True), ("should_not_trigger", False)):
        items = data.get(key)
        if not isinstance(items, list) or not all(isinstance(i, str) and i.strip() for i in items):
            raise EvalConfigError(f"{path}: '{key}' must be a list of non-empty strings")
        prompts += [TriggerPrompt(i, should_trigger) for i in items]
    if not prompts:
        raise EvalConfigError(f"{path}: no trigger prompts")
    return prompts


def build_router_prompt(catalog: list[SkillInfo]) -> str:
    skills = "\n".join(f'<skill name="{s.name}">{s.description}</skill>' for s in catalog)
    return f"{ROUTER_PREAMBLE}\n\n<skills>\n{skills}\n</skills>\n\n{ROUTER_FORMAT}"


class PickError(Exception):
    """The router's answer did not name a skill or 'none'."""


def parse_pick(text: str, names: list[str]) -> str | None:
    """The skill named on the last non-empty line, or None for 'none'."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise PickError("empty answer")
    answer = lines[-1].strip("`*\"'. ").lower().removeprefix("skill:").strip("`*\"'. ")
    if answer == "none":
        return None
    by_lower = {n.lower(): n for n in names}
    if answer in by_lower:
        return by_lower[answer]
    raise PickError(f"unrecognized answer: {lines[-1][:80]!r}")


def _route(system: str, prompt: TriggerPrompt, names: list[str], skill_name: str, client: ModelClient):
    """One routing call. Returns a TriggerRecord; fatal errors propagate."""
    try:
        completion = client.complete(system, prompt.text)
    except FatalModelError:
        raise
    except ModelError as e:
        return TriggerRecord(correct=False, error=str(e))

    usage = {"input_tokens": completion.input_tokens, "output_tokens": completion.output_tokens}
    if completion.stop_reason in ("refusal", "max_tokens"):
        return TriggerRecord(correct=False, error=completion.stop_reason, output=completion.text, **usage)
    try:
        picked = parse_pick(completion.text, names)
    except PickError as e:
        return TriggerRecord(correct=False, error=f"parse_error: {e}", output=completion.text, **usage)
    correct = (picked == skill_name) == prompt.should_trigger
    return TriggerRecord(correct=correct, picked=picked, output=completion.text, **usage)


def prepare_triggers(skills_dir: Path, evals_dir: Path, skill: str):
    """Load everything a trigger run needs. Raises EvalConfigError before any model call."""
    catalog = load_catalog(skills_dir)
    under_test = next((s for s in catalog if s.folder == skill), None)
    if under_test is None:
        raise EvalConfigError(f"skill '{skill}' not found in {skills_dir}")
    return catalog, under_test, load_triggers(evals_dir, skill)


def run_triggers(
    skill: str,
    *,
    skills_dir: Path,
    evals_dir: Path,
    client: ModelClient,
    runs: int = 1,
    threshold: float = 0.5,
    progress: Callable[[str], None] = lambda _: None,
) -> TriggerRun:
    catalog, under_test, prompts = prepare_triggers(skills_dir, evals_dir, skill)
    system = build_router_prompt(catalog)
    names = [s.name for s in catalog]

    results = []
    for prompt in prompts:
        records = [_route(system, prompt, names, under_test.name, client) for _ in range(runs)]
        pass_rate = sum(r.correct for r in records) / runs
        results.append(PromptResult(prompt, tuple(records), pass_rate, pass_rate > threshold))
        progress(f"{'trigger' if prompt.should_trigger else 'skip':7} {prompt.text[:60]!r}: {pass_rate:.0%}")
    return TriggerRun(skill, under_test.name, results)
