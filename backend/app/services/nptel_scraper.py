import asyncio
import re
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import parse_qs, urljoin, urlparse
import httpx
from bs4 import BeautifulSoup
from ..config import Settings
from ..errors import AppError
from ..utils.url_parser import extract_youtube_video_id, validate_nptel_url


@dataclass
class ParsedLecture:
    week_number: int
    lecture_number: int
    title: str
    nptel_url: str | None = None
    external_unit_id: str | None = None
    external_lesson_id: str | None = None
    youtube_url: str | None = None
    youtube_video_id: str | None = None
    transcript_url: str | None = None
    transcript_language: str | None = None


@dataclass
class ParsedCourse:
    title: str
    instructor: str | None
    institute: str | None
    course_code: str | None
    description: str | None
    image_url: str | None
    course_url: str
    lectures: list[ParsedLecture] = field(default_factory=list)


class CourseParser(Protocol):
    async def parse_course(self, url: str) -> ParsedCourse: ...


class GenericNptelParser:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def parse_course(self, url: str) -> ParsedCourse:
        safe_url = validate_nptel_url(url)
        headers = {"User-Agent": "NPTEL-AI-Notes-Generator/1.0 personal-study-tool"}
        async with httpx.AsyncClient(timeout=self.settings.scraper_timeout, headers=headers, follow_redirects=True) as client:
            response = await client.get(safe_url)
            if response.is_error or len(response.content) > 5_000_000:
                raise AppError("COURSE_EXTRACTION_FAILED", "Could not download the NPTEL course page.", 502)
        soup = BeautifulSoup(response.text, "lxml")
        try:
            return self.parse_html(response.text, safe_url)
        except AppError as exc:
            announcements_url = self._announcements_url(safe_url)
            if not announcements_url:
                raise
            async with httpx.AsyncClient(timeout=self.settings.scraper_timeout, headers=headers, follow_redirects=True) as client:
                fallback = await client.get(announcements_url)
            if fallback.is_error:
                raise exc
            return self.parse_html(fallback.text, safe_url)

    def parse_html(self, html: str, course_url: str) -> ParsedCourse:
        safe_url = validate_nptel_url(course_url)
        soup = BeautifulSoup(html, "lxml")
        title_node = soup.select_one("h1, h2, .course-title, [class*=course][class*=title]") or soup.find("title")
        title = self._clean(title_node.get_text(" ")) if title_node else "NPTEL Course"
        instructor = self._first_text(soup, [".instructor", "[class*=instructor]", "dt:-soup-contains('Instructor') + dd"])
        institute = self._first_text(soup, [".institute", ".institution", "[class*=institute]", "[class*=institution]"])
        code_match = re.search(r"\b([A-Z]{2,4}\d{3,4})\b", soup.get_text(" "))
        course_code = code_match.group(1) if code_match else None
        description_node = soup.select_one(".description, [class*=description], .about, [class*=overview]")
        image = soup.find("img")
        lectures: list[ParsedLecture] = []
        current_week = 1
        lecture_number = 0
        lecture_containers = soup.select(".lecture, [class*=lecture], li, tr")
        candidates = lecture_containers or soup.find_all("a", href=True)
        for node in candidates:
            text = self._clean(node.get_text(" "))
            inherited_week = self._week_from_ancestors(node)
            week_match = re.search(r"\b(?:week|module)\s*[-:]?\s*(\d+)\b", text, re.I)
            if week_match:
                current_week = int(week_match.group(1))
            links = node.find_all("a", href=True) if hasattr(node, "find_all") else []
            if getattr(node, "name", None) == "a" and node.get("href"):
                links = [node, *links]
            hrefs = [urljoin(safe_url, link["href"]) for link in links if link.get("href")]
            youtube_url = next((href for href in hrefs if "youtube.com" in href or "youtu.be" in href), None)
            transcript_url = next((href for href in hrefs if re.search(r"(transcript|subtitle|\.pdf|\.txt|\.html?)", href, re.I)), None)
            nptel_url = next((href for href in hrefs if "nptel.ac.in" in href and href != safe_url), None)
            lesson_url = next((href for href in hrefs if "lessonId=" in href or "lesson=" in href), None)
            is_lecture = youtube_url or transcript_url or lesson_url or re.search(r"\b(?:lecture|lec)\s*[-:]?\s*\d+", text, re.I)
            if not is_lecture:
                continue
            lecture_match = re.search(r"\b(?:lecture|lec)\s*[-:]?\s*(\d+)\b", text, re.I)
            title_text = re.sub(r"\b(?:watch|youtube|transcript|download|pdf)\b", " ", text, flags=re.I)
            title_text = self._clean(title_text) or f"Lecture {lecture_number + 1}"
            try:
                video_id = extract_youtube_video_id(youtube_url) if youtube_url else None
            except AppError:
                video_id = None
            if any(existing.youtube_video_id == video_id and video_id for existing in lectures):
                continue
            lecture_number += 1
            lecture_url = nptel_url or lesson_url
            unit_id, lesson_id = self._external_ids(lecture_url)
            lectures.append(ParsedLecture(
                week_number=int(week_match.group(1)) if week_match else inherited_week or current_week,
                lecture_number=int(lecture_match.group(1)) if lecture_match else lecture_number,
                title=title_text,
                nptel_url=lecture_url,
                external_unit_id=unit_id,
                external_lesson_id=lesson_id,
                youtube_url=youtube_url,
                youtube_video_id=video_id,
                transcript_url=transcript_url,
            ))
        if not lectures:
            raise AppError("LECTURES_NOT_FOUND", "No lecture links were found on this NPTEL page.", 404)
        return ParsedCourse(
            title=title,
            instructor=instructor,
            institute=institute,
            course_code=course_code,
            description=self._clean(description_node.get_text(" ")) if description_node else None,
            image_url=urljoin(safe_url, image.get("src")) if image and image.get("src") else None,
            course_url=safe_url,
            lectures=lectures,
        )

    def _clean(self, value: str) -> str:
        return " ".join(value.split())

    def _first_text(self, soup: BeautifulSoup, selectors: list[str]) -> str | None:
        for selector in selectors:
            node = soup.select_one(selector)
            if node:
                text = self._clean(node.get_text(" "))
                if text:
                    return text
        return None

    def _external_ids(self, url: str | None) -> tuple[str | None, str | None]:
        if not url:
            return None, None
        query = parse_qs(urlparse(url).query)
        unit_id = (query.get("unitId") or query.get("unit") or [""])[0] or None
        lesson_id = (query.get("lessonId") or query.get("lesson") or [""])[0] or None
        return unit_id, lesson_id

    def _announcements_url(self, url: str) -> str | None:
        parsed = urlparse(url)
        if parsed.hostname != "onlinecourses.nptel.ac.in":
            return None
        course_key = parsed.path.strip("/").split("/")[0]
        return f"https://onlinecourses.nptel.ac.in/{course_key}/announcements" if course_key else None

    def _week_from_ancestors(self, node) -> int | None:
        parent = getattr(node, "parent", None)
        while parent:
            heading = parent.find(["h2", "h3", "h4"]) if hasattr(parent, "find") else None
            text = self._clean(heading.get_text(" ") if heading else parent.get_text(" ") if hasattr(parent, "get_text") else "")
            match = re.search(r"\b(?:week|module)\s*[-:]?\s*(\d+)\b", text, re.I)
            if match:
                return int(match.group(1))
            parent = getattr(parent, "parent", None)
        return None
