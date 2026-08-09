from enum import StrEnum


class ProcessingState(StrEnum):
    pending = "pending"
    importing = "importing"
    processing = "processing"
    extracting = "extracting"
    transcript_found = "transcript_found"
    transcript_unavailable = "transcript_unavailable"
    generating_notes = "generating_notes"
    completed = "completed"
    partial = "partial"
    failed = "failed"
    cancelled = "cancelled"


class TranscriptSource(StrEnum):
    nptel_html = "nptel_html"
    nptel_pdf = "nptel_pdf"
    nptel_vtt = "nptel_vtt"
    nptel_subtitles = "nptel_subtitles"
    youtube_captions = "youtube_captions"
    unavailable = "unavailable"
