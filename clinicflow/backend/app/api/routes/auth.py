import time
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory tracking of login attempts
# key: username (lowercased)
# value: {"failed_attempts": int, "lockout_until": float}
auth_attempts = {}

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(req: LoginRequest):
    username = req.username.strip().lower()
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username cannot be empty."
        )

    now = time.time()
    
    # Initialize attempt state if not present
    if username not in auth_attempts:
        auth_attempts[username] = {"failed_attempts": 0, "lockout_until": 0.0}
        
    user_state = auth_attempts[username]
    
    # Check lockout active
    if user_state["lockout_until"] > now:
        remaining = int(user_state["lockout_until"] - now)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed attempts. Please wait {remaining}s."
        )
    
    # Check credentials
    if username == "admin" and req.password == "password123":
        # Reset attempts on success
        auth_attempts[username] = {"failed_attempts": 0, "lockout_until": 0.0}
        return {
            "token": "mock-token-12345",
            "username": "admin"
        }
    else:
        # Increment failed count
        failed = user_state["failed_attempts"] + 1
        lockout_until = 0.0
        
        if failed >= 4:
            lockout_until = now + 30.0
            auth_attempts[username] = {"failed_attempts": failed, "lockout_until": lockout_until}
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed attempts. Please wait 30s."
            )
        else:
            auth_attempts[username] = {"failed_attempts": failed, "lockout_until": lockout_until}
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid username or password. ({failed}/4 attempts)"
            )
