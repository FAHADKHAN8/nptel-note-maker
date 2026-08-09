import fitz
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from urllib.parse import quote

from ..config import Settings
from ..errors import AppError
from ..models import Lecture, Transcript
from ..models.enums import ProcessingState, TranscriptSource
from .caption_client import CaptionClient
from .hashing import stable_hash
from .transcript_cleaner import clean_transcript
from .vtt_parser import parse_vtt


class TranscriptResolver:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def resolve(self, db: Session, lecture: Lecture) -> Transcript:
        if lecture.transcript and lecture.transcript.cleaned_text and lecture.transcript.content_hash:
            return lecture.transcript
        if lecture.transcript_url:
            try:
                return await self._official_transcript(db, lecture)
            except AppError as exc:
                lecture.error_message = f"Official transcript failed: {exc.message}"
                db.commit()
        if lecture.youtube_video_id:
            return await self._youtube_transcript(db, lecture)
        lecture.status = ProcessingState.transcript_unavailable
        lecture.error_message = "No official transcript or YouTube captions were available."
        db.commit()
        raise AppError("TRANSCRIPT_NOT_FOUND", lecture.error_message, 404)

    async def _official_transcript(self, db: Session, lecture: Lecture) -> Transcript:
        headers = {"User-Agent": "NPTEL-AI-Notes-Generator/1.0 personal-study-tool"}
        try:
            async with httpx.AsyncClient(timeout=self.settings.scraper_timeout, headers=headers, follow_redirects=True) as client:
                response = await self._fetch_official(client, lecture.transcript_url)
        except httpx.HTTPError as exc:
            raise AppError("OFFICIAL_TRANSCRIPT_UNAVAILABLE", "Official transcript request failed.", 502) from exc
        if response.is_error:
            raise AppError("OFFICIAL_TRANSCRIPT_UNAVAILABLE", "Official transcript returned an error.", 502)
        content_type = response.headers.get("content-type", "").lower()
        if "text/vtt" in content_type or lecture.transcript_url.lower().endswith(".vtt") or response.text.lstrip().startswith(("WEBVTT", '"WEBVTT')):
            parsed = parse_vtt(response.text)
            raw = parsed.text
            source = TranscriptSource.nptel_vtt
            if not raw.strip():
                raise AppError("OFFICIAL_VTT_EMPTY", "Official VTT did not contain usable text.", 404)
            cleaned = clean_transcript(raw, [{"start": s.start, "duration": max(0, s.end - s.start), "text": s.text} for s in parsed.segments])
            return self._save(db, lecture, source, response.text, cleaned.text, [s.model_dump() for s in cleaned.segments], lecture.transcript_url)
        if "pdf" in content_type or lecture.transcript_url.lower().endswith(".pdf"):
            raw = self._pdf_text(response.content)
            source = TranscriptSource.nptel_pdf
        else:
            raw = self._html_text(response.text)
            source = TranscriptSource.nptel_html
        if not raw.strip():
            raise AppError("OFFICIAL_TRANSCRIPT_EMPTY", "Official transcript did not contain usable text.", 404)
        cleaned = clean_transcript(raw)
        return self._save(db, lecture, source, raw, cleaned.text, [], lecture.transcript_url)

    async def _fetch_official(self, client: httpx.AsyncClient, transcript_url: str) -> httpx.Response:
        response = await client.get(transcript_url)
        if not response.is_error:
            return response
        if transcript_url.lower().endswith(".vtt"):
            proxy = "https://onlinecourses.nptel.ac.in/e-learning/api/transcript?vttUrl=" + quote(transcript_url, safe="")
            proxied = await client.get(proxy)
            if not proxied.is_error:
                return proxied
        return response

    async def _youtube_transcript(self, db: Session, lecture: Lecture) -> Transcript:
        try:
            payload = await CaptionClient(self.settings).fetch(lecture.youtube_video_id)
        except AppError as exc:
            lecture.status = ProcessingState.transcript_unavailable
            lecture.error_message = exc.message
            db.commit()
            raise
        cleaned = clean_transcript(payload.get("transcript", ""), payload.get("segments", []))
        return self._save(db, lecture, TranscriptSource.youtube_captions, payload.get("transcript", ""), cleaned.text, [s.model_dump() for s in cleaned.segments], lecture.youtube_url, payload.get("language", "en"))

    def _save(self, db: Session, lecture: Lecture, source: str, raw: str, cleaned_text: str, segments: list[dict], source_url: str | None, language: str = "en") -> Transcript:
        transcript = lecture.transcript or Transcript(lecture_id=lecture.id, source=source)
        transcript.source = source
        transcript.language = language
        transcript.raw_text = raw
        transcript.cleaned_text = cleaned_text
        transcript.content_hash = stable_hash(cleaned_text)
        transcript.segments_json = segments
        transcript.character_count = len(cleaned_text)
        transcript.word_count = len(cleaned_text.split())
        transcript.source_url = source_url
        lecture.status = ProcessingState.transcript_found
        lecture.error_message = None
        db.add(transcript)
        db.commit()
        db.refresh(transcript)
        return transcript

    def _html_text(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        return soup.get_text(" ")

    def _pdf_text(self, data: bytes) -> str:
        with fitz.open(stream=data, filetype="pdf") as doc:
            return "\n".join(page.get_text() for page in doc)
