import re


SKIP_WORDS = {
    "hi", "hello", "hey", "hiya", "howdy", "yo",
    "i", "my", "the", "a", "an", "to", "for", "in", "on", "at", "is", "am", "it", "me", "i'm",
    "ok", "okay", "yes", "yeah", "yep", "sure", "right", "correct",
    "no", "nope", "nah", "not", "don't", "dont",
}


def extract_name(text: str) -> str | None:
    STOP_WORDS = {
        "and", "my", "number", "is", "phone", "cell", "email", "at", "with", 
        "for", "to", "from", "of", "the", "a", "an", "here", "there", "i", 
        "i'm", "am", "was", "were", "be", "been", "have", "has", "had", 
        "do", "does", "did", "please", "thanks", "thank", "but", "or", "so"
    }

    cleaned_text = text
    for prefix in ["actually", "my correct name is", "my name is"]:
        if cleaned_text.lower().startswith(prefix):
            cleaned_text = cleaned_text[len(prefix):].strip()
            if cleaned_text.lower().startswith("is"):
                cleaned_text = cleaned_text[2:].strip()
    
    patterns = [
        r"my name is ([A-Za-z][a-z]+(?:\s+[A-Za-z][a-z]+)*)",
        r"i'm ([A-Za-z][a-z]+(?:\s+[A-Za-z][a-z]+)*)",
        r"i am ([A-Za-z][a-z]+(?:\s+[A-Za-z][a-z]+)*)",
        r"this is ([A-Za-z][a-z]+(?:\s+[A-Za-z][a-z]+)*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            name_words = name.split()
            valid_words = []
            for word in name_words:
                cleaned_word = word.lower().strip(",.!?")
                if cleaned_word in STOP_WORDS or cleaned_word in SKIP_WORDS:
                    break
                valid_word = re.sub(r"[^A-Za-z]", "", word)
                if valid_word:
                    valid_words.append(word)
            if valid_words:
                name = " ".join(valid_words)
            if name.lower() not in SKIP_WORDS:
                return name
    
    if len(text.strip().split()) <= 4:
        return extract_name_simple(text)
    
    return None


def extract_name_simple(text: str) -> str | None:
    words = text.strip().split()
    if len(words) > 3:
        return None
    for i, w in enumerate(words):
        cleaned = w.strip(",;.!")
        if cleaned and cleaned.lower() not in SKIP_WORDS:
            if i + 1 < len(words):
                return f"{cleaned.title()} {words[i+1].strip(',;.!').title()}"
            return cleaned.title()
    return None


def extract_phone(text: str) -> str | None:
    digits = re.sub(r"\D", "", text)
    if 7 <= len(digits) <= 15:
        return digits
    patterns = [
        r"(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})",
        r"(\+?\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def extract_reason(text: str) -> str | None:
    cleaned = text.lower()
    patterns = [
        r"(?:because|for|reason is|have|having|need|needed|experiencing|feeling|feel)\s+(.+?)(?:\.|,|$)",
        r"(?:want|wanted|would like)\s+(?:to\s+)?(.+?)(?:\.|,|$)",
        r"(.+?)(?:\s+(?:so i want|so i need|because|due to))",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            reason = match.group(1).strip()
            if reason and len(reason) > 2:
                return reason


def is_affirmative(text: str) -> bool:
    affirmative = {"yes", "yeah", "yep", "sure", "correct", "right", "confirm", "book it", "that's right", "please do", "okay", "ok", "that works", "go ahead", "sounds good", "perfect", "great", "yes please", "alright"}
    text_lower = text.lower().strip().rstrip(".!,")
    return text_lower in affirmative or any(text_lower.startswith(w) for w in {"yes ", "yeah ", "yep ", "sure ", "correct ", "ok ", "okay ", "alright ", "that works", "go ahead", "sounds good", "perfect", "great", "yes please"})


def is_negative(text: str) -> bool:
    negative = {"no", "nope", "nah", "not", "don't", "dont"}
    text_lower = text.lower().strip().rstrip(".!,")
    return text_lower in negative or any(text_lower.startswith(w) for w in {"no", "nope", "nah"})


# ─── Field-answer guard helpers (used by engine.py, NOT by extraction funcs) ──

_GENERIC_CONFIRMATIONS = {
    "yes", "yeah", "yep", "sure", "ok", "okay", "right", "correct",
    "no", "nope", "nah", "not", "don't", "dont", "naw", "yup",
}

_WORKFLOW_INTENT_WORDS = {
    "book", "booking", "schedule", "scheduling", "appointment",
    "cancel", "cancellation", "cancelled", "reschedule", "rescheduling",
}


def is_plausible_name(text: str) -> bool:
    """Reject generic responses and intent statements as names. Used by engine.py."""
    lower = text.strip().lower().rstrip(".!?,")
    if not lower or len(lower) < 2:
        return False
    if lower in _GENERIC_CONFIRMATIONS:
        return False
    words = lower.split()
    if len(words) <= 3 and all(w in _GENERIC_CONFIRMATIONS or w in {"i", "am", "im", "i'm", "want", "need"} for w in words):
        return False
    if any(kw in lower for kw in _WORKFLOW_INTENT_WORDS):
        return False
    if re.search(r"\b(i['m\s]*am\s|i'm\s+|i\s+want\s+|i\s+need\s+|i['m\s]*here\s+to)", lower):
        return False
    return True


def is_plausible_phone(text: str) -> bool:
    """Only accept strings with enough digits to be a phone number."""
    digits = re.sub(r"\D", "", text)
    return 7 <= len(digits) <= 15


def is_plausible_reason(text: str) -> bool:
    """Reason should be free text; reject pure yes/no."""
    lower = text.strip().lower().rstrip(".!?,")
    if lower in _GENERIC_CONFIRMATIONS:
        return False
    if len(lower) < 3:
        return False
    return True


def is_plausible_slot(text: str) -> bool:
    """Slot-ish strings contain date/time indicators or are numeric selection."""
    lower = text.lower()
    # Numeric selection (e.g., "1", "2")
    if text.strip().isdigit():
        return True
    indicators = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
                    "today", "tomorrow", "next", "morning", "afternoon", "evening", "am", "pm",
                    "january", "february", "march", "april", "may", "june",
                    "july", "august", "september", "october", "november", "december",
                    ":", "at ", "/", "-"]
    return any(i in lower for i in indicators)
