import unittest
from pathlib import Path

import google_scholar_scraper
from google_scholar_scraper.app import main, run_packaging_smoke


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PackagingMetadataTests(unittest.TestCase):
    def test_package_version_matches_project_metadata(self) -> None:
        pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertEqual(google_scholar_scraper.__version__, "2.0.0")
        self.assertIn('version = "2.0.0"', pyproject)

    def test_gui_entrypoint_is_import_safe(self) -> None:
        self.assertTrue(callable(main))

    def test_packaging_smoke_writes_excel_and_csv_without_starting_gui(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            run_packaging_smoke(Path(temp_dir))

            self.assertTrue((Path(temp_dir) / "packaging-smoke.xlsx").exists())
            self.assertTrue((Path(temp_dir) / "packaging-smoke.csv").exists())

    def test_pyinstaller_spec_uses_windowed_onedir_identity(self) -> None:
        spec = (PROJECT_ROOT / "packaging" / "pyinstaller" / "GoogleScholarScraper.spec").read_text(encoding="utf-8")

        self.assertIn('entrypoint = src_path / "google_scholar_scraper" / "__main__.py"', spec)
        self.assertIn("console=False", spec)
        self.assertIn('name="Google-Scholar-Scraper-v2.0.0"', spec)
        self.assertIn('excludes=["tests", *excluded_optional_modules]', spec)
        self.assertIn('"pandas"', spec)
        self.assertIn('"torch"', spec)

    def test_build_script_uses_expected_artifact_names_and_guarded_cleaning(self) -> None:
        script = (PROJECT_ROOT / "scripts" / "build_windows.ps1").read_text(encoding="utf-8")

        self.assertIn("Google-Scholar-Scraper-v$Version-Portable-Windows-x64.zip", script)
        self.assertIn("Google-Scholar-Scraper-v$Version-Setup-Windows-x64.exe", script)
        self.assertIn("Refusing to remove path outside repository", script)
        self.assertIn('"build", "dist"', script)
        self.assertIn("System.Security.Cryptography.SHA256", script)

    def test_inno_setup_definition_uses_per_user_installer_metadata(self) -> None:
        iss = (PROJECT_ROOT / "installer" / "GoogleScholarScraper.iss").read_text(encoding="utf-8")

        self.assertIn('#define MyAppVersion "2.0.0"', iss)
        self.assertIn('#define MyAppPublisher "Mahdi Navaei"', iss)
        self.assertIn("PrivilegesRequired=lowest", iss)
        self.assertIn("Google-Scholar-Scraper-v2.0.0-Setup-Windows-x64", iss)


if __name__ == "__main__":
    unittest.main()
