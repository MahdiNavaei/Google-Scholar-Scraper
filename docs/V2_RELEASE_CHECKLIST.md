# V2.0.0 Release Checklist

Do not publish a tag or GitHub Release until the owner explicitly approves it.

## Repository

- [ ] Tracked worktree is clean.
- [ ] Version is `2.0.0` across package metadata, UI title, packaging config, installer config, README, changelog, release notes, and artifact names.
- [ ] Full deterministic test suite passes.
- [ ] README is current.
- [ ] `LICENSE` is present.
- [ ] `NOTICE` is present.
- [ ] `COMMERCIAL_LICENSE.md` is present.
- [ ] `CHANGELOG.md` is current.
- [ ] `docs/RELEASE_NOTES_V2.0.0.md` is current.

## UI

- [ ] Final UI from `3dcb420` or later release-readiness-only corrections is frozen.
- [ ] `docs/assets/google-scholar-scraper-v2.png` is current.
- [ ] Application-controlled UI text is English-only.

## Build

- [ ] `build/` and `dist/` are removed before final packaging.
- [ ] Final PyInstaller `onedir` build succeeds from current source.
- [ ] Final Portable ZIP exists.
- [ ] Final Installer exists.
- [ ] Final `SHA256SUMS.txt` exists.
- [ ] Artifact names are correct.

## Runtime

- [ ] Packaged app launches.
- [ ] Final UI is visible.
- [ ] Ranking-enabled mode works.
- [ ] Ranking-disabled mode works.
- [ ] Cancellation works.
- [ ] Partial-result behavior works.
- [ ] Excel export works.
- [ ] CSV export works.

## Artifact Consistency

- [ ] Portable and Installer are built from the same final source baseline.
- [ ] Installer contains the current final packaged app.
- [ ] No stale earlier artifact is reused.

## Release

- [ ] Inspect artifacts.
- [ ] Verify SHA-256 checksums.
- [ ] Create tag only after owner approval.
- [ ] Create GitHub Release only after owner approval.
- [ ] Attach Portable ZIP.
- [ ] Attach Installer.
- [ ] Attach `SHA256SUMS.txt`.
