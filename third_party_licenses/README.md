# Third Party Licenses

This source-tree directory documents the generated third-party license bundle used
for Windows releases.

The actual legal files are collected during the release build by:

`scripts/collect_third_party_licenses.py`

The collector copies license, notice, copyright, and author files from the exact
installed distributions constrained by `constraints/release-2.0.1.txt`. It also
copies the active Python runtime license and the Tcl/Tk license shipped with the
packaged application.

The generated Windows portable and installer layouts contain:

`third_party_licenses/MANIFEST.txt`

plus per-component legal files. These generated files are release artifacts and
are not committed manually, which avoids stale license text drifting away from
the exact dependency versions used to build the release.

The Windows build fails if any required component lacks an identifiable legal
file, if an installed dependency version differs from the release constraints,
or if the Python or Tcl/Tk runtime license cannot be collected.

The component summary and expected versions are documented in
`THIRD_PARTY_NOTICES.txt`. Application code licensing remains documented in
`LICENSE`, `NOTICE`, and `COMMERCIAL_LICENSE.md`.
