"""FieldMemory: Safe field merging with conflict detection for clinic conversations.

Rules:
  A — Empty fields can be filled.
  B — Confirmed fields cannot be silently overwritten.
  C — Explicit corrections may update the field after a short confirmation.
  D — Never infer a name from symptom text (e.g. "I feel sick" -> NOT "Mr. Sik").
"""

from typing import Optional, Any
from app.schemas.session import ExtractionResult, CorrectionSignals, ProposedUpdates
from app.services import session_store as store

PROTECTED_FIELDS: set = {"full_name", "phone"}


class FieldMemory:
    """Manages safe merging of extracted fields into collected_data."""

    def __init__(self, collected: dict):
        self.collected = collected

    # ------------------------------------------------------------------
    # 1. SAFE MERGE (top-level entry point)
    # ------------------------------------------------------------------
    def merge_extraction(self, extraction: ExtractionResult):
        """Apply extraction with safe semantics (Rules A & B)."""
        if extraction.full_name:
            self._safe_set("full_name", extraction.full_name)
        if extraction.phone:
            self._safe_set("phone", extraction.phone)
        if extraction.reason_for_visit:
            self._safe_set("reason_for_visit", extraction.reason_for_visit)
        if extraction.reason_for_cancellation:
            self._safe_set("reason_for_cancellation", extraction.reason_for_cancellation)
        if extraction.preferred_slot_or_date:
            self._safe_set("preferred_slot_or_date", extraction.preferred_slot_or_date)
        if extraction.doctor_name:
            self._safe_set("doctor_name", extraction.doctor_name)
        if extraction.insurance_provider:
            self._safe_set("insurance_provider", extraction.insurance_provider)
        if extraction.notes:
            self._safe_set("notes", extraction.notes)
        if extraction.appointment_identifier:
            self._safe_set("appointment_identifier", extraction.appointment_identifier)

        if extraction.symptoms:
            existing = self.collected.get("symptoms", [])
            updated = list(set(existing + extraction.symptoms))
            self.collected["symptoms"] = updated

        # Handle intent at session level
        if extraction.intent:
            pass  # handled in caller, not here

    def _safe_set(self, field: str, value: Any):
        """Set a field safely. Protected fields only update if empty or explicitly corrected."""
        if field not in PROTECTED_FIELDS:
            self.collected[field] = value
            return

        old = self.collected.get(field)
        if not old:
            # Rule A: empty field -> fill
            self.collected[field] = value
            # Mark as tentative until confirmed
            self.collected[f"{field}_confirmed"] = False
        elif old != value:
            # Rule B: conflicting value -> flag for clarification
            self.collected[f"pending_{field}_conflict"] = True
            self.collected[f"proposed_{field}"] = value

    # ------------------------------------------------------------------
    # 2. CORRECTION HANDLING (Rule C)
    # ------------------------------------------------------------------
    def apply_correction(self, extraction: ExtractionResult):
        """If the user is explicitly correcting a field, update it."""
        cs = extraction.correction_signals if extraction.correction_signals else None
        updates = extraction.proposed_updates if extraction.proposed_updates else None

        if cs:
            if getattr(cs, "name_correction", False) and updates and getattr(updates, "full_name", None):
                self.collected["full_name"] = updates.full_name
                self.collected["full_name_confirmed"] = True
                self._clear_conflict("full_name")
            if getattr(cs, "phone_correction", False) and updates and getattr(updates, "phone", None):
                self.collected["phone"] = updates.phone
                self.collected["phone_confirmed"] = True
                self._clear_conflict("phone")

        # Also handle simple "proposed_updates" if explicit
        if extraction.full_name and self.collected.get("pending_full_name_conflict"):
            # If there was a conflict and the user now reaffirms, take it
            if self._is_explicit_correction_signal(extraction.full_name):
                self.collected["full_name"] = extraction.full_name
                self.collected["full_name_confirmed"] = True
                self._clear_conflict("full_name")
        if extraction.phone and self.collected.get("pending_phone_conflict"):
            if self._is_explicit_correction_signal(extraction.phone):
                self.collected["phone"] = extraction.phone
                self.collected["phone_confirmed"] = True
                self._clear_conflict("phone")

    def _clear_conflict(self, field: str):
        self.collected.pop(f"pending_{field}_conflict", None)
        self.collected.pop(f"proposed_{field}", None)

    # ------------------------------------------------------------------
    # 3. RESOLVE CONFLICTS / PROPOSED UPDATES (part of merge_extraction)
    # ------------------------------------------------------------------
    def resolve_conflict(self, field: str, accept: bool) -> bool:
        """User accepts or rejects a proposed update for a protected field."""
        if not self.collected.get(f"pending_{field}_conflict"):
            return False
        if accept:
            proposed = self.collected.get(f"proposed_{field}")
            if proposed:
                self.collected[field] = proposed
        self._clear_conflict(field)
        return True

    # ------------------------------------------------------------------
    # 4. CONFIRMATION
    # ------------------------------------------------------------------
    def confirm_field(self, field: str):
        """Mark a field as confirmed (e.g. after the assistant uses it naturally)."""
        self.collected[f"{field}_confirmed"] = True

    # ------------------------------------------------------------------
    # 5. UTILITY HELPERS
    # ------------------------------------------------------------------
    def has_conflict(self, field: str) -> bool:
        return bool(self.collected.get(f"pending_{field}_conflict"))

    def get_conflicts(self) -> list[str]:
        return list(self.collected.get("possible_conflicts", []))

    @staticmethod
    def _is_explicit_correction_signal(text: str) -> bool:
        """Heuristic: is the user explicitly correcting their own information?"""
        if not text:
            return False
        lower = text.lower()
        corr_phrases = [
            "sorry", "actually", "i mean", "that number is wrong",
            "use this number", "my correct", "wrong", "instead",
            "i meant", "not ", "i'm sorry"
        ]
        return any(p in lower for p in corr_phrases)
