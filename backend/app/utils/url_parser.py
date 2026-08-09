import re
from urllib.parse import parse_qs, urlparse, urlunparse
from ..errors import AppError

NPTEL_HOSTS = {"nptel.ac.in", "www.nptel.ac.in", "onlinecourses.nptel.ac.in", "archive.nptel.ac.in"}
YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def validate_nptel_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme != "https" or parsed.hostname not in NPTEL_HOSTS:
        raise AppError("INVALID_NPTEL_URL", "Please enter a valid HTTPS NPTEL course URL.")
    if parsed.hostname == "www.nptel.ac.in":
        parsed = parsed._replace(netloc="nptel.ac.in")
        return urlunparse(parsed)
    return url.strip()


def extract_youtube_video_id(url_or_id: str) -> str:
    value = url_or_id.strip()
    if YOUTUBE_ID_RE.fullmatch(value):
        return value
    parsed = urlparse(value)
    host = parsed.hostname or ""
    if host.endswith("youtu.be"):
        candidate = parsed.path.strip("/").split("/")[0]
    elif "youtube.com" in host:
        candidate = parse_qs(parsed.query).get("v", [""])[0]
        if not candidate and "/embed/" in parsed.path:
            candidate = parsed.path.split("/embed/", 1)[1].split("/", 1)[0]
    else:
        candidate = ""
    if not YOUTUBE_ID_RE.fullmatch(candidate):
        raise AppError("INVALID_YOUTUBE_VIDEO_ID", "A valid YouTube video ID was not found.")
    return candidate
