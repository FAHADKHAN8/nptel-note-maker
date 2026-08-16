from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.errors import AppError
from app.models import Course, Lecture, Note, Transcript
from app.models.enums import TranscriptSource
from app.services.nptel_scraper import ParsedCourse, ParsedLecture


def test_import_process_job_and_exports(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'api.db'}", connect_args={"check_same_thread": False}, future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)

    def override_db():
        with Session() as session:
            yield session

    class FakeParser:
        def __init__(self, _settings):
            pass

        async def parse_course(self, url):
            return ParsedCourse(
                title="Fixture Course",
                instructor="Prof. A",
                institute="IIT Test",
                course_code="CS101",
                description="About",
                image_url=None,
                course_url=url,
                lectures=[ParsedLecture(week_number=1, lecture_number=1, title="Intro", youtube_url="https://youtube.com/watch?v=abcdefghijk", youtube_video_id="abcdefghijk", transcript_url="https://nptel.ac.in/t.html")],
            )

    def fake_add_task(fn, *args, **kwargs):
        return None

    monkeypatch.setattr("app.routers.courses.GenericNptelParser", FakeParser)
    monkeypatch.setattr("fastapi.BackgroundTasks.add_task", fake_add_task)
    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        imported = client.post("/api/courses/import", json={"url": "https://nptel.ac.in/courses/106/test"})
        assert imported.status_code == 200
        course_id = imported.json()["id"]
        assert imported.json()["course_code"] == "CS101"

        with Session() as session:
            course = session.get(Course, course_id)
            lecture = course.lectures[0]
            lecture.transcript = Transcript(source=TranscriptSource.youtube_captions, language="en", raw_text="raw", cleaned_text="clean", content_hash="hash", segments_json=[])
            lecture.note = Note(title="Intro", content_markdown="# Intro\n\nNotes", model_name="test", prompt_version="v1", source_transcript_hash="hash")
            session.commit()

        process = client.post(f"/api/courses/{course_id}/process")
        assert process.status_code == 200
        job_id = process.json()["id"]
        job = client.get(f"/api/jobs/{job_id}")
        assert job.status_code == 200
        assert job.json()["status"] == "pending"
        assert client.get(f"/api/courses/{course_id}").status_code == 200
        assert client.get(f"/api/courses/{course_id}/lectures").json()[0]["transcript_url"]
        assert client.get(f"/api/lectures/1/transcript").status_code == 200
        assert client.get(f"/api/lectures/1/notes").status_code == 200
        assert client.get(f"/api/lectures/1/export/markdown").status_code == 200
        assert client.get(f"/api/courses/{course_id}/export/markdown").status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_api_error_response_redacts_configured_nptel_cookie(monkeypatch):
    secret = "SID=local-secret; HSID=another-secret"

    class FakeSettings:
        nptel_cookie = secret

    monkeypatch.setattr("app.errors.get_settings", lambda: FakeSettings())

    @app.get("/api/test-redaction")
    def _redaction_route():
        raise AppError("TEST", f"failed with {secret}", 400, {"debug": secret})

    client = TestClient(app)
    response = client.get("/api/test-redaction")
    body = response.text
    assert response.status_code == 400
    assert secret not in body
    assert "[REDACTED]" in body
