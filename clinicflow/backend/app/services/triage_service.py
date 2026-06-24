from app.core.constants import UrgencyLevel


URGENT_KEYWORDS = [
    "chest pain",
    "chest discomfort",
    "trouble breathing",
    "shortness of breath",
    "difficulty breathing",
    "severe bleeding",
    "uncontrolled bleeding",
    "fainting",
    "passed out",
    "lost consciousness",
    "stroke",
    "sudden weakness",
    "slurred speech",
    "face drooping",
    "severe allergic reaction",
    "anaphylaxis",
    "cannot breathe",
    "can't breathe",
    "heart attack",
    "severe head injury",
]

MEDIUM_KEYWORDS = [
    "high fever",
    "persistent vomiting",
    "dehydrated",
    "severe pain",
    "broken bone",
    "fracture",
    "deep cut",
    "burn",
]


def evaluate_urgency(text: str) -> tuple[UrgencyLevel, list[str]]:
    text_lower = text.lower()
    found_signals = []

    for keyword in URGENT_KEYWORDS:
        if keyword in text_lower:
            found_signals.append(keyword)

    if found_signals:
        return UrgencyLevel.HIGH, found_signals

    for keyword in MEDIUM_KEYWORDS:
        if keyword in text_lower:
            found_signals.append(keyword)

    if found_signals:
        return UrgencyLevel.MEDIUM, found_signals

    return UrgencyLevel.NONE, []
