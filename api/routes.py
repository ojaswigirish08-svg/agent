import uuid
import base64
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from orchestrator.orchestrator import Orchestrator

router = APIRouter()
orchestrator: Orchestrator = None


def init_routes(orch: Orchestrator):
    global orchestrator
    orchestrator = orch


@router.post("/session/create")
async def create_session(
    resume: UploadFile = File(...),
    mode: str = Form(default="mock")
):
    try:
        file_bytes = await resume.read()

        if resume.filename.endswith(".pdf"):
            resume_text = await extract_pdf_text(file_bytes)
        else:
            resume_text = file_bytes.decode("utf-8", errors="ignore")

        candidate_id = str(uuid.uuid4())
        state = await orchestrator.create_session(
            resume_text=resume_text,
            candidate_id=candidate_id,
            mode=mode
        )

        return {
            "success": True,
            "session_id": state.session_id,
            "candidate_id": state.candidate_id,
            "domain": state.domain,
            "experience_level": state.experience_level,
            "duration_minutes": state.duration_minutes,
            "target_questions": state.target_questions,
            "mode": state.mode
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create session: {str(e)}"
        )


@router.get("/session/{session_id}/status")
async def get_session_status(session_id: str):
    state = orchestrator.get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session_id,
        "phase": state.phase,
        "turn_number": state.turn_number,
        "questions_asked": state.questions_asked,
        "interview_ended": state.interview_ended
    }


@router.post("/session/{session_id}/end")
async def end_session(session_id: str):
    state = orchestrator.get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    orchestrator.session_manager.end_session(session_id)
    return {"success": True}


async def extract_pdf_text(file_bytes: bytes) -> str:
    try:
        import pypdf
        import io
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception:
        return file_bytes.decode("utf-8", errors="ignore")