from sqlalchemy.orm import Session
from ..config import Settings
from ..errors import AppError
from ..models import GeneratedChunkCache, Lecture, Note, Transcript
from ..models.enums import ProcessingState, TranscriptSource
from ..services.caption_client import CaptionClient
from ..services.gemini_service import GeminiService
from ..services.transcript_cleaner import clean_transcript
from ..services.transcript_chunker import chunk_transcript
from .hashing import stable_hash
from .transcript_resolver import TranscriptResolver


class NotesPipeline:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def extract_youtube_transcript(self, db: Session, lecture: Lecture) -> Transcript:
        if not lecture.youtube_video_id:
            raise AppError("TRANSCRIPT_NOT_FOUND", "This lecture does not have a YouTube video ID.", 404)
        payload = await CaptionClient(self.settings).fetch(lecture.youtube_video_id)
        cleaned = clean_transcript(payload.get("transcript", ""), payload.get("segments", []))
        transcript = lecture.transcript or Transcript(lecture_id=lecture.id, source=TranscriptSource.youtube_captions)
        transcript.source = TranscriptSource.youtube_captions
        transcript.language = payload.get("language", "en")
        transcript.raw_text = payload.get("transcript", "")
        transcript.cleaned_text = cleaned.text
        transcript.content_hash = stable_hash(cleaned.text)
        transcript.segments_json = [segment.model_dump() for segment in cleaned.segments]
        transcript.character_count = len(cleaned.text)
        transcript.word_count = len(cleaned.text.split())
        lecture.status = ProcessingState.transcript_found
        db.add(transcript)
        db.commit()
        db.refresh(transcript)
        return transcript

    async def resolve_transcript(self, db: Session, lecture: Lecture) -> Transcript:
        return await TranscriptResolver(self.settings).resolve(db, lecture)

    async def generate_notes(self, db: Session, lecture: Lecture, options: dict) -> Note:
        transcript = lecture.transcript
        if not transcript:
            transcript = await self.resolve_transcript(db, lecture)
        if not transcript.content_hash:
            transcript.content_hash = stable_hash(transcript.cleaned_text)
            db.add(transcript)
            db.commit()
        lecture.status = ProcessingState.generating_notes
        db.commit()
        chunks = chunk_transcript(transcript.cleaned_text, transcript.segments_json, self.settings.transcript_chunk_size, self.settings.transcript_chunk_overlap)
        gemini = GeminiService(self.settings)
        settings_hash = stable_hash({"options": options, "model": self.settings.gemini_model})
        existing_note = lecture.note
        if (
            existing_note
            and not existing_note.is_user_edited
            and existing_note.source_transcript_hash == transcript.content_hash
            and existing_note.prompt_version == gemini.lecture_prompt_version
            and existing_note.model_name == self.settings.gemini_model
            and existing_note.generation_settings_hash == settings_hash
        ):
            lecture.status = ProcessingState.completed
            db.commit()
            return existing_note

        chunk_notes: list[str] = []
        for chunk in chunks:
            chunk_hash = stable_hash({"text": chunk.text, "start": chunk.start_seconds, "end": chunk.end_seconds})
            cached = (
                db.query(GeneratedChunkCache)
                .filter(
                    GeneratedChunkCache.lecture_id == lecture.id,
                    GeneratedChunkCache.chunk_index == chunk.index,
                    GeneratedChunkCache.chunk_hash == chunk_hash,
                    GeneratedChunkCache.prompt_version == gemini.chunk_prompt_version,
                    GeneratedChunkCache.model_name == self.settings.gemini_model,
                )
                .one_or_none()
            )
            if not cached:
                cached = GeneratedChunkCache(
                    lecture_id=lecture.id,
                    chunk_index=chunk.index,
                    chunk_hash=chunk_hash,
                    prompt_version=gemini.chunk_prompt_version,
                    model_name=self.settings.gemini_model,
                    generated_summary=await gemini.generate_chunk_summary(chunk=chunk, options=options),
                )
                db.add(cached)
                db.commit()
            chunk_notes.append(cached.generated_summary)

        markdown = await gemini.synthesize_lecture_notes(
            lecture_title=lecture.title,
            course_title=lecture.course.title,
            chunk_notes=chunk_notes,
            source_info={"transcript_source": transcript.source, "youtube_url": lecture.youtube_url, "nptel_url": lecture.nptel_url},
        )
        note = lecture.note or Note(lecture_id=lecture.id, title=lecture.title)
        note.content_markdown = markdown
        note.generation_style = options.get("detail_level", "detailed")
        note.model_name = self.settings.gemini_model
        note.prompt_version = gemini.lecture_prompt_version
        note.source_transcript_hash = transcript.content_hash
        note.generation_settings_hash = settings_hash
        note.is_user_edited = False
        lecture.status = ProcessingState.completed
        db.add(note)
        db.commit()
        db.refresh(note)
        return note
