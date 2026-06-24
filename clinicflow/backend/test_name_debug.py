from app.utils import text_helpers
from app.services.engine import _is_plausible_name, _SKIP_WORDS

msg = "My name is Alice Smith"
stripped = msg.strip()
print(f"Length: {len(stripped)}")
print(f"Has digits: {any(c.isdigit() for c in stripped)}")
name = text_helpers.extract_name(stripped)
print(f"extract_name: {name!r}")
if name:
    print(f"plausible: {_is_plausible_name(name, 'awaiting_name')}")
    print(f"skip: {name.lower() in _SKIP_WORDS}")
    alpha_ratio = sum(1 for c in name if c.isalpha() or c == ' ') / max(len(name), 1)
    print(f"alpha_ratio: {alpha_ratio}")
