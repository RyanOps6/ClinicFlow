"""Conversation reliability regression tests for ClinicFlow Milestone A."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_booking_name_memory():
    resp = client.post("/api/sessions/start", json={"session_type": "booking", "channel": "simulated"})
    sid = resp.json()["session_id"]

    r1 = client.post(f"/api/sessions/{sid}/message", json={"message": "I'm Aryan Sol, today I feel some head pain so I want to book an appointment"})
    data1 = r1.json()
    assert data1["collected_data"].get("full_name") == "Aryan Sol"
    assert "head pain" in (data1["collected_data"].get("reason_for_visit", "") or "")

    r2 = client.post(f"/api/sessions/{sid}/message", json={"message": "555-123-4567"})
    data2 = r2.json()
    assert data2["collected_data"].get("phone") == "5551234567"

    r3 = client.post(f"/api/sessions/{sid}/message", json={"message": "what's my name?"})
    data3 = r3.json()
    assert "Aryan Sol" in data3["assistant_message"]
    assert "Rachel" not in data3["assistant_message"]
    assert "Emily" not in data3["assistant_message"]

    print("BOOKING_NAME_MEMORY_TEST PASSED")


def test_booking_name_correction():
    resp = client.post("/api/sessions/start", json={"session_type": "booking", "channel": "simulated"})
    sid = resp.json()["session_id"]

    client.post(f"/api/sessions/{sid}/message", json={"message": "My name is Aryan Sol"})

    r = client.post(f"/api/sessions/{sid}/message", json={"message": "that's not my name"})
    data = r.json()
    assert "correct" in data["assistant_message"].lower() or "name" in data["assistant_message"].lower()

    r2 = client.post(f"/api/sessions/{sid}/message", json={"message": "My name is actually Aryan Kumar"})
    data2 = r2.json()
    assert data2["collected_data"].get("full_name") == "Aryan Kumar"

    print("BOOKING_NAME_CORRECTION_TEST PASSED")


def test_mid_flow_smalltalk_resume():
    resp = client.post("/api/sessions/start", json={"session_type": "booking", "channel": "simulated"})
    sid = resp.json()["session_id"]

    client.post(f"/api/sessions/{sid}/message", json={"message": "My name is Aryan Sol"})

    r = client.post(f"/api/sessions/{sid}/message", json={"message": "who are you?"})
    data = r.json()
    assert "receptionist" in data["assistant_message"].lower() or "assistant" in data["assistant_message"].lower()
    assert data["workflow_state"] in ["awaiting_phone", "awaiting_name"]

    print("MID_FLOW_SMALLTALK_RESUME_TEST PASSED")


def test_cancel_identity_lookup():
    resp = client.post("/api/sessions/start", json={"session_type": "cancel", "channel": "simulated"})
    sid = resp.json()["session_id"]

    r = client.post(f"/api/sessions/{sid}/message", json={"message": "1234567890"})
    data = r.json()
    assert data["workflow_state"].startswith("cancel_")
    # Should stay in cancel flow — either found appointments or couldn't find
    msg = data["assistant_message"].lower()
    assert "cancel" in msg or "found" in msg or "couldn" in msg or "no" in msg

    print("CANCEL_IDENTITY_LOOKUP_TEST PASSED")


def test_reschedule_correction():
    resp = client.post("/api/sessions/start", json={"session_type": "reschedule", "channel": "simulated"})
    sid = resp.json()["session_id"]

    r = client.post(f"/api/sessions/{sid}/message", json={"message": "1234567890"})
    data = r.json()
    assert data["workflow_state"].startswith("reschedule_")

    print("RESCHEDULE_CORRECTION_TEST PASSED")


def test_no_random_name_hallucination():
    resp = client.post("/api/sessions/start", json={"session_type": "booking", "channel": "simulated"})
    sid = resp.json()["session_id"]

    r = client.post(f"/api/sessions/{sid}/message", json={"message": "what's my name?"})
    data = r.json()
    common_names = ["Rachel", "Emily", "Thompson", "Wilson", "Johnson", "Sarah", "Michael"]
    for name in common_names:
        assert name not in data["assistant_message"], f"Should not hallucinate name {name}"

    print("NO_RANDOM_NAME_HALLUCINATION_TEST PASSED")


def test_side_question_resumes_booking():
    resp = client.post("/api/sessions/start", json={"session_type": "booking", "channel": "simulated"})
    sid = resp.json()["session_id"]

    # Provide name and phone
    client.post(f"/api/sessions/{sid}/message", json={"message": "My name is Aryan Sol"})
    client.post(f"/api/sessions/{sid}/message", json={"message": "555-123-4567"})

    # Ask a side question (should answer and resume)
    r = client.post(f"/api/sessions/{sid}/message", json={"message": "what is my name?"})
    data = r.json()
    assert "Aryan Sol" in data["assistant_message"]
    # After answering, should still ask for missing reason_for_visit
    assert "reason" in data["assistant_message"].lower() or "visit" in data["assistant_message"].lower() or data["workflow_state"] == "awaiting_reason"

    print("SIDE_QUESTION_RESUMES_TEST PASSED")


def test_ok_not_confirmation_early_state():
    resp = client.post("/api/sessions/start", json={"session_type": "booking", "channel": "simulated"})
    sid = resp.json()["session_id"]

    # In greeting state, "ok" should NOT be treated as confirmation
    r = client.post(f"/api/sessions/{sid}/message", json={"message": "ok"})
    data = r.json()
    assert data["collected_data"].get("confirmation") is not True
    # Should still be asking for name
    assert data["workflow_state"] in ["greeting", "awaiting_name"]

    print("OK_NOT_CONFIRMATION_TEST PASSED")


def test_name_query_when_no_name():
    resp = client.post("/api/sessions/start", json={"session_type": "booking", "channel": "simulated"})
    sid = resp.json()["session_id"]

    # Ask for name before providing one
    r = client.post(f"/api/sessions/{sid}/message", json={"message": "what's my name?"})
    data = r.json()
    # Should say it doesn't have the name yet
    assert "don't" in data["assistant_message"].lower() or "not" in data["assistant_message"].lower() or "yet" in data["assistant_message"].lower()
    assert "Rachel" not in data["assistant_message"]
    assert "Emily" not in data["assistant_message"]

    print("NAME_QUERY_NO_NAME_TEST PASSED")


def test_e2e_booking_flow():
    resp = client.post("/api/sessions/start", json={"session_type": "booking", "channel": "simulated"})
    sid = resp.json()["session_id"]

    client.post(f"/api/sessions/{sid}/message", json={"message": "My name is Aryan Sol"})
    client.post(f"/api/sessions/{sid}/message", json={"message": "555-123-4567"})
    client.post(f"/api/sessions/{sid}/message", json={"message": "I have a headache"})
    client.post(f"/api/sessions/{sid}/message", json={"message": "today 4:00pm"})
    r = client.post(f"/api/sessions/{sid}/message", json={"message": "yes"})
    data = r.json()
    assert data["completed"]
    assert data["appointment_id"] is not None

    print("E2E_BOOKING_FLOW_TEST PASSED")


if __name__ == "__main__":
    test_booking_name_memory()
    test_booking_name_correction()
    test_mid_flow_smalltalk_resume()
    test_cancel_identity_lookup()
    test_reschedule_correction()
    test_no_random_name_hallucination()
    test_side_question_resumes_booking()
    test_ok_not_confirmation_early_state()
    test_name_query_when_no_name()
    test_e2e_booking_flow()
    print("ALL TESTS PASSED")
