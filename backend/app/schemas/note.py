from pydantic import BaseModel
from .common import ORMModel


class NoteGenerationOptions(BaseModel):
    detail_level: str = "detailed"
    include_learning_objectives: bool = True
    include_examples: bool = True
    include_exam_points: bool = True
    include_revision_summary: bool = True
    include_mcqs: bool = True
    include_descriptive_questions: bool = True
    include_timestamps: bool = True


class NoteUpdate(BaseModel):
    content_markdown: str


class NoteRead(ORMModel):
    id: int
    lecture_id: int
    title: str
    content_markdown: str
    generation_style: str
    model_name: str | None
    prompt_version: str
    source_transcript_hash: str | None
    generation_settings_hash: str | None
    is_user_edited: bool
