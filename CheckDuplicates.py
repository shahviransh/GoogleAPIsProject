import json
import sys

def check_duplicates(json_file_path):
    """
    Check for duplicates in a JSON file based on the `chapter_url` field.
    """
    try:
        # Load the JSON data
        with open(json_file_path, 'r') as f:
            data = json.load(f)

        # Check for duplicates based on 'chapter_url'
        novel_urls = set()
        duplicates = []

        for entry in data:
            chapter_url = entry.get('novel_url')
            if chapter_url in novel_urls:
                duplicates.append(entry)
            else:
                novel_urls.add(chapter_url)
        print(novel_urls)
        return duplicates

    except Exception as e:
        print(f"Error: {e}")
        return []

if __name__ == "__main__":
    # Get the JSON file path from command-line arguments
    json_file_path = "results.json"

    # Check for duplicates
    duplicates = check_duplicates(json_file_path)

    # Display results
    if duplicates:
        print("Found duplicates:")
        for dup in duplicates:
            print(json.dumps(dup, indent=4))
    else:
        print("No duplicates found.")