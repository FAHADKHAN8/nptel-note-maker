from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .errors import AppError, app_error_handler
from .routers import courses, exports, jobs, lectures, notes, transcripts

settings = get_settings()

app = FastAPI(title=settings.app_name)
app.add_exception_handler(AppError, app_error_handler)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(courses.router)
app.include_router(lectures.router)
app.include_router(transcripts.router)
app.include_router(notes.router)
app.include_router(exports.router)
app.include_router(jobs.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}
