# NPTEL Data Flow

Safe technical notes only. No cookies, authorization headers, account data, or private browser state are required or stored.

## Current Implemented Flow

```text
NPTEL course URL
  -> GenericNptelParser
  -> visible HTML lecture links
  -> Course + Lecture rows
  -> TranscriptResolver
       -> existing stored transcript
       -> official NPTEL transcript URL when discovered
            -> direct VTT fetch first for .vtt
            -> NPTEL /e-learning/api/transcript?vttUrl=... proxy if direct VTT fails
            -> HTML/PDF text extraction for non-VTT links
       -> YouTube caption service fallback when video ID is discovered
  -> transcript cleaner + hash
  -> chunk cache + Gemini lecture notes
  -> week artifacts from lecture notes
  -> course artifact from week notes
  -> Markdown/PDF/DOCX/Obsidian exports
```

## URL And ID Handling

The parser validates NPTEL HTTPS URLs and supports current e-learning lesson query parameters:

```text
https://onlinecourses.nptel.ac.in/e-learning/course/noc26_ge93?unitId=17&lessonId=18
```

Persisted fields keep external identifiers separate from display ordering:

```text
external_unit_id = 17
external_lesson_id = 18
week_number = logical course week
lecture_number = logical course lecture order
```

## Transcript Handling

Official VTT parsing supports `WEBVTT` headers, timestamped cues, cue identifiers/settings, multiline text, HTML-like tags, JSON-wrapped VTT strings, malformed individual cues, adjacent duplicate removal, and Unicode.

YouTube fallback uses the existing Node caption service and public captions only. The application does not download video or audio.

## Unknowns

## Live Anonymous Boundary Checked On 2026-08-09

Checked URL:

```text
https://onlinecourses.nptel.ac.in/e-learning/course/noc26_ge93
```

Observed:

- The page itself returns anonymous HTTP 200 and is a Next.js app.
- The client bundle references `/e-learning/api/courseoutline?course_id=...` as the structured course source containing `course_name`, `units`, `lessons`, `order`, lesson IDs, video IDs, and `video_subtitles`.
- Anonymous `GET /e-learning/api/courseoutline?course_id=noc26_ge93` returns JSON status `401` with a Swayam login URL payload.
- Anonymous `GET /e-learning/api/lesson?course_id=noc26_ge93&unit_id=17&lesson_id=18` returns `{"content":"not visible"}`.
- Anonymous `GET /e-learning/api/announcement?course_id=noc26_ge93` returns public release announcements. These expose released week entry URLs such as `/noc26_ge93/unit?unit=17&lesson=18`, but not the full lesson list, lecture titles, VTT URLs, or YouTube video IDs.

Current implementation therefore uses:

1. `courseoutline` when it is accessible, preserving full structured metadata.
2. Announcement fallback when `courseoutline` is anonymous-401, importing only the released entry links and external IDs that are actually public.

Do not treat the announcement fallback as full course discovery.
