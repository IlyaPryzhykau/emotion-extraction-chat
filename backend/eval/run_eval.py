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


def _f1(precision: float, recall: float) -> float:
    """Harmonic mean of precision and recall (0.0 when both are 0)."""
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _macro_f1(results: list[FixtureResult]) -> float:
    """Mean per-label F1 over every label seen in expected or predicted.

    Macro (unlike micro) weights each label equally, so a rare label the model
    handles badly isn't hidden by common ones — and a spuriously predicted label
    scores 0, dragging the average down.
    """
    labels = sorted({label for r in results for label in r.expected | r.predicted})
    if not labels:
        return 1.0
    scores = []
    for label in labels:
        tp = sum(label in r.predicted and label in r.expected for r in results)
        fp = sum(label in r.predicted and label not in r.expected for r in results)
        fn = sum(label in r.expected and label not in r.predicted for r in results)
        scores.append(_f1(_ratio(tp, tp + fp), _ratio(tp, tp + fn)))
    return sum(scores) / len(scores)


def main() -> None:
    """Evaluate all fixtures and print per-fixture rows plus aggregate metrics."""
    if not settings.openai_api_key:
        raise SystemExit("OPENAI_API_KEY is not set; populate backend/.env first.")

    results = [_evaluate(f) for f in _load_fixtures()]

    tp = fp = fn = grounded = total = 0
    empties = correct_empties = 0
    print(f"{'fixture':<28}{'expected':<24}{'predicted':<24}{'grounded':>9}  ok")
    print("-" * 92)
    for r in results:
        tp += len(r.predicted & r.expected)
        fp += len(r.predicted - r.expected)
        fn += len(r.expected - r.predicted)
        grounded += r.findings_grounded
        total += r.findings_total
        if not r.expected:
            empties += 1
            correct_empties += not r.predicted
        exact = "✓" if r.predicted == r.expected else "·"
        print(
            f"{r.name:<28}"
            f"{', '.join(sorted(r.expected)) or '—':<24}"
            f"{', '.join(sorted(r.predicted)) or '—':<24}"
            f"{f'{r.findings_grounded}/{r.findings_total}':>9}  {exact}"
        )

    precision, recall = _ratio(tp, tp + fp), _ratio(tp, tp + fn)
    print("-" * 92)
    print(
        f"labels  micro  P={precision:.2f}  R={recall:.2f}  F1={_f1(precision, recall):.2f}"
        f"  (tp={tp} fp={fp} fn={fn})"
    )
    print(f"labels  macro  F1={_macro_f1(results):.2f}")
    print(f"abstention     {correct_empties}/{empties} empty-expected got no findings")
    print(f"grounding      {grounded}/{total} evidence quotes verbatim in transcript")


if __name__ == "__main__":
    main()
