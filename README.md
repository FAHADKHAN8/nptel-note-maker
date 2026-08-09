# NPTEL AI Notes Generator

A personal full-stack study tool for pasting an NPTEL course URL and generating structured, exam-ready Markdown notes using Gemini. The project is under active development: the deterministic course-processing pipeline is implemented and covered by offline fixtures/mocks, while live NPTEL discovery remains limited by what course pages expose without login or JavaScript execution.

## Features

- FastAPI backend with SQLAlchemy models for courses, lectures, transcripts, notes, chunk caches, and jobs.
- Node caption microservice using `youtube-captions-scraper`; it retrieves captions only, never videos.
- React/Vite frontend for importing courses, viewing lectures, editing transcripts, editing notes, and exporting files.
- Gemini integration via the current `google-genai` SDK using configurable `GEMINI_MODEL`.
- Transcript hashing, chunk hashing, cached chunk summaries, timestamp-aware chunking, structured prompts, and mocked-test-friendly service boundaries.
- One-click course processing with persistent job progress, resume behavior, per-lecture failures, week revision notes, and a course revision guide.

## Architecture

```text
React frontend -> FastAPI API -> SQLite/PostgreSQL-compatible DB
                         |-> Node caption service -> public YouTube captions
                         |-> Gemini API -> grounded Markdown notes
                         |-> export services -> PDF/DOCX/Obsidian ZIP
```

## Setup

Prerequisites: Python 3.12+, Node 22+, Docker Desktop optional, and a Gemini API key.

Docker:

```bash
docker compose up --build
```

Without Docker:

```bash
cd caption-service && npm install && npm start
cd backend && python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
```

Copy `.env.example` files to `.env` for real local configuration. Set `GEMINI_API_KEY` and `GEMINI_MODEL` in `backend/.env`.

For database migrations on a fresh database:

```bash
cd backend
python -m alembic upgrade head
```

The current app also calls `Base.metadata.create_all()` at startup for local convenience. If you already have an old `backend/nptel_notes.db` created before Alembic was used, stamp or recreate it before running migrations.

## API Endpoints

- `GET /api/health`
- `POST /api/courses/import`
- `POST /api/courses/youtube-prototype`
- `GET /api/courses`
- `GET /api/courses/{course_id}`
- `DELETE /api/courses/{course_id}`
- `POST /api/courses/{course_id}/process`
- `GET /api/courses/{course_id}/lectures`
- `GET /api/lectures/{lecture_id}`
- `POST /api/lectures/{lecture_id}/extract-transcript`
- `POST /api/lectures/{lecture_id}/generate-notes`
- `POST /api/lectures/{lecture_id}/regenerate-notes`
- `GET/PUT /api/lectures/{lecture_id}/transcript`
- `GET/PUT /api/lectures/{lecture_id}/notes`
- `GET /api/jobs/{job_id}`
- `GET /api/courses/{course_id}/jobs`
- `GET /api/lectures/{lecture_id}/export/markdown`
- `GET /api/lectures/{lecture_id}/export/pdf`
- `GET /api/lectures/{lecture_id}/export/docx`
- `GET /api/courses/{course_id}/export/pdf`
- `GET /api/courses/{course_id}/export/docx`
- `GET /api/courses/{course_id}/export/obsidian`
- `GET /api/courses/{course_id}/export/markdown`

## Example Curl

```bash
curl http://localhost:8000/api/health
curl -X POST http://localhost:8000/api/courses/youtube-prototype -H "Content-Type: application/json" -d "{\"youtube_url\":\"https://www.youtube.com/watch?v=abcdefghijk\",\"title\":\"Demo Lecture\"}"
```

## Testing

```bash
cd backend
pytest
```

Automated tests do not call Gemini.

## Course Import And Processing

`POST /api/courses/import` accepts `{"url": "https://..."}` or the older `{"course_url": "https://..."}` shape. The parser extracts title, instructor, institution, optional course code, weeks, lecture order, NPTEL lecture links, YouTube IDs, and transcript links when those are visible in the fetched HTML.

`POST /api/courses/{course_id}/process` creates a persistent job and returns quickly. The background processor resolves each lecture transcript, generates or reuses notes, records failures per lecture, synthesizes week notes from lecture notes, and synthesizes a course guide from week notes. Running processing again resumes from stored transcripts, notes, and cache metadata.

## Transcript Sources

- YouTube captions through the local caption service are partially implemented.
- Official NPTEL HTML transcript extraction is implemented when a transcript link is discoverable.
- Official NPTEL PDF transcript extraction uses PyMuPDF when a PDF link is discoverable.
- If official transcript extraction fails, the processor falls back to YouTube captions when a video ID exists.
- The app never downloads YouTube videos.

## Gemini Token Usage

Lecture generation stores a transcript hash, prompt version, model name, generation settings hash, and per-chunk summaries. Unchanged lecture notes are reused, and unchanged chunks are not resent to Gemini.

Week synthesis uses existing lecture notes, not raw transcripts. Course synthesis uses week notes, not raw transcripts.

## Graphify Development Workflow

Use Graphify before broad source inspection:

```bash
graphify update . --no-cluster
graphify query "trace note generation from endpoint through Gemini service"
```

`graphify-out/cost.json` is ignored because it is local cost telemetry.

## Screenshots

Add screenshots here after running the frontend locally.

## Limitations

- Live NPTEL course import is partial because some public pages hide lecture lists behind login or client-side rendering.
- YouTube caption extraction depends on an unofficial scraper.
- Videos without captions cannot be processed.
- Captions may contain errors.
- Transcript-only notes may miss diagrams and visual content.
- Gemini free-tier quotas may restrict batch processing.
- Users should review AI-generated notes before relying on them.

## Ethical And Legal Notes

This project only retrieves publicly available transcripts or captions for personal educational use. It does not download YouTube videos. Respect NPTEL and YouTube terms, rate limits, and instructor content rights.

## Future Improvements

Add robust NPTEL parser variants, Alembic autogeneration workflow, Redis/Celery workers, richer progress tracking, HTML/PDF official transcript extraction coverage, rate-limiting middleware, and production auth.

## Contributing

See `CONTRIBUTING.md`.

## License

MIT. See `LICENSE`.
