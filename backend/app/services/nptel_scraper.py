import asyncio
import html
import json
import re
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import parse_qs, urljoin, urlparse
import httpx
from bs4 import BeautifulSoup
from ..config import Settings
from ..errors import AppError
from ..utils.security import redact_secret
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
        client = NptelClient(self.settings)
        api_course = await client.fetch_course_outline(safe_url)
        if api_course:
            return api_course
        announcement_course = await client.fetch_announcement_outline(safe_url)
        if announcement_course:
            return announcement_course
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
            try:
                return self.parse_html(fallback.text, safe_url)
            except AppError:
                if client.last_courseoutline_auth_required:
                    raise AppError(
                        "NPTEL_AUTH_REQUIRED",
                        "NPTEL courseoutline requires a logged-in browser session. Set NPTEL_COOKIE locally to enable authenticated course discovery.",
                        401,
                    )
                raise

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


class NptelClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.headers = {"User-Agent": "NPTEL-AI-Notes-Generator/1.0 personal-study-tool"}
        self.last_courseoutline_auth_required = False

    async def fetch_course_outline(self, url: str) -> ParsedCourse | None:
        safe_url = validate_nptel_url(url)
        slug = self._course_slug(safe_url)
        if not slug:
            return None
        endpoint = f"https://onlinecourses.nptel.ac.in/e-learning/api/courseoutline?course_id={slug}"
        data = await self._get_json(endpoint, authenticated=False)
        if data is None:
            return None
        if self._auth_required(data):
            self.last_courseoutline_auth_required = True
            if not getattr(self.settings, "nptel_cookie", ""):
                return None
            data = await self._get_json(endpoint, authenticated=True)
            if data is None or self._auth_required(data):
                return None
            self.last_courseoutline_auth_required = False
        return self.parse_course_outline(data, safe_url)

    async def _get_json(self, url: str, authenticated: bool = False) -> dict | None:
        headers = {**self.headers, "Accept": "application/json"}
        if authenticated and getattr(self.settings, "nptel_cookie", ""):
            headers["Cookie"] = self.settings.nptel_cookie
        try:
            async with httpx.AsyncClient(timeout=self.settings.scraper_timeout, headers=headers, follow_redirects=True) as client:
                response = await client.get(url)
        except httpx.HTTPError:
            return None
        if response.is_error:
            return None
        try:
            return response.json()
        except json.JSONDecodeError:
            return None

    def _auth_required(self, data: dict) -> bool:
        return data.get("status") == 401 or "loginurl" in str(data.get("payload", "")).lower()

    def redact(self, value: str) -> str:
        return redact_secret(value, getattr(self.settings, "nptel_cookie", ""))

    async def fetch_announcement_outline(self, url: str) -> ParsedCourse | None:
        safe_url = validate_nptel_url(url)
        slug = self._course_slug(safe_url)
        if not slug:
            return None
        endpoint = f"https://onlinecourses.nptel.ac.in/e-learning/api/announcement?course_id={slug}"
        async with httpx.AsyncClient(timeout=self.settings.scraper_timeout, headers={**self.headers, "Accept": "application/json"}, follow_redirects=True) as client:
            response = await client.get(endpoint)
        if response.is_error:
            return None
        try:
            data = response.json()
        except json.JSONDecodeError:
            return None
        return self.parse_announcements(data, safe_url, slug)

    def parse_course_outline(self, data: dict, course_url: str) -> ParsedCourse | None:
        payload = self._payload(data)
        if not isinstance(payload, dict):
            return None
        course_info = payload.get("course_info") if isinstance(payload.get("course_info"), dict) else {}
        course_data = course_info.get("course") if isinstance(course_info.get("course"), dict) else {}
        title = payload.get("course_name") or course_data.get("title") or course_data.get("name") or "NPTEL Course"
        units = self._values(payload.get("units"))
        lessons = self._values(payload.get("lessons"))
        order = self._values(payload.get("order"))
        lesson_by_scope = {(str(item.get("unit_id")), str(item.get("lesson_id"))): item for item in lessons if isinstance(item, dict)}
        order_by_unit = {str(item.get("id")): item for item in order if isinstance(item, dict)}
        parsed: list[ParsedLecture] = []
        lecture_number = 0
        for week_number, unit in enumerate(sorted([u for u in units if isinstance(u, dict)], key=lambda u: int(u.get("unit_id") or u.get("id") or 0)), start=1):
            unit_id = str(unit.get("unit_id") or unit.get("id") or "")
            children = order_by_unit.get(unit_id, {}).get("children") or []
            ordered_lessons = []
            for child in children:
                if not isinstance(child, dict) or child.get("section") != "lesson":
                    continue
                lesson = lesson_by_scope.get((unit_id, str(child.get("id"))))
                if lesson:
                    ordered_lessons.append(lesson)
            if not ordered_lessons:
                ordered_lessons = sorted([lesson for lesson in lessons if str(lesson.get("unit_id")) == unit_id], key=lambda lesson: int(lesson.get("lesson_id") or 0))
            for lesson in ordered_lessons:
                lecture_number += 1
                video_id, youtube_url = self._youtube_from_lesson(lesson)
                parsed.append(ParsedLecture(
                    week_number=week_number,
                    lecture_number=lecture_number,
                    title=str(lesson.get("title") or lesson.get("lesson_title") or f"Lecture {lecture_number}"),
                    nptel_url=f"https://onlinecourses.nptel.ac.in/e-learning/course/{self._course_slug(course_url)}?unitId={unit_id}&lessonId={lesson.get('lesson_id')}",
                    external_unit_id=unit_id,
                    external_lesson_id=str(lesson.get("lesson_id")),
                    youtube_url=youtube_url,
                    youtube_video_id=video_id,
                    transcript_url=self._vtt_from_lesson(lesson),
                ))
        if not parsed:
            return None
        return ParsedCourse(
            title=str(title),
            instructor=course_data.get("instructor") or course_data.get("instructor_name"),
            institute=course_data.get("institute") or course_data.get("institution"),
            course_code=course_data.get("course_code"),
            description=course_data.get("description"),
            image_url=course_data.get("image_url") or course_data.get("thumbnail_url"),
            course_url=course_url,
            lectures=parsed,
        )

    def parse_announcements(self, data: dict, course_url: str, slug: str) -> ParsedCourse | None:
        lectures: list[ParsedLecture] = []
        seen: set[tuple[str, str]] = set()
        title = "NPTEL Course"
        for item in data.get("announcements", []):
            text = BeautifulSoup(item.get("html", ""), "lxml").get_text(" ", strip=True)
            title_match = re.search(r"lecture videos.+?course\s+[\"“]?([^\\.\"”]+)[\"”]?", text, re.I)
            if title_match:
                title = self._clean(title_match.group(1).strip(" \"“”"))
            week_match = re.search(r"Week(?:-No)?\s*0*(\d+)", text, re.I)
            html_text = html.unescape(item.get("html", ""))
            for unit_id, lesson_id in re.findall(rf"{re.escape(slug)}/unit\?unit=(\d+)&lesson=(\d+)", html_text):
                if (unit_id, lesson_id) in seen:
                    continue
                seen.add((unit_id, lesson_id))
                lectures.append(ParsedLecture(
                    week_number=int(week_match.group(1)) if week_match else len(lectures) + 1,
                    lecture_number=0,
                    title=f"Week {week_match.group(1)} released lecture entry" if week_match else f"Lecture {lecture_number}",
                    nptel_url=f"https://onlinecourses.nptel.ac.in/e-learning/course/{slug}?unitId={unit_id}&lessonId={lesson_id}",
                    external_unit_id=unit_id,
                    external_lesson_id=lesson_id,
                ))
        if not lectures:
            return None
        lectures.sort(key=lambda item: (item.week_number, int(item.external_unit_id or 0), int(item.external_lesson_id or 0)))
        for index, lecture in enumerate(lectures, start=1):
            lecture.lecture_number = index
        return ParsedCourse(title=title, instructor=None, institute=None, course_code=slug, description=None, image_url=None, course_url=course_url, lectures=lectures)

    def _payload(self, data: dict) -> object:
        payload = data.get("payload", data)
        if isinstance(payload, str):
            try:
                return json.loads(payload)
            except json.JSONDecodeError:
                return data
        return payload

    def _values(self, value: object) -> list:
        if isinstance(value, dict):
            return list(value.values())
        if isinstance(value, list):
            return value
        return []

    def _vtt_from_lesson(self, lesson: dict) -> str | None:
        subtitles = lesson.get("video_subtitles")
        if isinstance(subtitles, str):
            try:
                subtitles = json.loads(subtitles)
            except json.JSONDecodeError:
                return subtitles if subtitles.endswith(".vtt") else None
        if isinstance(subtitles, dict):
            preferred = lesson.get("preferred_vtt_lang") or "en"
            value = subtitles.get(preferred) or next(iter(subtitles.values()), None)
            return value if isinstance(value, str) else None
        return None

    def _youtube_from_lesson(self, lesson: dict) -> tuple[str | None, str | None]:
        for key in ("youtube_url", "video_url", "url"):
            value = lesson.get(key)
            if isinstance(value, str):
                try:
                    video_id = extract_youtube_video_id(value)
                    return video_id, f"https://www.youtube.com/watch?v={video_id}"
                except AppError:
                    pass
        value = lesson.get("video_id")
        if isinstance(value, str):
            try:
                video_id = extract_youtube_video_id(value)
                return video_id, f"https://www.youtube.com/watch?v={video_id}"
            except AppError:
                return value, None
        return None, None

    def _course_slug(self, url: str) -> str | None:
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]
        if "course" in parts:
            index = parts.index("course")
            if index + 1 < len(parts):
                return parts[index + 1]
        if parts:
            return parts[0]
        return None

    def _clean(self, value: str) -> str:
        return " ".join(value.split())
