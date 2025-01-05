import json


def filter_novels(
    data, title_keywords, tags_categories_keywords, tags_categories_logic, keyword
):
    printed_urls = set()  # To avoid duplicate prints

    # Parse keywords
    title_keywords = set(title_keywords)
    tags_categories_keywords = set(tags_categories_keywords)

    for dictionary in data:
        # Check title keywords
        title_match = any(
            keyword.lower() in dictionary["title"].lower() for keyword in title_keywords
        )

        # Check tags and categories based on AND/OR logic
        tags_categories = dictionary["tags"].split(", ") + dictionary[
            "categories"
        ].split(", ")
        if tags_categories_logic == "AND":
            tags_categories_match = all(
                keyword.lower() in map(str.lower, tags_categories)
                for keyword in tags_categories_keywords
            )
        else:  # "OR"
            tags_categories_match = any(
                keyword.lower() in map(str.lower, tags_categories)
                for keyword in tags_categories_keywords
            )

        # Filter chapters by keyword
        for chapter in dictionary["results"]:
            values_key = chapter["found_terms"].values()
            terms_match = (
                (keyword is None or keyword in values_key) if values_key else False
            )
            if title_match and tags_categories_match and terms_match:
                if chapter["chapter_url"] not in printed_urls:
                    print(chapter["chapter_url"])
                    printed_urls.add(chapter["chapter_url"])


def main():
    # Load data from JSON
    with open("results.json", "r") as f:
        data = json.load(f)

    # Get user input
    title_keywords = (
        input("Enter title keywords (comma or space-separated): ")
        .replace(",", " ")
        .split()
    )
    tags_categories_keywords = (
        input("Enter tags/categories keywords (comma or space-separated): ")
        .replace(",", " ")
        .split()
    )
    tags_categories_logic = (
        input("Enter logic for tags/categories (AND/OR): ").strip().upper()
    )
    keyword = input("Search for keyword (true/false/leave blank): ").strip().lower()

    # Convert keyword input to boolean or None
    keyword = None if not keyword else keyword == "true"

    # Filter novels and print results
    filter_novels(
        data, title_keywords, tags_categories_keywords, tags_categories_logic, keyword
    )


if __name__ == "__main__":
    main()