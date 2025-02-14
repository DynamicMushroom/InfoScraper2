# InfoScraper2

AI Data Scraper
A modular, extensible web scraper designed to collect text and image data for AI training. This scraper extracts content from web pages, cleans it, downloads images with validation, and stores data in multiple formats—all while respecting robots.txt, applying rate limits, and handling errors gracefully.

Features
Content Extraction & Cleaning:
Uses BeautifulSoup and textacy to extract main content and clean it for use in AI training.

Image Downloading:
Downloads, verifies, and stores image files and their metadata.

Multi-Format Storage:
Saves scraped text data in JSONL and Parquet formats.

Configurable & Modular:
Easily adjust settings (e.g., user agents, rate limiting, content filters) via a centralized configuration.

Concurrency & Robustness:
Implements multithreading, retry logic with exponential backoff, and detailed logging.

Installation
Clone the Repository:

bash
Copy
git clone https://github.com/your-username/ai-data-scraper.git
cd ai-data-scraper
Create a Virtual Environment:

bash
Copy
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
Install Dependencies:

bash
Copy
pip install -r requirements.txt
Usage
Configure Seed URLs:

Open the scraper.py (or main file) and update the seed_urls list with your target URLs:

python
Copy
seed_urls = [
    "https://example.com/article1",
    "https://example.com/article2"
]
Run the Scraper:

bash
Copy
python scraper.py
Output:

Text Data: Saved in the ai_training_data directory in JSONL and Parquet formats.
Images: Downloaded images are stored in the ai_training_data/images folder.
Configuration
The scraper is highly configurable through the CONFIG dictionary. Key options include:

output_dir:
Directory to store scraped data (default: ai_training_data).

max_workers:
Number of threads for concurrent scraping.

request_timeout:
Timeout for HTTP requests.

rate_limit_delay:
Delay (in seconds) between requests to avoid overwhelming servers.

content_filters:

min_text_length: Minimum acceptable text length.
allowed_languages: Languages allowed for the scraped content.
blocklist_phrases: Phrases that, if found in the content, will cause it to be rejected.
storage_formats:
Formats in which to store scraped text data (jsonl, parquet).

retry_attempts & retry_backoff:
Settings for retry logic in case of request failures.

Feel free to adjust these parameters to suit your specific needs.

Modular Architecture
This project is designed for modularity and ease of extension. Future plans include splitting functionality into dedicated modules:

Configuration Module:
Centralizes settings in a single file (config.py).

Storage Module:
Handles text and image storage operations (storage.py).

Scraper Module:
Orchestrates page fetching and processing (scraper.py).

Extractor Module:
Contains content extraction and cleaning logic (extractor.py).

Downloader Module:
Manages image downloading and validation (downloader.py).

Utilities Module:
Provides helper functions (e.g., for retries, rate limiting) (utils.py).

Roadmap
Upcoming features and enhancements:

Async I/O:
Transition to aiohttp/asyncio for improved performance on I/O-bound tasks.

Plugin Architecture:
Support for additional content types and extraction methods via plugins.

CLI Development:
Build a command-line interface for dynamic configuration and running the scraper.

Database Integration:
Add support for SQL/NoSQL databases for scalable storage and querying.

Enhanced Logging & Error Reporting:
Improve logging, including log rotation, alerting, and detailed error reports.

Testing:
Increase test coverage with unit and integration tests.

Contributing
Contributions are welcome! To contribute:

Fork the repository.
Create a new branch:
git checkout -b feature/your-feature-name
Commit your changes:
git commit -am 'Add new feature'
Push to the branch:
git push origin feature/your-feature-name
Open a pull request and explain your changes.
License
This project is licensed under the MIT License.

Contact
For questions, suggestions, or issues, please open an issue in this repository or contact dynamicmushroom@outlook.com.

