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

Live NPTEL/SWAYAM course metadata endpoints are not fully mapped yet. Current automated verification uses fixtures/mocks. Static HTML parsing is known to be insufficient for some client-rendered pages, so the next parser step is to identify anonymous structured metadata sources before considering browser automation.
