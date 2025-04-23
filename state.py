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
        return AdministrativeState(self.structure, date=self.date)

    def __repr__(self):
        regions = len(self.structure)
        districts = sum(len(dlist) for dlist in self.structure.values())
        return f"<AdministrativeState timespan=({self.valid_from}, {self.valid_to}), regions={regions}, districts={districts}>"