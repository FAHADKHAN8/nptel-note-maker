from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base
from .enums import ProcessingState


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    instructor: Mapped[str | None] = mapped_column(String(200))
    institute: Mapped[str | None] = mapped_column(String(200))
    course_code: Mapped[str | None] = mapped_column(String(80), index=True)
    source_url: Mapped[str] = mapped_column(String(1000), unique=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(1000))
    total_weeks: Mapped[int] = mapped_column(Integer, default=0)
    total_lectures: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(40), default=ProcessingState.pending)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    lectures = relationship("Lecture", back_populates="course", cascade="all, delete-orphan")
    jobs = relationship("ProcessingJob", back_populates="course", cascade="all, delete-orphan")
    artifacts = relationship("CourseArtifact", back_populates="course", cascade="all, delete-orphan")
