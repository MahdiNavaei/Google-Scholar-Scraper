from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import queue
import threading
import webbrowser
import tkinter as tk
from tkinter import filedialog, font as tkfont, ttk

from google_scholar_scraper import __version__
from google_scholar_scraper.exporters import save_to_csv, save_to_excel
from google_scholar_scraper.models import Article, ExtractionResult, ExtractionStatus
from google_scholar_scraper.scraper.client import scrape_scholar


DEFAULT_EXCEL_FILENAME = "scholar_articles.xlsx"
DEFAULT_CSV_FILENAME = "scholar_articles.csv"
APP_TITLE = "Google Scholar Scraper"

STATUS_COLORS = {
    "ready": {"bg": "#eef3f8", "border": "#c8d5e3", "heading": "#1f2937", "detail": "#4b5563"},
    "running": {"bg": "#edf5ff", "border": "#9cc9ff", "heading": "#174ea6", "detail": "#2f5f9f"},
    "success": {"bg": "#ecf8f1", "border": "#9ad7b1", "heading": "#166534", "detail": "#2f6b44"},
    "warning": {"bg": "#fff8e8", "border": "#e7c86f", "heading": "#8a5a00", "detail": "#6f5600"},
    "error": {"bg": "#fff1f2", "border": "#f1a9b3", "heading": "#9f1239", "detail": "#7f1d1d"},
}


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


def export_path(output_folder: str, filename: str = DEFAULT_EXCEL_FILENAME) -> Path:
    if output_folder:
        return Path(output_folder) / filename
    return Path(filename)


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


def status_heading(result: ExtractionResult) -> str:
    headings = {
        ExtractionStatus.SUCCESS: "Search complete",
        ExtractionStatus.PARTIAL_SUCCESS: "Search stopped early",
        ExtractionStatus.NO_RESULTS: "No results found",
        ExtractionStatus.RATE_LIMITED: "Google Scholar temporarily limited requests",
        ExtractionStatus.BLOCKED: "Google Scholar returned a challenge page",
        ExtractionStatus.NETWORK_ERROR: "Network request failed",
        ExtractionStatus.PARSING_ERROR: "Results could not be parsed safely",
        ExtractionStatus.CANCELLED: "Search cancelled",
    }
    return headings[result.status]


def status_tone(result: ExtractionResult) -> str:
    if result.status == ExtractionStatus.SUCCESS:
        return "success"
    if result.status in {ExtractionStatus.PARTIAL_SUCCESS, ExtractionStatus.CANCELLED, ExtractionStatus.RATE_LIMITED}:
        return "warning"
    if result.status in {
        ExtractionStatus.BLOCKED,
        ExtractionStatus.NETWORK_ERROR,
        ExtractionStatus.PARSING_ERROR,
        ExtractionStatus.NO_RESULTS,
    }:
        return "error"
    return "ready"


def result_summary(result: ExtractionResult) -> str:
    result_word = "result" if len(result.articles) == 1 else "results"
    parts = [
        f"{len(result.articles)} {result_word} found",
        f"{result.successful_pages}/{result.requested_pages} pages completed",
    ]
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
    link = "Open link" if article.link else "No link"
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
        self.window.title(f"{APP_TITLE} v{__version__}")
        self.window.geometry("1080x720")
        self.window.minsize(860, 560)
        self.window.configure(bg="#f5f7fb")
        self._configure_style()

        self.message_queue: queue.Queue[WorkerMessage] = queue.Queue()
        self.cancel_event: threading.Event | None = None
        self.worker: SearchWorker | None = None
        self.current_articles: list[Article] = []
        self.current_request: SearchRequest | None = None

        self.query_var = tk.StringVar()
        self.pages_var = tk.StringVar(value="1")
        self.output_folder_var = tk.StringVar()
        self.ranking_var = tk.BooleanVar(value=True)
        self.status_heading_var = tk.StringVar(value="Ready")
        self.status_var = tk.StringVar(value="Enter a query, choose pages, then start a search.")
        self.summary_var = tk.StringVar(value="No search has run yet.")
        self.empty_title_var = tk.StringVar(value="No results yet")
        self.empty_detail_var = tk.StringVar(value="Run a search to review Google Scholar results here.")
        self.progress_var = tk.IntVar(value=0)

        self._build_ui()
        self._set_idle_state()
        self._set_status_tone("ready")
        self.entry_query.focus_set()
        self.window.bind("<Return>", self._handle_enter)
        self.window.bind("<Escape>", self._handle_escape)
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def _configure_style(self) -> None:
        self.default_font = tkfont.nametofont("TkDefaultFont")
        self.default_font.configure(size=10)
        self.heading_font = tkfont.Font(family=self.default_font.actual("family"), size=15, weight="bold")
        self.section_font = tkfont.Font(family=self.default_font.actual("family"), size=11, weight="bold")

        self.style = ttk.Style(self.window)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self.style.configure("App.TFrame", background="#f5f7fb")
        self.style.configure("Header.TFrame", background="#f5f7fb")
        self.style.configure("Section.TLabelframe", background="#f5f7fb", bordercolor="#d8dee9")
        self.style.configure("Section.TLabelframe.Label", background="#f5f7fb", foreground="#1f2937", font=self.section_font)
        self.style.configure("App.TLabel", background="#f5f7fb", foreground="#1f2937")
        self.style.configure("Muted.TLabel", background="#f5f7fb", foreground="#5f6b7a")
        self.style.configure("Title.TLabel", background="#f5f7fb", foreground="#111827", font=self.heading_font)
        self.style.configure("Primary.TButton", padding=(14, 7), foreground="#ffffff", background="#1f6feb")
        self.style.map(
            "Primary.TButton",
            background=[("disabled", "#a7c4ef"), ("pressed", "#174ea6"), ("active", "#2f7df6")],
            foreground=[("disabled", "#eef4ff"), ("!disabled", "#ffffff")],
        )
        self.style.configure("Secondary.TButton", padding=(12, 7))
        self.style.configure("Treeview", rowheight=26)
        self.style.configure("Treeview.Heading", font=(self.default_font.actual("family"), 10, "bold"))
        self.style.configure("Horizontal.TProgressbar", troughcolor="#dfe6ef", background="#1f6feb")

    def _build_ui(self) -> None:
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(4, weight=1)

        header_frame = ttk.Frame(self.window, style="Header.TFrame")
        header_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        header_frame.columnconfigure(0, weight=1)
        ttk.Label(header_frame, text=f"{APP_TITLE} v{__version__}", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header_frame,
            text="Search, rank, review, and export Google Scholar results from a local desktop app.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        search_frame = ttk.LabelFrame(self.window, text="Search setup", style="Section.TLabelframe")
        search_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 8))
        search_frame.columnconfigure(1, weight=1)
        search_frame.columnconfigure(3, weight=1)

        ttk.Label(search_frame, text="Query", style="App.TLabel").grid(row=0, column=0, sticky="w", padx=(12, 8), pady=(12, 8))
        self.entry_query = ttk.Entry(search_frame, textvariable=self.query_var)
        self.entry_query.grid(row=0, column=1, columnspan=4, sticky="ew", padx=(0, 12), pady=(12, 8))

        ttk.Label(search_frame, text="Pages to scan", style="App.TLabel").grid(row=1, column=0, sticky="w", padx=(12, 8), pady=8)
        self.entry_pages = ttk.Entry(search_frame, textvariable=self.pages_var, width=8)
        self.entry_pages.grid(row=1, column=1, sticky="w", padx=(0, 16), pady=8)

        self.check_ranking = ttk.Checkbutton(
            search_frame,
            text="Rank by relevance",
            variable=self.ranking_var,
        )
        self.check_ranking.grid(row=1, column=2, sticky="w", padx=(0, 8), pady=8)
        ttk.Label(
            search_frame,
            text="Uses local lexical scoring; no external AI service.",
            style="Muted.TLabel",
        ).grid(row=1, column=3, columnspan=2, sticky="w", padx=(0, 12), pady=8)

        ttk.Label(search_frame, text="Export folder", style="App.TLabel").grid(row=2, column=0, sticky="w", padx=(12, 8), pady=(8, 12))
        self.entry_folder = ttk.Entry(search_frame, textvariable=self.output_folder_var)
        self.entry_folder.grid(row=2, column=1, columnspan=3, sticky="ew", padx=(0, 8), pady=(8, 12))
        self.button_browse = ttk.Button(search_frame, text="Browse", command=self.browse_folder, style="Secondary.TButton")
        self.button_browse.grid(row=2, column=4, sticky="e", padx=(0, 12), pady=(8, 12))

        action_frame = ttk.Frame(self.window, style="App.TFrame")
        action_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))
        action_frame.columnconfigure(2, weight=1)

        self.button_search = ttk.Button(action_frame, text="Search Scholar", command=self.start_search, style="Primary.TButton")
        self.button_search.grid(row=0, column=0, padx=(0, 8))
        self.button_cancel = ttk.Button(action_frame, text="Cancel", command=self.cancel_search, style="Secondary.TButton")
        self.button_cancel.grid(row=0, column=1, padx=8)

        self.status_frame = tk.Frame(self.window, bd=0, highlightthickness=1)
        self.status_frame.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 10))
        self.status_frame.columnconfigure(0, weight=1)

        self.status_heading_label = tk.Label(
            self.status_frame,
            textvariable=self.status_heading_var,
            anchor="w",
            font=(self.default_font.actual("family"), 10, "bold"),
        )
        self.status_heading_label.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 2))
        self.status_detail_label = tk.Label(self.status_frame, textvariable=self.status_var, anchor="w", justify="left")
        self.status_detail_label.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        self.progress_bar = ttk.Progressbar(self.status_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))

        results_frame = ttk.Frame(self.window, style="App.TFrame")
        results_frame.grid(row=4, column=0, sticky="nsew", padx=16, pady=(0, 16))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(1, weight=1)

        results_header = ttk.Frame(results_frame, style="App.TFrame")
        results_header.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        results_header.columnconfigure(1, weight=1)
        ttk.Label(results_header, text="Results", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(results_header, textvariable=self.summary_var, style="Muted.TLabel").grid(row=0, column=1, sticky="w", padx=12)
        self.button_export_excel = ttk.Button(results_header, text="Export Excel", command=self.export_excel_results, style="Secondary.TButton")
        self.button_export_excel.grid(row=0, column=2, padx=(8, 0))
        self.button_export_csv = ttk.Button(results_header, text="Export CSV", command=self.export_csv_results, style="Secondary.TButton")
        self.button_export_csv.grid(row=0, column=3, padx=(8, 0))

        self.results_content = ttk.Frame(results_frame, style="App.TFrame")
        self.results_content.grid(row=1, column=0, sticky="nsew")
        self.results_content.columnconfigure(0, weight=1)
        self.results_content.rowconfigure(0, weight=1)

        columns = ("title", "authors", "score", "link")
        self.table_container = ttk.Frame(self.results_content, style="App.TFrame")
        self.table_container.grid(row=0, column=0, sticky="nsew")
        self.table_container.columnconfigure(0, weight=1)
        self.table_container.rowconfigure(0, weight=1)

        self.results_table = ttk.Treeview(self.table_container, columns=columns, show="headings", selectmode="browse")
        self.results_table.heading("title", text="Title")
        self.results_table.heading("authors", text="Authors / Source")
        self.results_table.heading("score", text="Relevance")
        self.results_table.heading("link", text="Link")
        self.results_table.column("title", width=360, minwidth=220, stretch=True)
        self.results_table.column("authors", width=270, minwidth=170, stretch=True)
        self.results_table.column("score", width=90, minwidth=80, anchor="center", stretch=False)
        self.results_table.column("link", width=90, minwidth=80, anchor="center", stretch=False)
        self.results_table.grid(row=0, column=0, sticky="nsew")
        self.results_table.bind("<Double-1>", self.open_selected_link)

        scrollbar = ttk.Scrollbar(self.table_container, orient="vertical", command=self.results_table.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        horizontal_scrollbar = ttk.Scrollbar(self.table_container, orient="horizontal", command=self.results_table.xview)
        horizontal_scrollbar.grid(row=1, column=0, sticky="ew")
        self.results_table.configure(yscrollcommand=scrollbar.set, xscrollcommand=horizontal_scrollbar.set)

        self.empty_frame = ttk.Frame(self.results_content, style="App.TFrame")
        self.empty_frame.grid(row=0, column=0, sticky="nsew")
        self.empty_frame.columnconfigure(0, weight=1)
        self.empty_frame.rowconfigure(0, weight=1)
        empty_inner = ttk.Frame(self.empty_frame, style="App.TFrame")
        empty_inner.grid(row=0, column=0)
        ttk.Label(empty_inner, textvariable=self.empty_title_var, style="Title.TLabel").grid(row=0, column=0, pady=(0, 6))
        ttk.Label(empty_inner, textvariable=self.empty_detail_var, style="Muted.TLabel").grid(row=1, column=0)
        self.table_container.grid_remove()

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
            self._set_status("Check search setup", str(exc), "error")
            return

        self.current_request = request
        self.current_articles = []
        self._clear_results()
        self._show_empty_state("Searching", "Results will appear here as soon as the search completes.")
        self.progress_var.set(0)
        self.summary_var.set("Searching...")
        self._set_status("Searching Google Scholar", "Starting search...", "running")
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
            self._set_status("Cancelling search", "Finishing the current safe stop point...", "warning")

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

    def export_excel_results(self) -> None:
        if not self.current_articles:
            self.status_var.set("No results to export.")
            return

        folder = self.current_request.output_folder if self.current_request else self.output_folder_var.get().strip()
        path = export_path(folder)
        save_to_excel(self.current_articles, path)
        self.status_var.set(f"Exported {len(self.current_articles)} results to {path}.")

    def export_csv_results(self) -> None:
        if not self.current_articles:
            self.status_var.set("No results to export.")
            return

        folder = self.current_request.output_folder if self.current_request else self.output_folder_var.get().strip()
        path = export_path(folder, DEFAULT_CSV_FILENAME)
        save_to_csv(self.current_articles, path)
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
        self._set_status(
            "Searching Google Scholar",
            f"{phase.capitalize()} page {current_page} of {total_pages}...",
            "running",
        )

    def _handle_result(self, payload: object) -> None:
        result = payload if isinstance(payload, ExtractionResult) else None
        if result is None:
            self._set_status("Search failed", "The application did not receive a valid result.", "error")
            self._show_empty_state("No results to display", "The search ended before any results could be shown.")
            self._set_idle_state()
            return

        self.current_articles = result.articles
        if result.articles:
            self._render_results(result.articles)
        else:
            self._clear_results()
            self._show_empty_state("No results to display", status_message(result))
        self._set_status(status_heading(result), status_message(result), status_tone(result))
        self.summary_var.set(result_summary(result))
        self.progress_var.set(progress_value(result.successful_pages, result.requested_pages))
        self._set_idle_state()

    def _render_results(self, articles: list[Article]) -> None:
        self._clear_results()
        for article in articles:
            self.results_table.insert("", tk.END, values=article_row(article))
        self._show_results_table()

    def _clear_results(self) -> None:
        for item in self.results_table.get_children():
            self.results_table.delete(item)

    def _show_results_table(self) -> None:
        self.empty_frame.grid_remove()
        self.table_container.grid()

    def _show_empty_state(self, title: str, detail: str) -> None:
        self.empty_title_var.set(title)
        self.empty_detail_var.set(detail)
        self.table_container.grid_remove()
        self.empty_frame.grid()

    def _set_status(self, heading: str, detail: str, tone: str) -> None:
        self.status_heading_var.set(heading)
        self.status_var.set(detail)
        self._set_status_tone(tone)

    def _set_status_tone(self, tone: str) -> None:
        colors = STATUS_COLORS.get(tone, STATUS_COLORS["ready"])
        self.status_frame.configure(bg=colors["bg"], highlightbackground=colors["border"])
        self.status_heading_label.configure(bg=colors["bg"], fg=colors["heading"])
        self.status_detail_label.configure(bg=colors["bg"], fg=colors["detail"])

    def _set_running_state(self) -> None:
        self.button_search.configure(state=tk.DISABLED)
        self.button_cancel.configure(state=tk.NORMAL)
        self.button_export_excel.configure(state=tk.DISABLED)
        self.button_export_csv.configure(state=tk.DISABLED)
        self.entry_query.configure(state=tk.DISABLED)
        self.entry_pages.configure(state=tk.DISABLED)
        self.entry_folder.configure(state=tk.DISABLED)
        self.button_browse.configure(state=tk.DISABLED)
        self.check_ranking.configure(state=tk.DISABLED)

    def _set_idle_state(self) -> None:
        self.button_search.configure(state=tk.NORMAL)
        self.button_cancel.configure(state=tk.DISABLED)
        export_state = tk.NORMAL if self.current_articles else tk.DISABLED
        self.button_export_excel.configure(state=export_state)
        self.button_export_csv.configure(state=export_state)
        self.entry_query.configure(state=tk.NORMAL)
        self.entry_pages.configure(state=tk.NORMAL)
        self.entry_folder.configure(state=tk.NORMAL)
        self.button_browse.configure(state=tk.NORMAL)
        self.check_ranking.configure(state=tk.NORMAL)

    def _is_running(self) -> bool:
        return bool(self.worker and self.worker.is_alive())

    def _handle_enter(self, _event=None) -> None:
        if not self._is_running():
            self.start_search()

    def _handle_escape(self, _event=None) -> None:
        if self._is_running():
            self.cancel_search()


def run() -> None:
    app = MainWindow()
    app.run()
