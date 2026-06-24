import os
import time
import logging
from typing import Optional
from sqlalchemy.orm import Session as DBSession

from app.models.call_session import CallSession
from app.services import conversation_service as conv_svc
from app.services.session_store import get_session

logger = logging.getLogger(__name__)

def transcribe_audio(audio_chunk: bytes) -> str:
    """
    Mock speech-to-text transcription.
    If the bytes can be decoded as UTF-8, use that text (facilitates easy simulation/testing).
    Otherwise, default to a standard clinic inquiry.
    """
    try:
        decoded = audio_chunk.decode("utf-8")
        if decoded:
            return decoded
    except Exception:
        pass
    return "Hello, I want to book an appointment"

def synthesize_text_to_speech(text: str, output_path: str) -> float:
    """
    Convert text to speech and save as a .wav file using pyttsx3.
    Measures the duration of the synthesis and returns it in seconds.
    """
    import pyttsx3
    
    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
        
    start_time = time.time()
    
    # Initialize engine locally per call to avoid threading issues
    engine = pyttsx3.init()
    try:
        engine.save_to_file(text, output_path)
        engine.runAndWait()
    finally:
        try:
            engine.stop()
        except Exception:
            pass
            
    elapsed_time = time.time() - start_time
    return elapsed_time

def process_voice_turn(db: DBSession, session_id: int, audio_chunk: bytes) -> dict:
    """
    Processes a voice conversation turn.
    1. Transcribes the simulated user audio chunk to text.
    2. Feeds the text response to conversation_service.handle_message.
    3. Synthesizes the assistant response to a wav audio file.
    4. Measures/reports pipeline performance metrics.
    """
    session = get_session(db, session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")
        
    # STT Phase
    user_text = transcribe_audio(audio_chunk)
    
    # Conversation Engine Phase
    engine_start = time.time()
    resp = conv_svc.handle_message(db, session, user_text)
    engine_duration = time.time() - engine_start
    
    # TTS Phase
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # backend/
    replies_dir = os.path.join(base_dir, "voice_replies")
    audio_filename = f"reply_{session_id}_{int(time.time() * 1000)}.wav"
    audio_path = os.path.join(replies_dir, audio_filename)
    
    tts_duration = synthesize_text_to_speech(resp.assistant_message, audio_path)
    
    total_duration = engine_duration + tts_duration
    
    return {
        "transcription": user_text,
        "assistant_response": resp.assistant_message,
        "engine_duration_seconds": engine_duration,
        "tts_duration_seconds": tts_duration,
        "total_duration_seconds": total_duration,
        "audio_file_path": audio_path,
        "workflow_state": resp.workflow_state,
        "completed": resp.completed,
    }
