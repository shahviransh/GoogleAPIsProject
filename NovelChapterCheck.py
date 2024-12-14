import requests
from bs4 import BeautifulSoup
import time
from dotenv import load_dotenv
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from alive_progress import alive_bar
import sys

# Load environment variables from a .env file
load_dotenv()

BASE_URL = os.getenv("CRAWL_URL")
NOVEL_LINKS_FILE = "novel_links.txt"
OUTPUT_FILE = "final.json"
PROGRESS_FILE = "results.json"
CHAPTER_LIMIT = 5
SEARCH_TERMS = os.getenv("KEYWORDS").split(",")

# Create a lock for get_soup
soup_lock = Lock()

class FetchError(Exception):
    """Exception raised when fetching data fails."""
    pass


def get_soup(url):
    """Fetch the content of a URL and return a BeautifulSoup object."""
    with soup_lock:  # Ensure only one thread can execute this block at a time
        try:
            time.sleep(1)  # Add a delay to avoid hitting the server too frequently
            response = requests.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except requests.exceptions.RequestException as e:
            raise FetchError(f"Error fetching {url}: {e}")


def extract_chapter_links(novel_url):
    """Extract the links to the first CHAPTER_LIMIT chapters from the novel's page."""
    chapter_links = []
    soup = get_soup(novel_url)
    if soup is None:
        return chapter_links

    # Extract chapter links from the unordered list in the '#chpagedlist' section
    ul_tag = soup.select_one("#chpagedlist ul.chapter-list")
    if not ul_tag:
        return chapter_links

    for li_tag in ul_tag.find_all("li")[:CHAPTER_LIMIT]:
        a_tag = li_tag.find("a")
        if a_tag:
            href = a_tag.get("href")
            if href:
                chapter_links.append(BASE_URL + href)

    return chapter_links


def search_terms_in_chapter(chapter_url):
    """Search for specific terms in a chapter's content."""
    soup = get_soup(chapter_url)
    if soup is None:
        return {term: False for term in SEARCH_TERMS}

    text_content = soup.find('div', class_='chapter-content')
    text_content = text_content.get_text(separator=' ', strip=True) if text_content else ""
    found_terms = {term: term in text_content for term in SEARCH_TERMS}
    return found_terms


def process_novel(novel_url):
    """Process each novel by visiting its chapters and searching for terms."""
    chapter_links = extract_chapter_links(novel_url)
    novel_results = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_chapter = {
            executor.submit(search_terms_in_chapter, chapter_url): chapter_url
            for chapter_url in chapter_links
        }

        for future in as_completed(future_to_chapter):
            chapter_url = future_to_chapter[future]
            try:
                found_terms = future.result()
                novel_results.append(
                    {"chapter_url": chapter_url, "found_terms": found_terms}
                )
                if any(found_terms.values()):
                    print(f"  Found terms in chapter: {chapter_url}")
                    break
            except Exception as exc:
                raise FetchError(f"Error processing chapter {chapter_url}: {exc}")

    return novel_results


def save_progress(results):
    """Save progress to a JSON file."""
    try:
        with open(PROGRESS_FILE, "w") as f:
            json.dump(results, f, indent=4)
    except Exception as e:
        raise FetchError(f"Error saving progress: {e}")


def load_progress():
    """Load progress from a JSON file."""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            raise FetchError(f"Error loading progress: {e}")
    return []


def main():
    """Main function to process all novel links and search for terms in their chapters."""
    with open(NOVEL_LINKS_FILE, "r") as file:
        novel_links = [line.strip() for line in file.readlines()]

    all_results = load_progress()
    completed_novels = {result["novel_url"] for result in all_results}
    total_novels = len([novel_url for novel_url in novel_links if novel_url not in completed_novels])
    print(f"\nProcessing {total_novels} novels...")

    with ThreadPoolExecutor(max_workers=10) as executor, alive_bar(total_novels) as bar:
        future_to_novel = {
            executor.submit(process_novel, novel_url): novel_url
            for novel_url in novel_links
            if novel_url not in completed_novels
        }

        for future in as_completed(future_to_novel):
            novel_url = future_to_novel[future]
            try:
                novel_results = future.result()
                if novel_results:
                    all_results.append(
                        {"novel_url": novel_url, "results": novel_results}
                    )
                    save_progress(all_results)  # Save after each novel
                bar()
            except Exception as exc:
                raise FetchError(f"Error processing novel {novel_url}: {exc}")

        filtered_results = []
        # Save to text file all results that are True
        with open(OUTPUT_FILE, "w") as f:
            for result in all_results:
                for chapter in result["results"]:
                    if any(chapter["found_terms"].values()):
                        # Prepare a dictionary for each chapter where terms are found
                        chapter_data = {
                            "novel_url": result["novel_url"],
                            "chapter_url": chapter["chapter_url"],
                            "found_terms": {term: found for term, found in chapter["found_terms"].items() if found}
                        }
                        filtered_results.append(chapter_data)
            # Dump the list of filtered results to a JSON file
            json.dump(filtered_results, f, indent=4)
    print(f"\nSearch complete. Results saved in {OUTPUT_FILE}")


if __name__ == "__main__":
    try:
        main()
    except FetchError as fe:
        print(f"An error occurred: {fe}")
        sys.exit(1)
