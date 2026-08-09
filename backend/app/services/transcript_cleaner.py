import html
import re
import unicodedata
from pydantic import BaseModel


class CaptionSegment(BaseModel):
    start: float | None = None
    duration: float | None = None
    text: str


class CleanedTranscript(BaseModel):
    text: str
    segments: list[CaptionSegment]


NOISE_RE = re.compile(r"^\s*(\[?music\]?|\[?applause\]?|\(music\)|♪+)\s*$", re.I)


def normalize_text(text: str) -> str:
    decoded = html.unescape(text)
    normalized = unicodedata.normalize("NFKC", decoded)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def clean_transcript(raw_text: str, segments: list[dict] | None = None) -> CleanedTranscript:
    cleaned_segments: list[CaptionSegment] = []
    previous = ""
    for item in segments or [{"text": raw_text}]:
        text = normalize_text(str(item.get("text", "")))
        if not text or NOISE_RE.fullmatch(text):
            continue
        if text == previous or (previous and text in previous):
            continue
        cleaned_segments.append(CaptionSegment(start=item.get("start"), duration=item.get("duration"), text=text))
        previous = text
    combined = " ".join(segment.text for segment in cleaned_segments)
    combined = re.sub(r"\s+([,.;:?!])", r"\1", combined)
    combined = re.sub(r"([a-z0-9])\s+([A-Z])", r"\1. \2", combined)
    return CleanedTranscript(text=combined.strip(), segments=cleaned_segments)
