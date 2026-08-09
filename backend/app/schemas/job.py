from datetime import datetime
from .common import ORMModel


class JobRead(ORMModel):
    id: int
    course_id: int | None
    lecture_id: int | None
    job_type: str
    status: str
    stage: str | None
    progress: int
    total_lectures: int
    completed_lectures: int
    failed_lectures: int
    current_lecture_id: int | None
    current_lecture_title: str | None
    message: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    updated_at: datetime
    completed_at: datetime | None
