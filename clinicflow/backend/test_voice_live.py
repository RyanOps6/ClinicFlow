import os
from app.core.db import SessionLocal
from app.services.voice_handler import process_voice_turn
from app.services import conversation_service as conv_svc

def run_live_voice_test():
    db = SessionLocal()
    try:
        # 1. Initialize a clean voice session
        print("--- Starting a new simulated voice session ---")
        session, greeting = conv_svc.handle_start_session(db, "unified", "voice")
        print(f"Bot Greeting: \"{greeting}\"\n")
        
        # 2. Simulate what the patient says (UTF-8 bytes)
        simulated_speech = b"My name is Aryan and I want to cancel my appointment"
        print(f"Patient Spoke: \"{simulated_speech.decode('utf-8')}\"")
        print("Processing through Speech-to-Text, State Engine, and Text-to-Speech...")
        
        # 3. Process the voice turn using your exact function
        result = process_voice_turn(db, session.id, simulated_speech)
        
        print("\nExecution Metrics Success!")
        print("=" * 60)
        print(f"Decoded Speech  : {result['transcription']}")
        print(f"Bot Text Reply : {result['assistant_response']}")
        print(f"Audio Output   : {result['audio_file_path']}")
        print("=" * 60)
        print("Latency Performance Telemetry:")
        print(f"   * State Engine Processing : {result['engine_duration_seconds']:.4f}s")
        print(f"   * Audio TTS Synthesis     : {result['tts_duration_seconds']:.4f}s")
        print(f"   * Total Loop Latency      : {result['total_duration_seconds']:.4f}s")
        print("=" * 60)
        
        # 4. Verify the file exists on your computer
        if os.path.exists(result['audio_file_path']):
            print("\nVerification complete! Play the file to hear the AI speak:")
            print(f"   {result['audio_file_path']}")
        else:
            print("\nWarning: Audio file path was returned but not found on disk.")
            
    except Exception as e:
        print(f"Test Failed: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    run_live_voice_test()
