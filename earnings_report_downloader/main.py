import os
import datetime
import requests
from sec_edgar_downloader import Downloader
from bs4 import BeautifulSoup

def download_latest_earnings_html(ticker: str, download_dir: str = "sec_filings") -> tuple[str, str] | None:
    """
    Downloads the latest 10-K or 10-Q (earnings reports) HTML filing for a given ticker.

    Args:
        ticker (str): The stock ticker symbol (e.g., "AAPL").
        download_dir (str): The directory to save the downloaded filings.

    Returns:
        tuple[str, str] | None: A tuple containing (filing_type, file_path) if successful,
                                 otherwise None.
    """
    # Important: Provide a valid User-Agent as required by the SEC.
    # Replace "Your Company Name" and "your.email@example.com" with your actual details.
    dl = Downloader("MyCompanyName", "my.email@domain.com", download_dir)

    print(f"Searching for the latest 10-Q for {ticker}...")
    try:
        # Get the latest 10-Q (quarterly report)
        dl.get("10-Q", ticker, limit=1)
        filing_type = "10-Q"
    except Exception as e:
        print(f"No 10-Q found for {ticker} or an error occurred: {e}")
        print(f"Searching for the latest 10-K for {ticker} instead...")
        try:
            # If no 10-Q, try 10-K (annual report)
            dl.get("10-K", ticker, limit=1)
            filing_type = "10-K"
        except Exception as e_k:
            print(f"No 10-K found for {ticker} either, or an error occurred: {e_k}")
            return None

    # Determine the path to the downloaded HTML file
    ticker_dir = os.path.join(download_dir, ticker, filing_type)
    sub_directories = [d for d in os.listdir(ticker_dir) if os.path.isdir(os.path.join(ticker_dir, d))]

    if sub_directories:
        # The latest filing will be in the most recently created directory
        latest_sub_dir = max(sub_directories, key=lambda d: os.path.getmtime(os.path.join(ticker_dir, d)))
        
        # Look for the primary HTML document
        filing_path = None
        for root, _, files in os.walk(os.path.join(ticker_dir, latest_sub_dir)):
            for file in files:
                if file.endswith(".htm") or file.endswith(".html"):
                    filing_path = os.path.join(root, file)
                    break
            if filing_path:
                break
        
        if filing_path:
            print(f"Downloaded latest {filing_type} for {ticker} to: {filing_path}")
            return filing_type, filing_path
        else:
            print(f"No HTML file found in the latest {filing_type} directory for {ticker}.")
            return None
    
    print(f"No filings found for {ticker} in {filing_type} type.")
    return None

def convert_html_to_pdf(html_file_path: str, output_pdf_path: str) -> None:
    """
    Converts an HTML file to a PDF file using WeasyPrint.

    Args:
        html_file_path (str): Path to the input HTML file.
        output_pdf_path (str): Path to save the output PDF file.
    """
    try:
        from weasyprint import HTML, CSS
        print(f"Converting {html_file_path} to PDF...")
        HTML(filename=html_file_path).write_pdf(output_pdf_path)
        print(f"Successfully converted to PDF: {output_pdf_path}")
    except ImportError:
        print("WeasyPrint is not installed. Please install it using 'pip install weasyprint'.")
        print("Note: WeasyPrint requires additional system dependencies (e.g., cairo, pango, gdk-pixbuf).")
        print("Refer to https://weasyprint.org/docs/install/ for installation instructions.")
    except Exception as e:
        print(f"Error converting HTML to PDF: {e}")

def main():
    ticker = input("Enter the stock ticker (e.g., AAPL): ").upper()
    download_directory = "sec_earnings_reports"
    os.makedirs(download_directory, exist_ok=True)

    filing_info = download_latest_earnings_html(ticker, download_directory)

    if filing_info:
        filing_type, html_file_path = filing_info
        output_pdf_name = f"{ticker}_latest_earnings_{filing_type}.pdf"
        output_pdf_path = os.path.join(download_directory, output_pdf_name)
        convert_html_to_pdf(html_file_path, output_pdf_path)
    else:
        print(f"Could not find or download the latest earnings report for {ticker}.")

if __name__ == "__main__":
    main()