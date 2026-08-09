import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.errors import AppError
from app.models import Course, Lecture, Note, ProcessingJob, Transcript
from app.models.enums import ProcessingState, TranscriptSource
from app.services.course_processor import CourseProcessor
from app.services.nptel_scraper import GenericNptelParser
from app.services.transcript_resolver import TranscriptResolver


class FakeSettings:
    gemini_api_key = "test"
    gemini_model = "test-model"
    transcript_chunk_size = 80
    transcript_chunk_overlap = 0
    caption_service_url = "http://caption"
    caption_service_timeout = 1
    scraper_timeout = 1


class FakeGemini:
    chunk_calls = 0
    week_calls = 0
    course_calls = 0
    chunk_prompt_version = "NPTEL_CHUNK_SUMMARY_V1"
    lecture_prompt_version = "NPTEL_LECTURE_NOTES_V1"
    week_prompt_version = "NPTEL_WEEK_SYNTHESIS_V1"
    course_prompt_version = "NPTEL_COURSE_SYNTHESIS_V1"

    def __init__(self, _settings):
        pass

    async def generate_chunk_summary(self, *, chunk, options):
        FakeGemini.chunk_calls += 1
        return f"chunk {chunk.index} summary"

    async def synthesize_lecture_notes(self, *, lecture_title, course_title, chunk_notes, source_info):
        return f"# {lecture_title}\n\n" + "\n".join(chunk_notes)

    async def synthesize_week_notes(self, *, course_title, week_number, lecture_notes):
        FakeGemini.week_calls += 1
        return f"# Week {week_number} Revision Notes"

    async def synthesize_course_notes(self, *, course_title, week_notes):
        FakeGemini.course_calls += 1
        return "# Course Revision Guide"


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)
    with Session() as session:
        yield session


def test_nptel_parser_extracts_fixture_metadata_and_order():
    html = """
    <html><head><title>Artificial Intelligence - NPTEL</title></head>
    <body>
      <h1>Artificial Intelligence</h1>
      <div class="instructor">Instructor: Prof. A</div>
      <div class="institute">IIT Test</div>
      <section class="week"><h2>Week 1</h2>
        <div class="lecture"><a href="/courses/106/test/lec1">Lecture 1: Introduction</a>
          <a href="https://www.youtube.com/watch?v=abcdefghijk">Watch</a>
          <a href="/transcripts/lec1.html">Transcript</a>
        </div>
        <div class="lecture"><a href="/courses/106/test/lec2">Lecture 2: Search</a>
          <a href="https://youtu.be/bcdefghijkl">Watch</a>
        </div>
      </section>
      <section class="week"><h2>Week 2</h2>
        <div class="lecture"><a href="/courses/106/test/lec3">Lecture 3: A Star</a>
          <a href="/transcripts/lec3.pdf">PDF Transcript</a>
        </div>
      </section>
    </body></html>
    """
    parsed = GenericNptelParser(FakeSettings()).parse_html(html, "https://nptel.ac.in/courses/106/test")
    assert parsed.title == "Artificial Intelligence"
    assert parsed.institute == "IIT Test"
    assert len(parsed.lectures) == 3
    assert [lecture.week_number for lecture in parsed.lectures] == [1, 1, 2]
    assert parsed.lectures[0].youtube_video_id == "abcdefghijk"
    assert parsed.lectures[0].transcript_url == "https://nptel.ac.in/transcripts/lec1.html"
    assert parsed.lectures[2].transcript_url.endswith("/transcripts/lec3.pdf")


@pytest.mark.asyncio
async def test_transcript_resolver_reuses_existing_transcript(db_session):
    course = Course(title="Course", source_url="https://nptel.ac.in/courses/1", total_weeks=1, total_lectures=1)
    lecture = Lecture(course=course, title="Lecture", week_number=1, lecture_number=1)
    lecture.transcript = Transcript(source=TranscriptSource.nptel_html, language="en", raw_text="Raw", cleaned_text="Clean", content_hash="abc", segments_json=[])
    db_session.add(course)
    db_session.commit()
    resolved = await TranscriptResolver(FakeSettings()).resolve(db_session, lecture)
    assert resolved.content_hash == "abc"


@pytest.mark.asyncio
async def test_transcript_resolver_prefers_official_then_falls_back_to_youtube(monkeypatch, db_session):
    async def official_fails(self, db, lecture):
        raise AppError("OFFICIAL_FAILED", "Official failed.", 502)

    async def youtube_works(self, db, lecture):
        return self._save(db, lecture, TranscriptSource.youtube_captions, "hello world", "hello world", [], lecture.youtube_url)

    monkeypatch.setattr(TranscriptResolver, "_official_transcript", official_fails)
    monkeypatch.setattr(TranscriptResolver, "_youtube_transcript", youtube_works)
    course = Course(title="Course", source_url="https://nptel.ac.in/courses/2", total_weeks=1, total_lectures=1)
    lecture = Lecture(course=course, title="Lecture", week_number=1, lecture_number=1, transcript_url="https://nptel.ac.in/t.html", youtube_url="https://youtube.com/watch?v=abcdefghijk", youtube_video_id="abcdefghijk")
    db_session.add(course)
    db_session.commit()
    resolved = await TranscriptResolver(FakeSettings()).resolve(db_session, lecture)
    assert resolved.source == TranscriptSource.youtube_captions
    assert resolved.content_hash


@pytest.mark.asyncio
async def test_course_processor_partial_and_resume(monkeypatch, db_session):
    from app.services import course_processor, notes_service

    async def fake_resolve(self, db, lecture):
        if "Bad" in lecture.title:
            raise AppError("TRANSCRIPT_NOT_FOUND", "Captions unavailable.", 404)
        lecture.transcript = Transcript(source=TranscriptSource.youtube_captions, language="en", raw_text=lecture.title, cleaned_text=f"{lecture.title} content.", content_hash=f"hash-{lecture.id}", segments_json=[])
        db.add(lecture.transcript)
        db.commit()
        return lecture.transcript

    FakeGemini.chunk_calls = 0
    FakeGemini.week_calls = 0
    FakeGemini.course_calls = 0
    monkeypatch.setattr(notes_service.NotesPipeline, "resolve_transcript", fake_resolve)
    monkeypatch.setattr(notes_service, "GeminiService", FakeGemini)
    monkeypatch.setattr(course_processor, "GeminiService", FakeGemini)

    course = Course(title="Course", source_url="https://nptel.ac.in/courses/3", total_weeks=1, total_lectures=4)
    for index, title in enumerate(["One", "Two", "Bad Three", "Four"], start=1):
        course.lectures.append(Lecture(title=title, week_number=1, lecture_number=index, youtube_video_id="abcdefghijk"))
    db_session.add(course)
    db_session.commit()
    job = ProcessingJob(course_id=course.id, job_type="course_processing")
    db_session.add(job)
    db_session.commit()

    await CourseProcessor(FakeSettings()).process(db_session, course.id, job.id)
    assert job.status == ProcessingState.partial
    assert job.completed_lectures == 3
    assert job.failed_lectures == 1
    first_chunk_calls = FakeGemini.chunk_calls

    retry = ProcessingJob(course_id=course.id, job_type="course_processing")
    db_session.add(retry)
    db_session.commit()
    await CourseProcessor(FakeSettings()).process(db_session, course.id, retry.id)
    assert FakeGemini.chunk_calls == first_chunk_calls
    assert retry.status == ProcessingState.partial
    assert FakeGemini.week_calls >= 1
    assert FakeGemini.course_calls >= 1
