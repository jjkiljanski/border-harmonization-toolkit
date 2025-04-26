from copy import deepcopy
import os
import csv

class AdministrativeState:
    """
    Represents the administrative structure for a given point in time.
    Each region contains a list of districts, each with a name, type, and seat.
    """

    def __init__(self, state_dict, timespan):
        """
        Args:
            region_to_districts (dict): A mapping from region name to a list of district dicts.
            date (str, optional): Date this state is valid for.
        """
        self.structure = deepcopy(state_dict)  # deep copy to prevent mutation
        self.valid_from, self.valid_to = timespan

    def find_district(self, searched_name):
        """
        Find and return the region and district dict by district name or district alternative name.
        
        Returns:
            (region_name, district_dict) or (None, None) if not found
        """
        for region, districts in self.structure.items():
            for district in districts:
                if district["district_name"] == searched_name or searched_name in district["alternative_names"]:
                    return region, district
        return None, None
    
    def pop_district(self, region_name, district_name):
        """
        Removes and returns the district dict with the given name from the specified region.

        Args:
            region_name (str): The name of the region.
            district_name (str): The name of the district to remove.

        Returns:
            dict: The removed district dictionary.

        Raises:
            ValueError: If the region does not exist or the district is not found in that region.
        """
        if region_name not in self.structure:
            raise ValueError(f"Region '{region_name}' not found in structure.")

        districts = self.structure[region_name]

        for i, district in enumerate(districts):
            if district["district_name"] == district_name:
                return districts.pop(i)

        raise ValueError(f"District '{district_name}' not found in region '{region_name}'.")
    
    def add_district_if_absent(self, region_name, district_dict):
        """
        Adds the given district dict to the specified region. Raises an error if it already exists in the region.

        Args:
            region_name (str): The target region name.
            district_dict (dict): A dict with at least a "district_name" key.

        Raises:
            ValueError: If the district already exists in the region.
        """
        if "district_name" not in district_dict:
            raise ValueError(f"District dictionary must contain a 'district_name' key: {district_dict}")

        if region_name not in self.structure:
            raise ValueError(f"The region {region_name} doesn't exist for the current state.")

        # Check for name collision
        for existing in self.structure[region_name]:
            alt_names = existing.get("alternative_names") or [] # Returns alternative_names list or empty list if existing['alternative_names'] is None
            if existing["district_name"] == district_dict["district_name"] or district_dict["district_name"] in alt_names:
                raise ValueError(f"District '{district_dict['district_name']}' already exists in region '{region_name}'.")

        self.structure[region_name].append(district_dict)
        self.structure[region_name].sort(key=lambda district: district["district_name"])

    def to_dict(self):
        """Returns a dict version of the state (for saving/exporting)."""
        return {
            "valid_from": self.date,
            "valid_to": self.valid_to,
            "regions": deepcopy(self.structure)
        }
    
    def to_r_d_list(self, is_poland = False, with_alt_names = False):
        """
        Returns a list of (region, district) pairs, sorted alphabetically.
        If is_poland is true, the method doesn't return pairs from regions outside Poland.
        If with_alt_names is true, pairs with alternative district names are also added.
        """
        r_d_list = []
        for region, districts in self.structure.items():
            if is_poland:
                if region in ['CZECHOSŁOWACJA', 'NIEMCY', 'LITWA']:
                    continue
            for district in districts:
                r_d_list.append((region, district["district_name"]))
                if with_alt_names:
                    if district.get("alternative_names"):
                        for alt_name in district["alternative_names"]:
                            r_d_list.append((region, alt_name))
        r_d_list.sort()
        return r_d_list
    
    def compare_to_r_d_list(self, r_d_list, verbose = False):
        # Comparison of the dist lists
        r_d_state_list = self.to_r_d_list(is_poland = True, with_alt_names = False)
        d_state_list = [district for region, district in r_d_state_list]
        d_state_set = set(d_state_list)
        d_aim_list = [district for region, district in r_d_list]
        d_aim_set = set(d_aim_list)
        list_difference_1 = list(d_state_set - d_aim_set)
        list_difference_1.sort()
        list_difference_2 = list(d_aim_set - d_state_set)
        list_difference_2.sort()
        list_differences = (list_difference_1, list_difference_2)
        list_proximity = len(list_difference_1) + len(list_difference_2)
        list_comparison = list_proximity, list_differences

        # Comparison of the region-district state
        r_d_state_list = self.to_r_d_list(is_poland = True, with_alt_names = False)
        r_d_state_set = set(r_d_state_list)
        r_d_aim_set = set(r_d_list)
        state_difference_1 = list(r_d_state_set - r_d_aim_set)
        state_difference_1.sort()
        state_difference_2 = list(r_d_aim_set - r_d_state_set)
        state_difference_2.sort()
        state_differences = (state_difference_1, state_difference_2)
        state_proximity = len(state_difference_1) + len(state_difference_2)
        state_comparison = state_proximity, state_differences

        if verbose == True:
            print(f"State {self}:")
            print("District list comparison:")
            print(f"\tDistance from the d_list: {list_proximity}")
            print(f"\tAbsent in d_list to identify: {list_difference_1}.\n Absent in state: {list_difference_2}.")
            print("(Region,district) pairs comparison:")
            print(f"\tDistance from the r_d_list: {state_proximity}")
            print(f"\tAbsent in r_d_list to identify: {state_difference_1}.\n Absent in state: {state_difference_2}.")

        return list_comparison, state_comparison

    def to_csv(self):
        """
        Saves the current state to a CSV file with (region, district) pairs, sorted alphabetically.

        Args:
            folder_path (str): Path to the folder where the file will be saved.
        """
        if not self.valid_from or not self.valid_to:
            raise ValueError("Both 'valid_from' and 'valid_to' must be set to save CSV.")

        filepath = f"output/state_{self.valid_from}-{self.valid_to}.csv"

        rows = self.to_r_d_list

        with open(filepath, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Region", "District"])  # Header
            writer.writerows(rows)

        print(f"Saved state to: {filepath}")


    def copy(self):
        """Returns a deep copy of this state."""
        return deepcopy(self)
    
    def apply_changes(self, changes_list):
        # Creates a copy of itself, applies all changes to the copy and returns it as a new state.
        new_state = self.copy()

        # Take the date of the change and ensure that all changes have the same date.
        change_date = changes_list[0].date
        for change in changes_list:
            if change.date != change_date:
                raise ValueError(f"Changes applied to the state {self} have different dates!")
        
        # Define the end and origin of states
        self.valid_to = change_date
        new_state.valid_from = change_date

        all_d_created = []
        all_d_abolished = []
        all_d_b_changed = []
        all_r_changed = []
            
        for change in changes_list:
            # Apply change and store information on the affected districts
            d_created, d_abolished, d_b_changed, r_changed = change.apply(new_state)
            all_d_created += d_created
            all_d_abolished += d_abolished
            all_d_b_changed += d_b_changed
            all_r_changed += r_changed
        
        d_affected = (
            all_d_created,
            all_d_abolished,
            all_d_b_changed,
            all_r_changed
        )

        return (new_state, d_affected)

    def __repr__(self):
        regions = len(self.structure)
        districts = sum(len(dlist) for dlist in self.structure.values())
        return f"<AdministrativeState timespan=({self.valid_from}, {self.valid_to}), regions={regions}, districts={districts}>"