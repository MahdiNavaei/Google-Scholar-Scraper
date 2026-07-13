"""Compatibility launcher for the restructured application."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from google_scholar_scraper.app import main


if __name__ == "__main__":
    main()
