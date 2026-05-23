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
    EmotionLabel.SADNESS: (
        "low mood, sorrow, or grief about a loss or how things are; passive, not "
        "goal-blocked (vs disappointment, which is a specific unmet expectation)"
    ),
    EmotionLabel.ANXIETY: (
        "worry or unease about an uncertain or anticipated future; diffuse, with no "
        "single resolvable obstacle (vs fear: no concrete present threat; vs stress: "
        "about uncertainty, not current workload)"
    ),
    EmotionLabel.ANGER: (
        "hostility or indignation toward a person or situation seen as unfair or "
        "wrong; involves blame (vs frustration, which is impersonal blockage)"
    ),
    EmotionLabel.FRUSTRATION: (
        "annoyance at being blocked, delayed, or things repeatedly not working; an "
        "obstructed goal with no clear wrongdoer to blame"
    ),
    EmotionLabel.FEAR: (
        "dread of a specific, identifiable, present or imminent threat (reserve for "
        "concrete threats; default diffuse worry to anxiety)"
    ),
    EmotionLabel.GUILT: (
        "distress over a specific act they believe was wrong or caused harm — "
        "'I did a bad thing'"
    ),
    EmotionLabel.SHAME: (
        "feeling the self is inadequate, flawed, or exposed — 'I am bad / not good "
        "enough'; about identity, not a single act"
    ),
    EmotionLabel.LONELINESS: (
        "feeling disconnected, isolated, unsupported, or that no one understands them"
    ),
    EmotionLabel.DISAPPOINTMENT: (
        "a specific hope, expectation, or outcome went unmet; being let down by an "
        "event, person, or oneself"
    ),
    EmotionLabel.STRESS: (
        "feeling under pressure or stretched thin — current demands exceed capacity "
        "right now (vs anxiety, which is about future uncertainty)"
    ),
}
