import re
from pydantic import BaseModel


class TranscriptChunk(BaseModel):
    index: int
    text: str
    start_seconds: float | None
    end_seconds: float | None


def chunk_transcript(text: str, segments: list[dict] | None = None, max_chars: int = 12000, overlap: int = 500) -> list[TranscriptChunk]:
    if segments:
        chunks: list[TranscriptChunk] = []
        current: list[str] = []
        start = end = None
        for segment in segments:
            seg_text = str(segment.get("text", "")).strip()
            if not seg_text:
                continue
            if start is None:
                start = segment.get("start")
            end = (segment.get("start") or 0) + (segment.get("duration") or 0)
            if sum(len(x) for x in current) + len(seg_text) > max_chars and current:
                chunks.append(TranscriptChunk(index=len(chunks), text=" ".join(current), start_seconds=start, end_seconds=end))
                tail = " ".join(current)[-overlap:]
                current = [tail, seg_text] if tail else [seg_text]
                start = segment.get("start")
            else:
                current.append(seg_text)
        if current:
            chunks.append(TranscriptChunk(index=len(chunks), text=" ".join(current), start_seconds=start, end_seconds=end))
        return chunks
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks, current = [], ""
    for sentence in sentences:
        if len(current) + len(sentence) > max_chars and current:
            chunks.append(TranscriptChunk(index=len(chunks), text=current.strip(), start_seconds=None, end_seconds=None))
            current = current[-overlap:] + " " + sentence
        else:
            current += " " + sentence
    if current.strip():
        chunks.append(TranscriptChunk(index=len(chunks), text=current.strip(), start_seconds=None, end_seconds=None))
    return chunks
