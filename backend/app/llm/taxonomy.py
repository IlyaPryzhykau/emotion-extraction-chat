"""The fixed negative-emotion taxonomy.

The brief states there is no single "right" definition of a negative emotion, so
we commit to a closed set of ten labels. A closed set is *evaluable*
(precision/recall against fixtures) and defensible, where open-ended labels are
neither. See ASSUMPTIONS.md.

This module is the single source of truth for the label set; the extractor
validates against it, and the frontend mirrors it.
"""

from enum import Enum


class EmotionLabel(str, Enum):
    """A negative emotion the system is allowed to report.

    Inherits from ``str`` so values serialize directly to JSON and compare to
    plain strings coming back from the model.
    """

    SADNESS = "sadness"
    ANXIETY = "anxiety"
    ANGER = "anger"
    FRUSTRATION = "frustration"
    FEAR = "fear"
    GUILT = "guilt"
    SHAME = "shame"
    LONELINESS = "loneliness"
    DISAPPOINTMENT = "disappointment"
    STRESS = "stress/overwhelm"


class Intensity(str, Enum):
    """Coarse intensity of a finding.

    Three buckets, not a 0-10 scale: an LLM cannot calibrate a fine numeric scale
    reliably, and coarse buckets are honest about that granularity.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Human-readable, conversation-grounded hints for the model. These describe how an
# emotion typically surfaces when someone talks about their day; they are guidance
# for the *analyst*, never shown to the conversationalist.
LABEL_DESCRIPTIONS: dict[EmotionLabel, str] = {
    EmotionLabel.SADNESS: "low mood, grief, feeling down or tearful",
    EmotionLabel.ANXIETY: "worry about the future, nervousness, unease, racing thoughts",
    EmotionLabel.ANGER: "irritation or hostility directed at someone or something",
    EmotionLabel.FRUSTRATION: "being blocked, things not working, repeated annoyance",
    EmotionLabel.FEAR: "acute threat or dread about a specific thing",
    EmotionLabel.GUILT: "feeling responsible for harm or a wrongdoing",
    EmotionLabel.SHAME: "feeling bad about oneself, inadequacy, embarrassment",
    EmotionLabel.LONELINESS: "feeling disconnected, isolated, or unsupported",
    EmotionLabel.DISAPPOINTMENT: "unmet expectations, being let down",
    EmotionLabel.STRESS: "feeling overwhelmed, under pressure, stretched too thin",
}
