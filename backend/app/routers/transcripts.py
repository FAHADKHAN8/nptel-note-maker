from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..errors import AppError
from ..models import Lecture
from ..schemas.transcript import TranscriptRead, TranscriptUpdate
from ..services.hashing import stable_hash

router = APIRouter(tags=["transcripts"])


@router.get("/api/lectures/{lecture_id}/transcript", response_model=TranscriptRead)
def get_transcript(lecture_id: int, db: Session = Depends(get_db)):
    lecture = db.get(Lecture, lecture_id)
    if not lecture or not lecture.transcript:
        raise AppError("TRANSCRIPT_NOT_FOUND", "Transcript not found.", 404)
    return lecture.transcript


@router.put("/api/lectures/{lecture_id}/transcript", response_model=TranscriptRead)
def update_transcript(lecture_id: int, payload: TranscriptUpdate, db: Session = Depends(get_db)):
    lecture = db.get(Lecture, lecture_id)
    if not lecture or not lecture.transcript:
        raise AppError("TRANSCRIPT_NOT_FOUND", "Transcript not found.", 404)
    lecture.transcript.cleaned_text = payload.cleaned_text
    lecture.transcript.content_hash = stable_hash(payload.cleaned_text)
    lecture.transcript.character_count = len(payload.cleaned_text)
    lecture.transcript.word_count = len(payload.cleaned_text.split())
    db.commit()
    db.refresh(lecture.transcript)
    return lecture.transcript
