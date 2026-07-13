# Google Scholar Scraper V2 Implementation Plan

## 1. Executive Summary

V2 should remain a lightweight Windows desktop application for extracting, ranking, reviewing, and exporting Google Scholar search results. The smallest useful product direction is:

> A lightweight desktop application for extracting, ranking, reviewing, and exporting Google Scholar search results, with local machine-learning-based relevance scoring and no LLM, GPU, external AI API, or model download requirement.

This repository is currently very small. The tracked project contains only `README.md` and `prog.py`. The current implementation is a single Tkinter script that builds Google Scholar URLs, requests each page synchronously, parses result blocks with BeautifulSoup, and writes title, authors, and link fields to an Excel file through pandas.

Milestone 1 is documentation and architecture only. No V2 feature is implemented by this plan.

## 2. Current Repository Baseline

Tracked files inspected:

- `README.md`
- `prog.py`

Repository structure:

```text
.
|-- README.md
`-- prog.py
```

Current Git history is minimal:

- `687aa78 Initial commit`
- `6824d55 Update README.md`
- `c8edf4d Add files via upload`

There are no dependency declaration files, package metadata files, tests, CI workflows, build scripts, release scripts, fixtures, or documentation files beyond the README.

## 3. Current Behavior

The current entrypoint is `prog.py`. Running the file creates a Tkinter window immediately at import/runtime and starts `window.mainloop()`.

Current user workflow:

1. Enter a Google Scholar query.
2. Enter the number of result pages.
3. Optionally choose an output folder.
4. Click `Extract Data`.
5. Wait while the GUI blocks during network requests and parsing.
6. Receive a status label saying extraction completed.
7. Find `scholar_articles.xlsx` in the chosen folder or current working directory.

Current scraping behavior:

- Builds URLs using string interpolation:
  `https://scholar.google.com/scholar?start={page*10}&q={query}&hl=en&as_sdt=0,5`
- Uses `requests.get(url)` without a session.
- Does not set explicit headers.
- Does not set a timeout.
- Does not validate status codes.
- Does not handle network exceptions.
- Parses all `div.gs_ri` result blocks.
- Extracts:
  - `h3.gs_rt` text as title
  - `div.gs_a` text as authors
  - first `a` tag `href` as link
- Does not extract snippet, cited-by count, publication year, venue, PDF link, or result position.
- Does not detect blocked pages, CAPTCHA pages, empty results, or parser drift.
- Does not remove duplicates.
- Exports only Excel.

Current GUI behavior:

- Uses Tkinter.
- Uses global widgets and callbacks.
- Runs scraping synchronously on the GUI thread.
- Does not validate empty query.
- Converts page count with `int()` directly, so invalid input raises an uncaught exception.
- Does not support progress, cancellation, partial results, or user-facing error categories.

## 4. Current Architecture

Current architecture is a single script with mixed responsibilities:

- HTTP request construction and execution
- HTML parsing
- result shaping
- Excel export
- GUI creation
- GUI callbacks
- file path construction
- application entrypoint

This makes the project easy to understand but hard to test. Importing the file starts the GUI, so unit tests cannot safely import scraping or export functions without launching the app.

## 5. Audit Findings

### Critical

No critical issues were found for a small personal desktop utility. The current tool does not handle failures well, but it does not contain secrets, authentication flows, destructive file operations, or privileged infrastructure behavior.

### High

- Network calls have no timeout. A request can hang indefinitely and freeze the UI.
- Scraping runs on the Tkinter main thread. The app becomes unresponsive during extraction.
- HTTP errors, blocks, CAPTCHA responses, network errors, and parser failures are not distinguished.
- HTML parsing assumes every result has title, author metadata, and link elements. Missing elements can crash extraction.
- User input is not validated. Empty queries, non-integer page counts, zero/negative pages, and very large page counts are not handled.

### Medium

- Query parameters are interpolated directly into the URL instead of using structured parameter encoding.
- No request headers are set. This can increase block risk and makes behavior less explicit.
- No duplicate detection exists.
- Empty result pages are treated the same as successful pages with no entries.
- The output path is built with string concatenation instead of `pathlib`.
- Export always writes `scholar_articles.xlsx`, which can overwrite a previous export without warning.
- There is no CSV export despite CSV being useful for lightweight review and portability.
- There are no tests or saved HTML fixtures.
- README says to run `python scholar_scraper.py`, but the actual file is `prog.py`.

### Low

- Function names are understandable but not organized by responsibility.
- The UI is functional but visually basic.
- Dependency installation is documented manually rather than pinned or declared.
- There is no release packaging guidance.
- Status messages are minimal and always imply success after export.

## 6. V2 Product Contract

V2 is a lightweight Windows desktop application for extracting Google Scholar search results, reviewing them in a desktop UI, optionally ranking them with deterministic local relevance scoring, and exporting the collected data.

V2 is not a research platform, paper summarizer, citation graph system, crawler framework, hosted SaaS product, AI agent, RAG system, or anti-bot bypass tool.

Primary workflow:

1. User launches the Windows desktop app.
2. User enters a search query.
3. User chooses the number of Google Scholar result pages to collect.
4. User optionally chooses an output location.
5. User optionally enables local relevance scoring.
6. User starts extraction.
7. App shows progress and remains responsive.
8. User can cancel before completion.
9. App displays collected results in a table.
10. User exports results to CSV or Excel.
11. App clearly reports success, partial success, no results, blocked pages, network errors, or parser errors.

Expected inputs:

- Non-empty search query.
- Positive bounded page count.
- Optional output directory or export file path.
- Optional relevance ranking toggle.

Expected outputs:

- In-app table of articles.
- CSV export.
- Excel export.
- User-facing status and error messages.

Supported platform:

- Windows is the primary target.
- Python source execution remains useful for developers.
- Portable ZIP and installer builds are release targets.

## 7. Explicit V2 Scope

V2 should include:

- Clean project structure.
- Extractable, import-safe modules.
- Safer Google Scholar URL parameter handling.
- Reusable HTTP session.
- Explicit timeout.
- Conservative request headers.
- HTTP status validation.
- Network exception handling.
- Safe HTML parsing with missing-field handling.
- Blocked/CAPTCHA/empty-result detection.
- Duplicate removal.
- Article data model.
- Local relevance scoring.
- Improved desktop UI.
- Background extraction thread.
- Progress reporting.
- Cancellation support.
- CSV and Excel export.
- Better user-facing error states.
- Windows portable release.
- Windows installer.
- Professional README and release documentation.
- Basic deterministic automated tests.

## 8. Explicit Non-Goals

V2 must not include:

- LLM integration.
- Ollama.
- OpenAI, Anthropic, Gemini, or other external AI APIs.
- GPU or CUDA requirements.
- Large model downloads.
- Transformer models.
- Background model servers.
- Docker.
- SearchApi.io.
- CAPTCHA solving.
- WAF bypass.
- Proxy rotation.
- Account login.
- Credential use.
- Browser stealth automation.
- SaaS backend.
- Authentication.
- User database.
- Hosted dashboard.
- Citation graph analysis.
- PDF processing.
- Paper summarization.
- RAG.
- Vector database.
- Autonomous agents.
- Multiple search providers unless later evidence shows a small natural abstraction is needed.

## 9. Proposed Architecture

Use a small package with clear modules and no heavy framework. Each module should have one reason to exist and be directly testable.

Recommended modules:

- `app.py`
  - Responsibility: application entrypoint.
  - Why it exists: keeps launch logic separate from importable modules.
  - Must not contain: scraping logic, parsing rules, export implementation.

- `ui/`
  - Responsibility: desktop UI, user input, progress display, result table, export commands.
  - Why it exists: GUI code has different concerns from scraping and parsing.
  - Must not contain: raw HTTP parsing logic or relevance math.

- `scraper/client.py`
  - Responsibility: Google Scholar HTTP requests, URL parameter construction, session handling, timeout, status handling.
  - Why it exists: network behavior needs isolated tests and clear reliability boundaries.
  - Must not contain: Tkinter code or export code.

- `scraper/parser.py`
  - Responsibility: parse Google Scholar HTML into article candidates and detect page states.
  - Why it exists: parser behavior is the most important deterministic test target.
  - Must not contain: live HTTP calls.

- `models.py`
  - Responsibility: article data model and extraction result model.
  - Why it exists: avoids dictionary drift and makes export/UI/test code consistent.
  - Must not contain: network or GUI behavior.

- `dedupe.py`
  - Responsibility: simple duplicate detection and canonical key generation.
  - Why it exists: duplicate handling should be deterministic and testable.
  - Must not contain: UI or HTTP behavior.

- `ranking.py`
  - Responsibility: local relevance scoring.
  - Why it exists: ranking has distinct behavior and tests.
  - Must not contain: external API calls, model downloads, or GUI behavior.

- `exporters.py`
  - Responsibility: CSV and Excel export.
  - Why it exists: file output needs path validation and tests.
  - Must not contain: scraping behavior.

- `config.py`
  - Responsibility: constants such as default timeout, max pages, default filenames, and status labels.
  - Why it exists: only if constants are shared across modules.
  - Must not become: a large settings framework.

## 10. Proposed Repository Structure

```text
.
|-- README.md
|-- pyproject.toml
|-- src/
|   `-- google_scholar_scraper/
|       |-- __init__.py
|       |-- app.py
|       |-- config.py
|       |-- models.py
|       |-- dedupe.py
|       |-- ranking.py
|       |-- exporters.py
|       |-- scraper/
|       |   |-- __init__.py
|       |   |-- client.py
|       |   `-- parser.py
|       `-- ui/
|           |-- __init__.py
|           `-- tkinter_app.py
|-- tests/
|   |-- fixtures/
|   |   |-- scholar_results_basic.html
|   |   |-- scholar_results_empty.html
|   |   |-- scholar_blocked.html
|   |   `-- scholar_missing_fields.html
|   |-- test_parser.py
|   |-- test_dedupe.py
|   |-- test_ranking.py
|   |-- test_exporters.py
|   `-- test_validation.py
|-- docs/
|   |-- V2_IMPLEMENTATION_PLAN.md
|   `-- RELEASE.md
|-- packaging/
|   |-- pyinstaller/
|   |   `-- google-scholar-scraper.spec
|   `-- windows/
|       `-- installer.iss
`-- .github/
    `-- workflows/
        `-- ci.yml
```

This structure is a target for later milestones. Milestone 1 does not create it except for this document.

## 11. Scraping Reliability Design

Reasonable V2 reliability improvements:

- Use `requests.Session`.
- Use structured `params` for URL construction.
- Set an explicit timeout, for example 15 seconds.
- Set conservative browser-like headers, especially `User-Agent` and `Accept-Language`.
- Validate status codes.
- Categorize network exceptions.
- Detect likely block/CAPTCHA pages by page text and expected result container absence.
- Treat zero parsed results differently from parser failure.
- Parse missing fields safely.
- Stop or mark partial success when later pages fail after earlier pages succeeded.
- Add bounded retry only for transient network exceptions if it is simple and conservative.
- Add duplicate filtering after collection.

V2 reliability boundaries:

- Do not solve CAPTCHA.
- Do not bypass access controls.
- Do not rotate proxies.
- Do not use stealth browser automation.
- Do not run aggressive retry loops.
- Do not hide scraping behavior from the user.

Recommended result states:

- `SUCCESS`: requested extraction completed and at least one article was collected.
- `PARTIAL_SUCCESS`: some articles were collected but one or more pages failed.
- `NO_RESULTS`: request completed but no result entries were present.
- `BLOCKED`: response appears blocked or CAPTCHA-like.
- `NETWORK_ERROR`: request failed before reliable parsing.
- `PARSING_ERROR`: response was received but could not be parsed according to expected rules.
- `CANCELLED`: user cancelled extraction.

## 12. Article Data Model

Recommended fields:

- `title`: required string after normalization, or fallback empty string if parser preserves incomplete records.
- `authors`: optional string.
- `link`: optional string.
- `snippet`: optional string.
- `source_line`: optional string from `gs_a`.
- `position`: integer result position across collected pages.
- `page`: integer source page number.
- `relevance_score`: optional float from 0 to 100.

Use a dataclass initially. A validation library is not justified for this small desktop app.

Example:

```python
@dataclass(frozen=True)
class Article:
    title: str
    authors: str = ""
    link: str = ""
    snippet: str = ""
    source_line: str = ""
    page: int = 1
    position: int = 0
    relevance_score: float | None = None
```

## 13. Duplicate Detection Strategy

Use deterministic duplicate keys:

1. Prefer normalized link when present.
2. Otherwise use normalized title.
3. Optionally combine normalized title and source line when links are missing.

Normalization should:

- Lowercase.
- Strip whitespace.
- Collapse internal whitespace.
- Remove trailing punctuation that does not change identity.

This is sufficient for V2. Fuzzy matching is not necessary initially because it can incorrectly merge distinct papers.

## 14. Lightweight AI Relevance Ranking Design

Recommended V2 approach: use scikit-learn TF-IDF plus cosine similarity if packaging tests show the size is acceptable. Keep a small pure-Python fallback or defer fallback until packaging evidence requires it.

Inputs:

- Reference text: user search query.
- Document text: article title plus available snippet and source line.

Output:

- A deterministic `0-100` relevance score.

Why this feature is useful:

- Google Scholar ordering is not always aligned with the user's exact query intent.
- Users scraping multiple pages need a fast way to review likely relevant results first.
- A visible score is more useful than adding a vague "AI" label.

Expected usefulness:

- Good enough for lexical relevance and query-term alignment.
- Most useful when titles/snippets contain query terms.
- Less useful for semantic paraphrases.
- Weak for very short queries such as one acronym.
- Weak when only titles are available.

Metadata to include:

- Include title.
- Include snippet when available.
- Include source line/authors lightly as text, but do not overweight it.

Small result sets:

- With one result, return either `100` if there is meaningful token overlap or the computed similarity normalized to 0-100. Avoid pretending strong confidence.
- With very small result sets, explainability matters more than score precision.

Short queries:

- Scores may cluster or become zero.
- UI should show the score as a review aid, not as a correctness guarantee.

Dependency decision:

- `scikit-learn` provides reliable TF-IDF and cosine similarity.
- Standard library-only TF-IDF is possible, but implementing tokenization, vectorization, and cosine math adds code that must be tested and maintained.
- For a Windows desktop executable, `scikit-learn` increases build size. This should be measured during packaging milestone before final release.

Recommendation:

- Start with `scikit-learn` only if packaging size remains acceptable.
- If executable size or packaging complexity becomes unacceptable, replace with a minimal local TF-IDF implementation before release.
- Do not use embeddings, transformer models, model downloads, external APIs, or LLMs.

Explainability:

- Display the score as "Relevance".
- Optionally keep a simple reason field later, such as matched query terms, but do not add it unless users need it.

## 15. UI Strategy

Recommended UI technology: Tkinter for V2.

Rationale:

- Already used by the project.
- Included with Python.
- Easy to package.
- Minimal dependency impact.
- Sufficient for a compact desktop tool.
- Lower risk than introducing a heavier GUI framework.

CustomTkinter can improve appearance, but it adds a runtime dependency and packaging surface. It can be considered only if the plain Tkinter UI cannot meet an acceptable visual baseline.

Minimum useful V2 UI:

- Query input.
- Page count input with bounds.
- Output path selector.
- Relevance ranking toggle.
- Start button.
- Cancel button.
- Progress bar or page progress label.
- Current status label.
- Results table.
- Export CSV action.
- Export Excel action.
- Clear user-facing error messages.

Implementation notes:

- Use a background worker thread for scraping.
- Communicate back to Tkinter with a thread-safe queue and `after()` polling.
- Disable start while extraction is running.
- Enable cancel only during extraction.
- Keep the UI small and direct.

## 16. Export Strategy

Supported formats:

- CSV: standard library `csv`, always available, small and robust.
- Excel: pandas or openpyxl-backed export, because the current app already promises Excel.

Recommended behavior:

- Let user choose export path.
- Avoid silent overwrite where practical.
- Preserve table column order.
- Include relevance score when enabled.
- Export partial results when extraction is partial and user chooses to proceed.

CSV should be the simplest default. Excel remains important for continuity with the current README and user expectations.

## 17. Packaging and Release Strategy

Recommended Windows release strategy:

- Use PyInstaller `onedir` for the primary portable build.
- Zip the `onedir` folder as the portable release artifact.
- Use Inno Setup to create a Windows installer from the `onedir` build.
- Avoid PyInstaller `onefile` as the primary artifact unless later testing shows it is clearly better.

Rationale:

- `onedir` usually starts faster than `onefile`.
- `onedir` is easier to debug when dependency files are missing.
- `onefile` can increase antivirus false positives and startup extraction delays.
- Inno Setup is mature and appropriate for a simple Windows installer.

Release artifacts:

- Portable ZIP.
- Installer executable.
- GitHub-generated source archive.
- SHA256 checksums if practical.
- Release notes documenting supported OS, known limitations, and no CAPTCHA bypass.

Do not build artifacts in Milestone 1.

## 18. Testing Strategy

V2 should use deterministic tests and avoid live Google Scholar tests in normal CI.

Required tests by end of V2:

- Parser extracts title, authors/source line, link, and snippet from a basic saved fixture.
- Parser handles missing title/link/authors without crashing.
- Parser detects empty result pages.
- Parser detects likely blocked/CAPTCHA pages.
- Duplicate removal keeps first occurrence and removes repeated links/titles.
- Relevance scoring returns bounded deterministic scores.
- Relevance scoring handles empty query/document inputs.
- CSV export writes expected columns and rows.
- Excel export writes expected columns and rows if Excel dependency is retained.
- Input validation rejects empty query and invalid page counts.
- Worker cancellation stops before starting additional pages where feasible.

CI should run:

- Unit tests.
- Basic lint/static check if adopted later.
- No live scraping by default.

Live smoke tests may be manual release checks only, because Google Scholar markup and blocking behavior are external and unstable.

## 19. Dependency Plan

Current imports:

- `requests`
- `beautifulsoup4`
- `pandas`
- `tkinter` from the standard library

Recommended V2 dependencies:

- `requests`
  - Purpose: HTTP client.
  - Type: runtime.
  - Standard library insufficiency: `urllib` is more verbose and less ergonomic for sessions, timeouts, and errors.
  - Packaging impact: low.
  - Necessity: yes.

- `beautifulsoup4`
  - Purpose: tolerant HTML parsing.
  - Type: runtime.
  - Standard library insufficiency: `html.parser` alone does not provide convenient search APIs.
  - Packaging impact: low.
  - Necessity: yes.

- `pandas`
  - Purpose: current Excel export.
  - Type: runtime if retained.
  - Standard library insufficiency: no native `.xlsx` writing.
  - Packaging impact: medium to high.
  - Necessity: questionable. It may be replaced with `openpyxl` for narrower Excel export.

- `openpyxl`
  - Purpose: direct Excel export without full pandas.
  - Type: runtime if chosen.
  - Standard library insufficiency: no native `.xlsx` writing.
  - Packaging impact: medium, likely lower than pandas.
  - Necessity: recommended replacement candidate for pandas.

- `scikit-learn`
  - Purpose: TF-IDF and cosine similarity.
  - Type: runtime if ranking uses it.
  - Standard library insufficiency: robust vectorization and similarity would otherwise require custom implementation.
  - Packaging impact: high.
  - Necessity: conditional. Use only if packaging remains acceptable; otherwise implement small local TF-IDF.

- `pytest`
  - Purpose: tests.
  - Type: development only.
  - Standard library insufficiency: `unittest` could work, but pytest improves fixture-based parser tests with low development friction.
  - Packaging impact: none for runtime if excluded from release.
  - Necessity: recommended for development.

Avoid:

- LLM SDKs.
- Browser automation packages unless a later explicit decision changes extraction strategy.
- Docker-related dependencies.
- SearchApi clients.
- Vector databases.

## 20. Migration Strategy from Current Version

Recommended migration:

1. Add package structure while preserving current behavior.
2. Move pure functions out of `prog.py` into importable modules.
3. Keep the old user workflow working during restructuring.
4. Add tests around parser/export behavior before changing scraping behavior.
5. Replace direct dictionaries with an article dataclass.
6. Add safe parser behavior and result states.
7. Add dedupe.
8. Add ranking.
9. Replace the UI with a threaded V2 UI.
10. Update README and release docs.
11. Add packaging scripts.

Avoid a large rewrite in one milestone. Each milestone should leave the app runnable.

## 21. Compatibility Considerations

- Preserve the basic "enter query, choose pages, export results" workflow.
- Preserve Excel export support.
- Prefer CSV as an additional export, not a replacement.
- Keep Windows as the primary supported platform.
- Keep source execution possible for developers.
- Do not require users to install model files or start services.
- Clearly document that Google Scholar blocking can happen and is not bypassed.

## 22. Risks and Mitigations

- Risk: Google Scholar markup changes.
  - Mitigation: parser tests with fixtures, safe missing-field handling, clear parser error states.

- Risk: Google Scholar blocks automated requests.
  - Mitigation: conservative request behavior, explicit blocked state, no bypass claims.

- Risk: GUI freezes.
  - Mitigation: background worker and queue-based UI updates.

- Risk: dependency bloat from pandas/scikit-learn.
  - Mitigation: measure build size; prefer `openpyxl` over pandas; replace scikit-learn with local TF-IDF if needed.

- Risk: relevance score is over-trusted.
  - Mitigation: label as a review aid, keep deterministic, avoid quality claims.

- Risk: onefile packaging causes slow startup or antivirus warnings.
  - Mitigation: use PyInstaller `onedir` as primary artifact.

## 23. Milestone Plan

### Milestone 1: Audit and V2 implementation plan

Objective:

- Audit current repository and define V2 architecture and scope.

Expected changes:

- Add `docs/V2_IMPLEMENTATION_PLAN.md`.

Non-goals:

- No runtime behavior changes.
- No refactors.
- No dependencies.

Verification requirements:

- Confirm repository baseline.
- Confirm only documentation changed.
- Confirm no V2 implementation started.

Completion criteria:

- Plan exists and matches actual repository.

### Milestone 2: Project restructuring without functional expansion

Objective:

- Create package layout and import-safe modules while preserving behavior.

Expected changes:

- Add `pyproject.toml`.
- Move code into `src/google_scholar_scraper/`.
- Add minimal app entrypoint.
- Keep current workflow intact.

Non-goals:

- No new scraping features.
- No new UI design.
- No ranking.

Verification requirements:

- App still launches.
- Existing extraction path still works at the same functional level.
- Importing modules does not launch the GUI.

Completion criteria:

- Code is modular enough for tests without changing user-facing behavior.

### Milestone 3: Scraper reliability and safe parsing

Objective:

- Make extraction safer and more explicit without adding anti-bot behavior.

Expected changes:

- Session-based client.
- Structured params.
- Timeout.
- Headers.
- Status handling.
- Safe parser.
- result states.
- saved HTML fixtures.

Non-goals:

- No CAPTCHA bypass.
- No proxy rotation.
- No browser automation unless impossible to keep requests-based behavior.

Verification requirements:

- Parser fixture tests.
- Network error handling tests with mocked responses.
- Manual smoke run if safe.

Completion criteria:

- App distinguishes success, no results, blocked, network error, and parser error.

### Milestone 4: Article model, normalization, validation, and duplicate handling

Objective:

- Introduce stable result data model and deterministic duplicate removal.

Expected changes:

- Article dataclass.
- Collection result model.
- Input validation.
- Normalization helpers.
- Dedupe by link/title.

Non-goals:

- No fuzzy clustering.
- No database.

Verification requirements:

- Unit tests for validation and dedupe.
- Export still works with the model.

Completion criteria:

- Result data is consistent across scraper, UI, ranking, and export.

### Milestone 5: Lightweight local AI relevance ranking

Objective:

- Add deterministic local relevance scores.

Expected changes:

- Ranking module.
- TF-IDF/cosine scoring or measured local alternative.
- UI toggle.
- Score column.

Non-goals:

- No LLMs.
- No embeddings.
- No model downloads.
- No external APIs.

Verification requirements:

- Unit tests for bounded scores.
- Tests for empty/short inputs.
- Packaging impact measured before final release.

Completion criteria:

- Results can be ranked locally without network AI calls.

### Milestone 6: New desktop UI and background execution

Objective:

- Improve usability while keeping the app simple.

Expected changes:

- Cleaner Tkinter UI.
- Background worker.
- Progress display.
- Cancellation.
- Results table.
- User-facing error messages.

Non-goals:

- No complex dashboard.
- No multi-user features.
- No hosted interface.

Verification requirements:

- Manual UI smoke tests.
- Cancellation smoke test.
- Error state smoke tests with mocked or fixture-backed flows where possible.

Completion criteria:

- UI remains responsive during extraction and supports review/export workflow.

### Milestone 7: Export, packaging, portable build, and installer

Objective:

- Prepare Windows release artifacts.

Expected changes:

- CSV export.
- Excel export finalized.
- PyInstaller `onedir` spec.
- Portable ZIP process.
- Inno Setup installer script.
- Release notes template.

Non-goals:

- No cloud release service beyond GitHub Releases.
- No auto-update system.

Verification requirements:

- Build portable artifact locally or in CI.
- Run built executable.
- Export CSV and Excel from built app.
- Verify installer installs and uninstalls cleanly.

Completion criteria:

- Release artifacts are reproducible and documented.

### Milestone 8: Testing, documentation, release readiness, and final audit

Objective:

- Close quality gaps and prepare professional release.

Expected changes:

- README rewrite.
- `docs/RELEASE.md`.
- CI workflow.
- Final test suite.
- Release checklist.

Non-goals:

- No major new product features.

Verification requirements:

- Full tests pass.
- Build passes.
- Manual release smoke test.
- Documentation matches actual behavior.

Completion criteria:

- V2 is ready for a GitHub Release with known limitations documented.

## 24. Definition of Done for V2

V2 is done when:

- The app launches on Windows from source and from packaged artifacts.
- User can enter a query and bounded page count.
- Extraction runs without freezing the UI.
- User can cancel extraction.
- Results appear in a table.
- App distinguishes success, partial success, no results, blocked, network error, parser error, and cancellation.
- Missing HTML fields do not crash parsing.
- Duplicate results are removed deterministically.
- Local relevance scores are available without LLMs, external AI APIs, GPU, Docker, model downloads, or background model servers.
- CSV export works.
- Excel export works.
- Tests cover parser fixtures, dedupe, ranking, export, and validation.
- README explains installation, usage, limitations, and release artifacts accurately.
- Portable ZIP exists.
- Windows installer exists.
- Release notes state known limitations, including that CAPTCHA/blocking is detected but not bypassed.
- Final audit confirms no SearchApi dependency and no out-of-scope AI/agent infrastructure.
