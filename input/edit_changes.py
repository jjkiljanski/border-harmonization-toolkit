import json

# Input and output file paths
input_file = 'old_district_changes.json'
output_file = 'changes_list.json'

def process_district_changes():
    # Read the JSON data from the input file
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Process each dictionary in the list
    for entry in data:
        entry["matter"]["change_type"] = entry["change_type"]
        entry.pop("change_type")
    
    for entry in data:
        matter = entry["matter"]
        if matter.get('change_type') == 'UnitReform':
            matter["unit_type"] = "Region"
            matter["current_name"] = entry["current_name"]
            entry.pop("current_name")
        if matter.get('change_type') == 'RChange':
            country = ""
            if matter["take_from"]["region"] in ['CZECHOSŁOWACJA', 'LITWA', 'NIEMCY']:
                country = "ABROAD"
            else:
                country = "HOMELAND"
            matter["take_to"] = ("HOMELAND", matter["take_to"], matter["take_from"]["district_name"])
            matter["take_from"] = (country, matter["take_from"]["region"], matter["take_from"]["district_name"])
            matter["change_type"] = "ChangeAdmState"
        if matter.get('change_type') == 'OneToMany':
            matter["unit_attribute"] = 'territory'
            matter["unit_type"] = 'District'
            new_take_from_dict = {}
            new_take_from_dict["delete_unit"] = matter["take_from"]["delete_district"]
            new_take_from_dict["current_name"] = matter["take_from"]["district_name"]
            matter["take_from"] = new_take_from_dict

            new_take_to = []
            for old_take_to_dict in matter["take_to"]:
                new_take_to_dict = {}
                new_take_to_dict["create"] = old_take_to_dict["create"]
                if not new_take_to_dict["create"]:
                    new_take_to_dict["current_name"] = old_take_to_dict["district_name"]
                else:
                    new_take_to_dict["weight_from"] = old_take_to_dict["weight_from"]
                    new_take_to_dict["weight_to"] = old_take_to_dict["weight_to"]
                    new_take_to_dict["district"] = {
                        "name_id": old_take_to_dict["district_name"],
                        "name_variants": [old_take_to_dict["district_name"]] + old_take_to_dict.get("alternative_names", []),
                        "seat_name_variants": [old_take_to_dict["seat"]] + old_take_to_dict.get("alternative_seat_names", []),
                        "states": [{
                            "current_name": old_take_to_dict["district_name"],
                            "current_seat_name": old_take_to_dict["seat"],
                            "current_dist_type": old_take_to_dict["district_type"]
                            }]
                        }
                    new_take_to_dict["new_district_address"] = ('HOMELAND', old_take_to_dict["region"], old_take_to_dict["district_name"])
                new_take_to.append(new_take_to_dict)
            matter["take_to"] = new_take_to
        if matter.get('change_type') == 'ManyToOne':
            new_take_from = []
            for old_take_from_dict in matter["take_from"]:
                new_take_from_dict = {}
                new_take_from_dict["current_name"] = old_take_from_dict["district_name"]
                new_take_from_dict["weight_from"] = old_take_from_dict["weight_from"]
                new_take_from_dict["weight_to"] = old_take_from_dict["weight_to"]
                new_take_from_dict["delete_unit"] = old_take_from_dict["delete_district"]
                new_take_from.append(new_take_from_dict)
            matter["take_from"] = new_take_from
            new_take_to = {
                "create": matter["take_to"]["create"]
            }
            if not matter["take_to"]["create"]:
                new_take_to["current_name"] = matter["take_to"]["current_name"]
            else:
                new_take_to["district"] = {
                    "name_id": matter["take_to"]["district_name"],
                    "name_variants": [matter["take_to"]["district_name"]] + matter["take_to"].get("alternative_names", []),
                    "seat_name_variants": [matter["take_to"]["seat"]] + matter["take_to"].get("alternative_seat_names", []),
                    "states": [{
                        "current_name": matter["take_to"]["district_name"],
                        "current_seat_name": matter["take_to"]["seat"],
                        "current_dist_type": matter["take_to"]["district_type"]
                    }]
                }
                new_take_to["new_district_address"] = ('HOMELAND', matter['take_to']['region'], matter['take_to']['district_name'])
            matter["take_to"] = new_take_to
            
        if entry["matter"].get('change_type') == 'ManyToOne':
            matter["unit_attribute"] = 'territory'
            matter["unit_type"] = 'District'
            

    from collections import OrderedDict

    ordered_keys = ['date', 'source', 'description', 'order', 'matter']
    ordered_data = []

    for entry in data:
        ordered_entry = OrderedDict()
        
        for key in ordered_keys:
            if key == 'matter' and 'matter' in entry and isinstance(entry['matter'], dict):
                # Reorder 'matter': 'change_type' first, rest follow
                matter = entry['matter']
                ordered_matter = OrderedDict()
                if 'change_type' in matter:
                    ordered_matter['change_type'] = matter['change_type']
                for mk, mv in matter.items():
                    if mk != 'change_type':
                        ordered_matter[mk] = mv
                ordered_entry['matter'] = ordered_matter
            elif key in entry:
                ordered_entry[key] = entry[key]

        # Add any top-level keys not specified
        for key in entry:
            if key not in ordered_keys:
                ordered_entry[key] = entry[key]

        ordered_data.append(ordered_entry)


    # Write the modified data to the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(ordered_data, f, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    process_district_changes()
 
