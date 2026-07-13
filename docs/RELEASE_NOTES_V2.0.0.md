# Google Scholar Scraper V2.0.0 Release Notes

## Overview

Google Scholar Scraper V2.0.0 is a lightweight Windows desktop application for
extracting, ranking, reviewing, and exporting Google Scholar search results.

The release focuses on reliability, local-first operation, and clear desktop
workflow. It does not use LLMs, external AI APIs, model downloads, GPU
acceleration, browser automation, proxy rotation, CAPTCHA solving, or CAPTCHA
bypass.

## Major Improvements

- Safer requests-based Google Scholar extraction with explicit timeouts, reusable HTTP sessions, bounded retries, request pacing, and structured query parameters.
- Explicit result states for success, partial success, no results, rate limits, blocked/challenge pages, network errors, parser errors, and cancellation.
- Partial-result preservation when extraction stops after earlier pages succeed.
- Deterministic article validation, normalization, and duplicate removal.
- Import-safe package layout with testable modules.

## Smart Relevance Ranking

V2 adds optional local lexical relevance ranking. The ranking uses deterministic
TF-IDF-style token scoring against the query and collected article metadata.

The score is a review aid, not a scientific quality score or semantic confidence
claim. Ranking runs locally and does not call an external AI service.

## Desktop UI

- Polished English-only Tkinter/ttk interface.
- Query input, page count, ranking toggle, export folder, progress, status panel, and result table.
- Background worker execution keeps the UI responsive during extraction.
- Cooperative cancellation preserves collected results when available.
- Final screenshot: `docs/assets/google-scholar-scraper-v2.png`.

## Export Formats

- Excel: `scholar_articles.xlsx`
- CSV: `scholar_articles.csv`

Both exports include:

- Title
- Authors
- Link
- Relevance Score

CSV is written as UTF-8 with BOM for practical compatibility with Excel on
Windows while preserving Unicode content.

## Windows Artifacts

Expected release artifacts:

- `Google-Scholar-Scraper-v2.0.0-Portable-Windows-x64.zip`
- `Google-Scholar-Scraper-v2.0.0-Setup-Windows-x64.exe`
- `SHA256SUMS.txt`

The portable ZIP is produced from a PyInstaller `onedir` build. The installer is
compiled with Inno Setup from the same newly generated `onedir` application.

## Licensing

Google Scholar Scraper V2.0.0 is source-available for noncommercial use under
the PolyForm Noncommercial License 1.0.0.

Commercial use requires a separate written commercial license from Mahdi Navaei.
See `COMMERCIAL_LICENSE.md` and `NOTICE`.

## Known Limitations

- Google Scholar may rate-limit, block, or challenge automated requests.
- The application detects and reports these states; it does not bypass them.
- Google Scholar markup can change. Parser fixtures cover known structures, but future changes may require maintenance.
- Ranking is lexical and local. It does not provide semantic understanding or paper-quality assessment.
- The normal CI test suite is deterministic and does not depend on live Google Scholar access.

## Upgrade Notes From Legacy Version

- The legacy `prog.py` launcher remains available, but the primary source entrypoint is now `python -m google_scholar_scraper`.
- Runtime dependencies are declared in `pyproject.toml`.
- Exports are now explicit actions after result review rather than a single automatic Excel write.
- CSV export is now supported.
- pandas is no longer required.

## Checksum Verification

After downloading release artifacts, verify them against `SHA256SUMS.txt`.

PowerShell example:

```powershell
Get-FileHash .\Google-Scholar-Scraper-v2.0.0-Portable-Windows-x64.zip -Algorithm SHA256
Get-FileHash .\Google-Scholar-Scraper-v2.0.0-Setup-Windows-x64.exe -Algorithm SHA256
```

Compare the reported hashes with the corresponding lines in `SHA256SUMS.txt`.
