import os
import pytest
from app.core.db import SessionLocal
from app.services import conversation_service as conv_svc
from app.services.voice_handler import process_voice_turn

def test_voice_turn_happy_path():
    db = SessionLocal()
    try:
        # Start a unified session
        session, greeting = conv_svc.handle_start_session(db, "unified", "voice")
        assert session.id is not None
        assert greeting is not None
        
        # Turn 1: User says name
        audio_chunk = b"My name is Alice Smith"
        result = process_voice_turn(db, session.id, audio_chunk)
        
        # Verify result content
        assert result["transcription"] == "My name is Alice Smith"
        assert result["assistant_response"] is not None
        assert "engine_duration_seconds" in result
        assert "tts_duration_seconds" in result
        assert "total_duration_seconds" in result
        
        # Verify file creation
        audio_path = result["audio_file_path"]
        assert audio_path.endswith(".wav")
        assert os.path.exists(audio_path)
        assert os.path.getsize(audio_path) > 0
        
        # Verify performance metrics: local TTS should be fast (< 3s), total pipeline (with LLM API) should be reasonable (< 10s)
        assert result["tts_duration_seconds"] < 3.0
        assert result["total_duration_seconds"] < 10.0
        
        # Clean up audio file
        if os.path.exists(audio_path):
            os.remove(audio_path)
    finally:
        db.close()

def test_voice_turn_default_mock_speech():
    db = SessionLocal()
    try:
        session, _ = conv_svc.handle_start_session(db, "unified", "voice")
        
        # If we pass random non-UTF8 bytes, it should default transcription
        audio_chunk = b"\x80\x81\x82" # invalid UTF-8
        result = process_voice_turn(db, session.id, audio_chunk)
        
        assert result["transcription"] == "Hello, I want to book an appointment"
        
        # Clean up
        audio_path = result["audio_file_path"]
        if os.path.exists(audio_path):
            os.remove(audio_path)
    finally:
        db.close()
