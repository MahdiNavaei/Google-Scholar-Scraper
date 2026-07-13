import unittest
from pathlib import Path

import google_scholar_scraper
from google_scholar_scraper.app import main, run_packaging_smoke


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PackagingMetadataTests(unittest.TestCase):
    def test_package_version_matches_project_metadata(self) -> None:
        pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertEqual(google_scholar_scraper.__version__, "2.0.1")
        self.assertIn('version = "2.0.1"', pyproject)
        self.assertIn('requires-python = ">=3.10"', pyproject)

    def test_gui_entrypoint_is_import_safe(self) -> None:
        self.assertTrue(callable(main))

    def test_packaging_smoke_writes_excel_and_csv_without_starting_gui(self) -> None:
        import tempfile
        import csv

        with tempfile.TemporaryDirectory() as temp_dir:
            run_packaging_smoke(Path(temp_dir))

            self.assertTrue((Path(temp_dir) / "packaging-smoke.xlsx").exists())
            csv_path = Path(temp_dir) / "packaging-smoke.csv"
            self.assertTrue(csv_path.exists())
            with csv_path.open(newline="", encoding="utf-8-sig") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["Title"], "Unicode Smoke: cafe, alpha + beta, 医学 AI")
            self.assertEqual(rows[0]["Relevance Score"], "88.8")
            self.assertEqual(rows[1]["Relevance Score"], "")

    def test_pyinstaller_spec_uses_windowed_onedir_identity(self) -> None:
        spec = (PROJECT_ROOT / "packaging" / "pyinstaller" / "GoogleScholarScraper.spec").read_text(encoding="utf-8")

        self.assertIn('entrypoint = src_path / "google_scholar_scraper" / "__main__.py"', spec)
        self.assertIn("console=False", spec)
        self.assertIn('name="Google-Scholar-Scraper-v2.0.1"', spec)
        self.assertIn("THIRD_PARTY_NOTICES.txt", spec)
        self.assertIn("COMMERCIAL_LICENSE.md", spec)
        self.assertIn('excludes=["tests", *excluded_optional_modules]', spec)
        self.assertIn('"h2"', spec)
        self.assertIn('"pandas"', spec)
        self.assertIn('"torch"', spec)

    def test_build_script_uses_expected_artifact_names_and_guarded_cleaning(self) -> None:
        script = (PROJECT_ROOT / "scripts" / "build_windows.ps1").read_text(encoding="utf-8")

        self.assertIn("Google-Scholar-Scraper-v$Version-Portable-Windows-x64.zip", script)
        self.assertIn("Google-Scholar-Scraper-v$Version-Setup-Windows-x64.exe", script)
        self.assertIn("Refusing to remove path outside repository", script)
        self.assertIn('"build", "dist"', script)
        self.assertIn("System.Security.Cryptography.SHA256", script)
        self.assertIn("Copy-DistributionNotices", script)
        self.assertIn("Remove-OptionalHttp2Metadata", script)
        self.assertIn("THIRD_PARTY_NOTICES.txt", script)
        self.assertNotIn("installer/$InstallerName", script)

    def test_inno_setup_definition_uses_per_user_installer_metadata(self) -> None:
        iss = (PROJECT_ROOT / "installer" / "GoogleScholarScraper.iss").read_text(encoding="utf-8")

        self.assertIn('#define MyAppVersion "2.0.1"', iss)
        self.assertIn('#define MyAppPublisher "Mahdi Navaei"', iss)
        self.assertIn("PrivilegesRequired=lowest", iss)
        self.assertIn("Google-Scholar-Scraper-v2.0.1-Setup-Windows-x64", iss)

    def test_release_licensing_and_notice_files_are_present(self) -> None:
        license_text = (PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8")
        notice = (PROJECT_ROOT / "NOTICE").read_text(encoding="utf-8")
        commercial = (PROJECT_ROOT / "COMMERCIAL_LICENSE.md").read_text(encoding="utf-8")
        third_party = (PROJECT_ROOT / "THIRD_PARTY_NOTICES.txt").read_text(encoding="utf-8")

        self.assertIn("PolyForm Noncommercial License 1.0.0", license_text)
        self.assertIn("Mahdi Navaei", notice)
        self.assertIn("Commercial use requires a separate written commercial license", commercial)
        self.assertIn("beautifulsoup4 4.14.3", third_party)
        self.assertIn("PyInstaller 6.20.0", third_party)

    def test_windows_workflow_builds_installer_and_uploads_artifacts_without_release_publish(self) -> None:
        workflow = (PROJECT_ROOT / ".github" / "workflows" / "build-windows.yml").read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch", workflow)
        self.assertIn("choco install innosetup", workflow)
        self.assertIn("Build Windows Installer", workflow)
        self.assertIn("Copy distribution notices", workflow)
        self.assertIn("h2-*.dist-info", workflow)
        self.assertIn("Installer install-launch-export-uninstall smoke", workflow)
        self.assertIn("unins000.exe", workflow)
        self.assertIn("constraints/release-2.0.1.txt", workflow)
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertNotIn("softprops/action-gh-release", workflow)

    def test_release_constraints_pin_expected_dependency_versions(self) -> None:
        constraints = (PROJECT_ROOT / "constraints" / "release-2.0.1.txt").read_text(encoding="utf-8")

        self.assertIn("beautifulsoup4==4.14.3", constraints)
        self.assertIn("requests==2.32.5", constraints)
        self.assertIn("pyinstaller==6.20.0", constraints)


if __name__ == "__main__":
    unittest.main()
