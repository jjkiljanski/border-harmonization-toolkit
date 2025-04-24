from copy import deepcopy
import os
import csv

class AdministrativeState:
    """
    Represents the administrative structure for a given point in time.
    Each region contains a list of districts, each with a name, type, and seat.
    """

    def __init__(self, state_dict, valid_to=None):
        """
        Args:
            region_to_districts (dict): A mapping from region name to a list of district dicts.
            date (str, optional): Date this state is valid for.
        """
        self.structure = deepcopy(state_dict["regions"])  # deep copy to prevent mutation
        self.valid_from = state_dict["valid_from"]
        self.valid_to = valid_to

    def find_district(self, searched_name):
        """
        Find and return the region and district dict by district name or district seat.
        
        Returns:
            (region_name, district_dict) or (None, None) if not found
        """
        for region, districts in self.structure.items():
            for district in districts:
                if district["name"] == searched_name or district["seat"]==searched_name:
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
            if district["name"] == district_name:
                return districts.pop(i)

        raise ValueError(f"District '{district_name}' not found in region '{region_name}'.")
    
    def add_district_if_absent(self, region_name, district_dict):
        """
        Adds the given district dict to the specified region. Raises an error if it already exists in the region.

        Args:
            region_name (str): The target region name.
            district_dict (dict): A dict with at least a "name" key.

        Raises:
            ValueError: If the district already exists in the region.
        """
        if "name" not in district_dict:
            raise ValueError("District dictionary must contain a 'name' key.")

        if region_name not in self.structure:
            raise ValueError(f"The region {region_name} doesn't exist for the current state.")

        # Check for name collision
        for existing in self.structure[region_name]:
            if existing["name"] == district_dict["name"] or district_dict["name"] in existing.get("alternative_names", []):
                raise ValueError(f"District '{district_dict['name']}' already exists in region '{region_name}'.")

        self.structure[region_name].append(district_dict)
        self.structure[region_name].sort(key=lambda district: district["name"])

    def to_dict(self):
        """Returns a dict version of the state (for saving/exporting)."""
        return {
            "valid_from": self.date,
            "valid_to": self.valid_to,
            "regions": deepcopy(self.structure)
        }

    def to_csv(self):
        """
        Saves the current state to a CSV file with (region, district) pairs, sorted alphabetically.

        Args:
            folder_path (str): Path to the folder where the file will be saved.
        """
        if not self.valid_from or not self.valid_to:
            raise ValueError("Both 'valid_from' and 'valid_to' must be set to save CSV.")

        filepath = f"output/state_{self.valid_from}-{self.valid_to}.csv"

        rows = []
        for region, districts in self.structure.items():
            for district in districts:
                rows.append((region, district["name"]))

        # Sort by region then district
        rows.sort()

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
            
        for change in changes_list:
            change.apply(new_state)

        return new_state

    def __repr__(self):
        regions = len(self.structure)
        districts = sum(len(dlist) for dlist in self.structure.values())
        return f"<AdministrativeState timespan=({self.valid_from}, {self.valid_to}), regions={regions}, districts={districts}>"