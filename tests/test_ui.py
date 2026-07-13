import queue
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from google_scholar_scraper.models import Article, ExtractionResult, ExtractionStatus
from google_scholar_scraper.ui import tkinter_app
from google_scholar_scraper.ui.tkinter_app import (
    MainWindow,
    SearchRequest,
    SearchWorker,
    WorkerMessage,
    article_row,
    export_path,
    progress_value,
    result_summary,
    status_message,
    validate_search_inputs,
    export_error_message,
)


class DummyVar:
    def __init__(self, value=None) -> None:
        self.value = value

    def get(self):
        return self.value

    def set(self, value) -> None:
        self.value = value


class DummyWidget:
    def __init__(self) -> None:
        self.state = None
        self.visible = True

    def configure(self, **kwargs) -> None:
        if "state" in kwargs:
            self.state = kwargs["state"]

    def grid(self, **_kwargs) -> None:
        self.visible = True

    def grid_remove(self) -> None:
        self.visible = False


class DummyTable:
    def __init__(self) -> None:
        self.rows = []

    def insert(self, _parent, _index, values) -> None:
        self.rows.append(values)

    def get_children(self):
        return list(range(len(self.rows)))

    def delete(self, item) -> None:
        self.rows.pop(item)


class DummyStyle:
    def configure(self, *_args, **_kwargs) -> None:
        return None


class FakeRunningWorker:
    def is_alive(self) -> bool:
        return True


class UiHelperTests(unittest.TestCase):
    def test_validate_search_inputs_rejects_empty_query(self) -> None:
        with self.assertRaisesRegex(ValueError, "Enter a search query"):
            validate_search_inputs("   ", "1", True)

    def test_validate_search_inputs_rejects_invalid_page_count(self) -> None:
        with self.assertRaisesRegex(ValueError, "whole number"):
            validate_search_inputs("query", "abc", True)

    def test_validate_search_inputs_rejects_zero_or_negative_page_count(self) -> None:
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            validate_search_inputs("query", "0", True)
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            validate_search_inputs("query", "-1", True)

    def test_validate_search_inputs_accepts_valid_input(self) -> None:
        request = validate_search_inputs("  machine learning  ", "2", False, " out ")

        self.assertEqual(request, SearchRequest("machine learning", 2, False, "out"))

    def test_progress_value_never_reports_false_full_for_partial(self) -> None:
        self.assertEqual(progress_value(1, 4), 25)
        self.assertEqual(progress_value(4, 4), 100)
        self.assertEqual(progress_value(0, 0), 0)

    def test_article_row_formats_score_and_missing_link(self) -> None:
        ranked = Article(title="Title", authors="Authors", link="https://example.edu", relevance_score=91.24)
        unranked = Article(title="No Link", authors="", link="")

        self.assertEqual(article_row(ranked), ("Title", "Authors", "91.2", "Open link"))
        self.assertEqual(article_row(unranked), ("No Link", "", "", "No link"))

    def test_export_path_preserves_default_filename(self) -> None:
        self.assertEqual(export_path(""), Path("scholar_articles.xlsx"))
        self.assertEqual(export_path("out"), Path("out") / "scholar_articles.xlsx")

    def test_every_status_has_user_message(self) -> None:
        for status in ExtractionStatus:
            result = ExtractionResult(status=status, articles=[], requested_pages=1)
            self.assertTrue(status_message(result))

    def test_result_summary_includes_counts(self) -> None:
        result = ExtractionResult(
            status=ExtractionStatus.SUCCESS,
            articles=[Article("A")],
            requested_pages=3,
            successful_pages=2,
            duplicates_removed=1,
            invalid_articles_removed=1,
        )

        self.assertEqual(result_summary(result), "1 result found | 2/3 pages completed | 1 duplicate removed | 1 invalid record removed")

    def test_export_error_message_is_user_facing(self) -> None:
        self.assertEqual(export_error_message(PermissionError("denied")), "Export failed: denied")


class WorkerTests(unittest.TestCase):
    def test_worker_emits_progress_and_result_without_tkinter(self) -> None:
        messages: queue.Queue[WorkerMessage] = queue.Queue()
        cancel_event = threading.Event()

        def fake_scrape(_query, _pages, ranking_enabled, progress_callback, cancel_event):
            self.assertTrue(ranking_enabled)
            self.assertFalse(cancel_event.is_set())
            progress_callback(1, 2, "requesting")
            return ExtractionResult(
                status=ExtractionStatus.SUCCESS,
                articles=[Article("A", relevance_score=50.0)],
                requested_pages=2,
                successful_pages=1,
                message="Done",
            )

        worker = SearchWorker(SearchRequest("query", 2, True), messages, cancel_event, scrape_func=fake_scrape)
        worker.start()
        worker.join(timeout=2)

        self.assertFalse(worker.is_alive())
        self.assertEqual(messages.get_nowait().kind, "progress")
        result_message = messages.get_nowait()
        self.assertEqual(result_message.kind, "result")
        self.assertEqual(result_message.payload.status, ExtractionStatus.SUCCESS)

    def test_worker_surfaces_exception_as_network_error_result(self) -> None:
        messages: queue.Queue[WorkerMessage] = queue.Queue()
        cancel_event = threading.Event()

        def failing_scrape(*_args, **_kwargs):
            raise RuntimeError("boom")

        worker = SearchWorker(SearchRequest("query", 1, True), messages, cancel_event, scrape_func=failing_scrape)
        worker.start()
        worker.join(timeout=2)

        result_message = messages.get_nowait()
        self.assertEqual(result_message.kind, "result")
        self.assertEqual(result_message.payload.status, ExtractionStatus.NETWORK_ERROR)


class MainWindowStateTests(unittest.TestCase):
    def make_window(self) -> MainWindow:
        window = MainWindow.__new__(MainWindow)
        window.current_articles = []
        window.current_request = SearchRequest("query", 1, True, "")
        window.worker = None
        window.cancel_event = None
        window.query_var = DummyVar("query")
        window.pages_var = DummyVar("1")
        window.ranking_var = DummyVar(True)
        window.output_folder_var = DummyVar("")
        window.status_var = DummyVar("")
        window.status_heading_var = DummyVar("")
        window.summary_var = DummyVar("")
        window.empty_title_var = DummyVar("")
        window.empty_detail_var = DummyVar("")
        window.progress_var = DummyVar(0)
        window.status_frame = DummyWidget()
        window.status_accent = DummyWidget()
        window.status_heading_label = DummyWidget()
        window.status_detail_label = DummyWidget()
        window.style = DummyStyle()
        window.empty_frame = DummyWidget()
        window.table_container = DummyWidget()
        window.button_search = DummyWidget()
        window.button_cancel = DummyWidget()
        window.button_export_excel = DummyWidget()
        window.button_export_csv = DummyWidget()
        window.entry_query = DummyWidget()
        window.entry_pages = DummyWidget()
        window.entry_folder = DummyWidget()
        window.button_browse = DummyWidget()
        window.check_ranking = DummyWidget()
        window.results_table = DummyTable()
        return window

    def test_running_state_disables_search_and_enables_cancel(self) -> None:
        window = self.make_window()

        window._set_running_state()

        self.assertEqual(window.button_search.state, tkinter_app.tk.DISABLED)
        self.assertEqual(window.button_cancel.state, tkinter_app.tk.NORMAL)
        self.assertEqual(window.button_export_excel.state, tkinter_app.tk.DISABLED)
        self.assertEqual(window.button_export_csv.state, tkinter_app.tk.DISABLED)

    def test_idle_state_enables_export_only_with_results(self) -> None:
        window = self.make_window()
        window._set_idle_state()
        self.assertEqual(window.button_export_excel.state, tkinter_app.tk.DISABLED)
        self.assertEqual(window.button_export_csv.state, tkinter_app.tk.DISABLED)

        window.current_articles = [Article("A")]
        window._set_idle_state()
        self.assertEqual(window.button_export_excel.state, tkinter_app.tk.NORMAL)
        self.assertEqual(window.button_export_csv.state, tkinter_app.tk.NORMAL)

    def test_search_does_not_start_second_worker(self) -> None:
        window = self.make_window()
        window.worker = FakeRunningWorker()

        window.start_search()

        self.assertIsInstance(window.worker, FakeRunningWorker)

    def test_cancel_sets_event_and_status(self) -> None:
        window = self.make_window()
        window.worker = FakeRunningWorker()
        window.cancel_event = threading.Event()

        window.cancel_search()

        self.assertTrue(window.cancel_event.is_set())
        self.assertEqual(window.button_cancel.state, tkinter_app.tk.DISABLED)
        self.assertEqual(window.status_heading_var.get(), "Cancelling search")
        self.assertEqual(window.status_var.get(), "Finishing the current safe stop point...")

    def test_handle_progress_updates_status_and_progress(self) -> None:
        window = self.make_window()

        window._handle_progress({"current_page": 1, "total_pages": 4, "phase": "requesting"})

        self.assertEqual(window.progress_var.get(), 25)
        self.assertEqual(window.status_heading_var.get(), "Searching Google Scholar")
        self.assertEqual(window.status_var.get(), "Requesting page 1 of 4...")

    def test_handle_success_result_renders_articles_and_enables_export(self) -> None:
        window = self.make_window()
        result = ExtractionResult(
            status=ExtractionStatus.SUCCESS,
            articles=[Article("A", "Author", "https://example.edu", 80.0)],
            requested_pages=1,
            successful_pages=1,
            message="Done",
        )

        window._handle_result(result)

        self.assertEqual(window.current_articles, result.articles)
        self.assertEqual(window.results_table.rows, [("A", "Author", "80.0", "Open link")])
        self.assertEqual(window.status_heading_var.get(), "Search complete")
        self.assertEqual(window.status_var.get(), "Done")
        self.assertEqual(window.button_export_excel.state, tkinter_app.tk.NORMAL)
        self.assertEqual(window.button_export_csv.state, tkinter_app.tk.NORMAL)

    def test_partial_and_cancelled_results_are_rendered(self) -> None:
        window = self.make_window()
        for status in (ExtractionStatus.PARTIAL_SUCCESS, ExtractionStatus.CANCELLED):
            result = ExtractionResult(
                status=status,
                articles=[Article("A")],
                requested_pages=3,
                successful_pages=1,
                message=status.value,
            )
            window._handle_result(result)
            self.assertEqual(window.current_articles, result.articles)
            self.assertEqual(window.button_export_excel.state, tkinter_app.tk.NORMAL)
            self.assertEqual(window.button_export_csv.state, tkinter_app.tk.NORMAL)

    def test_export_uses_final_displayed_articles(self) -> None:
        window = self.make_window()
        window.current_articles = [Article("A")]
        with tempfile.TemporaryDirectory() as temp_dir:
            window.current_request = SearchRequest("query", 1, True, temp_dir)
            expected_path = Path(temp_dir) / "scholar_articles.xlsx"

            with patch("google_scholar_scraper.ui.tkinter_app.save_to_excel") as save_to_excel:
                window.export_excel_results()

        save_to_excel.assert_called_once_with([Article("A")], expected_path)

    def test_excel_export_failure_updates_status_without_crashing(self) -> None:
        window = self.make_window()
        window.current_articles = [Article("A")]
        with tempfile.TemporaryDirectory() as temp_dir:
            window.current_request = SearchRequest("query", 1, True, temp_dir)

            with (
                patch("google_scholar_scraper.ui.tkinter_app.save_to_excel", side_effect=PermissionError("denied")),
                patch("google_scholar_scraper.ui.tkinter_app.messagebox.showerror") as showerror,
            ):
                window.export_excel_results()

        self.assertEqual(window.status_var.get(), "Export failed: denied")
        showerror.assert_called_once_with("Export failed", "Export failed: denied")

    def test_csv_export_uses_final_displayed_articles(self) -> None:
        window = self.make_window()
        window.current_articles = [Article("A")]
        with tempfile.TemporaryDirectory() as temp_dir:
            window.current_request = SearchRequest("query", 1, True, temp_dir)
            expected_path = Path(temp_dir) / "scholar_articles.csv"

            with patch("google_scholar_scraper.ui.tkinter_app.save_to_csv") as save_to_csv:
                window.export_csv_results()

        save_to_csv.assert_called_once_with([Article("A")], expected_path)

    def test_csv_export_failure_updates_status_without_crashing(self) -> None:
        window = self.make_window()
        window.current_articles = [Article("A")]
        with tempfile.TemporaryDirectory() as temp_dir:
            window.current_request = SearchRequest("query", 1, True, temp_dir)

            with (
                patch("google_scholar_scraper.ui.tkinter_app.save_to_csv", side_effect=OSError("disk full")),
                patch("google_scholar_scraper.ui.tkinter_app.messagebox.showerror") as showerror,
            ):
                window.export_csv_results()

        self.assertEqual(window.status_var.get(), "Export failed: disk full")
        showerror.assert_called_once_with("Export failed", "Export failed: disk full")


if __name__ == "__main__":
    unittest.main()
