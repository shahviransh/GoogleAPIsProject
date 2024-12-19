# Enumerate a json file containing a list of dictionaries and print all true values

import json

def main():
    with open('data.json', 'r') as f:
        data = json.load(f)
    
    for dictionary in data:
        for chapter in dictionary["results"]:
            for key, value in chapter["found_terms"].items():
                if value == True:
                    print(dictionary["novel_url"])

if __name__ == "__main__":
    main()