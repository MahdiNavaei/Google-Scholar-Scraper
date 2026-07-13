# Google Scholar Scraper V2 UI/UX Audit

Milestone: 7.5 UI/UX Audit, Visual Validation, and Product Polish

Baseline reviewed: `7f537f8` (`Google Scholar Scraper v2.0.0`)

## Screenshots Reviewed

Baseline screenshots captured from the real rendered Tkinter application:

- `docs/ui-audit/before/01-idle.png`
- `docs/ui-audit/before/02-running.png`
- `docs/ui-audit/before/03-success-results-ranking-enabled.png`
- `docs/ui-audit/before/04-results-ranking-disabled.png`
- `docs/ui-audit/before/05-partial-success.png`
- `docs/ui-audit/before/06-error-network.png`
- `docs/ui-audit/before/07-cancelled.png`
- `docs/ui-audit/before/08-resized-small.png`
- `docs/ui-audit/before/09-resized-large.png`

The screenshots were opened and visually inspected before implementation.

## Findings

### High

- The first impression is still close to a default Tkinter form. There is no strong product header, title hierarchy, or release-quality visual identity inside the window.
- Primary action hierarchy is weak. `Search`, `Cancel`, `Export Excel`, and `Export CSV` share the same visual weight and appear in one row even before results exist.
- Partial success and cancelled states look too similar to full success. The green progress bar and plain text do not visually communicate warning or interruption.
- Error states are easy to miss. Network errors are shown as plain text above a blank table with no clear severity treatment or next-step framing.
- The empty results area looks unfinished before a search and after no-result/error states.

### Medium

- Results table readability is limited by long titles, long author metadata, and full raw URLs. The URL column consumes scan space while the main interaction is double-click/open.
- Status text is visually disconnected from the progress bar and results table. It should behave like a compact status panel rather than loose labels.
- Export controls are not grouped with the results area, where users naturally need them.
- Form spacing and alignment are serviceable but feel generic; field labels and controls do not create a clear workflow.
- The `Smart Relevance Ranking` label is long and not clearly connected to how results are sorted.

### Low

- The default window size is usable, but the small resized state feels cramped around the action row.
- Typography is consistent but flat. The UI uses tiny default text everywhere and lacks a readable headline/subtitle distinction.
- The window title is acceptable, but application identity should also be visible inside the app for screenshots.

## Proposed Improvements

- Add a restrained application header with product name, version, and a short workflow description.
- Replace the single action row with clearer grouping: primary `Search Scholar`, secondary `Cancel`, and result-scoped export actions.
- Add a compact status panel with severity-aware styling for ready, running, success, partial/cancelled, and error states.
- Replace the blank idle/error table with an explicit empty state until articles exist.
- Keep export disabled until results exist, but make export discoverable in the results header after results are available.
- Make the table easier to scan by showing compact link availability text in the UI while preserving full links for export and double-click behavior.
- Add initial focus to the query field and bind Enter to start a search.
- Improve microcopy while keeping all application-controlled UI text English-only.

## Rejected Changes

- No framework migration. Tkinter/ttk can meet this milestone with focused style, layout, and state improvements.
- No dark theme or decorative visual effects. The application is a research utility and should remain calm and readable.
- No icons or custom branding asset in this milestone. There is no existing suitable icon, and placeholder branding would not improve usability.
- No new product features, export formats, scraping behavior, or AI functionality.

## After Polish Review

After implementation, the same key UI states were recaptured from the real rendered Tkinter application and visually inspected:

- Idle
- Running
- Success with ranking enabled
- Results with ranking disabled
- Partial success
- Network error
- Cancelled
- Small resized window
- Large resized window

The polished UI resolves the high-priority issues found in the baseline audit:

- The window now has an in-app product header, version, and clearer workflow framing.
- Search, cancel, and export actions are grouped by task stage instead of competing in one row.
- Ready, running, success, warning, and error states now use distinct status panels.
- Blank table states were replaced with explicit empty-state messaging.
- Result export controls are placed in the results header and remain disabled until exportable results exist.
- The table now uses compact link text in the UI while preserving full links for double-click opening and file export.
- Small-window layout keeps the relevance and link columns visible, with horizontal scrolling available for long titles and author metadata.

Remaining minor tradeoff: long scholarly titles and author lists can still be clipped in the table at narrower widths. This is acceptable for this milestone because the table is scrollable, exported files retain the full values, and expanding into multi-line table rows would add complexity without improving the core workflow enough.
