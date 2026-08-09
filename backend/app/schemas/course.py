from datetime import datetime
from pydantic import BaseModel, Field
from .common import ORMModel


class CourseImportRequest(BaseModel):
    course_url: str | None = Field(default=None, min_length=12, max_length=1000)
    url: str | None = Field(default=None, min_length=12, max_length=1000)

    @property
    def resolved_url(self) -> str:
        return self.course_url or self.url or ""


class YouTubeLectureRequest(BaseModel):
    youtube_url: str = Field(min_length=11, max_length=1000)
    title: str = "Single YouTube Lecture"


class CourseRead(ORMModel):
    id: int
    title: str
    description: str | None
    instructor: str | None
    institute: str | None
    course_code: str | None
    source_url: str
    thumbnail_url: str | None
    total_weeks: int
    total_lectures: int
    status: str
    created_at: datetime
    updated_at: datetime
