import json

def main():
    with open('results.json', 'r') as f:
        data = json.load(f)
    
    printed_urls = set()  # To avoid duplicate prints
    for dictionary in data:
        for chapter in dictionary["results"]:
            if any(value is True for value in chapter["found_terms"].values()):
                if dictionary["novel_url"] not in printed_urls:
                    print(dictionary["novel_url"])
                    printed_urls.add(dictionary["novel_url"])
                break  # Exit the loop early as we found a true value for this novel

if __name__ == "__main__":
    main()