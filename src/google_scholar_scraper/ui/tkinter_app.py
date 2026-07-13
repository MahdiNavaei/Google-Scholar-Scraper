from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import queue
import threading
import webbrowser
import tkinter as tk
from tkinter import filedialog, ttk

from google_scholar_scraper.exporters import save_to_excel
from google_scholar_scraper.models import Article, ExtractionResult, ExtractionStatus
from google_scholar_scraper.scraper.client import scrape_scholar


DEFAULT_EXCEL_FILENAME = "scholar_articles.xlsx"


@dataclass(frozen=True)
class SearchRequest:
    query: str
    pages: int
    ranking_enabled: bool
    output_folder: str = ""


@dataclass(frozen=True)
class WorkerMessage:
    kind: str
    payload: object


def validate_search_inputs(query: str, pages: str, ranking_enabled: bool, output_folder: str = "") -> SearchRequest:
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("Enter a search query.")

    try:
        page_count = int(pages.strip())
    except ValueError as exc:
        raise ValueError("Page count must be a whole number.") from exc

    if page_count <= 0:
        raise ValueError("Page count must be greater than zero.")

    return SearchRequest(
        query=clean_query,
        pages=page_count,
        ranking_enabled=ranking_enabled,
        output_folder=output_folder.strip(),
    )


def export_path(output_folder: str) -> Path:
    if output_folder:
        return Path(output_folder) / DEFAULT_EXCEL_FILENAME
    return Path(DEFAULT_EXCEL_FILENAME)


def status_message(result: ExtractionResult) -> str:
    messages = {
        ExtractionStatus.SUCCESS: result.message or "Search completed successfully.",
        ExtractionStatus.PARTIAL_SUCCESS: result.message or "Search stopped early. Collected results were preserved.",
        ExtractionStatus.NO_RESULTS: result.message or "No results found.",
        ExtractionStatus.RATE_LIMITED: result.message or "Google Scholar temporarily limited requests.",
        ExtractionStatus.BLOCKED: result.message or "Google Scholar returned a blocked or challenge page.",
        ExtractionStatus.NETWORK_ERROR: result.message or "Network request failed.",
        ExtractionStatus.PARSING_ERROR: result.message or "The response could not be interpreted safely.",
        ExtractionStatus.CANCELLED: result.message or "Search was cancelled.",
    }
    return messages[result.status]


def result_summary(result: ExtractionResult) -> str:
    parts = [f"{len(result.articles)} results", f"{result.successful_pages} of {result.requested_pages} pages completed"]
    if result.duplicates_removed:
        parts.append(f"{result.duplicates_removed} duplicate removed" + ("" if result.duplicates_removed == 1 else "s"))
    if result.invalid_articles_removed:
        parts.append(
            f"{result.invalid_articles_removed} invalid record removed"
            + ("" if result.invalid_articles_removed == 1 else "s")
        )
    return " | ".join(parts)


def progress_value(current_page: int, total_pages: int) -> int:
    if total_pages <= 0:
        return 0
    return max(0, min(100, int((current_page / total_pages) * 100)))


def article_row(article: Article) -> tuple[str, str, str, str]:
    score = "" if article.relevance_score is None else f"{article.relevance_score:.1f}"
    link = article.link if article.link else "No link"
    return (article.title, article.authors, score, link)


class SearchWorker(threading.Thread):
    def __init__(
        self,
        request: SearchRequest,
        message_queue: queue.Queue[WorkerMessage],
        cancel_event: threading.Event,
        scrape_func=scrape_scholar,
    ) -> None:
        super().__init__(daemon=True)
        self.request = request
        self.message_queue = message_queue
        self.cancel_event = cancel_event
        self.scrape_func = scrape_func

    def run(self) -> None:
        try:
            result = self.scrape_func(
                self.request.query,
                self.request.pages,
                ranking_enabled=self.request.ranking_enabled,
                progress_callback=self._progress,
                cancel_event=self.cancel_event,
            )
        except Exception as exc:  # defensive UI boundary: do not surface tracebacks in normal UI
            result = ExtractionResult(
                status=ExtractionStatus.NETWORK_ERROR,
                articles=[],
                requested_pages=self.request.pages,
                message=f"Search failed: {exc.__class__.__name__}.",
                diagnostic=exc.__class__.__name__,
            )
        self.message_queue.put(WorkerMessage("result", result))

    def _progress(self, current_page: int, total_pages: int, phase: str) -> None:
        self.message_queue.put(
            WorkerMessage(
                "progress",
                {
                    "current_page": current_page,
                    "total_pages": total_pages,
                    "phase": phase,
                },
            )
        )


class MainWindow:
    def __init__(self) -> None:
        self.window = tk.Tk()
        self.window.title("Google Scholar Scraper")
        self.window.geometry("1000x680")
        self.window.minsize(820, 520)

        self.message_queue: queue.Queue[WorkerMessage] = queue.Queue()
        self.cancel_event: threading.Event | None = None
        self.worker: SearchWorker | None = None
        self.current_articles: list[Article] = []
        self.current_request: SearchRequest | None = None

        self.query_var = tk.StringVar()
        self.pages_var = tk.StringVar(value="1")
        self.output_folder_var = tk.StringVar()
        self.ranking_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Ready.")
        self.summary_var = tk.StringVar(value="No results yet.")
        self.progress_var = tk.IntVar(value=0)

        self._build_ui()
        self._set_idle_state()
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self) -> None:
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(3, weight=1)

        search_frame = ttk.LabelFrame(self.window, text="Search")
        search_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))
        search_frame.columnconfigure(1, weight=1)
        search_frame.columnconfigure(4, weight=1)

        ttk.Label(search_frame, text="Query").grid(row=0, column=0, sticky="w", padx=8, pady=8)
        self.entry_query = ttk.Entry(search_frame, textvariable=self.query_var)
        self.entry_query.grid(row=0, column=1, columnspan=4, sticky="ew", padx=8, pady=8)

        ttk.Label(search_frame, text="Pages").grid(row=1, column=0, sticky="w", padx=8, pady=8)
        self.entry_pages = ttk.Entry(search_frame, textvariable=self.pages_var, width=8)
        self.entry_pages.grid(row=1, column=1, sticky="w", padx=8, pady=8)

        self.check_ranking = ttk.Checkbutton(
            search_frame,
            text="Smart Relevance Ranking",
            variable=self.ranking_var,
        )
        self.check_ranking.grid(row=1, column=2, sticky="w", padx=8, pady=8)

        ttk.Label(search_frame, text="Output folder").grid(row=2, column=0, sticky="w", padx=8, pady=8)
        self.entry_folder = ttk.Entry(search_frame, textvariable=self.output_folder_var)
        self.entry_folder.grid(row=2, column=1, columnspan=3, sticky="ew", padx=8, pady=8)
        self.button_browse = ttk.Button(search_frame, text="Browse", command=self.browse_folder)
        self.button_browse.grid(row=2, column=4, sticky="e", padx=8, pady=8)

        action_frame = ttk.Frame(self.window)
        action_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=4)
        action_frame.columnconfigure(3, weight=1)

        self.button_search = ttk.Button(action_frame, text="Search", command=self.start_search)
        self.button_search.grid(row=0, column=0, padx=(0, 8))
        self.button_cancel = ttk.Button(action_frame, text="Cancel", command=self.cancel_search)
        self.button_cancel.grid(row=0, column=1, padx=8)
        self.button_export = ttk.Button(action_frame, text="Export Excel", command=self.export_results)
        self.button_export.grid(row=0, column=2, padx=8)

        progress_frame = ttk.Frame(self.window)
        progress_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=8)
        progress_frame.columnconfigure(0, weight=1)

        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky="ew")
        ttk.Label(progress_frame, textvariable=self.status_var).grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Label(progress_frame, textvariable=self.summary_var).grid(row=2, column=0, sticky="w", pady=(2, 0))

        results_frame = ttk.LabelFrame(self.window, text="Results")
        results_frame.grid(row=3, column=0, sticky="nsew", padx=12, pady=(4, 12))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)

        columns = ("title", "authors", "score", "link")
        self.results_table = ttk.Treeview(results_frame, columns=columns, show="headings", selectmode="browse")
        self.results_table.heading("title", text="Title")
        self.results_table.heading("authors", text="Authors / Source")
        self.results_table.heading("score", text="Relevance")
        self.results_table.heading("link", text="Link")
        self.results_table.column("title", width=360, minwidth=220)
        self.results_table.column("authors", width=260, minwidth=160)
        self.results_table.column("score", width=90, minwidth=80, anchor="center")
        self.results_table.column("link", width=260, minwidth=120)
        self.results_table.grid(row=0, column=0, sticky="nsew")
        self.results_table.bind("<Double-1>", self.open_selected_link)

        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_table.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.results_table.configure(yscrollcommand=scrollbar.set)

    def browse_folder(self) -> None:
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.output_folder_var.set(folder_path)

    def start_search(self) -> None:
        if self._is_running():
            return

        try:
            request = validate_search_inputs(
                self.query_var.get(),
                self.pages_var.get(),
                self.ranking_var.get(),
                self.output_folder_var.get(),
            )
        except ValueError as exc:
            self.status_var.set(str(exc))
            return

        self.current_request = request
        self.current_articles = []
        self._clear_results()
        self.progress_var.set(0)
        self.summary_var.set("Searching...")
        self.status_var.set("Starting search...")
        self._set_running_state()

        self.cancel_event = threading.Event()
        self.message_queue = queue.Queue()
        self.worker = SearchWorker(request, self.message_queue, self.cancel_event)
        self.worker.start()
        self.window.after(100, self.poll_worker_queue)

    def cancel_search(self) -> None:
        if self.cancel_event is not None and self._is_running():
            self.cancel_event.set()
            self.button_cancel.configure(state=tk.DISABLED)
            self.status_var.set("Cancelling...")

    def poll_worker_queue(self) -> None:
        while True:
            try:
                message = self.message_queue.get_nowait()
            except queue.Empty:
                break

            if message.kind == "progress":
                self._handle_progress(message.payload)
            elif message.kind == "result":
                self._handle_result(message.payload)

        if self._is_running():
            self.window.after(100, self.poll_worker_queue)

    def export_results(self) -> None:
        if not self.current_articles:
            self.status_var.set("No results to export.")
            return

        folder = self.current_request.output_folder if self.current_request else self.output_folder_var.get().strip()
        path = export_path(folder)
        save_to_excel(self.current_articles, path)
        self.status_var.set(f"Exported {len(self.current_articles)} results to {path}.")

    def open_selected_link(self, _event=None) -> None:
        selected = self.results_table.selection()
        if not selected:
            return
        index = self.results_table.index(selected[0])
        if index >= len(self.current_articles):
            return
        link = self.current_articles[index].link
        if link:
            webbrowser.open(link)

    def on_close(self) -> None:
        if self._is_running() and self.cancel_event is not None:
            self.cancel_event.set()
        self.window.destroy()

    def run(self) -> None:
        self.window.mainloop()

    def _handle_progress(self, payload: object) -> None:
        data = payload if isinstance(payload, dict) else {}
        current_page = int(data.get("current_page", 0))
        total_pages = int(data.get("total_pages", 0))
        phase = str(data.get("phase", "working"))
        self.progress_var.set(progress_value(current_page, total_pages))
        self.status_var.set(f"{phase.capitalize()} page {current_page} of {total_pages}...")

    def _handle_result(self, payload: object) -> None:
        result = payload if isinstance(payload, ExtractionResult) else None
        if result is None:
            self.status_var.set("Search failed.")
            self._set_idle_state()
            return

        self.current_articles = result.articles
        self._render_results(result.articles)
        self.status_var.set(status_message(result))
        self.summary_var.set(result_summary(result))
        self.progress_var.set(progress_value(result.successful_pages, result.requested_pages))
        self._set_idle_state()

    def _render_results(self, articles: list[Article]) -> None:
        self._clear_results()
        for article in articles:
            self.results_table.insert("", tk.END, values=article_row(article))

    def _clear_results(self) -> None:
        for item in self.results_table.get_children():
            self.results_table.delete(item)

    def _set_running_state(self) -> None:
        self.button_search.configure(state=tk.DISABLED)
        self.button_cancel.configure(state=tk.NORMAL)
        self.button_export.configure(state=tk.DISABLED)
        self.entry_query.configure(state=tk.DISABLED)
        self.entry_pages.configure(state=tk.DISABLED)
        self.entry_folder.configure(state=tk.DISABLED)
        self.button_browse.configure(state=tk.DISABLED)
        self.check_ranking.configure(state=tk.DISABLED)

    def _set_idle_state(self) -> None:
        self.button_search.configure(state=tk.NORMAL)
        self.button_cancel.configure(state=tk.DISABLED)
        self.button_export.configure(state=tk.NORMAL if self.current_articles else tk.DISABLED)
        self.entry_query.configure(state=tk.NORMAL)
        self.entry_pages.configure(state=tk.NORMAL)
        self.entry_folder.configure(state=tk.NORMAL)
        self.button_browse.configure(state=tk.NORMAL)
        self.check_ranking.configure(state=tk.NORMAL)

    def _is_running(self) -> bool:
        return bool(self.worker and self.worker.is_alive())


def run() -> None:
    app = MainWindow()
    app.run()
