from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base
from .enums import ProcessingState


class Lecture(Base):
    __tablename__ = "lectures"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    week_number: Mapped[int] = mapped_column(Integer, default=1)
    lecture_number: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(300))
    nptel_url: Mapped[str | None] = mapped_column(String(1000))
    transcript_url: Mapped[str | None] = mapped_column(String(1000))
    youtube_url: Mapped[str | None] = mapped_column(String(1000))
    youtube_video_id: Mapped[str | None] = mapped_column(String(20), index=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(40), default=ProcessingState.pending)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    course = relationship("Course", back_populates="lectures")
    transcript = relationship("Transcript", back_populates="lecture", cascade="all, delete-orphan", uselist=False)
    note = relationship("Note", back_populates="lecture", cascade="all, delete-orphan", uselist=False)
