from pathlib import Path
import argparse

from google_scholar_scraper.exporters import save_to_csv, save_to_excel
from google_scholar_scraper.models import Article
from google_scholar_scraper.ui.tkinter_app import run


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--packaging-smoke",
        metavar="OUTPUT_DIR",
        help="write sample Excel and CSV exports, then exit",
    )
    args = parser.parse_args(argv)
    if args.packaging_smoke:
        run_packaging_smoke(Path(args.packaging_smoke))
        return

    run()


def run_packaging_smoke(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    articles = [
        Article(
            title='یادگیری عمیق, "پزشکی"',
            authors="Packaging Smoke",
            link="https://example.edu/smoke",
            relevance_score=88.8,
        ),
        Article(title="Unranked Smoke", authors="", link=""),
    ]
    save_to_excel(articles, output_dir / "packaging-smoke.xlsx")
    save_to_csv(articles, output_dir / "packaging-smoke.csv")
