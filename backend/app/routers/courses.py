import asyncio
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from ..config import get_settings
from ..database import SessionLocal, get_db
from ..errors import AppError
from ..models import Course, Lecture, ProcessingJob
from ..schemas.job import JobRead
from ..schemas.course import CourseImportRequest, CourseRead, YouTubeLectureRequest
from ..services.course_processor import CourseProcessor
from ..services.nptel_scraper import GenericNptelParser
from ..utils.url_parser import extract_youtube_video_id, validate_nptel_url

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.post("/import", response_model=CourseRead)
async def import_course(payload: CourseImportRequest, db: Session = Depends(get_db)):
    safe_url = validate_nptel_url(payload.resolved_url)
    parsed = await GenericNptelParser(get_settings()).parse_course(safe_url)
    existing = db.query(Course).filter(Course.source_url == parsed.course_url).one_or_none()
    if existing:
        return existing
    course = Course(title=parsed.title, description=parsed.description, instructor=parsed.instructor, institute=parsed.institute, course_code=parsed.course_code, source_url=parsed.course_url, thumbnail_url=parsed.image_url, total_weeks=max(l.week_number for l in parsed.lectures), total_lectures=len(parsed.lectures))
    db.add(course)
    db.flush()
    for item in parsed.lectures:
        db.add(Lecture(course_id=course.id, week_number=item.week_number, lecture_number=item.lecture_number, title=item.title, nptel_url=item.nptel_url, transcript_url=item.transcript_url, youtube_url=item.youtube_url, youtube_video_id=item.youtube_video_id))
    db.commit()
    db.refresh(course)
    return course


@router.post("/youtube-prototype", response_model=CourseRead)
def youtube_prototype(payload: YouTubeLectureRequest, db: Session = Depends(get_db)):
    video_id = extract_youtube_video_id(payload.youtube_url)
    course = Course(title=payload.title, source_url=f"https://www.youtube.com/watch?v={video_id}", total_weeks=1, total_lectures=1)
    db.add(course)
    db.flush()
    db.add(Lecture(course_id=course.id, week_number=1, lecture_number=1, title=payload.title, youtube_url=course.source_url, youtube_video_id=video_id))
    db.commit()
    db.refresh(course)
    return course


@router.get("", response_model=list[CourseRead])
def list_courses(db: Session = Depends(get_db)):
    return db.query(Course).order_by(Course.created_at.desc()).all()


@router.get("/{course_id}", response_model=CourseRead)
def get_course(course_id: int, db: Session = Depends(get_db)):
    course = db.get(Course, course_id)
    if not course:
        raise AppError("RESOURCE_NOT_FOUND", "Course not found.", 404)
    return course


@router.delete("/{course_id}")
def delete_course(course_id: int, db: Session = Depends(get_db)):
    course = db.get(Course, course_id)
    if not course:
        raise AppError("RESOURCE_NOT_FOUND", "Course not found.", 404)
    db.delete(course)
    db.commit()
    return {"ok": True}


async def _run_course_job(course_id: int, job_id: int) -> None:
    async with asyncio.Lock():
        with SessionLocal() as session:
            try:
                await CourseProcessor(get_settings()).process(session, course_id, job_id)
            except Exception as exc:
                job = session.get(ProcessingJob, job_id)
                if job:
                    job.status = "failed"
                    job.error_message = str(exc)
                    job.message = "Course processing failed."
                    session.commit()


@router.post("/{course_id}/process", response_model=JobRead)
def process_course(course_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    course = db.get(Course, course_id)
    if not course:
        raise AppError("RESOURCE_NOT_FOUND", "Course not found.", 404)
    job = CourseProcessor(get_settings()).create_job(db, course)
    background_tasks.add_task(_run_course_job, course_id, job.id)
    return job
