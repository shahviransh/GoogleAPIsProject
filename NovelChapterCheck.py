import requests
from bs4 import BeautifulSoup
import time
from dotenv import load_dotenv
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import vertexai
from vertexai.generative_models import GenerativeModel
import sys
import threading

# Load environment variables from a .env file
load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
BASE_URL = os.getenv("CRAWL_URL")
promptQuestion = os.getenv("PROMPT_QUESTION")
NOVEL_LINKS_FILE = "novel_links.txt"
OUTPUT_FILE = "final.json"
PROGRESS_FILE = "results.json"
CHAPTER_LIMIT = 5
SEARCH_TERMS = os.getenv("KEYWORDS").split(",")

lock = threading.Lock()
vertexai.init(project=PROJECT_ID, location="us-central1")


def get_soup(url):
    """Fetch the content of a URL and return a BeautifulSoup object."""
    with lock:
        try:
            time.sleep(0.5)  # Add a delay to avoid overloading the server
            response = requests.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            os._exit(1)  # Exit immediately on any network error


def gemini_response(text):
    """Formats translated text using the Gemini API."""
    with lock:
        try:
            time.sleep(0.5)
            model = GenerativeModel("gemini-1.5-pro-002")
            response = model.generate_content(
                [
                    f"""
                    {promptQuestion}

                    {text}
                    """
                ]
            )
            return response.text
        except Exception as e:
            print(f"Error in Gemini API response: {e}")
            os._exit(1)  # Exit immediately on any API error


def extract_chapter_links(novel_url):
    """Extract the links to the first CHAPTER_LIMIT chapters from the novel's page."""
    chapter_links = []
    soup = get_soup(novel_url)
    if soup is None:
        return chapter_links

    # Extract chapter links from the unordered list in the '#chpagedlist' section
    ul_tag = soup.select_one("#chpagedlist ul.chapter-list")
    if not ul_tag:
        print(f"Chapter list not found for {novel_url}")
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
        os._exit(1)
    text_content = soup.find("div", class_="chapter-content")
    text_content = (
        text_content.get_text(separator=" ", strip=True) if text_content else ""
    )

    if text_content != "" and any(term in text_content for term in SEARCH_TERMS):
        response = gemini_response(text_content)
        if response and "yes" in response:
            return {term: True for term in SEARCH_TERMS}

    return {term: False for term in SEARCH_TERMS}


def process_novel(novel_url):
    """Process each novel by visiting its chapters and searching for terms."""
    chapter_links = extract_chapter_links(novel_url)
    novel_results = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_chapter = {
            executor.submit(search_terms_in_chapter, chapter_url): chapter_url
            for chapter_url in chapter_links
        }

        for future in as_completed(future_to_chapter):
            if future.exception() is not None:
                print(f"Error processing chapter: {future.exception()}")
                os._exit(1)  # Stop everything on any error
            try:
                chapter_url = future_to_chapter[future]
                found_terms = future.result()
                novel_results.append(
                    {"chapter_url": chapter_url, "found_terms": found_terms}
                )
            except Exception as exc:
                print(f"Error processing chapter {chapter_url}: {exc}")
                os._exit(1)  # Stop everything on any error

    return novel_results


def save_progress(results):
    """Save progress to a JSON file."""
    try:
        temp_file = f"{PROGRESS_FILE}.tmp"
        with open(temp_file, "w") as f:
            json.dump(results, f, indent=4)
        os.replace(temp_file, PROGRESS_FILE)  # Atomic write
    except Exception as e:
        print(f"Error saving progress: {e}")
        os._exit(1)  # Exit if progress cannot be saved


def load_progress():
    """Load progress from a JSON file."""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading progress: {e}")
            os._exit(1)  # Exit if progress cannot be loaded
    return []


def main():
    """Main function to process all novel links and search for terms in their chapters."""
    try:
        with open(NOVEL_LINKS_FILE, "r") as file:
            novel_links = [line.strip() for line in file.readlines()]
    except Exception as e:
        print(f"Error reading novel links file: {e}")
        os._exit(1)  # Exit if the novel links file can't be read

    all_results = load_progress()
    completed_novels = {result["novel_url"] for result in all_results}
    total_novels = len(
        [novel_url for novel_url in novel_links if novel_url not in completed_novels]
    )
    print(f"\nProcessing {total_novels} novels...")

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_novel = {
            executor.submit(process_novel, novel_url): novel_url
            for novel_url in novel_links
            if novel_url not in completed_novels
        }

        for future in as_completed(future_to_novel):
            if future.exception() is not None:
                print(f"Error processing novel: {future.exception()}")
                os._exit(1)  # Stop everything on any error
            try:
                novel_url = future_to_novel[future]
                novel_results = future.result()
                if novel_results:
                    all_results.append(
                        {"novel_url": novel_url, "results": novel_results}
                    )
                    save_progress(all_results)
            except Exception as exc:
                print(f"Error processing novel {novel_url}: {exc}")
                os._exit(1)  # Stop everything on any error

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
                            "found_terms": {
                                term: found
                                for term, found in chapter["found_terms"].items()
                                if found
                            },
                        }
                        filtered_results.append(chapter_data)
            # Dump the list of filtered results to a JSON file
            json.dump(filtered_results, f, indent=4)
    print(f"\nSearch complete. Results saved in {OUTPUT_FILE}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nManual interruption. Exiting...")
        os._exit(1)
    except Exception as exc:
        print(f"An unexpected error occurred: {exc}")
        os._exit(1)
