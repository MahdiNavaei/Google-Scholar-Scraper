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

COLORS = {
    "app_bg": "#f3f6fb",
    "surface": "#ffffff",
    "surface_alt": "#f8fafc",
    "text": "#111827",
    "muted": "#5b677a",
    "border": "#d8e0ea",
    "border_strong": "#b9c6d6",
    "primary": "#185abc",
    "primary_hover": "#1f6feb",
    "secondary_hover": "#f4f7fb",
    "disabled": "#a6afbd",
    "selection": "#dbeafe",
}

STATUS_COLORS = {
    "ready": {"bg": "#f8fafc", "border": "#d8e0ea", "accent": "#64748b", "heading": "#1f2937", "detail": "#5b677a"},
    "running": {"bg": "#f5f9ff", "border": "#c5dcfb", "accent": "#185abc", "heading": "#174ea6", "detail": "#355f96"},
    "success": {"bg": "#f4fbf7", "border": "#bde7cd", "accent": "#16803c", "heading": "#166534", "detail": "#366b49"},
    "warning": {"bg": "#fffaf0", "border": "#edd79a", "accent": "#b7791f", "heading": "#8a5a00", "detail": "#725a18"},
    "error": {"bg": "#fff5f6", "border": "#f2bdc5", "accent": "#c0264d", "heading": "#9f1239", "detail": "#7f1d1d"},
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
        self.window.geometry("1080x700")
        self.window.minsize(860, 560)
        self.window.configure(bg=COLORS["app_bg"])
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
        try:
            self.default_font.configure(family="Segoe UI", size=10)
        except tk.TclError:
            self.default_font.configure(size=10)
        font_family = self.default_font.actual("family")
        self.heading_font = tkfont.Font(family=font_family, size=16, weight="bold")
        self.section_font = tkfont.Font(family=self.default_font.actual("family"), size=11, weight="bold")
        self.status_font = tkfont.Font(family=font_family, size=10, weight="bold")
        self.table_font = tkfont.Font(family=font_family, size=10)
        self.table_heading_font = tkfont.Font(family=font_family, size=10, weight="bold")

        self.style = ttk.Style(self.window)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self.style.configure("App.TFrame", background=COLORS["app_bg"])
        self.style.configure("Surface.TFrame", background=COLORS["surface"])
        self.style.configure("Header.TFrame", background=COLORS["app_bg"])
        self.style.configure("App.TLabel", background=COLORS["app_bg"], foreground=COLORS["text"])
        self.style.configure("Surface.TLabel", background=COLORS["surface"], foreground=COLORS["text"])
        self.style.configure("Muted.TLabel", background=COLORS["app_bg"], foreground=COLORS["muted"])
        self.style.configure("SurfaceMuted.TLabel", background=COLORS["surface"], foreground=COLORS["muted"])
        self.style.configure("Title.TLabel", background=COLORS["app_bg"], foreground=COLORS["text"], font=self.heading_font)
        self.style.configure("SectionTitle.TLabel", background=COLORS["surface"], foreground=COLORS["text"], font=self.section_font)
        self.style.configure("TEntry", fieldbackground="#ffffff", bordercolor=COLORS["border_strong"], lightcolor=COLORS["border"], darkcolor=COLORS["border"])
        self.style.map("TEntry", bordercolor=[("focus", COLORS["primary"])])
        self.style.configure("Horizontal.TProgressbar", troughcolor="#edf2f7", background=COLORS["primary"], bordercolor="#edf2f7", lightcolor=COLORS["primary"], darkcolor=COLORS["primary"])
        self.style.configure(
            "Treeview",
            background="#ffffff",
            fieldbackground="#ffffff",
            foreground=COLORS["text"],
            rowheight=30,
            borderwidth=0,
            relief="flat",
            font=self.table_font,
        )
        self.style.map(
            "Treeview",
            background=[("selected", COLORS["selection"])],
            foreground=[("selected", COLORS["text"])],
        )
        self.style.configure(
            "Treeview.Heading",
            background="#eef3f8",
            foreground=COLORS["text"],
            bordercolor=COLORS["border"],
            relief="flat",
            font=self.table_heading_font,
        )

    def _surface(self, parent, *, border: str | None = None) -> tk.Frame:
        return tk.Frame(
            parent,
            bg=COLORS["surface"],
            bd=0,
            highlightthickness=1 if border else 0,
            highlightbackground=border or COLORS["surface"],
            highlightcolor=border or COLORS["surface"],
        )

    def _button(self, parent, *, text: str, command, kind: str = "secondary", width: int | None = None) -> tk.Button:
        is_primary = kind == "primary"
        button = tk.Button(
            parent,
            text=text,
            command=command,
            width=width or (16 if is_primary else 12),
            padx=12,
            pady=7,
            bd=0,
            relief=tk.FLAT,
            cursor="hand2",
            font=(self.default_font.actual("family"), 10, "bold" if is_primary else "normal"),
            bg=COLORS["primary"] if is_primary else COLORS["surface_alt"],
            fg="#ffffff" if is_primary else COLORS["text"],
            activebackground=COLORS["primary_hover"] if is_primary else COLORS["secondary_hover"],
            activeforeground="#ffffff" if is_primary else COLORS["text"],
            disabledforeground="#edf4ff" if is_primary else COLORS["disabled"],
            highlightthickness=1,
            highlightbackground=COLORS["primary"] if is_primary else COLORS["border_strong"],
            highlightcolor=COLORS["primary"] if is_primary else COLORS["border_strong"],
        )
        return button

    def _build_ui(self) -> None:
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(4, weight=1)

        header_frame = ttk.Frame(self.window, style="Header.TFrame")
        header_frame.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 10))
        header_frame.columnconfigure(0, weight=1)
        ttk.Label(header_frame, text=f"{APP_TITLE} v{__version__}", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header_frame,
            text="Search, rank, review, and export Google Scholar results from a local desktop app.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        search_frame = self._surface(self.window, border=COLORS["border"])
        search_frame.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))
        search_frame.columnconfigure(1, weight=1)
        search_frame.columnconfigure(3, weight=1)

        ttk.Label(search_frame, text="Search setup", style="SectionTitle.TLabel").grid(row=0, column=0, columnspan=5, sticky="w", padx=14, pady=(12, 4))

        ttk.Label(search_frame, text="Query", style="Surface.TLabel").grid(row=1, column=0, sticky="w", padx=(14, 10), pady=(8, 8))
        self.entry_query = ttk.Entry(search_frame, textvariable=self.query_var)
        self.entry_query.grid(row=1, column=1, columnspan=4, sticky="ew", padx=(0, 14), pady=(8, 8), ipady=3)

        ttk.Label(search_frame, text="Pages to scan", style="Surface.TLabel").grid(row=2, column=0, sticky="w", padx=(14, 10), pady=8)
        self.entry_pages = ttk.Entry(search_frame, textvariable=self.pages_var, width=8)
        self.entry_pages.grid(row=2, column=1, sticky="w", padx=(0, 18), pady=8, ipady=3)

        self.check_ranking = tk.Checkbutton(
            search_frame,
            text="Rank by relevance",
            variable=self.ranking_var,
            bg=COLORS["surface"],
            fg=COLORS["text"],
            activebackground=COLORS["surface"],
            activeforeground=COLORS["text"],
            selectcolor="#ffffff",
            bd=0,
            highlightthickness=0,
            font=(self.default_font.actual("family"), 10),
        )
        self.check_ranking.grid(row=2, column=2, sticky="w", padx=(0, 8), pady=8)
        ttk.Label(
            search_frame,
            text="Uses local lexical scoring; no external AI service.",
            style="SurfaceMuted.TLabel",
        ).grid(row=2, column=3, columnspan=2, sticky="w", padx=(0, 14), pady=8)

        ttk.Label(search_frame, text="Export folder", style="Surface.TLabel").grid(row=3, column=0, sticky="w", padx=(14, 10), pady=(8, 14))
        self.entry_folder = ttk.Entry(search_frame, textvariable=self.output_folder_var)
        self.entry_folder.grid(row=3, column=1, columnspan=3, sticky="ew", padx=(0, 10), pady=(8, 14), ipady=3)
        self.button_browse = self._button(search_frame, text="Browse", command=self.browse_folder, width=11)
        self.button_browse.grid(row=3, column=4, sticky="e", padx=(0, 14), pady=(8, 14))

        action_frame = ttk.Frame(self.window, style="App.TFrame")
        action_frame.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 10))
        action_frame.columnconfigure(2, weight=1)

        self.button_search = self._button(action_frame, text="Search Scholar", command=self.start_search, kind="primary", width=16)
        self.button_search.grid(row=0, column=0, padx=(0, 8))
        self.button_cancel = self._button(action_frame, text="Cancel", command=self.cancel_search, width=12)
        self.button_cancel.grid(row=0, column=1, padx=(4, 0))

        self.status_frame = self._surface(self.window, border=COLORS["border"])
        self.status_frame.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 10))
        self.status_frame.columnconfigure(1, weight=1)
        self.status_accent = tk.Frame(self.status_frame, width=4, bg=STATUS_COLORS["ready"]["accent"])
        self.status_accent.grid(row=0, column=0, rowspan=3, sticky="nsw")

        self.status_heading_label = tk.Label(
            self.status_frame,
            textvariable=self.status_heading_var,
            anchor="w",
            font=self.status_font,
        )
        self.status_heading_label.grid(row=0, column=1, sticky="ew", padx=14, pady=(10, 2))
        self.status_detail_label = tk.Label(self.status_frame, textvariable=self.status_var, anchor="w", justify="left")
        self.status_detail_label.grid(row=1, column=1, sticky="ew", padx=14, pady=(0, 7))
        self.progress_bar = ttk.Progressbar(self.status_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=2, column=1, sticky="ew", padx=14, pady=(0, 11))

        results_frame = ttk.Frame(self.window, style="App.TFrame")
        results_frame.grid(row=4, column=0, sticky="nsew", padx=18, pady=(0, 18))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(1, weight=1)

        results_header = ttk.Frame(results_frame, style="App.TFrame")
        results_header.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        results_header.columnconfigure(1, weight=1)
        ttk.Label(results_header, text="Results", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(results_header, textvariable=self.summary_var, style="Muted.TLabel").grid(row=0, column=1, sticky="w", padx=12)
        self.button_export_excel = self._button(results_header, text="Export Excel", command=self.export_excel_results, width=12)
        self.button_export_excel.grid(row=0, column=2, padx=(8, 0))
        self.button_export_csv = self._button(results_header, text="Export CSV", command=self.export_csv_results, width=12)
        self.button_export_csv.grid(row=0, column=3, padx=(8, 0))

        self.results_content = ttk.Frame(results_frame, style="App.TFrame")
        self.results_content.grid(row=1, column=0, sticky="nsew")
        self.results_content.columnconfigure(0, weight=1)
        self.results_content.rowconfigure(0, weight=1)

        columns = ("title", "authors", "score", "link")
        self.table_container = self._surface(self.results_content, border=COLORS["border"])
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
            self._set_button_state(self.button_cancel, tk.DISABLED)
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
        self.status_accent.configure(bg=colors["accent"])
        self.status_heading_label.configure(bg=colors["bg"], fg=colors["heading"])
        self.status_detail_label.configure(bg=colors["bg"], fg=colors["detail"])
        self.style.configure("Horizontal.TProgressbar", background=colors["accent"], lightcolor=colors["accent"], darkcolor=colors["accent"])

    def _set_running_state(self) -> None:
        self._set_button_state(self.button_search, tk.DISABLED, kind="primary")
        self._set_button_state(self.button_cancel, tk.NORMAL)
        self._set_button_state(self.button_export_excel, tk.DISABLED)
        self._set_button_state(self.button_export_csv, tk.DISABLED)
        self.entry_query.configure(state=tk.DISABLED)
        self.entry_pages.configure(state=tk.DISABLED)
        self.entry_folder.configure(state=tk.DISABLED)
        self.button_browse.configure(state=tk.DISABLED)
        self.check_ranking.configure(state=tk.DISABLED)

    def _set_idle_state(self) -> None:
        self._set_button_state(self.button_search, tk.NORMAL, kind="primary")
        self._set_button_state(self.button_cancel, tk.DISABLED)
        export_state = tk.NORMAL if self.current_articles else tk.DISABLED
        self._set_button_state(self.button_export_excel, export_state)
        self._set_button_state(self.button_export_csv, export_state)
        self.entry_query.configure(state=tk.NORMAL)
        self.entry_pages.configure(state=tk.NORMAL)
        self.entry_folder.configure(state=tk.NORMAL)
        self.button_browse.configure(state=tk.NORMAL)
        self.check_ranking.configure(state=tk.NORMAL)

    def _set_button_state(self, button, state: str, *, kind: str = "secondary") -> None:
        is_primary = kind == "primary"
        if state == tk.DISABLED:
            button.configure(
                state=tk.DISABLED,
                bg="#9bbbe8" if is_primary else "#f1f4f8",
                fg="#edf4ff" if is_primary else COLORS["disabled"],
                highlightbackground="#9bbbe8" if is_primary else COLORS["border"],
                cursor="arrow",
            )
            return
        button.configure(
            state=tk.NORMAL,
            bg=COLORS["primary"] if is_primary else COLORS["surface_alt"],
            fg="#ffffff" if is_primary else COLORS["text"],
            highlightbackground=COLORS["primary"] if is_primary else COLORS["border_strong"],
            cursor="hand2",
        )

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
