"""The emotion extractor — the analyst pass.

Reads a full conversation transcript and returns structured negative-emotion
findings using the strong model's structured-output mode. This is the only place
that reasons about emotions; it is entirely separate from the conversationalist.

Each finding carries a verbatim ``evidence`` quote as its grounding; the analysis
flow stores the model's structured output directly. (The eval harness separately
verifies that evidence quotes actually appear in the transcript — that quality
check lives offline, not in the write path.)
"""

from pydantic import BaseModel, Field

from app.core.config import settings
from app.db.enums import MessageRole
from app.db.models import Message
from app.llm.client import parse_structured
from app.llm.prompts import EXTRACTOR_SYSTEM
from app.llm.taxonomy import EmotionLabel, Intensity, LABEL_DESCRIPTIONS


class EmotionFinding(BaseModel):
    """One negative-emotion finding from the analyst (pre-grounding)."""

    label: EmotionLabel
    intensity: Intensity
    trigger: str = Field(description="Short phrase: what the emotion is about.")
    evidence: str = Field(description="Verbatim quote from one of the user's messages.")
    confidence: float = Field(ge=0.0, le=1.0)


class EmotionExtraction(BaseModel):
    """The analyst's structured output: zero or more findings."""

    findings: list[EmotionFinding]


def _taxonomy_block() -> str:
    """Render the taxonomy as 'label: description' lines for the prompt."""
    return "\n".join(
        f"- {label.value}: {LABEL_DESCRIPTIONS[label]}" for label in EmotionLabel
    )


def _format_transcript(messages: list[Message]) -> str:
    """Render the raw transcript; the analyst sees who said what."""
    speaker = {MessageRole.USER: "User", MessageRole.ASSISTANT: "Companion"}
    return "\n".join(f"{speaker[m.role]}: {m.content}" for m in messages)


def extract_emotions(messages: list[Message]) -> EmotionExtraction:
    """Run the analyst pass over a transcript and return structured findings."""
    system = f"{EXTRACTOR_SYSTEM}{_taxonomy_block()}"
    transcript = _format_transcript(messages)
    return parse_structured(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Transcript:\n{transcript}"},
        ],
        response_format=EmotionExtraction,
        model=settings.extraction_model,
    )
