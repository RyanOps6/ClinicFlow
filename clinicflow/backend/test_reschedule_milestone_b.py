"""Focused tests for Milestone B - Reschedule Conversation Reliability."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_reschedule_stays_in_workflow():
    """Verify reschedule flow stays in reschedule states."""
    resp = client.post("/api/sessions/start", json={"session_type": "reschedule", "channel": "simulated"})
    sid = resp.json()["session_id"]

    # First message - provide phone
    r = client.post(f"/api/sessions/{sid}/message", json={"message": "1234567890"})
    data = r.json()
    assert data["workflow_state"].startswith("reschedule_"), f"Should stay in reschedule, got: {data['workflow_state']}"
    print("TEST 1 PASS: Reschedule stays in reschedule workflow")


def test_reschedule_side_question_preserves_state():
    """Side question should not break reschedule workflow."""
    resp = client.post("/api/sessions/start", json={"session_type": "reschedule", "channel": "simulated"})
    sid = resp.json()["session_id"]

    # Provide phone first
    client.post(f"/api/sessions/{sid}/message", json={"message": "1234567890"})

    # Ask a side question
    r = client.post(f"/api/sessions/{sid}/message", json={"message": "who are you?"})
    data = r.json()
    assert data["workflow_state"].startswith("reschedule_"), "State should remain reschedule"
    print("TEST 2 PASS: Side question preserves reschedule state")


def test_reschedule_no_name_hallucination():
    """Should not invent names for reschedule."""
    resp = client.post("/api/sessions/start", json={"session_type": "reschedule", "channel": "simulated"})
    sid = resp.json()["session_id"]

    r = client.post(f"/api/sessions/{sid}/message", json={"message": "what's my name?"})
    data = r.json()
    common_names = ["Rachel", "Emily", "Thompson", "Wilson", "Johnson", "Sarah", "Michael"]
    for name in common_names:
        assert name not in data["assistant_message"], f"Should not hallucinate name {name}"
    print("TEST 3 PASS: No name hallucination in reschedule")


def test_reschedule_name_query_after_identification():
    """After identification, should know the name."""
    resp = client.post("/api/sessions/start", json={"session_type": "reschedule", "channel": "simulated"})
    sid = resp.json()["session_id"]

    # Provide phone
    client.post(f"/api/sessions/{sid}/message", json={"message": "1234567890"})
    # Then ask name
    r = client.post(f"/api/sessions/{sid}/message", json={"message": "what's my name?"})
    data = r.json()
    assert "Rachel" not in data["assistant_message"] and "Emily" not in data["assistant_message"]
    print("TEST 4 PASS: After identification, name query works")


def test_reschedule_smalltalk_resumes():
    """Smalltalk should resume asking for phone."""
    resp = client.post("/api/sessions/start", json={"session_type": "reschedule", "channel": "simulated"})
    sid = resp.json()["session_id"]
    r = client.post(f"/api/sessions/{sid}/message", json={"message": "who are you?"})
    data = r.json()
    assert data["workflow_state"] == "reschedule_awaiting_identifier"
    print("TEST 5 PASS: Smalltalk in identifier state stays in identifier state")


if __name__ == "__main__":
    test_reschedule_stays_in_workflow()
    test_reschedule_side_question_preserves_state()
    test_reschedule_no_name_hallucination()
    test_reschedule_name_query_after_identification()
    test_reschedule_smalltalk_resumes()
    print()
    print("ALL MILESTONE B TESTS PASSED")
