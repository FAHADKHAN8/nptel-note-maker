from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..config import get_settings
from ..database import get_db
from ..errors import AppError
from ..models import Lecture
from ..schemas.lecture import LectureRead
from ..schemas.note import NoteGenerationOptions, NoteRead
from ..schemas.transcript import TranscriptRead
from ..services.notes_service import NotesPipeline

router = APIRouter(tags=["lectures"])


def _lecture(db: Session, lecture_id: int) -> Lecture:
    lecture = db.get(Lecture, lecture_id)
    if not lecture:
        raise AppError("RESOURCE_NOT_FOUND", "Lecture not found.", 404)
    return lecture


@router.get("/api/courses/{course_id}/lectures", response_model=list[LectureRead])
def course_lectures(course_id: int, db: Session = Depends(get_db)):
    return db.query(Lecture).filter(Lecture.course_id == course_id).order_by(Lecture.week_number, Lecture.lecture_number).all()


@router.get("/api/lectures/{lecture_id}", response_model=LectureRead)
def get_lecture(lecture_id: int, db: Session = Depends(get_db)):
    return _lecture(db, lecture_id)


@router.post("/api/lectures/{lecture_id}/extract-transcript", response_model=TranscriptRead)
async def extract_transcript(lecture_id: int, db: Session = Depends(get_db)):
    return await NotesPipeline(get_settings()).extract_youtube_transcript(db, _lecture(db, lecture_id))


@router.post("/api/lectures/{lecture_id}/generate-notes", response_model=NoteRead)
async def generate_notes(lecture_id: int, options: NoteGenerationOptions = NoteGenerationOptions(), db: Session = Depends(get_db)):
    return await NotesPipeline(get_settings()).generate_notes(db, _lecture(db, lecture_id), options.model_dump())


@router.post("/api/lectures/{lecture_id}/regenerate-notes", response_model=NoteRead)
async def regenerate_notes(lecture_id: int, options: NoteGenerationOptions = NoteGenerationOptions(), db: Session = Depends(get_db)):
    return await NotesPipeline(get_settings()).generate_notes(db, _lecture(db, lecture_id), options.model_dump())
