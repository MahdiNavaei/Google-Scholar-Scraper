# Google Scholar Scraper V2.0.1 Release Notes

## Overview

V2.0.1 is a hardening release focused on packaging correctness, distribution safety, release verification, and user-facing failure handling.

## Changes

- Corrected the supported Python version declaration to Python 3.10+.
- Added exact release dependency constraints.
- Added third-party dependency notice tracking.
- Improved Windows portable and installer distribution metadata.
- Added installer lifecycle smoke validation.
- Improved export error handling.
- Improved partial-success wording.

## Verification

Validated with source compilation, deterministic tests, package installation,
Windows artifact builds, installer smoke checks, and SHA-256 verification.

## Release Process

V2.0.1 artifacts use a separate versioned artifact set from V2.0.0.
