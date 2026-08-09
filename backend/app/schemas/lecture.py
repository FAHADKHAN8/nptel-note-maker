from datetime import datetime
from .common import ORMModel


class LectureRead(ORMModel):
    id: int
    course_id: int
    week_number: int
    lecture_number: int
    title: str
    nptel_url: str | None
    transcript_url: str | None
    youtube_url: str | None
    youtube_video_id: str | None
    duration_seconds: int | None
    error_message: str | None
    status: str
    created_at: datetime
    updated_at: datetime
