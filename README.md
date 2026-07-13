# Google-Scholar-Scraper
The Google Scholar Scraper is a Python program that allows users to extract articles from Google Scholar based on the provided title or keyword. It retrieves the article's title, authors, and link, and saves the extracted data into an Excel file. The program utilizes web scraping techniques to navigate through multiple pages of search results, providing a comprehensive extraction process.


## Features:

1-  User-friendly interface: The program offers a simple and intuitive graphical user interface (GUI) built using the Tkinter library.

2- Customizable search: Users can enter their desired article title or keyword to retrieve relevant scholarly articles.

3- Multiple page scraping: Users can specify the number of pages they want to scrape, allowing them to extract data from a larger pool of search results.

4- Data extraction: The program extracts the article's title, authors, and link for each entry, ensuring comprehensive data retrieval.

5- Excel and CSV output: The extracted data can be exported after review as either an Excel workbook or a UTF-8 CSV file.

6- Optional output folder: Users can specify the output folder where the Excel file will be saved. If not provided, the file will be saved in the program's directory.

## Usage:

1- Enter the desired article title or keyword in the "Article Title or Keyword" field.

2- Specify the number of pages to scrape in the "Number of Pages" field.

3- (Optional) Provide the output folder where the Excel file will be saved.

4- Click the "Browse" button to select the output folder.

5- Click the "Extract Data" button to initiate the scraping process.

6- Wait for the non-blocking search to complete while progress is shown.

7- Review the results table, then click "Export Excel" or "Export CSV" to save the data.

## Dependencies:

Python 3.x

Requests library

BeautifulSoup library

OpenPyXL library for Excel writing

Tkinter library (standard with Python)

## Installation:

Clone the repository from GitHub.

Install the required dependencies using pip: pip install requests beautifulsoup4 openpyxl.

Install the project in editable mode: pip install -e .

Run the program using Python: python -m google_scholar_scraper.

The legacy launcher is also available: python prog.py.

Note: Google Scholar may rate-limit or block automated requests. The application reports these states instead of treating them as a successful empty extraction.

V2 includes local lexical relevance ranking. It does not use LLMs, model downloads, or external AI APIs.

The desktop UI supports Smart Relevance Ranking, cooperative cancellation, result review, and explicit Excel/CSV export.

