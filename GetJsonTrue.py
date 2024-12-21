import json

def main():
    with open("results.json", "r") as f:
        data = json.load(f)

    printed_urls = set()  # To avoid duplicate prints
    for dictionary in data:
        for chapter in dictionary["results"]:
            if all(
                value
                for term, value in chapter["found_terms"].items()
                if term.startswith("f")
            ):
                if chapter["chapter_url"] not in printed_urls:
                    print(chapter["chapter_url"])
                    printed_urls.add(chapter["chapter_url"])
                break  # Exit the loop early as we found a true value for this novel


if __name__ == "__main__":
    main()
