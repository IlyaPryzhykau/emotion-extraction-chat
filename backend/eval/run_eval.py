"""Offline evaluation of the emotion extractor against hand-written fixtures.

Run from the backend directory:

    python -m eval.run_eval

For each fixture it runs the real extractor (this is the only step that calls the
API), then reports two things:

1. **Grounding (model-free):** every finding's ``evidence`` must appear verbatim in
   one of the user's messages. This is the hard guard against hallucinated quotes —
   no model is involved in checking it.
2. **Label precision / recall:** the set of predicted labels (after the confidence
   floor, matching what the app stores) vs. the fixture's expected labels.

Fixtures are intentionally small and honest; expected labels list only emotions a
reasonable reader would clearly say are present.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.db.enums import MessageRole
from app.db.models import Message
from app.llm.extractor import EmotionFinding, extract_emotions

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@dataclass
class FixtureResult:
    """Outcome of evaluating one fixture."""

    name: str
    expected: set[str]
    predicted: set[str]
    findings_total: int
    findings_grounded: int


def _load_fixtures() -> list[dict]:
    """Load every fixture JSON, sorted by name for stable output."""
    fixtures = [json.loads(path.read_text("utf-8")) for path in sorted(FIXTURES_DIR.glob("*.json"))]
    if not fixtures:
        raise SystemExit(f"No fixtures found in {FIXTURES_DIR}")
    return fixtures


def _to_messages(transcript: list[dict]) -> list[Message]:
    """Build (unsaved) ORM messages the extractor can format — no DB needed."""
    return [
        Message(role=MessageRole(turn["role"]), content=turn["content"])
        for turn in transcript
    ]


def _is_grounded(finding: EmotionFinding, transcript: list[dict]) -> bool:
    """True if the evidence quote appears verbatim in any user message."""
    return any(
        turn["role"] == "user" and finding.evidence in turn["content"]
        for turn in transcript
    )


def _evaluate(fixture: dict) -> FixtureResult:
    """Run the extractor on one fixture and score it."""
    transcript = fixture["transcript"]
    extraction = extract_emotions(_to_messages(transcript))
    kept = [
        f for f in extraction.findings if f.confidence >= settings.extraction_min_confidence
    ]
    return FixtureResult(
        name=fixture["name"],
        expected=set(fixture["expected_labels"]),
        predicted={f.label.value for f in kept},
        findings_total=len(kept),
        findings_grounded=sum(_is_grounded(f, transcript) for f in kept),
    )


def _ratio(numerator: int, denominator: int) -> float:
    """Safe ratio: 1.0 when there's nothing to score (no errors possible)."""
    return numerator / denominator if denominator else 1.0


def main() -> None:
    """Evaluate all fixtures and print per-fixture rows plus aggregate metrics."""
    if not settings.openai_api_key:
        raise SystemExit("OPENAI_API_KEY is not set; populate backend/.env first.")

    results = [_evaluate(f) for f in _load_fixtures()]

    tp = fp = fn = grounded = total = 0
    print(f"{'fixture':<18}{'expected':<22}{'predicted':<22}{'grounded':>9}")
    print("-" * 71)
    for r in results:
        tp += len(r.predicted & r.expected)
        fp += len(r.predicted - r.expected)
        fn += len(r.expected - r.predicted)
        grounded += r.findings_grounded
        total += r.findings_total
        print(
            f"{r.name:<18}"
            f"{', '.join(sorted(r.expected)) or '—':<22}"
            f"{', '.join(sorted(r.predicted)) or '—':<22}"
            f"{f'{r.findings_grounded}/{r.findings_total}':>9}"
        )

    print("-" * 71)
    print(
        f"label precision: {_ratio(tp, tp + fp):.2f}   "
        f"recall: {_ratio(tp, tp + fn):.2f}   "
        f"(tp={tp} fp={fp} fn={fn})"
    )
    print(f"evidence grounding: {grounded}/{total} verbatim in transcript")


if __name__ == "__main__":
    main()
