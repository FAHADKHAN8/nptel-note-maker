from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base
from .enums import ProcessingState


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    lecture_id: Mapped[int | None] = mapped_column(ForeignKey("lectures.id", ondelete="CASCADE"))
    job_type: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), default=ProcessingState.pending)
    stage: Mapped[str | None] = mapped_column(String(80))
    progress: Mapped[int] = mapped_column(Integer, default=0)
    total_lectures: Mapped[int] = mapped_column(Integer, default=0)
    completed_lectures: Mapped[int] = mapped_column(Integer, default=0)
    failed_lectures: Mapped[int] = mapped_column(Integer, default=0)
    current_lecture_id: Mapped[int | None] = mapped_column(Integer)
    current_lecture_title: Mapped[str | None] = mapped_column(String(300))
    message: Mapped[str | None] = mapped_column(String(500))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    course = relationship("Course", back_populates="jobs")
