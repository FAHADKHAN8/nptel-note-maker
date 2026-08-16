# Graph Report - NPTEL NOTES MAKER  (2026-08-16)

## Corpus Check
- 79 files · ~20,698 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 477 nodes · 1033 edges · 37 communities (33 shown, 4 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 110 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0e4675e9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]

## God Nodes (most connected - your core abstractions)
1. `AppError` - 49 edges
2. `GeminiService` - 33 edges
3. `NotesPipeline` - 25 edges
4. `NptelClient` - 25 edges
5. `TranscriptResolver` - 24 edges
6. `Base` - 22 edges
7. `CaptionClient` - 20 edges
8. `CourseProcessor` - 20 edges
9. `FakeSettings` - 19 edges
10. `NPTEL AI Notes Generator` - 18 edges

## Surprising Connections (you probably didn't know these)
- `test_clean_transcript_removes_noise_and_duplicates()` --calls--> `clean_transcript()`  [INFERRED]
  backend/tests/test_utils.py → backend/app/services/transcript_cleaner.py
- `test_filename_sanitization()` --calls--> `sanitize_filename()`  [INFERRED]
  backend/tests/test_utils.py → backend/app/utils/security.py
- `test_nptel_url_validation()` --calls--> `validate_nptel_url()`  [INFERRED]
  backend/tests/test_utils.py → backend/app/utils/url_parser.py
- `test_youtube_video_id_extraction()` --calls--> `extract_youtube_video_id()`  [INFERRED]
  backend/tests/test_utils.py → backend/app/utils/url_parser.py
- `FakeCookieSettings` --uses--> `Base`  [INFERRED]
  backend/tests/test_course_processing_mvp.py → backend/app/database.py

## Import Cycles
- None detected.

## Communities (37 total, 4 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.09
Nodes (33): run_migrations_offline(), get_settings(), Settings, get_db(), app_error_handler(), AppError, Session, Session (+25 more)

### Community 1 - "Community 1"
Cohesion: 0.16
Nodes (17): Base, DeclarativeBase, GeneratedChunkCache, CourseArtifact, Course, ProcessingState, TranscriptSource, Lecture (+9 more)

### Community 2 - "Community 2"
Cohesion: 0.13
Nodes (20): Any, AsyncClient, Settings, Lecture, Session, Settings, Transcript, Lecture (+12 more)

### Community 3 - "Community 3"
Cohesion: 0.17
Nodes (11): Course, Lecture, Session, Settings, CourseArtifact, ProcessingJob, CourseProcessor, JobStage (+3 more)

### Community 4 - "Community 4"
Cohesion: 0.29
Nodes (18): Response, Session, Course, Lecture, course_docx(), course_md(), course_obsidian(), course_pdf() (+10 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (34): Session, Settings, BeautifulSoup, Protocol, CourseParser, GenericNptelParser, NptelClient, ParsedCourse (+26 more)

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (23): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+15 more)

### Community 7 - "Community 7"
Cohesion: 0.09
Nodes (21): dependencies, axios, lucide-react, react, react-dom, react-markdown, react-router-dom, @vitejs/plugin-react (+13 more)

### Community 8 - "Community 8"
Cohesion: 0.17
Nodes (20): Session, BaseModel, NoteGenerationOptions, course_lectures(), extract_transcript(), generate_notes(), get_lecture(), _lecture() (+12 more)

### Community 9 - "Community 9"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, allowSyntheticDefaultImports, esModuleInterop, forceConsistentCasingInFileNames, isolatedModules, jsx, lib (+10 more)

### Community 10 - "Community 10"
Cohesion: 0.11
Nodes (18): API Endpoints, Architecture, Authenticated NPTEL Courses, Contributing, Course Import And Processing, Ethical And Legal Notes, Example Curl, Features (+10 more)

### Community 11 - "Community 11"
Cohesion: 0.27
Nodes (6): api, CourseDetails(), Dashboard(), ImportCourse(), NotesEditor(), TranscriptViewer()

### Community 12 - "Community 12"
Cohesion: 0.14
Nodes (13): Batch Course Processing, Course Importing, End-to-End Flow, Export System, Frontend, Gemini Integration, Highest Priority Next Steps, Jobs (+5 more)

### Community 13 - "Community 13"
Cohesion: 0.14
Nodes (11): Settings, chunk_transcript(), TranscriptChunk, test_chunk_transcript(), test_clean_transcript_removes_noise_and_duplicates(), test_filename_sanitization(), test_nested_secret_redaction(), test_nptel_url_validation() (+3 more)

### Community 14 - "Community 14"
Cohesion: 0.18
Nodes (10): dependencies, express, he, youtube-captions-scraper, name, scripts, dev, start (+2 more)

### Community 15 - "Community 15"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 16 - "Community 16"
Cohesion: 0.29
Nodes (6): Current Implemented Flow, Live Anonymous Boundary Checked On 2026-08-09, NPTEL Data Flow, Transcript Handling, Unknowns, URL And ID Handling

### Community 17 - "Community 17"
Cohesion: 0.40
Nodes (4): Contributing, External Services, Local Checks, Secrets

### Community 18 - "Community 18"
Cohesion: 0.40
Nodes (3): app, port, timeoutMs

### Community 19 - "Community 19"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 20 - "Community 20"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 21 - "Community 21"
Cohesion: 0.50
Nodes (3): For /graphify explain, For /graphify path, graphify reference: query, path, explain

### Community 22 - "Community 22"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

## Knowledge Gaps
- **133 isolated node(s):** `Request`, `JSONResponse`, `CourseImportRequest`, `YouTubeLectureRequest`, `BackgroundTasks` (+128 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AppError` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 8`?**
  _High betweenness centrality (0.110) - this node is a cross-community bridge._
- **Why does `GeminiService` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 13`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Why does `NotesPipeline` connect `Community 3` to `Community 8`, `Community 1`, `Community 2`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `AppError` (e.g. with `FakeCookieSettings` and `FakeGemini`) actually correct?**
  _`AppError` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `GeminiService` (e.g. with `Course` and `Lecture`) actually correct?**
  _`GeminiService` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `NotesPipeline` (e.g. with `Course` and `Lecture`) actually correct?**
  _`NotesPipeline` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `NptelClient` (e.g. with `FakeCookieSettings` and `FakeGemini`) actually correct?**
  _`NptelClient` has 9 INFERRED edges - model-reasoned connections that need verification._