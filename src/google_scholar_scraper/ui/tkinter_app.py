import tkinter as tk
from tkinter import filedialog

from google_scholar_scraper.exporters import save_to_excel
from google_scholar_scraper.models import ExtractionStatus
from google_scholar_scraper.scraper.client import scrape_scholar


class MainWindow:
    def __init__(self) -> None:
        self.window = tk.Tk()
        self.window.title("Google Scholar Scraper")
        self.window.geometry("400x250")

        label_query = tk.Label(self.window, text="Article Title or Keyword:")
        label_query.pack()
        self.entry_query = tk.Entry(self.window, width=40)
        self.entry_query.pack()

        label_pages = tk.Label(self.window, text="Number of Pages:")
        label_pages.pack()
        self.entry_pages = tk.Entry(self.window, width=40)
        self.entry_pages.pack()

        label_folder = tk.Label(self.window, text="Output Folder (optional):")
        label_folder.pack()
        self.entry_folder = tk.Entry(self.window, width=40)
        self.entry_folder.pack()

        button_browse = tk.Button(self.window, text="Browse", command=self.browse_folder)
        button_browse.pack()

        button_extract = tk.Button(self.window, text="Extract Data", command=self.scrape_articles)
        button_extract.pack()

        self.label_status = tk.Label(self.window, text="")
        self.label_status.pack()

    def browse_folder(self) -> None:
        folder_path = filedialog.askdirectory()
        self.entry_folder.delete(0, tk.END)
        self.entry_folder.insert(tk.END, folder_path)

    def scrape_articles(self) -> None:
        query = self.entry_query.get()
        num_pages = int(self.entry_pages.get())

        result = scrape_scholar(query, num_pages)

        folder_path = self.entry_folder.get()
        if folder_path:
            filename = f"{folder_path}/scholar_articles.xlsx"
        else:
            filename = "scholar_articles.xlsx"

        if result.status in {ExtractionStatus.SUCCESS, ExtractionStatus.PARTIAL_SUCCESS} and result.articles:
            save_to_excel(result.articles, filename)
            self.label_status.config(text=f"{result.message} Data saved to scholar_articles.xlsx.")
            return

        self.label_status.config(text=result.message)

    def run(self) -> None:
        self.window.mainloop()


def run() -> None:
    app = MainWindow()
    app.run()
