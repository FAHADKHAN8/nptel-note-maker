import json
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup


TIMING_RE = re.compile(
    r"(?P<start>(?:\d{2}:)?\d{2}:\d{2}[.,]\d{3})\s*-->\s*"
    r"(?P<end>(?:\d{2}:)?\d{2}:\d{2}[.,]\d{3})(?:\s+.*)?$"
)


@dataclass(frozen=True)
class VttSegment:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class ParsedVtt:
    text: str
    segments: list[VttSegment]


def parse_vtt(payload: str) -> ParsedVtt:
    text = _unwrap_json_string(payload).replace("\ufeff", "")
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n"))
    segments: list[VttSegment] = []
    previous = ""
    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines or lines[0].upper().startswith(("WEBVTT", "NOTE", "STYLE", "REGION")):
            lines = lines[1:]
        timing_index = next((index for index, line in enumerate(lines) if TIMING_RE.match(line)), None)
        if timing_index is None:
            continue
        match = TIMING_RE.match(lines[timing_index])
        if not match:
            continue
        cue_text = _clean_cue_text(" ".join(lines[timing_index + 1 :]))
        if not cue_text or cue_text == previous:
            continue
        try:
            segments.append(VttSegment(start=_timestamp(match.group("start")), end=_timestamp(match.group("end")), text=cue_text))
            previous = cue_text
        except ValueError:
            continue
    return ParsedVtt(text=" ".join(segment.text for segment in segments).strip(), segments=segments)


def _unwrap_json_string(payload: str) -> str:
    stripped = payload.strip()
    if not stripped:
        return ""
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        return payload
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("vtt", "transcript", "data", "content"):
            if isinstance(value.get(key), str):
                return value[key]
    return payload


def _timestamp(value: str) -> float:
    parts = value.replace(",", ".").split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    raise ValueError(value)


def _clean_cue_text(value: str) -> str:
    soup = BeautifulSoup(value, "lxml")
    text = soup.get_text(" ")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
