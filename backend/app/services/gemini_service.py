import asyncio
from pathlib import Path
from google import genai
from google.genai import types
from ..config import Settings
from ..errors import AppError
from ..prompts import CHUNK_PROMPT_VERSION, COURSE_PROMPT_VERSION, LECTURE_PROMPT_VERSION, WEEK_PROMPT_VERSION
from .transcript_chunker import TranscriptChunk


class GeminiService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = genai.Client(api_key=settings.gemini_api_key) if settings.gemini_api_key else None

    def _prompt(self, name: str) -> str:
        return (Path(__file__).parents[1] / "prompts" / name).read_text(encoding="utf-8")

    async def _generate(self, contents: str, system: str) -> str:
        if not self.client or not self.settings.gemini_model:
            raise AppError("GEMINI_GENERATION_FAILED", "Gemini is not configured. Set GEMINI_API_KEY and GEMINI_MODEL.", 503)
        delay = 1.0
        for attempt in range(self.settings.gemini_max_retries + 1):
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.client.models.generate_content,
                        model=self.settings.gemini_model,
                        contents=contents,
                        config=types.GenerateContentConfig(system_instruction=system),
                    ),
                    timeout=self.settings.gemini_request_timeout,
                )
                return response.text or ""
            except Exception as exc:
                message = str(exc).lower()
                if "quota" in message or "429" in message:
                    raise AppError("GEMINI_QUOTA_EXCEEDED", "Gemini quota was exceeded. Try again later.", 429) from exc
                if attempt >= self.settings.gemini_max_retries or "400" in message:
                    raise AppError("GEMINI_GENERATION_FAILED", "Gemini could not generate notes.", 502) from exc
                await asyncio.sleep(delay)
                delay *= 2
        raise AppError("GEMINI_GENERATION_FAILED", "Gemini could not generate notes.", 502)

    async def generate_lecture_notes(self, *, lecture_title: str, course_title: str, chunks: list[TranscriptChunk], options: dict, source_info: dict) -> str:
        chunk_prompt = self._prompt("chunk_notes.txt")
        merge_prompt = self._prompt("merge_notes.txt")
        final_prompt = self._prompt("final_notes.txt")
        chunk_notes = []
        for chunk in chunks:
            chunk_notes.append(await self._generate(f"Options: {options}\nChunk {chunk.index} [{chunk.start_seconds}-{chunk.end_seconds}]\n{chunk.text}", chunk_prompt))
        merged = await self._generate("\n\n".join(chunk_notes), merge_prompt)
        return await self._generate(f"Lecture: {lecture_title}\nCourse: {course_title}\nSource: {source_info}\n\n{merged}", final_prompt)

    async def generate_chunk_summary(self, *, chunk: TranscriptChunk, options: dict) -> str:
        return await self._generate(f"Options: {options}\nChunk {chunk.index} [{chunk.start_seconds}-{chunk.end_seconds}]\n{chunk.text}", self._prompt("chunk_notes.txt"))

    async def synthesize_lecture_notes(self, *, lecture_title: str, course_title: str, chunk_notes: list[str], source_info: dict) -> str:
        merged = await self._generate("\n\n".join(chunk_notes), self._prompt("merge_notes.txt"))
        return await self._generate(f"Lecture: {lecture_title}\nCourse: {course_title}\nSource: {source_info}\nPrompt: {LECTURE_PROMPT_VERSION}\n\n{merged}", self._prompt("final_notes.txt"))

    @property
    def chunk_prompt_version(self) -> str:
        return CHUNK_PROMPT_VERSION

    @property
    def lecture_prompt_version(self) -> str:
        return LECTURE_PROMPT_VERSION

    async def synthesize_week_notes(self, *, course_title: str, week_number: int, lecture_notes: list[str]) -> str:
        return await self._generate(f"Course: {course_title}\nWeek: {week_number}\n\n" + "\n\n".join(lecture_notes), self._prompt("week_synthesis.txt"))

    async def synthesize_course_notes(self, *, course_title: str, week_notes: list[str]) -> str:
        return await self._generate(f"Course: {course_title}\n\n" + "\n\n".join(week_notes), self._prompt("course_synthesis.txt"))

    @property
    def week_prompt_version(self) -> str:
        return WEEK_PROMPT_VERSION

    @property
    def course_prompt_version(self) -> str:
        return COURSE_PROMPT_VERSION
