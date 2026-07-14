# Google Scholar Scraper V2.0.1 Release Notes

## Overview

V2.0.1 is a focused hardening release for packaging correctness, distribution
notices, dependency security, release verification, and user-facing failure
handling. It does not add new scraping capabilities or change the accepted V2
UI design.

## Fixed

- Corrected the supported source-runtime declaration to Python 3.10+.
- Corrected partial-success wording so preserved results are not described as
  already exported.
- Added safe user-facing handling for expected Excel and CSV filesystem write
  failures.
- Aligned local and GitHub Actions checksum entries to use plain release
  artifact filenames.

## Distribution And Dependency Hardening

- Added exact V2.0.1 release-build constraints.
- Updated the constrained HTTP dependency set to `requests 2.33.0`,
  `urllib3 2.7.0`, and `idna 3.15` following the final dependency security
  review.
- Raised the declared Requests runtime floor to `requests>=2.33,<3`.
- Included `LICENSE`, `NOTICE`, `COMMERCIAL_LICENSE.md`, and
  `THIRD_PARTY_NOTICES.txt` at the distribution root.
- Added deterministic third-party legal-file collection from the exact installed
  release-build distributions.
- Added a generated `third_party_licenses/MANIFEST.txt` and corresponding legal
  files for runtime dependencies, Python, Tcl/Tk, PyInstaller, and PyInstaller
  hooks used by the Windows distribution.
- Removed duplicate project notice files from the PyInstaller `_internal`
  directory.

## Windows Verification

- Added clean installer install-launch-export-uninstall smoke validation on a
  GitHub-hosted Windows runner.
- Added verification that installed and portable layouts contain the required
  project notices and populated third-party license bundle.
- Continued packaged Excel and CSV smoke validation with Unicode data and
  relevance-score coverage.

## Release Integrity

V2.0.1 uses a new versioned source commit, workflow run, Portable ZIP, Installer
EXE, and SHA-256 checksum set. The published V2.0.0 tag, release, and assets are
not modified by this patch release.
