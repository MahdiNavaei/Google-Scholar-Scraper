# Google-Scholar-Scraper
The Google Scholar Scraper is a Python program that allows users to extract articles from Google Scholar based on the provided title or keyword. It retrieves the article's title, authors, and link, and saves the extracted data into an Excel file. The program utilizes web scraping techniques to navigate through multiple pages of search results, providing a comprehensive extraction process.


## Features:

1-  User-friendly interface: The program offers a simple and intuitive graphical user interface (GUI) built using the Tkinter library.

2- Customizable search: Users can enter their desired article title or keyword to retrieve relevant scholarly articles.

3- Multiple page scraping: Users can specify the number of pages they want to scrape, allowing them to extract data from a larger pool of search results.

4- Data extraction: The program extracts the article's title, authors, and link for each entry, ensuring comprehensive data retrieval.

5- Excel output: The extracted data is saved into an Excel file, making it easily accessible and compatible with other applications.

6- Optional output folder: Users can specify the output folder where the Excel file will be saved. If not provided, the file will be saved in the program's directory.

## Usage:

1- Enter the desired article title or keyword in the "Article Title or Keyword" field.

2- Specify the number of pages to scrape in the "Number of Pages" field.

3- (Optional) Provide the output folder where the Excel file will be saved.

4- Click the "Browse" button to select the output folder.

5- Click the "Extract Data" button to initiate the scraping process.

6- Wait for the program to complete the extraction and save the data to an Excel file.

7- The status label will display a message indicating the completion of the extraction process.

## Dependencies:

Python 3.x

Requests library

BeautifulSoup library

Pandas library

Tkinter library (standard with Python)

## Installation:

Clone the repository from GitHub.

Install the required dependencies using pip: pip install requests beautifulsoup4 pandas.

Run the program using Python: python scholar_scraper.py.

