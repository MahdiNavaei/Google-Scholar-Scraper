from __future__ import annotations

import argparse
import re
import shutil
import sys
from importlib import metadata
from pathlib import Path


RUNTIME_DISTRIBUTIONS = (
    "beautifulsoup4",
    "soupsieve",
    "openpyxl",
    "et-xmlfile",
    "requests",
    "urllib3",
    "charset-normalizer",
    "idna",
    "certifi",
    "typing-extensions",
)

BUNDLING_DISTRIBUTIONS = (
    "pyinstaller",
    "pyinstaller-hooks-contrib",
)

LEGAL_FILE_PREFIXES = (
    "LICENSE",
    "LICENCE",
    "COPYING",
    "NOTICE",
    "AUTHORS",
    "COPYRIGHT",
)


def canonical_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def read_constraints(path: Path) -> dict[str, str]:
    versions: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "==" not in line:
            continue
        name, version = line.split("==", 1)
        versions[canonical_name(name.strip())] = version.strip()
    return versions


def is_legal_file(relative_path: Path) -> bool:
    upper_name = relative_path.name.upper()
    if any(upper_name.startswith(prefix) for prefix in LEGAL_FILE_PREFIXES):
        return True
    return any(part.lower() in {"license", "licenses", "licence", "licences"} for part in relative_path.parts)


def safe_destination_name(relative_path: Path, used_names: set[str]) -> str:
    name = relative_path.name
    if name not in used_names:
        used_names.add(name)
        return name

    stem = relative_path.stem
    suffix = relative_path.suffix
    counter = 2
    while True:
        candidate = f"{stem}-{counter}{suffix}"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        counter += 1


def collect_distribution_legal_files(
    distribution_name: str,
    expected_versions: dict[str, str],
    output_root: Path,
) -> tuple[str, list[str]]:
    canonical = canonical_name(distribution_name)
    expected_version = expected_versions.get(canonical)
    if expected_version is None:
        raise RuntimeError(f"No exact release constraint found for {distribution_name}.")

    distribution = metadata.distribution(distribution_name)
    actual_version = distribution.version
    if actual_version != expected_version:
        raise RuntimeError(
            f"Version mismatch for {distribution_name}: expected {expected_version}, installed {actual_version}."
        )

    destination = output_root / canonical
    destination.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    used_names: set[str] = set()

    for file_entry in distribution.files or ():
        relative_path = Path(str(file_entry))
        if not is_legal_file(relative_path):
            continue
        source = Path(distribution.locate_file(file_entry))
        if not source.is_file():
            continue
        destination_name = safe_destination_name(relative_path, used_names)
        shutil.copy2(source, destination / destination_name)
        copied.append(destination_name)

    if not copied:
        raise RuntimeError(
            f"No license, notice, copyright, or author file was found in the installed {distribution_name} {actual_version} distribution."
        )

    return actual_version, sorted(copied)


def copy_python_license(output_root: Path) -> list[str]:
    candidates = (
        Path(sys.base_prefix) / "LICENSE.txt",
        Path(sys.base_prefix) / "LICENSE",
        Path(sys.prefix) / "LICENSE.txt",
        Path(sys.prefix) / "LICENSE",
    )
    destination = output_root / "python"
    destination.mkdir(parents=True, exist_ok=True)

    for candidate in candidates:
        if candidate.is_file():
            target = destination / candidate.name
            shutil.copy2(candidate, target)
            return [target.name]

    raise RuntimeError("Could not locate the Python runtime license in the active release-build interpreter.")


def copy_tcl_tk_licenses(app_dir: Path, output_root: Path) -> list[str]:
    internal_dir = app_dir / "_internal"
    candidates = sorted(
        {
            *internal_dir.glob("_tk_data/**/license.terms"),
            *internal_dir.glob("_tcl_data/**/license.terms"),
        }
    )
    if not candidates:
        raise RuntimeError("Could not locate Tcl/Tk license.terms in the packaged application.")

    destination = output_root / "tcl-tk"
    destination.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    used_names: set[str] = set()
    for candidate in candidates:
        base_name = "license.terms"
        destination_name = safe_destination_name(Path(base_name), used_names)
        shutil.copy2(candidate, destination / destination_name)
        copied.append(destination_name)
    return copied


def write_manifest(
    output_root: Path,
    collected: list[tuple[str, str, list[str]]],
    python_files: list[str],
    tcl_tk_files: list[str],
) -> None:
    lines = [
        "Google Scholar Scraper V2.0.1 third-party license bundle",
        "",
        "This directory was assembled from the exact constrained release-build environment.",
        "Each listed file is copied from the installed distribution metadata or packaged runtime.",
        "",
    ]
    for distribution_name, version, files in collected:
        lines.append(f"{distribution_name} {version}")
        for file_name in files:
            lines.append(f"  - {canonical_name(distribution_name)}/{file_name}")
        lines.append("")

    lines.append("Python runtime")
    for file_name in python_files:
        lines.append(f"  - python/{file_name}")
    lines.append("")

    lines.append("Tcl/Tk runtime")
    for file_name in tcl_tk_files:
        lines.append(f"  - tcl-tk/{file_name}")
    lines.append("")

    (output_root / "MANIFEST.txt").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect exact third-party license files for a Windows release bundle.")
    parser.add_argument("--constraints", type=Path, required=True)
    parser.add_argument("--app-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    constraints = args.constraints.resolve()
    app_dir = args.app_dir.resolve()
    output_root = args.output_dir.resolve()

    if not constraints.is_file():
        raise RuntimeError(f"Constraints file not found: {constraints}")
    if not app_dir.is_dir():
        raise RuntimeError(f"Packaged application directory not found: {app_dir}")

    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    expected_versions = read_constraints(constraints)
    collected: list[tuple[str, str, list[str]]] = []
    for distribution_name in (*RUNTIME_DISTRIBUTIONS, *BUNDLING_DISTRIBUTIONS):
        version, files = collect_distribution_legal_files(distribution_name, expected_versions, output_root)
        collected.append((distribution_name, version, files))

    python_files = copy_python_license(output_root)
    tcl_tk_files = copy_tcl_tk_licenses(app_dir, output_root)
    write_manifest(output_root, collected, python_files, tcl_tk_files)

    print(f"Collected third-party licenses in: {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
