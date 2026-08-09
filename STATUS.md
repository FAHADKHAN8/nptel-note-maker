# STATUS

Last audited: 2026-08-09

## Repository Status

- Backend FastAPI application: 🟡 Implemented but incomplete. Imports and health endpoint work.
- Configuration/settings: 🟡 Implemented but incomplete. Pydantic settings exist; production hardening is minimal.
- SQLAlchemy database setup: 🟡 Implemented but incomplete. Models exist; app still calls `create_all`.
- Course model: 🟡 Implemented but incomplete.
- Lecture model: 🟡 Implemented but incomplete. External NPTEL unit/lesson IDs are stored separately from display order.
- Transcript model: 🟡 Implemented but incomplete. Content hash now exists.
- Note model: 🟡 Implemented but incomplete. Prompt/model/transcript cache metadata now exists.
- Job model: ✅ Verified. Tracks stage, totals, completed/failed counts, current lecture, progress, timestamps, and errors.
- Migrations/Alembic: ✅ Verified. Empty development DB was recreated and upgraded through latest migration.
- API error handling: 🟡 Implemented but incomplete. Structured `AppError` exists.
- Validation schemas: 🟡 Implemented but incomplete.
- CORS: ✅ Complete and verified for configurable local origins.
- Logging: ❌ Missing beyond framework defaults.
- Tests: 🟡 Implemented but incomplete. 14 backend tests pass; coverage is still narrow.

## Course Importing

- `POST /api/courses/import`: 🟡 Partial. It supports `url` and `course_url`, validates NPTEL URLs, persists parser metadata, and is covered by fixtures. Live public pages tested did not expose lecture lists in fetched HTML.
- `POST /api/courses/youtube-prototype`: ✅ Complete and verified by inspection for creating a one-lecture course from a YouTube URL.
- Metadata/weeks/lectures/transcript links/video IDs: 🟡 Parser-dependent and not live-verified.

## YouTube Caption Service

- `caption-service/`: 🟡 Implemented but incomplete.
- `youtube-captions-scraper`: ✅ Present.
- `/health`: ✅ Implemented.
- `/captions`: ✅ Implemented for video IDs, language, timestamps, timeout, structured errors, and empty-caption handling.
- Video downloads: ✅ Not implemented, as desired.
- Automated tests: ❌ Missing.

## Transcript Pipeline

- Official NPTEL transcript extraction: 🟡 Partial. VTT, HTML, and PDF links are supported when discoverable.
- YouTube fallback: ✅ Verified with mocked resolver path; live caption availability depends on YouTube.
- HTML/PDF transcript handling: 🟡 Partial. HTML text and PyMuPDF PDF extraction implemented.
- VTT parsing: ✅ Verified with synthetic raw/JSON-wrapped VTT fixture.
- Cleaning: 🟡 Implemented and tested lightly.
- Timestamp preservation: 🟡 Implemented for caption segments.
- Duplicate caption removal: 🟡 Implemented with simple adjacent-duplicate logic.
- Chunking: 🟡 Implemented and tested lightly.
- Persistence: ✅ Implemented.
- Manual editing: ✅ Implemented; edits now update transcript hash.

## Gemini Integration

- SDK: ✅ Uses current `google-genai` via `from google import genai`.
- `GEMINI_API_KEY` and `GEMINI_MODEL`: ✅ Configured.
- Service abstraction: ✅ Implemented.
- Error handling/retry/backoff/quota: 🟡 Implemented but basic.
- Response parsing: 🟡 Uses `response.text`; no schema validation.
- Tests: ✅ Mocked; no Gemini quota used.

## Notes

- `POST /api/lectures/{lecture_id}/generate-notes`: 🟡 Functional if transcript/captions and Gemini are configured.
- `POST /api/lectures/{lecture_id}/regenerate-notes`: 🟡 Same as generate; automatic cache-aware reuse exists, but no user-selectable regeneration level yet.
- `GET /api/lectures/{lecture_id}/notes`: ✅ Implemented.
- `PUT /api/lectures/{lecture_id}/notes`: ✅ Implemented.
- Chunk cache reuse: ✅ Implemented for unchanged chunks.
- Whole-note reuse: ✅ Implemented for unchanged transcript, prompt version, model, and generation settings.

## Batch Course Processing

- `POST /api/courses/{course_id}/process`: ✅ Verified with mocked integrations. Creates a job and runs resumable processing in background.

## Jobs

- `GET /api/jobs/{job_id}`: ✅ Implemented for existing records.
- `GET /api/courses/{course_id}/jobs`: ✅ Implemented for existing records.
- Real asynchronous execution/progress: 🟡 Partial. Uses FastAPI background tasks and DB job records, not Celery/Redis.

## Export System

- Lecture Markdown/PDF/DOCX: ✅ Implemented.
- Course PDF/DOCX: ✅ Implemented.
- Course Markdown: ✅ Implemented.
- Obsidian ZIP: ✅ Implemented.
- Export quality: 🟡 Basic formatting; generated files contain notes when notes exist.

## Frontend

- Dashboard/import/course/lecture/transcript/notes screens: 🟡 Implemented but sparse.
- Generate Notes/Save/export buttons: 🟡 Implemented for basic lecture flow.
- Batch processing and job display: 🟡 Partial. Course page can start/resume and poll progress. Loading/error states remain basic.
- Build: ✅ Verified after adding Vite/TypeScript config.

## End-to-End Flow

```text
NPTEL URL        -> partial, fixture-verified and live-limited
YouTube URL      -> working for lecture creation
lecture          -> working
caption/transcript -> partial, official links when discoverable plus YouTube fallback
cleaning         -> working
Gemini           -> partial, requires real key/model
notes            -> partial, mocked tests pass
editor           -> working basic edit/save
Markdown         -> working lecture export
PDF/DOCX         -> working basic exports
Obsidian         -> working basic course ZIP
week synthesis   -> working in mocked tests
course synthesis -> working in mocked tests
```

## Highest Priority Next Steps

1. Add parser variants for current NPTEL client-rendered and login-gated course structures.
2. Add a real manual workflow test with a Gemini key and a small course/week whose lecture links are publicly discoverable.
3. Add cancellation/pause controls for long jobs.
4. Replace `datetime.utcnow()` with timezone-aware UTC timestamps.
5. Add richer frontend error/loading states and individual lecture retry.
