import json
from collections import Counter

with open('input/initial_state.json', 'r', encoding='utf-8') as f:
    initial_state = json.load(f)

adm_state_dict = []
adm_state_dict = {"POLAND": [], "ABROAD": []}
dist_state_list = []
region_state_list = []

all_names_list = [] # List with all names to check if some names repeat
all_d_r_list = [] # List with all names of districts in regions to verify that they are not double

for region_name, dist_list in initial_state.items():
    if region_name in ["ZIEMIA WILEŃSKA", "ŚLĄSK NIEMIECKI", "ZAOLZIE"]:
        country_name = "ABROAD"
    else:
        country_name = "POLAND"
    adm_state_dict[country_name].append({region_name: [district['district_name'] for district in dist_list]}) # Administrative state
    all_d_r_list += [district['district_name'] for district in dist_list] # For check that the names don't double
    region_dist_list = []
    for dist in dist_list:
        dist_dict = {"name_id": dist["district_name"]}
        dist_name_variants = [dist["district_name"]] + dist.get("alternative_names", [])
        dist_dict["name_variants"] = dist_name_variants
        all_names_list += dist_name_variants
        dist_seat_name_variants = [dist["seat"]] + dist.get("alternative_seat_names", [])
        dist_dict["seat_name_variants"] = dist_seat_name_variants
        dist_state_dict = {"current_name": dist["district_name"], "current_seat_name": dist["seat"], "current_dist_type": dist["district_type"], "timespan": None}
        dist_dict["states"] = [dist_state_dict]
        region_dist_list.append(dist_dict)
    dist_state_list += region_dist_list
    region_state_list.append({"name_id": region_name, "name_variants": [region_name], "is_poland": True, "states": [{"current_name": region_name, "timespan": None}]})

# Verify that there are no double district names
counts = Counter(all_names_list)

for item, count in counts.items():
    if count >= 2:
        print(f"The name {item} appears {count} times in the initial state!")

# Verify that there are no double districts in regions

counts = Counter(all_d_r_list)

for item, count in counts.items():
    if count >= 2:
        print(f"The district {item} is connected with a region {count} times in the initial administrative state!")



# Dump to JSON
with open("input/initial_adm_state.json", "w", encoding="utf-8") as f:
    json.dump({"unit_hierarchy": adm_state_dict}, f, ensure_ascii=False, indent=2)

# Dump to JSON
with open("input/initial_dist_state_list.json", "w", encoding="utf-8") as f:
    json.dump(dist_state_list, f, ensure_ascii=False, indent=2)

# Dump to JSON
with open("input/initial_region_state_list.json", "w", encoding="utf-8") as f:
    json.dump(region_state_list, f, ensure_ascii=False, indent=2)
    #After creation, "Warszawa", "Pomorze", "Śląskie", "POLESIE", and "Wołyń" should be added as name variants.