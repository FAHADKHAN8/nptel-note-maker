from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..errors import AppError
from ..models import Lecture
from ..schemas.note import NoteRead, NoteUpdate

router = APIRouter(tags=["notes"])


@router.get("/api/lectures/{lecture_id}/notes", response_model=NoteRead)
def get_notes(lecture_id: int, db: Session = Depends(get_db)):
    lecture = db.get(Lecture, lecture_id)
    if not lecture or not lecture.note:
        raise AppError("RESOURCE_NOT_FOUND", "Notes not found.", 404)
    return lecture.note


@router.put("/api/lectures/{lecture_id}/notes", response_model=NoteRead)
def update_notes(lecture_id: int, payload: NoteUpdate, db: Session = Depends(get_db)):
    lecture = db.get(Lecture, lecture_id)
    if not lecture or not lecture.note:
        raise AppError("RESOURCE_NOT_FOUND", "Notes not found.", 404)
    lecture.note.content_markdown = payload.content_markdown
    lecture.note.is_user_edited = True
    db.commit()
    db.refresh(lecture.note)
    return lecture.note
