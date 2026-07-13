# V2.0.0 Release Verification Record

This document is the completed verification record for the published V2.0.0
release. It is not a forward-looking checklist and does not authorize any
future tag or GitHub Release publication.

## Release Baseline

- Published release: `v2.0.0`
- Source commit intended for the release tag: `7336b8d`
- Release artifact family:
  - `Google-Scholar-Scraper-v2.0.0-Portable-Windows-x64.zip`
  - `Google-Scholar-Scraper-v2.0.0-Setup-Windows-x64.exe`
  - `SHA256SUMS.txt`

## Verified Evidence

- Deterministic unit tests passed before the V2.0.0 release gate.
- The Windows artifact workflow completed and produced the portable ZIP,
  installer executable, and checksum file.
- The portable ZIP was downloaded from the public V2.0.0 release and verified
  against the published checksum file.
- The portable executable launched successfully from the release ZIP.
- The packaged smoke command produced non-empty Excel and CSV exports.
- The installer artifact was downloaded from the public V2.0.0 release and
  verified against the published checksum file.
- The installer file was confirmed as a non-empty Windows PE executable.

## V2.0.0 Scope Limitations

- A full install-launch-export-uninstall smoke was not performed before the
  V2.0.0 release. V2.0.1 adds that lifecycle check to the remote Windows build
  workflow.
- V2.0.0 package metadata claimed Python 3.9+, but the source uses Python 3.10
  type syntax. V2.0.1 corrects the declared minimum to Python 3.10+.
- V2.0.0 portable and installer layouts did not include all repository license
  and notice files at the distribution root. V2.0.1 adds those files.
- V2.0.0 did not include a consolidated third-party notices file. V2.0.1 adds
  `THIRD_PARTY_NOTICES.txt`.

## Release Governance

Do not move, delete, replace, or republish the V2.0.0 tag, release, or assets.
Future patch work must use a new version, commit, workflow run, and artifact
set.
