from pydantic import BaseModel
from .common import ORMModel


class TranscriptUpdate(BaseModel):
    cleaned_text: str


class TranscriptRead(ORMModel):
    id: int
    lecture_id: int
    source: str
    language: str
    raw_text: str
    cleaned_text: str
    content_hash: str | None
    segments_json: list[dict]
    character_count: int
    word_count: int
    source_url: str | None
