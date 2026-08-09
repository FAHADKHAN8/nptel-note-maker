from datetime import datetime

from sqlalchemy.orm import Session, selectinload

from ..config import Settings
from ..errors import AppError
from ..models import Course, CourseArtifact, Lecture, ProcessingJob
from ..models.enums import ProcessingState
from .gemini_service import GeminiService
from .hashing import stable_hash
from .notes_service import NotesPipeline


class JobStage:
    extracting_transcript = "EXTRACTING_TRANSCRIPT"
    generating_notes = "GENERATING_NOTES"
    generating_week_summaries = "GENERATING_WEEK_SUMMARIES"
    generating_course_summary = "GENERATING_COURSE_SUMMARY"
    completed = "COMPLETED"


class CourseProcessor:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.pipeline = NotesPipeline(settings)

    async def process(self, db: Session, course_id: int, job_id: int) -> ProcessingJob:
        job = db.get(ProcessingJob, job_id)
        course = db.get(Course, course_id, options=[selectinload(Course.lectures), selectinload(Course.artifacts)])
        if not job or not course:
            raise AppError("RESOURCE_NOT_FOUND", "Course or job not found.", 404)
        job.status = ProcessingState.processing
        course.status = ProcessingState.processing
        job.started_at = job.started_at or datetime.utcnow()
        job.total_lectures = len(course.lectures)
        self._save_progress(db, job, "Processing course.")
        for lecture in sorted(course.lectures, key=lambda item: (item.week_number, item.lecture_number, item.id)):
            job.current_lecture_id = lecture.id
            job.current_lecture_title = lecture.title
            try:
                if not self._has_reusable_note(lecture):
                    job.stage = JobStage.extracting_transcript
                    self._save_progress(db, job, f"Resolving transcript for {lecture.title}.")
                    await self.pipeline.resolve_transcript(db, lecture)
                    job.stage = JobStage.generating_notes
                    self._save_progress(db, job, f"Generating notes for {lecture.title}.")
                    await self.pipeline.generate_notes(db, lecture, {"detail_level": "detailed"})
                lecture.status = ProcessingState.completed
                lecture.error_message = None
            except AppError as exc:
                lecture.status = ProcessingState.failed
                lecture.error_message = exc.message
            except Exception as exc:
                lecture.status = ProcessingState.failed
                lecture.error_message = str(exc)
            self._recount(course, job)
            self._save_progress(db, job, f"{job.completed_lectures}/{job.total_lectures} lectures completed.")
        await self._synthesize_weeks(db, course, job)
        await self._synthesize_course(db, course, job)
        self._recount(course, job)
        job.status = ProcessingState.completed if job.failed_lectures == 0 else ProcessingState.partial
        course.status = job.status
        job.stage = JobStage.completed
        job.current_lecture_id = None
        job.current_lecture_title = None
        job.completed_at = datetime.utcnow()
        self._save_progress(db, job, "Processing complete." if job.failed_lectures == 0 else "Processing completed with lecture failures.")
        return job

    def create_job(self, db: Session, course: Course) -> ProcessingJob:
        job = ProcessingJob(course_id=course.id, job_type="course_processing", status=ProcessingState.pending, stage="PENDING", total_lectures=len(course.lectures), progress=0, message="Queued.")
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def _has_reusable_note(self, lecture: Lecture) -> bool:
        return bool(lecture.note and lecture.transcript and lecture.transcript.content_hash and lecture.note.source_transcript_hash == lecture.transcript.content_hash)

    def _recount(self, course: Course, job: ProcessingJob) -> None:
        job.completed_lectures = sum(1 for lecture in course.lectures if lecture.status == ProcessingState.completed)
        job.failed_lectures = sum(1 for lecture in course.lectures if lecture.status == ProcessingState.failed)
        job.progress = int(((job.completed_lectures + job.failed_lectures) / job.total_lectures) * 100) if job.total_lectures else 0

    def _save_progress(self, db: Session, job: ProcessingJob, message: str) -> None:
        job.message = message
        db.add(job)
        db.commit()

    async def _synthesize_weeks(self, db: Session, course: Course, job: ProcessingJob) -> None:
        gemini = GeminiService(self.settings)
        for week in sorted({lecture.week_number for lecture in course.lectures if lecture.note}):
            notes = [lecture.note.content_markdown for lecture in sorted(course.lectures, key=lambda item: item.lecture_number) if lecture.week_number == week and lecture.note]
            if not notes:
                continue
            source_hash = stable_hash(notes)
            existing = self._artifact(db, course.id, "week", week)
            if existing and existing.source_hash == source_hash and existing.prompt_version == gemini.week_prompt_version and existing.model_name == self.settings.gemini_model:
                continue
            job.stage = JobStage.generating_week_summaries
            self._save_progress(db, job, f"Generating Week {week} revision notes.")
            markdown = await gemini.synthesize_week_notes(course_title=course.title, week_number=week, lecture_notes=notes)
            self._upsert_artifact(db, existing, course.id, "week", week, markdown, source_hash, gemini.week_prompt_version)

    async def _synthesize_course(self, db: Session, course: Course, job: ProcessingJob) -> None:
        gemini = GeminiService(self.settings)
        artifacts = db.query(CourseArtifact).filter(CourseArtifact.course_id == course.id, CourseArtifact.artifact_type == "week").order_by(CourseArtifact.week_number).all()
        week_notes = [artifact.content_markdown for artifact in artifacts]
        if not week_notes:
            return
        source_hash = stable_hash(week_notes)
        existing = self._artifact(db, course.id, "course", None)
        if existing and existing.source_hash == source_hash and existing.prompt_version == gemini.course_prompt_version and existing.model_name == self.settings.gemini_model:
            return
        job.stage = JobStage.generating_course_summary
        self._save_progress(db, job, "Generating course revision guide.")
        markdown = await gemini.synthesize_course_notes(course_title=course.title, week_notes=week_notes)
        self._upsert_artifact(db, existing, course.id, "course", None, markdown, source_hash, gemini.course_prompt_version)

    def _artifact(self, db: Session, course_id: int, artifact_type: str, week_number: int | None) -> CourseArtifact | None:
        query = db.query(CourseArtifact).filter(CourseArtifact.course_id == course_id, CourseArtifact.artifact_type == artifact_type)
        query = query.filter(CourseArtifact.week_number == week_number) if week_number is not None else query.filter(CourseArtifact.week_number.is_(None))
        return query.one_or_none()

    def _upsert_artifact(self, db: Session, artifact: CourseArtifact | None, course_id: int, artifact_type: str, week_number: int | None, markdown: str, source_hash: str, prompt_version: str) -> None:
        artifact = artifact or CourseArtifact(course_id=course_id, artifact_type=artifact_type, week_number=week_number)
        artifact.content_markdown = markdown
        artifact.source_hash = source_hash
        artifact.prompt_version = prompt_version
        artifact.model_name = self.settings.gemini_model
        db.add(artifact)
        db.commit()
