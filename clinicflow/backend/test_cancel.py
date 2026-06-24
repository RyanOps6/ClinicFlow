import requests
import sys

BASE = 'http://localhost:8000'


def test_cancel_yes():
    print("=== TEST 1: Successful Cancel Flow ===")
    session_resp = requests.post(f'{BASE}/api/sessions/start', json={'session_type': 'cancel', 'channel': 'simulated'})
    assert session_resp.status_code == 200, f"Start failed: {session_resp.text}"
    session = session_resp.json()
    session_id = session['session_id']
    print(f"Session ID: {session_id}")
    print(f"Initial: {session['assistant_message']}")

    # Provide phone
    msg_resp = requests.post(f'{BASE}/api/sessions/{session_id}/message', json={'message': '555-1234'})
    assert msg_resp.status_code == 200, f"Phone step failed: {msg_resp.text}"
    msg_data = msg_resp.json()
    print(f"Assistant: {msg_data['assistant_message']}")
    print(f"State: {msg_data['workflow_state']}")
    target_id = msg_data['collected_data'].get('target_appointment_id')
    print(f"Target ID: {target_id}")

    # Confirm cancel
    msg_resp = requests.post(f'{BASE}/api/sessions/{session_id}/message', json={'message': 'yes'})
    assert msg_resp.status_code == 200, f"Confirm step failed: {msg_resp.text}"
    msg_data = msg_resp.json()
    print(f"Assistant: {msg_data['assistant_message']}")
    print(f"Completed: {msg_data['completed']}")
    print(f"State: {msg_data['workflow_state']}")
    assert "cancelled" in msg_data['assistant_message'].lower(), "Expected cancellation success message"

    if target_id:
        apt_resp = requests.get(f'{BASE}/api/appointments/{target_id}')
        if apt_resp.status_code == 200:
            apt = apt_resp.json()
            print(f"Appointment status: {apt.get('status')}")
    print("TEST 1 PASSED\n")


def test_cancel_no():
    print("=== TEST 2: Decline Cancel Flow ===")
    session_resp = requests.post(f'{BASE}/api/sessions/start', json={'session_type': 'cancel', 'channel': 'simulated'})
    assert session_resp.status_code == 200
    session = session_resp.json()
    session_id = session['session_id']

    # Provide phone
    msg_resp = requests.post(f'{BASE}/api/sessions/{session_id}/message', json={'message': '555-1234'})
    assert msg_resp.status_code == 200
    msg_data = msg_resp.json()
    target_id = msg_data['collected_data'].get('target_appointment_id')

    # Decline cancel
    msg_resp = requests.post(f'{BASE}/api/sessions/{session_id}/message', json={'message': 'no'})
    assert msg_resp.status_code == 200
    msg_data = msg_resp.json()
    print(f"Assistant: {msg_data['assistant_message']}")
    print(f"Completed: {msg_data['completed']}")
    assert "remains scheduled" in msg_data['assistant_message'].lower() or "no problem" in msg_data['assistant_message'].lower(), "Expected decline message"
    assert "cancelled" not in msg_data['assistant_message'].lower(), "Should not say cancelled when declined"
    print("TEST 2 PASSED\n")


def test_ambiguous():
    print("=== TEST 3: Ambiguous Confirmation ===")
    session_resp = requests.post(f'{BASE}/api/sessions/start', json={'session_type': 'cancel', 'channel': 'simulated'})
    assert session_resp.status_code == 200
    session = session_resp.json()
    session_id = session['session_id']

    # Provide phone
    msg_resp = requests.post(f'{BASE}/api/sessions/{session_id}/message', json={'message': '555-1234'})
    assert msg_resp.status_code == 200
    msg_data = msg_resp.json()

    # Ambiguous
    msg_resp = requests.post(f'{BASE}/api/sessions/{session_id}/message', json={'message': 'maybe'})
    assert msg_resp.status_code == 200
    msg_data = msg_resp.json()
    print(f"Assistant: {msg_data['assistant_message']}")
    print(f"State: {msg_data['workflow_state']}")
    assert msg_data['workflow_state'] == 'cancel_awaiting_confirmation', "Should stay in confirmation state"
    print("TEST 3 PASSED\n")


if __name__ == "__main__":
    test_cancel_yes()
    test_cancel_no()
    test_ambiguous()
    print("ALL TESTS PASSED")
