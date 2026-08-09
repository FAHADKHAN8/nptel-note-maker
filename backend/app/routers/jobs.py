from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..errors import AppError
from ..models import ProcessingJob
from ..schemas.job import JobRead

router = APIRouter(tags=["jobs"])


@router.get("/api/jobs/{job_id}", response_model=JobRead)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(ProcessingJob, job_id)
    if not job:
        raise AppError("RESOURCE_NOT_FOUND", "Job not found.", 404)
    return job


@router.get("/api/courses/{course_id}/jobs", response_model=list[JobRead])
def course_jobs(course_id: int, db: Session = Depends(get_db)):
    return db.query(ProcessingJob).filter(ProcessingJob.course_id == course_id).order_by(ProcessingJob.created_at.desc()).all()
