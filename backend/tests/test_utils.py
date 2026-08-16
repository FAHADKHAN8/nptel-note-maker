import pytest
from app.services.transcript_cleaner import clean_transcript
from app.services.transcript_chunker import chunk_transcript
from app.utils.security import redact_secret, redact_secrets, sanitize_filename
from app.utils.url_parser import extract_youtube_video_id, validate_nptel_url


def test_nptel_url_validation():
    assert validate_nptel_url("https://nptel.ac.in/courses/1")
    with pytest.raises(Exception):
        validate_nptel_url("http://localhost/admin")


def test_youtube_video_id_extraction():
    assert extract_youtube_video_id("https://www.youtube.com/watch?v=abcdefghijk") == "abcdefghijk"
    assert extract_youtube_video_id("abcdefghijk") == "abcdefghijk"


def test_clean_transcript_removes_noise_and_duplicates():
    cleaned = clean_transcript("", [{"text": "Hello&nbsp;world"}, {"text": "Hello world"}, {"text": "[Music]"}, {"text": "Next point"}])
    assert cleaned.text == "Hello world. Next point"


def test_chunk_transcript():
    chunks = chunk_transcript("One sentence. Two sentence. Three sentence.", max_chars=20, overlap=3)
    assert len(chunks) > 1


def test_filename_sanitization():
    assert sanitize_filename("A/B:C*") == "A-B-C"


def test_secret_redaction():
    assert redact_secret("Cookie token=secret-value failed", "token=secret-value") == "Cookie [REDACTED] failed"


def test_nested_secret_redaction():
    secret = "SID=local-secret"
    value = {"message": f"failed with {secret}", "items": [secret, "safe"]}
    assert redact_secrets(value, [secret]) == {"message": "failed with [REDACTED]", "items": ["[REDACTED]", "safe"]}
