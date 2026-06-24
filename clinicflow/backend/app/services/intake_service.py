from typing import Optional

from app.schemas.intake import IntakeData


INTALK_STEPS = [
    ("awaiting_name", "What is your full name?"),
    ("awaiting_symptoms", "Can you describe your symptoms?"),
    ("awaiting_duration", "How long have you had these symptoms?"),
    ("awaiting_reason", "What is the main reason for your visit?"),
    ("awaiting_insurance", "Do you have insurance information to provide?"),
]


def get_next_step(current_step: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if current_step is None:
        return INTALK_STEPS[0]
    for i, (step, prompt) in enumerate(INTALK_STEPS):
        if step == current_step and i + 1 < len(INTALK_STEPS):
            return INTALK_STEPS[i + 1]
    return None, None


def is_intake_complete(current_step: Optional[str]) -> bool:
    return current_step == INTALK_STEPS[-1][0]
