from fastapi import APIRouter

router = APIRouter(prefix="/api/intake", tags=["intake"])


@router.post("/submit")
def submit_intake():
    return {"status": "not_implemented", "message": "Intake endpoint scaffolded for future use"}
