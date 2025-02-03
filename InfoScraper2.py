
import os
import re
import json
import time
import random
import logging
import hashlib
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime
from urllib.robotparser import RobotFileParser
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from langdetect import detect
from PIL import Image
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from textacy import preprocessing

# --------------------------
# Configuration
# --------------------------
CONFIG = {
    "output_dir": "ai_training_data",
    "max_workers": 5,
    "request_timeout": 15,
    "rate_limit_delay": 1,
    "user_agents": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ..."
    ],
    "content_filters": {
        "min_text_length": 500,
        "allowed_languages": ["en"],
        "blocklist_phrases": ["lorem ipsum", "test content"]
    },
    "storage_formats": ["jsonl", "parquet"],
    "max_text_storage": 1000,   # flush after 1000 records
    "retry_attempts": 3,
    "retry_backoff": 2  # seconds
}

# --------------------------
# Logging Setup
# --------------------------
logging.basicConfig(
    filename='scraper.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --------------------------
# Helper Classes
# --------------------------
class StorageManager:
    """
    Manages storage for scraped text and image metadata.
    Flushes text data to disk in multiple formats.
    """
    def __init__(self, output_dir, storage_formats, max_storage):
        self.output_dir = output_dir
        self.storage_formats = storage_formats
        self.max_storage = max_storage
        self.text_storage = []
        self.image_storage = []

        os.makedirs(self.output_dir, exist_ok=True)
        # Create an images subfolder
        os.makedirs(os.path.join(self.output_dir, "images"), exist_ok=True)

    def store_text(self, data):
        self.text_storage.append(data)
        if len(self.text_storage) >= self.max_storage:
            self.flush_text_storage()

    def flush_text_storage(self):
        if not self.text_storage:
            return

        df = pd.DataFrame(self.text_storage)
        timestamp = datetime.now().timestamp()
        if "jsonl" in self.storage_formats:
            jsonl_path = os.path.join(self.output_dir, f"text_{timestamp}.jsonl")
            df.to_json(jsonl_path, orient="records", lines=True)
            logging.info(f"Flushed text data to {jsonl_path}")

        if "parquet" in self.storage_formats:
            parquet_path = os.path.join(self.output_dir, f"text_{timestamp}.parquet")
            df.to_parquet(parquet_path)
            logging.info(f"Flushed text data to {parquet_path}")

        self.text_storage = []

    def store_image(self, data, image_content):
        """
        Saves image metadata and writes image file.
        """
        self.image_storage.append(data)
        image_folder = os.path.join(self.output_dir, "images")
        image_path = os.path.join(image_folder, data["filename"])
        try:
            # Write image content to file
            with open(image_path, 'wb') as f:
                f.write(image_content)
            logging.info(f"Saved image {data['filename']}")
        except Exception as e:
            logging.error(f"Error saving image {data['filename']}: {e}")

class ContentExtractor:
    """
    Extracts and cleans text from a BeautifulSoup-parsed page.
    """
    @staticmethod
    def extract(soup):
        # Try common selectors for main content
        for selector in ['article', 'main', '[role="main"]']:
            element = soup.select_one(selector)
            if element:
                return element.get_text()
        # Fallback: extract all text
        return soup.get_text()

    @staticmethod
    def clean(text):
        cleaner = preprocessing.make_pipeline(
            preprocessing.normalize.whitespace,
            preprocessing.remove.html_tags,
            preprocessing.replace.urls,
            preprocessing.replace.emails,
            preprocessing.replace.phone_numbers,
            preprocessing.normalize.unicode
        )
        cleaned = cleaner(text)
        return re.sub(r'\s+', ' ', cleaned).strip()

class ImageDownloader:
    """
    Downloads and validates images from a given URL.
    """
    def __init__(self, session, storage_manager):
        self.session = session
        self.storage_manager = storage_manager

    def download(self, url, domain):
        try:
            response = self.session.get(url, stream=True, timeout=CONFIG["request_timeout"])
            response.raise_for_status()
            # Validate image content by attempting to open it
            img = Image.open(BytesIO(response.content))
            img.verify()  # Verify that it is, indeed, an image

            # Re-open image (verify() leaves the image in an unusable state)
            img = Image.open(BytesIO(response.content))
            content_hash = hashlib.sha256(response.content).hexdigest()
            filename = f"{domain}_{content_hash}.{img.format.lower()}"

            image_data = {
                "url": url,
                "filename": filename,
                "dimensions": img.size,
                "format": img.format,
                "source_domain": domain,
                "timestamp": datetime.now().isoformat()
            }
            self.storage_manager.store_image(image_data, response.content)
        except Exception as e:
            logging.error(f"Error downloading image {url}: {e}")

class AIDataScraper:
    """
    Main scraper class responsible for orchestrating page fetching,
    content extraction, image downloading, and storage.
    """
    def __init__(self):
        self.storage_manager = StorageManager(
            output_dir=CONFIG["output_dir"],
            storage_formats=CONFIG["storage_formats"],
            max_storage=CONFIG["max_text_storage"]
        )
        self.session = self._init_session()
        self.image_downloader = ImageDownloader(self.session, self.storage_manager)

    def _init_session(self):
        session = requests.Session()
        retries = Retry(
            total=CONFIG["retry_attempts"],
            backoff_factor=CONFIG["retry_backoff"],
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def get_robots_parser(self, domain):
        rp = RobotFileParser()
        rp.set_url(f"{domain}/robots.txt")
        try:
            rp.read()
        except Exception as e:
            logging.warning(f"Could not read robots.txt from {domain}: {e}")
        return rp

    def validate_content(self, text):
        if len(text) < CONFIG["content_filters"]["min_text_length"]:
            return False
        # Check if any blocklist phrases appear
        for phrase in CONFIG["content_filters"]["blocklist_phrases"]:
            if phrase.lower() in text.lower():
                return False
        try:
            lang = detect(text)
            if lang not in CONFIG["content_filters"]["allowed_languages"]:
                return False
        except Exception as e:
            logging.warning(f"Language detection failed: {e}")
            return False
        return True

    def retry_request(self, func, *args, **kwargs):
        """
        Basic retry wrapper with exponential backoff.
        """
        attempts = CONFIG["retry_attempts"]
        backoff = CONFIG["retry_backoff"]
        for attempt in range(1, attempts + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logging.error(f"Attempt {attempt} failed with error: {e}")
                if attempt < attempts:
                    time.sleep(backoff ** attempt)
        raise Exception("Maximum retry attempts reached.")

    def scrape_page(self, url):
        try:
            # Respect robots.txt
            domain = url.split('/')[2]
            rp = self.get_robots_parser(f"https://{domain}")
            if not rp.can_fetch("*", url):
                logging.warning(f"Skipping {url} due to robots.txt restrictions")
                return

            headers = {
                "User-Agent": random.choice(CONFIG["user_agents"]),
                "Accept-Language": "en-US,en;q=0.9"
            }

            # Rate limiting
            time.sleep(CONFIG["rate_limit_delay"])
            response = self.retry_request(
                self.session.get, url, headers=headers, timeout=CONFIG["request_timeout"]
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')
            raw_text = ContentExtractor.extract(soup)
            cleaned_text = ContentExtractor.clean(raw_text)

            if self.validate_content(cleaned_text):
                record = {
                    "url": url,
                    "content": cleaned_text,
                    "timestamp": datetime.now().isoformat(),
                    "source_domain": domain
                }
                self.storage_manager.store_text(record)
                logging.info(f"Scraped and stored text from {url}")
            else:
                logging.info(f"Content at {url} did not pass validation.")

            # Process images on the page
            for img in soup.find_all('img'):
                img_url = img.get('src')
                if img_url and img_url.startswith('http'):
                    self.image_downloader.download(img_url, domain)

        except Exception as e:
            logging.error(f"Error scraping {url}: {e}")

    def run(self, seed_urls):
        with ThreadPoolExecutor(max_workers=CONFIG["max_workers"]) as executor:
            futures = [executor.submit(self.scrape_page, url) for url in seed_urls]
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"Error in thread: {e}")

# --------------------------
# Main Execution
# --------------------------
if __name__ == "__main__":
    scraper = AIDataScraper()
    seed_urls = [
        # Add your target URLs here
        "https://example.com/article1",
        "https://example.com/article2"
    ]
    scraper.run(seed_urls)
    # Ensure that any remaining text data is flushed to storage
    scraper.storage_manager.flush_text_storage()
