import csv
import tempfile
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

    def test_pyinstaller_spec_uses_windowed_onedir_identity_without_duplicate_notice_datas(self) -> None:
        spec = (PROJECT_ROOT / "packaging" / "pyinstaller" / "GoogleScholarScraper.spec").read_text(encoding="utf-8")

        self.assertIn('entrypoint = src_path / "google_scholar_scraper" / "__main__.py"', spec)
        self.assertIn("console=False", spec)
        self.assertIn('name="Google-Scholar-Scraper-v2.0.1"', spec)
        self.assertIn("datas=[]", spec)
        self.assertNotIn("distribution_documents", spec)
        self.assertIn('excludes=["tests", *excluded_optional_modules]', spec)
        self.assertIn('"h2"', spec)
        self.assertIn('"pandas"', spec)
        self.assertIn('"torch"', spec)

    def test_build_script_uses_expected_artifact_names_and_license_collection(self) -> None:
        script = (PROJECT_ROOT / "scripts" / "build_windows.ps1").read_text(encoding="utf-8")

        self.assertIn("Google-Scholar-Scraper-v$Version-Portable-Windows-x64.zip", script)
        self.assertIn("Google-Scholar-Scraper-v$Version-Setup-Windows-x64.exe", script)
        self.assertIn("Refusing to remove path outside repository", script)
        self.assertIn('"build", "dist"', script)
        self.assertIn("System.Security.Cryptography.SHA256", script)
        self.assertIn("Collect-ThirdPartyLicenses", script)
        self.assertIn("Verify-DistributionCompliance", script)
        self.assertIn("collect_third_party_licenses.py", script)
        self.assertIn("third_party_licenses", script)
        self.assertNotIn("installer/$InstallerName", script)

    def test_third_party_license_collector_covers_runtime_and_packaging_components(self) -> None:
        collector = (PROJECT_ROOT / "scripts" / "collect_third_party_licenses.py").read_text(encoding="utf-8")

        for distribution_name in (
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
            "pyinstaller",
            "pyinstaller-hooks-contrib",
        ):
            self.assertIn(f'"{distribution_name}"', collector)
        self.assertIn("copy_python_license", collector)
        self.assertIn("copy_tcl_tk_licenses", collector)
        self.assertIn("MANIFEST.txt", collector)

    def test_inno_setup_definition_uses_per_user_installer_metadata(self) -> None:
        iss = (PROJECT_ROOT / "installer" / "GoogleScholarScraper.iss").read_text(encoding="utf-8")

        self.assertIn('#define MyAppVersion "2.0.1"', iss)
        self.assertIn('#define MyAppPublisher "Mahdi Navaei"', iss)
        self.assertIn("PrivilegesRequired=lowest", iss)
        self.assertIn("Google-Scholar-Scraper-v2.0.1-Setup-Windows-x64", iss)

    def test_release_licensing_notice_and_release_note_files_are_present(self) -> None:
        license_text = (PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8")
        notice = (PROJECT_ROOT / "NOTICE").read_text(encoding="utf-8")
        commercial = (PROJECT_ROOT / "COMMERCIAL_LICENSE.md").read_text(encoding="utf-8")
        third_party = (PROJECT_ROOT / "THIRD_PARTY_NOTICES.txt").read_text(encoding="utf-8")
        release_notes = (PROJECT_ROOT / "docs" / "RELEASE_NOTES_V2.0.1.md").read_text(encoding="utf-8")

        self.assertIn("PolyForm Noncommercial License 1.0.0", license_text)
        self.assertIn("Mahdi Navaei", notice)
        self.assertIn("Commercial use requires a separate written commercial license", commercial)
        self.assertIn("beautifulsoup4 4.14.3", third_party)
        self.assertIn("requests 2.33.0", third_party)
        self.assertIn("urllib3 2.7.0", third_party)
        self.assertIn("idna 3.15", third_party)
        self.assertIn("Google Scholar Scraper V2.0.1", release_notes)

    def test_windows_workflow_builds_installer_collects_licenses_and_uploads_artifacts_without_release_publish(self) -> None:
        workflow = (PROJECT_ROOT / ".github" / "workflows" / "build-windows.yml").read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch", workflow)
        self.assertIn("pull_request", workflow)
        self.assertIn("choco install innosetup", workflow)
        self.assertIn("Build Windows Installer", workflow)
        self.assertIn("Collect exact third-party licenses", workflow)
        self.assertIn("Verify packaged executable and distribution compliance", workflow)
        self.assertIn("Installer install-launch-export-uninstall smoke", workflow)
        self.assertIn("unins000.exe", workflow)
        self.assertIn("constraints/release-2.0.1.txt", workflow)
        self.assertIn("third_party_licenses", workflow)
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertNotIn("softprops/action-gh-release", workflow)

    def test_release_constraints_pin_expected_dependency_versions(self) -> None:
        constraints = (PROJECT_ROOT / "constraints" / "release-2.0.1.txt").read_text(encoding="utf-8")

        self.assertIn("beautifulsoup4==4.14.3", constraints)
        self.assertIn("requests==2.33.0", constraints)
        self.assertIn("urllib3==2.7.0", constraints)
        self.assertIn("idna==3.15", constraints)
        self.assertIn("pyinstaller==6.20.0", constraints)


if __name__ == "__main__":
    unittest.main()
