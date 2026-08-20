import pytest
import httpx
import json
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.errors import AppError
from app.models import Course, Lecture, Note, ProcessingJob, Transcript
from app.models.enums import ProcessingState, TranscriptSource
from app.services.course_processor import CourseProcessor
from app.services.nptel_scraper import GenericNptelParser, NptelClient
from app.services.transcript_resolver import TranscriptResolver
from app.services.vtt_parser import parse_vtt


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class FakeSettings:
    gemini_api_key = "test"
    gemini_model = "test-model"
    transcript_chunk_size = 80
    transcript_chunk_overlap = 0
    caption_service_url = "http://caption"
    caption_service_timeout = 1
    scraper_timeout = 1
    nptel_cookie = ""


class FakeCookieSettings(FakeSettings):
    nptel_cookie = "SID=local-secret; HSID=another-secret"


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


def test_nptel_parser_keeps_external_ids_separate_from_order():
    html = """
    <h1>Course</h1>
    <section><h2>Week 1</h2>
      <a class="lecture" href="https://onlinecourses.nptel.ac.in/e-learning/course/noc26_ge93?unitId=17&lessonId=18">Lecture 1: Intro</a>
    </section>
    """
    parsed = GenericNptelParser(FakeSettings()).parse_html(html, "https://onlinecourses.nptel.ac.in/e-learning/course/noc26_ge93")
    lecture = parsed.lectures[0]
    assert lecture.week_number == 1
    assert lecture.lecture_number == 1
    assert lecture.external_unit_id == "17"
    assert lecture.external_lesson_id == "18"


def test_nptel_client_parses_sanitized_courseoutline_fixture():
    fixture = {
        "course_name": "Fundamentals of Artificial Intelligence",
        "course_id": "noc26_ge93",
        "course_info": {"course": {"instructor": "Prof. Example", "institute": "IIT Example", "course_code": "noc26_ge93"}},
        "units": {
            "17": {"unit_id": 17, "title": "Week 1"},
            "22": {"unit_id": 22, "title": "Week 2"},
        },
        "lessons": {
            "18": {
                "unit_id": 17,
                "lesson_id": 18,
                "title": "Lecture 1: Introduction",
                "video_id": "abcdefghijk",
                "video_subtitles": '{"en":"https://storage.googleapis.com/sanitized/Lec-01.vtt"}',
                "preferred_vtt_lang": "en",
            },
            "19": {
                "unit_id": 17,
                "lesson_id": 19,
                "title": "Lecture 2: Search",
                "youtube_url": "https://www.youtube.com/watch?v=bcdefghijkl",
            },
            "23": {
                "unit_id": 22,
                "lesson_id": 23,
                "title": "Lecture 3: Heuristics",
            },
        },
        "order": [
            {"id": 17, "children": [{"section": "lesson", "id": 18}, {"section": "lesson", "id": 19}]},
            {"id": 22, "children": [{"section": "lesson", "id": 23}]},
        ],
    }
    parsed = NptelClient(FakeSettings()).parse_course_outline(fixture, "https://onlinecourses.nptel.ac.in/e-learning/course/noc26_ge93")
    assert parsed.title == "Fundamentals of Artificial Intelligence"
    assert len(parsed.lectures) == 3
    assert [lecture.week_number for lecture in parsed.lectures] == [1, 1, 2]
    assert [lecture.external_unit_id for lecture in parsed.lectures] == ["17", "17", "22"]
    assert [lecture.external_lesson_id for lecture in parsed.lectures] == ["18", "19", "23"]
    assert parsed.lectures[0].transcript_url == "https://storage.googleapis.com/sanitized/Lec-01.vtt"
    assert parsed.lectures[0].youtube_video_id == "abcdefghijk"
    assert parsed.lectures[1].youtube_video_id == "bcdefghijkl"


def test_nptel_client_parses_live_shape_payload_string_and_filters_non_videos():
    fixture = json.loads((FIXTURES_DIR / "courseoutline_sanitized.json").read_text(encoding="utf-8"))
    parsed = NptelClient(FakeSettings()).parse_course_outline(
        fixture,
        "https://onlinecourses.nptel.ac.in/e-learning/course/noc26_ge93",
    )

    assert parsed.title == "Fundamentals of Artificial Intelligence"
    assert parsed.instructor == "Prof. Example"
    assert parsed.institute == "IIT Example"
    assert parsed.course_code == "noc26_ge93"
    assert len({lecture.week_number for lecture in parsed.lectures}) == 2
    assert len(parsed.lectures) == 6
    assert [lecture.external_unit_id for lecture in parsed.lectures] == ["17", "17", "17", "22", "22", "22"]
    assert [lecture.external_lesson_id for lecture in parsed.lectures] == ["18", "19", "20", "23", "24", "25"]
    assert [lecture.lecture_number for lecture in parsed.lectures] == [1, 2, 3, 1, 2, 3]
    assert [lecture.title for lecture in parsed.lectures[:3]] == [
        "Lec 1: Introduction to Artificial Intelligence",
        "Lec 2: Problem Solving as State Space Search",
        "Lec 3: Uninformed Search",
    ]
    assert all("Assignment" not in lecture.title for lecture in parsed.lectures)
    assert all("Feedback" not in lecture.title for lecture in parsed.lectures)
    assert all("Lecture Notes" not in lecture.title for lecture in parsed.lectures)


def test_nptel_client_courseoutline_transcript_source_metadata():
    fixture = json.loads((FIXTURES_DIR / "courseoutline_sanitized.json").read_text(encoding="utf-8"))
    parsed = NptelClient(FakeSettings()).parse_course_outline(
        fixture,
        "https://onlinecourses.nptel.ac.in/e-learning/course/noc26_ge93",
    )
    lecture_a = parsed.lectures[0]
    lecture_b = parsed.lectures[1]

    assert lecture_a.transcript_url == "https://storage.googleapis.com/sanitized/noc26_ge93/Lec-01.vtt"
    assert lecture_a.youtube_video_id == "abcdefghijk"
    assert lecture_a.youtube_url == "https://www.youtube.com/watch?v=abcdefghijk"
    assert lecture_b.transcript_url is None
    assert lecture_b.youtube_video_id == "bcdefghijkl"
    assert lecture_b.youtube_url == "https://www.youtube.com/watch?v=bcdefghijkl"


def test_nptel_client_rejects_malformed_payload_string_cleanly():
    parsed = NptelClient(FakeSettings()).parse_course_outline(
        {"status": 200, "payload": "{\"course_info\":"},
        "https://onlinecourses.nptel.ac.in/e-learning/course/noc26_ge93",
    )
    assert parsed is None


@pytest.mark.asyncio
async def test_nptel_client_retries_courseoutline_with_cookie_after_auth_required(monkeypatch):
    calls = []
    fixture = {
        "course_name": "Authenticated Course",
        "units": {"10": {"unit_id": 10, "title": "Week 1"}},
        "lessons": {
            "11": {
                "unit_id": 10,
                "lesson_id": 11,
                "title": "Lecture 1",
                "video_id": "abcdefghijk",
                "video_subtitles": {"en": "https://storage.googleapis.com/sanitized/Lec-01.vtt"},
            }
        },
        "order": [{"id": 10, "children": [{"section": "lesson", "id": 11}]}],
    }

    async def fake_get_json(self, url, authenticated=False):
        calls.append({"url": url, "authenticated": authenticated, "cookie": self.settings.nptel_cookie if authenticated else None})
        if not authenticated:
            return {"status": 401, "message": "Unauthorized Error", "payload": "{\"loginurl\":\"https://swayam.gov.in/mycourses\"}"}
        return fixture

    monkeypatch.setattr(NptelClient, "_get_json", fake_get_json)
    parsed = await NptelClient(FakeCookieSettings()).fetch_course_outline("https://onlinecourses.nptel.ac.in/e-learning/course/noc26_ge93")
    assert [call["authenticated"] for call in calls] == [False, True]
    assert calls[0]["cookie"] is None
    assert calls[1]["cookie"] == FakeCookieSettings.nptel_cookie
    assert parsed.title == "Authenticated Course"
    assert parsed.lectures[0].external_unit_id == "10"
    assert parsed.lectures[0].external_lesson_id == "11"
    assert parsed.lectures[0].youtube_video_id == "abcdefghijk"
    assert parsed.lectures[0].transcript_url == "https://storage.googleapis.com/sanitized/Lec-01.vtt"
    assert FakeCookieSettings.nptel_cookie not in repr(parsed)


@pytest.mark.asyncio
async def test_nptel_client_does_not_retry_without_cookie(monkeypatch):
    calls = []

    async def fake_get_json(self, url, authenticated=False):
        calls.append(authenticated)
        return {"status": 401, "message": "Unauthorized Error", "payload": "{\"loginurl\":\"https://swayam.gov.in/mycourses\"}"}

    monkeypatch.setattr(NptelClient, "_get_json", fake_get_json)
    parsed = await NptelClient(FakeSettings()).fetch_course_outline("https://onlinecourses.nptel.ac.in/e-learning/course/noc26_ge93")
    assert parsed is None
    assert calls == [False]


def test_nptel_client_redacts_cookie_from_debug_text():
    client = NptelClient(FakeCookieSettings())
    assert client.redact(f"failed with {FakeCookieSettings.nptel_cookie}") == "failed with [REDACTED]"


@pytest.mark.asyncio
async def test_nptel_client_cookie_header_only_on_authenticated_retry(monkeypatch):
    requests = []
    fixture = {
        "course_name": "Authenticated Course",
        "units": {"10": {"unit_id": 10, "title": "Week 1"}},
        "lessons": {
            "11": {
                "unit_id": 10,
                "lesson_id": 11,
                "title": "Lecture 1",
                "video_id": "abcdefghijk",
                "video_subtitles": {"en": "https://storage.googleapis.com/sanitized/Lec-01.vtt"},
            }
        },
        "order": [{"id": 10, "children": [{"section": "lesson", "id": 11}]}],
    }

    def handler(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(200, json={"status": 401, "payload": "{\"loginurl\":\"https://swayam.gov.in/mycourses\"}"})
        return httpx.Response(200, json=fixture)

    transport = httpx.MockTransport(handler)

    class FakeAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, transport=transport, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    parsed = await NptelClient(FakeCookieSettings()).fetch_course_outline("https://onlinecourses.nptel.ac.in/e-learning/course/noc26_ge93")

    assert parsed.title == "Authenticated Course"
    assert len(requests) == 2
    assert "cookie" not in requests[0].headers
    assert requests[1].headers["cookie"] == FakeCookieSettings.nptel_cookie
    assert FakeCookieSettings.nptel_cookie not in repr(parsed)


def test_nptel_client_parses_anonymous_announcement_fallback():
    fixture = {
        "announcements": [
            {
                "html": (
                    "The lecture videos for Week-No 01 have been uploaded for the course "
                    "Fundamentals of Artificial Intelligence. Link: "
                    '<a href="https://onlinecourses.nptel.ac.in/noc26_ge93/unit?unit=17&amp;lesson=18">week</a>'
                )
            },
            {
                "html": (
                    "The lecture videos for Week-No 02 have been uploaded. Link: "
                    '<a href="https://onlinecourses.nptel.ac.in/noc26_ge93/unit?unit=22&amp;lesson=23">week</a>'
                )
            },
        ]
    }
    parsed = NptelClient(FakeSettings()).parse_announcements(fixture, "https://onlinecourses.nptel.ac.in/e-learning/course/noc26_ge93", "noc26_ge93")
    assert parsed.title == "Fundamentals of Artificial Intelligence"
    assert len(parsed.lectures) == 2
    assert parsed.lectures[0].external_unit_id == "17"
    assert parsed.lectures[0].external_lesson_id == "18"
    assert parsed.lectures[0].transcript_url is None


def test_vtt_parser_handles_wrapped_multiline_duplicate_malformed_and_unicode():
    parsed = parse_vtt(
        '"WEBVTT\\n\\n'
        'cue-1\\n00:31.840 --> 00:38.220 align:start\\nWelcome to the course of Fundamentals of Artificial\\nIntelligence.\\n\\n'
        'bad cue\\nnot a timestamp\\nignore me\\n\\n'
        '00:38.220 --> 00:44.330\\n<v Instructor>Welcome to the course of Fundamentals of Artificial Intelligence.</v>\\n\\n'
        '00:44.330 --> 00:45.000\\nUnicode π and matrix Aᵀ.\\n"'
    )
    assert len(parsed.segments) == 2
    assert parsed.segments[0].start == 31.84
    assert parsed.segments[0].text == "Welcome to the course of Fundamentals of Artificial Intelligence."
    assert "Unicode" in parsed.text


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
async def test_transcript_resolver_uses_official_vtt(monkeypatch, db_session):
    class FakeResponse:
        is_error = False
        content = b""
        headers = {"content-type": "text/vtt"}
        text = "WEBVTT\n\n00:00.000 --> 00:02.000\nHello <b>AI</b> learners.\n"

    async def fetch_vtt(self, client, transcript_url):
        return FakeResponse()

    monkeypatch.setattr(TranscriptResolver, "_fetch_official", fetch_vtt)
    course = Course(title="Course", source_url="https://nptel.ac.in/courses/4", total_weeks=1, total_lectures=1)
    lecture = Lecture(course=course, title="Lecture", week_number=1, lecture_number=1, transcript_url="https://storage.googleapis.com/test/Lec-01.vtt")
    db_session.add(course)
    db_session.commit()
    resolved = await TranscriptResolver(FakeSettings()).resolve(db_session, lecture)
    assert resolved.source == TranscriptSource.nptel_vtt
    assert resolved.cleaned_text == "Hello AI learners."
    assert resolved.segments_json[0]["start"] == 0.0


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
