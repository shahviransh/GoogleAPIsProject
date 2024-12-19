import json

def main():
    # Read the input file
    with open('results.json', 'r') as f:
        data = json.load(f)
    
    # Filter out chapters where any found_terms value is True
    for dictionary in data:
        dictionary["results"] = [
            chapter for chapter in dictionary["results"] 
            if not any(value is True for value in chapter["found_terms"].values())
        ]
    
    # Write the cleaned data back to the file
    with open('results.json', 'w') as f:
        json.dump(data, f, indent=4)

if __name__ == "__main__":
    main()