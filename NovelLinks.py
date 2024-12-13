import requests
from bs4 import BeautifulSoup
import time
from dotenv import load_dotenv
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load environment variables from a .env file
load_dotenv()

BASE_URL = os.getenv("CRAWL_URL")
START_URL = f'{BASE_URL}{os.getenv("START_PAGE")}'
OUTPUT_FILE = "novel_links.txt"
PROGRESS_FILE = "progress.json"
NUM_WORKERS = 5

def get_soup(url):
    """Fetches and parses the URL content using BeautifulSoup."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None


def extract_novel_links(soup):
    """Extracts and returns a list of novel links from the parsed page."""
    links = []
    if soup is None:
        return links
    for a_tag in soup.select('a[href^="/novel/"]'):
        href = a_tag.get("href")
        if href not in links:
            links.append(href)
    return links


def get_next_page(soup):
    """Finds and returns the URL for the next page, or None if there is no next page."""
    if soup is None:
        return None
    next_page = soup.find("a", string=">")
    if next_page:
        return BASE_URL + next_page.get("href")
    return None


def load_progress():
    """Loads the last saved progress from the progress file."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {"processed_urls": [], "novel_links": []}


def save_progress(processed_urls, novel_links):
    """Saves the current progress to a file."""
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump({"processed_urls": list(processed_urls), "novel_links": list(novel_links)}, f)


def process_url(current_url, processed_urls, novel_links):
    """Processes a single URL and updates the progress and links."""
    if current_url in processed_urls:  # Skip if this URL is already processed
        return None

    print(f"Processing: {current_url}")
    soup = get_soup(current_url)
    if not soup:
        return None

    page_links = extract_novel_links(soup)
    novel_links.update(page_links)
    next_page = get_next_page(soup)
    processed_urls.add(current_url)
    return next_page


def main():
    progress = load_progress()
    processed_urls = set(progress.get("processed_urls", []))
    novel_links = set(progress.get("novel_links", []))

    if processed_urls:
        max_url = max(processed_urls, key=lambda url: int(url.split("-")[-1].replace(".html", "")) if "-" in url and url.endswith(".html") else 0)
        next_url_num = int(max_url.split("-")[-1].replace(".html", "")) + 1
        task_urls = [max_url.rsplit("-", 1)[0] + f"-{next_url_num}.html"]
    else:
        task_urls = [START_URL]
    
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        while task_urls:
            future_to_url = {executor.submit(process_url, url, processed_urls, novel_links): url for url in task_urls}
            task_urls = []  # Reset task URLs

            for future in as_completed(future_to_url):
                next_page = future.result()
                if next_page and next_page not in processed_urls:
                    task_urls.append(next_page)
            
            save_progress(processed_urls, novel_links)

    # Save final results
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for link in sorted(novel_links):
            f.write(f"{BASE_URL}{link}\n")

    print(f"Saved {len(novel_links)} novel links to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()