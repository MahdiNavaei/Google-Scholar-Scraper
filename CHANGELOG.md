# Changelog

## 2.0.1

### Fixed

- Corrected the declared minimum Python version to 3.10, matching the codebase's use of modern type syntax.
- Reworded partial-success extraction messages so they no longer imply an export occurred automatically.
- Added UI error handling for Excel and CSV export filesystem failures.
- Aligned local and CI checksum file entries so installer hashes use the plain artifact filename.

### Changed

- Added exact V2.0.1 release-candidate dependency constraints.
- Added root-level third-party notices for the expected Windows distribution dependency set.
- Included `LICENSE`, `NOTICE`, `COMMERCIAL_LICENSE.md`, and `THIRD_PARTY_NOTICES.txt` in PyInstaller portable and installer layouts.
- Added remote Windows installer install-launch-export-uninstall smoke coverage.
- Improved project metadata for package consumers and repository presentation.

## 2.0.0

### Added

- Import-safe Python package layout under `src/google_scholar_scraper`.
- Safer Google Scholar extraction with reusable sessions, explicit timeouts, bounded retries, conservative request pacing, and explicit failure states.
- Deterministic parser fixtures for success, missing fields, empty results, rate limits, blocked/challenge pages, parser drift, and temporary Google server errors.
- Article normalization, validation, and deterministic duplicate removal.
- Local lexical relevance ranking with no LLM, no external AI API, no model download, and no GPU requirement.
- Responsive Tkinter/ttk desktop UI with background worker execution, progress reporting, cancellation, result review, and English-only interface text.
- CSV and Excel export from reviewed results.
- Windows PyInstaller `onedir` packaging, portable ZIP generation, Inno Setup installer definition, and SHA-256 checksum generation.
- Final UI screenshot for README use.
- PolyForm Noncommercial License 1.0.0, attribution notice, commercial licensing document, release notes, release checklist, and CI workflows.

### Changed

- Replaced the legacy single-script implementation with separated modules for scraping, parsing, ranking, deduplication, export, and UI.
- Replaced synchronous GUI scraping with a background worker and queue-based UI updates.
- Replaced pandas-based export with direct `openpyxl` Excel export and standard-library CSV export.
- Updated documentation to describe the project as source-available for noncommercial use rather than OSI-approved open source.

### Fixed

- Invalid page-count and empty-query inputs now produce user-facing validation messages.
- Network failures, rate limits, blocked/challenge pages, no-result pages, parser incompatibility, partial success, and cancellation are classified explicitly.
- Missing optional Scholar fields no longer crash parsing.
- Partial results are preserved when later pages fail or extraction is cancelled.
