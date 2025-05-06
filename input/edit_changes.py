import json

# Input and output file paths
input_file = 'district_changes.json'
output_file = 'new_district_changes.json'

def process_district_changes():
    # Read the JSON data from the input file
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Process each dictionary in the list
    for entry in data:
        if entry.get('change_type') == 'RChange':
            matter = entry["matter"]
            country = ""
            if matter["take_from"]["region"] in ['CZECHOSŁOWACJA', 'LITWA', 'NIEMCY']:
                country = "ABROAD"
            else:
                country = "HOMELAND"
            matter["take_to"] = ("HOMELAND", matter["take_to"], matter["take_from"]["district_name"])
            matter["take_from"] = (country, matter["take_from"]["region"], matter["take_from"]["district_name"])

    # Write the modified data to the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    process_district_changes()
 
