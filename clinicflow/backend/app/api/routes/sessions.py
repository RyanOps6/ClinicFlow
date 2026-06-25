import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session as DBSession

from app.core.db import get_db
from app.schemas.session import (
    SendMessageRequest,
    SendMessageResponse,
    SessionSnapshot,
    StartSessionRequest,
    StartSessionResponse,
    MessageEntry,
)
from app.services import conversation_service as conv_svc
from app.services.session_store import get_session, get_collected_data, get_transcript, get_offered_slots

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("/start", response_model=StartSessionResponse)
def start_session(req: StartSessionRequest, db: DBSession = Depends(get_db)):
    session, greeting = conv_svc.handle_start_session(db, req.session_type, req.channel)
    return StartSessionResponse(
        session_id=session.id,
        session_uid=session.session_uid,
        assistant_message=greeting,
        workflow_state=session.workflow_state or "greeting",
        collected_data={},
    )


@router.post("/{session_id}/message", response_model=SendMessageResponse)
def send_message(session_id: int, req: SendMessageRequest, db: DBSession = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found")

    resp = conv_svc.handle_message(db, session, req.message)
    resp.session_uid = session.session_uid
    return resp


@router.get("/{session_id}", response_model=SessionSnapshot)
def get_session_detail(session_id: int, db: DBSession = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionSnapshot(
        id=session.id,
        session_uid=session.session_uid,
        session_type=session.session_type,
        channel=session.channel,
        status=session.status,
        intent=session.intent,
        workflow_state=session.workflow_state,
        collected_data=get_collected_data(session),
        transcript=get_transcript(session),
        offered_slots=get_offered_slots(session),
        selected_slot=session.selected_slot,
        summary_text=session.summary_text,
        urgency_level=session.urgency_level,
        started_at=session.started_at,
        ended_at=session.ended_at,
        created_at=session.created_at,
    )


@router.get("/{session_id}/audit-logs")
def get_session_audit_logs(session_id: int, db: DBSession = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found")

    from app.models.conversation_audit_log import ConversationAuditLog
    logs = db.query(ConversationAuditLog).filter(
        ConversationAuditLog.session_id == session.id
    ).order_by(ConversationAuditLog.created_at.asc()).all()

    return [
        {
            "id": log.id,
            "session_id": log.session_id,
            "user_text": log.user_text,
            "workflow_state_before": log.workflow_state_before,
            "llm_payload_sent": json.loads(log.llm_payload_sent) if log.llm_payload_sent else None,
            "llm_raw_response": json.loads(log.llm_raw_response) if log.llm_raw_response else None,
            "final_action": log.final_action,
            "created_at": log.created_at.isoformat() if log.created_at else None
        }
        for log in logs
    ]


@router.get("", response_model=list[SessionSnapshot])
def list_sessions(page: int = 1, limit: int = 20, db: DBSession = Depends(get_db)):
    from app.models.call_session import CallSession
    skip = (page - 1) * limit
    sessions = db.query(CallSession).order_by(CallSession.created_at.desc()).offset(skip).limit(limit).all()
    
    return [
        SessionSnapshot(
            id=s.id,
            session_uid=s.session_uid,
            session_type=s.session_type,
            channel=s.channel,
            status=s.status,
            intent=s.intent or "unknown",
            workflow_state=s.workflow_state,
            collected_data=get_collected_data(s),
            transcript=get_transcript(s),
            offered_slots=get_offered_slots(s),
            selected_slot=s.selected_slot,
            summary_text=s.summary_text,
            urgency_level=s.urgency_level,
            started_at=s.started_at,
            ended_at=s.ended_at,
            created_at=s.created_at,
        )
        for s in sessions
    ]


@router.get("/{session_id}/messages", response_model=list[MessageEntry])
def get_session_messages(session_id: int, db: DBSession = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found")
        
    transcript = get_transcript(session)
    return [
        MessageEntry(role=m.get("role", "user"), content=m.get("content", ""))
        for m in transcript
    ]


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: int, db: DBSession = Depends(get_db)):
    import os
    import base64
    from fastapi.concurrency import run_in_threadpool
    from app.services.voice_handler import process_voice_turn

    await websocket.accept()
    try:
        while True:
            # Receive user audio chunk/bytes (UTF-8 encoded text or raw audio bytes)
            audio_data = await websocket.receive_bytes()
            
            # Process the voice turn through STT -> Engine -> TTS
            result = await run_in_threadpool(process_voice_turn, db, session_id, audio_data)
            
            # Read generated audio response bytes
            audio_file_path = result["audio_file_path"]
            encoded_audio = ""
            if os.path.exists(audio_file_path):
                with open(audio_file_path, "rb") as f:
                    response_audio_bytes = f.read()
                encoded_audio = base64.b64encode(response_audio_bytes).decode("utf-8")
                
            await websocket.send_json({
                "transcription": result["transcription"],
                "assistant_response": result["assistant_response"],
                "audio": encoded_audio,
                "completed": result["completed"],
                "workflow_state": result["workflow_state"],
            })
    except WebSocketDisconnect:
        pass
    except Exception as e:
        import logging
        logging.error(f"WebSocket error in turn processing: {e}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
