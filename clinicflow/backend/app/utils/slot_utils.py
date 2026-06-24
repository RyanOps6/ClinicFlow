from datetime import datetime, timedelta
import re

SLOT_TIMES = ["09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00"]
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def generate_slots(days: int = 7) -> list:
    today = datetime.now()
    slots = []
    for day_offset in range(days):
        date = today + timedelta(days=day_offset)
        date_str = date.strftime("%Y-%m-%d")
        day_name = DAY_NAMES[date.weekday()]
        for time_str in SLOT_TIMES:
            slots.append({
                "date": date_str,
                "day": day_name,
                "time": time_str,
                "label": f"{day_name} {date_str} at {time_str}",
            })
    return slots


def format_slots_for_display(slots: list) -> list:
    return [s["label"] for s in slots]


_ORDINALS = {"first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3,
             "fourth": 4, "4th": 4, "fifth": 5, "5th": 5, "sixth": 6, "6th": 6,
             "seventh": 7, "7th": 7, "eighth": 8, "8th": 8}


def match_slot(user_input: str, offered_slots: list) -> str | None:
    user_lower = user_input.strip().lower()

    # First, try to match by index/ordinal selection
    words = user_lower.split()
    for w in words:
        clean_w = w.strip(",.!?")
        if clean_w.isdigit():
            val = int(clean_w)
            if 1 <= val <= len(offered_slots):
                # Ensure it's not a time hour
                is_hour = False
                for slot in offered_slots:
                    for part in slot.split():
                        if ":" in part:
                            hour_str = part.split(":")[0]
                            if hour_str.lstrip("0") == clean_w.lstrip("0"):
                                is_hour = True
                                break
                if not is_hour:
                    return offered_slots[val - 1]
        if clean_w in _ORDINALS:
            idx = _ORDINALS[clean_w] - 1
            if 0 <= idx < len(offered_slots):
                return offered_slots[idx]

    # Try matching by components (Day, Time, Doctor)
    candidates = []
    for slot in offered_slots:
        slot_lower = slot.lower()
        
        # Day name (if mentioned in user input)
        user_days = [d.lower() for d in DAY_NAMES if d.lower() in user_lower]
        if user_days:
            slot_day = None
            for d in DAY_NAMES:
                if d.lower() in slot_lower:
                    slot_day = d.lower()
                    break
            if slot_day not in user_days:
                continue
                
        # Doctor name (if mentioned in user input)
        user_docs = []
        if "smith" in user_lower:
            user_docs.append("smith")
        if "jones" in user_lower:
            user_docs.append("jones")
        if user_docs:
            slot_doc = None
            if "smith" in slot_lower:
                slot_doc = "smith"
            elif "jones" in slot_lower:
                slot_doc = "jones"
            if slot_doc not in user_docs:
                continue
                
        # Time string
        time_str = None
        if " at " in slot_lower:
            time_part = slot_lower.split(" at ")[-1].split(" — ")[0].strip()
            time_str = time_part
            
        if time_str:
            hour = time_str.split(":")[0].lstrip("0")
            minute = time_str.split(":")[1]
            
            if time_str in user_lower:
                candidates.append(slot)
                continue
            elif re.search(r'\b' + hour + r'\b', user_lower):
                if minute == "00":
                    candidates.append(slot)
                    continue
                elif minute in user_lower:
                    candidates.append(slot)
                    continue
        else:
            candidates.append(slot)
            
    if len(candidates) == 1:
        return candidates[0]
    elif len(candidates) > 1:
        best_match = None
        best_overlap = -1
        for c in candidates:
            c_words = set(c.lower().replace("—", "").split())
            user_words = set(user_lower.split())
            overlap = len(c_words.intersection(user_words))
            if overlap > best_overlap:
                best_overlap = overlap
                best_match = c
        return best_match

    normalized = normalize_natural_slot(user_input)
    if normalized:
        for slot in offered_slots:
            if slot.startswith(normalized):
                return slot

    return None


def _normalize_time(time_str: str) -> str | None:
    time_str = time_str.strip().lower().replace(".", "").replace(" ", "")
    match = re.match(r'(\d{1,2})(?::(\d{2}))?(am|pm)?', time_str, re.IGNORECASE)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) and match.group(2).isdigit() else 0
        ampm = match.group(3)
        if ampm:
            ampm = ampm.lower()
            if ampm.startswith('p') and hour != 12:
                hour += 12
            elif ampm.startswith('a') and hour == 12:
                hour = 0
        if minute >= 30:
            hour += 1
        hour = max(9, min(16, hour))
        return f"{hour:02d}:00"
    return None


def _parse_relative_date(date_str: str) -> str | None:
    today = datetime.now()
    lower = date_str.strip().lower()
    if lower in ("today", "tonight"):
        return today.strftime("%Y-%m-%d")
    if lower in ("tomorrow", "tmrw", "tmr"):
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    for i, day in enumerate(DAY_NAMES):
        if day.lower() in lower:
            today_idx = today.weekday()
            target_idx = i
            days_diff = (target_idx - today_idx) % 7
            if days_diff == 0:
                days_diff = 7
            return (today + timedelta(days=days_diff)).strftime("%Y-%m-%d")
    return None


def normalize_natural_slot(user_input: str) -> str | None:
    if not user_input:
        return None

    lower = user_input.strip().lower()

    time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)', lower)
    if not time_match:
        time_match = re.search(r'\b(\d{1,2})(?::\d{2})?\b', lower)

    if not time_match:
        return None

    normalized_time = _normalize_time(time_match.group(0))
    if not normalized_time:
        return None

    date_str = None
    if "tomorrow" in lower or "tmrw" in lower or "tmr" in lower:
        date_str = _parse_relative_date("tomorrow")
    elif "today" in lower or "tonight" in lower:
        date_str = _parse_relative_date("today")
    else:
        for day in DAY_NAMES:
            if day.lower() in lower:
                date_str = _parse_relative_date(day)
                break
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")

    slots = generate_slots()
    target_label = None
    for slot in slots:
        if slot["date"] == date_str and slot["time"] == normalized_time:
            target_label = slot["label"]
            break

    if not target_label:
        available_times = [s["time"] for s in slots if s["date"] == date_str]
        if available_times:
            target_hour = int(normalized_time.split(":")[0])
            closest = min(available_times, key=lambda t: abs(int(t.split(":")[0]) - target_hour))
            for slot in slots:
                if slot["date"] == date_str and slot["time"] == closest:
                    target_label = slot["label"]
                    break

    return target_label


def format_slot_for_speech(slot: str) -> str:
    """Format slot string to remove year, month, and day for better TTS conversion.
    E.g., 'Wednesday 2026-06-24 at 10:00 — Dr. Smith' -> 'Wednesday at 10:00 — Dr. Smith'
    """
    if not slot:
        return ""
    return re.sub(r'\s\d{4}-\d{2}-\d{2}\s', ' ', slot)
