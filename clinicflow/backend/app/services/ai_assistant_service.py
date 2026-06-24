from typing import Optional

from app.llm.client import llm_client
from app.llm.prompts import (
    build_analysis_prompt,
    build_response_prompt,
    build_summary_prompt,
)
from app.schemas.session import ExtractionResult, CorrectionSignals, ProposedUpdates


def _parse_extraction_result(result: dict) -> ExtractionResult:
    """Parse raw JSON into ExtractionResult with safe defaults."""
    
    if not result:
        return ExtractionResult()
    
    try:
        # Parse correction_signals
        correction = CorrectionSignals()
        cs = result.get("correction_signals", {})
        if cs:
            correction = CorrectionSignals(
                name_correction=bool(cs.get("name_correction", False)),
                phone_correction=bool(cs.get("phone_correction", False))
            )
        
        # Parse proposed_updates
        updates = ProposedUpdates()
        pu = result.get("proposed_updates", {})
        if pu:
            updates = ProposedUpdates(
                full_name=pu.get("full_name") or None,
                phone=pu.get("phone") or None
            )
        
        # Parse symptoms safely
        symptoms = result.get("symptoms", [])
        if isinstance(symptoms, list):
            symptoms = [str(s) for s in symptoms]
        else:
            symptoms = []
        
        # Parse urgency_signals
        urgency = result.get("urgency_signals", [])
        if isinstance(urgency, list):
            urgency = [str(s) for s in urgency]
        else:
            urgency = []
        
        # Parse possible_conflicts
        conflicts = result.get("possible_conflicts", [])
        if not isinstance(conflicts, list):
            conflicts = []
        
        return ExtractionResult(
            intent=str(result["intent"]) if result.get("intent") else None,
            explicit_intent_switch_requested=bool(result.get("explicit_intent_switch_requested", False)),
            full_name=str(result["full_name"]) if result.get("full_name") else None,
            phone=str(result["phone"]) if result.get("phone") else None,
            reason_for_visit=str(result["reason_for_visit"]) if result.get("reason_for_visit") else None,
            reason_for_cancellation=str(result["reason_for_cancellation"]) if result.get("reason_for_cancellation") else None,
            preferred_slot_or_date=str(result["preferred_slot_or_date"]) if result.get("preferred_slot_or_date") else None,
            doctor_name=str(result["doctor_name"]) if result.get("doctor_name") else None,
            insurance_provider=str(result["insurance_provider"]) if result.get("insurance_provider") else None,
            symptoms=symptoms,
            urgency_signals=urgency,
            confirmation=bool(result["confirmation"]) if result.get("confirmation") is not None else None,
            cancellation_requested=bool(result.get("cancellation_requested", False)),
            reschedule_requested=bool(result.get("reschedule_requested", False)),
            correction_signals=correction,
            proposed_updates=updates,
            possible_conflicts=conflicts,
            notes=str(result["notes"]) if result.get("notes") else None,
            confidence=float(result.get("confidence", 0.0)),
            appointment_identifier=str(result["appointment_identifier"]) if result.get("appointment_identifier") else None,
        )
    except (KeyError, ValueError, TypeError):
        return ExtractionResult()


def analyze_message(message: str, session_context: dict) -> Optional[ExtractionResult]:
    if not llm_client.available:
        return None

    messages = build_analysis_prompt(message, session_context)
    result = llm_client.extract_json(messages)

    if not result:
        return None

    res_obj = _parse_extraction_result(result)
    if res_obj:
        import json
        res_obj.llm_payload_sent = json.dumps(messages)
        res_obj.llm_raw_response = json.dumps(result)
    return res_obj


def generate_response(workflow_context: dict) -> Optional[str]:
    if not llm_client.available:
        return None

    messages = build_response_prompt(workflow_context)
    return llm_client.chat(messages, max_tokens=256)


def generate_summary(session_data: dict) -> Optional[str]:
    if not llm_client.available:
        return None

    messages = build_summary_prompt(session_data)
    return llm_client.chat(messages, max_tokens=512)
