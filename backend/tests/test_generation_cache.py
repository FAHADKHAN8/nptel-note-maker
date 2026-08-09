from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import pytest

from app.database import Base
from app.models import Course, Lecture, Transcript
from app.models.enums import TranscriptSource
from app.services.notes_service import NotesPipeline


class FakeSettings:
    gemini_api_key = "test"
    gemini_model = "test-model"
    transcript_chunk_size = 20
    transcript_chunk_overlap = 0
    caption_service_url = "http://caption"
    caption_service_timeout = 1


class FakeGemini:
    chunk_calls = 0
    synthesis_calls = 0
    chunk_prompt_version = "NPTEL_CHUNK_SUMMARY_V1"
    lecture_prompt_version = "NPTEL_LECTURE_NOTES_V1"

    def __init__(self, _settings):
        pass

    async def generate_chunk_summary(self, *, chunk, options):
        FakeGemini.chunk_calls += 1
        return f"summary {chunk.index}: {chunk.text}"

    async def synthesize_lecture_notes(self, *, lecture_title, course_title, chunk_notes, source_info):
        FakeGemini.synthesis_calls += 1
        return f"# {lecture_title}\n\n" + "\n".join(chunk_notes)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)
    with Session() as session:
        yield session


@pytest.mark.asyncio
async def test_generate_notes_reuses_unchanged_transcript(monkeypatch, db_session):
    from app.services import notes_service

    FakeGemini.chunk_calls = 0
    FakeGemini.synthesis_calls = 0
    monkeypatch.setattr(notes_service, "GeminiService", FakeGemini)

    course = Course(title="Course", source_url="https://example.test/course", total_weeks=1, total_lectures=1)
    lecture = Lecture(course=course, week_number=1, lecture_number=1, title="Lecture")
    lecture.transcript = Transcript(
        source=TranscriptSource.youtube_captions,
        language="en",
        raw_text="One sentence. Two sentence. Three sentence.",
        cleaned_text="One sentence. Two sentence. Three sentence.",
        segments_json=[],
    )
    db_session.add(course)
    db_session.commit()

    pipeline = NotesPipeline(FakeSettings())
    first = await pipeline.generate_notes(db_session, lecture, {"detail_level": "detailed"})
    second = await pipeline.generate_notes(db_session, lecture, {"detail_level": "detailed"})

    assert first.id == second.id
    assert FakeGemini.chunk_calls > 0
    assert FakeGemini.synthesis_calls == 1
    assert second.source_transcript_hash == lecture.transcript.content_hash
