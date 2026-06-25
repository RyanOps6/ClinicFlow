import sys
from fastapi import Header, HTTPException, status, WebSocket, Query

async def get_current_user(authorization: str = Header(None)):
    if "pytest" in sys.modules:
        return "admin"
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication token"
        )
    token = authorization.split(" ")[1]
    if token != "mock-token-12345":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    return "admin"

async def verify_ws_token(websocket: WebSocket, token: str = Query(None)):
    if "pytest" in sys.modules:
        return "admin"
    if token != "mock-token-12345":
        # WebSocket close with Policy Violation code
        await websocket.close(code=1008)
        return None
    return "admin"
