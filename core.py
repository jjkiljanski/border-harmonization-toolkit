import json
from pathlib import Path
from pydantic import parse_obj_as, ValidationError
from typing import List

from data_models import *
from border_changes import *
from state import *

class AdministrativeHistory():
    def __init__(self, border_changes_path, initial_state_path, timespan):
        self.border_changes_path = border_changes_path
        self.initial_state_path = initial_state_path

        self.start_date, self.end_date = timespan
        self.start_date = datetime.strptime(self.start_date, "%d.%m.%Y").date()
        self.end_date = datetime.strptime(self.end_date, "%d.%m.%Y").date()

        # Create lists to store Change objects and Administrative State objects
        self.changes_list = []
        self.states_list = []

        # Create empty attribute to store district registry
        self.district_registry = None

        # Create changes list
        self._load_changes_from_json()
        self._create_changes_list()

        # Create AdministrativeState object for the initial state
        self._load_state_from_json()
        self._create_initial_state()

        # Create chronological changes dict {[date]: List[Change]}
        self._create_changes_dates_list()
        self._create_changes_chronology()

        # Create states for the whole timespan
        self._create_history()

    def _load_changes_from_json(self):
        """
        Load a list of changes from a JSON file and validate according to a Pydantic
        data model defined in data_models module.

        Args:
            file_path (str): Path to the JSON file containing the list of changes.
        """
        with open(self.border_changes_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("Expected a list of changes in the JSON file")

        # Use pydantic to parse and validate the list
        try:
            self._pydantic_changes_list = parse_obj_as(List[ChangeEntry], data)
            n_changes = len(self._pydantic_changes_list)
            print(f"✅ Loaded {n_changes} validated changes.")
        except ValidationError as e:
            print(e.json(indent=2))

    def _load_state_from_json(self):
        """
        Load the administrative state from a JSON file and validate according to a Pydantic
        data model defined in data_models module.

        Args:
            file_path (str): Path to the JSON file containing the administrative state.
        """
        # Open the file and load the data
        with open(self.initial_state_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate the data using Pydantic directly
        try:
            self._pydantic_initial_state = AdministrativeStateEntry(regions = data)
            print("✅ Loaded initial state.")
        except ValidationError as e:
            print(e.json(indent=2))
    
    def _create_changes_list(self):
        for change in self._pydantic_changes_list:
            if isinstance(change, RChangeEntry):
                self.changes_list.append(RChange(change))
            if isinstance(change, DOneToManyEntry):
                self.changes_list.append(DOneToManyChange(change))
            if isinstance(change, DManyToOneEntry):
                self.changes_list.append(DManyToOneChange(change))
            if isinstance(change, RReformEntry):
                self.changes_list.append(RReform(change))
            if isinstance(change, RCreateEntry):
                self.changes_list.append(RCreate(change))

        self.changes_list.sort(key=lambda change: change.date)

        del self._pydantic_changes_list
        print("✅ Successfully created the list of Change objects.")

    def _create_initial_state(self):
        # Create a dict out of pydantic model
        self._initial_state_dict = self._pydantic_initial_state.model_dump()
        self._initial_state_dict = self._initial_state_dict["regions"]
        del self._pydantic_initial_state

        # Create an AdministrativeState object for the initial state
        timespan = (self.start_date, self.end_date)
        initial_state = AdministrativeState(self._initial_state_dict, timespan)
        self.states_list.append(initial_state)
        del self._initial_state_dict
        print("✅ Successfully created AdministrativeState object for the initial state.")

        self.district_registry = DistrictRegistry([deepcopy(district) for district_list in initial_state.structure.values() for district in district_list])

    def _create_changes_dates_list(self):
        self.changes_dates = [change.date for change in self.changes_list]
        self.changes_dates = list(set(self.changes_dates))
        self.changes_dates.sort()

    def _create_changes_chronology(self):
        self.changes_chron_dict = {}
        for change in self.changes_list:
            if change.date in self.changes_chron_dict.keys():
                self.changes_chron_dict[change.date].append(change)
            else:
                self.changes_chron_dict[change.date] = [change]

        for date, change_list in self.changes_chron_dict.items():
            # Sort changes for every date according to the order.
            # change.order = None puts the changes at the end of the list.
            change_list.sort(key=lambda change: (change.order is None, change.order))

        # Check if all changes are there
        assert set(self.changes_chron_dict.keys()) == set(self.changes_dates), f"Lists not equal!\nset(self.changes_chron_dict.keys()):\n {set(self.changes_chron_dict.keys())};\nset(self.changes_dates):\n{set(self.changes_dates)}."

        # Uncomment for debugging only
        # for date, change_list in self.changes_chron_dict.items():
        #     for change in change_list:
        #         print(f"{date}: {change.change_type}, order: {change.order}")
        #         change.echo()

    def _create_history(self):
        for date in self.changes_dates:
            changes_list = self.changes_chron_dict[date]
            old_state = self.states_list[-1]
            new_state, d_affected = old_state.apply_changes(changes_list)
            #print(f"{date}: Changes applied, administrative state {new_state} created.")
            self.states_list.append(new_state)

            all_d_created, all_d_abolished, all_d_b_changed, all_r_changed = d_affected
            self.district_registry.districts += all_d_created

    def list_change_dates(self, lang = "pol"):
        # Lists all the dates of border changes.
        if lang == "pol":
            print("Wszystkie daty zmian granic:")
        elif lang == "eng":
            print("All dates of border changes:")
        else:
            raise ValueError("Wrong value for the lang parameter.") 
        for date in self.changes_dates: print(date)

    def summarize_by_date(self, lang = "pol"):
        # Prints all changes ordered by date.
        for change in self.changes_list:
            change.echo(lang)

    def print_all_states(self):
        for state in self.states_list:
            print(state)

    def identify_state(self, r_d_aim_list):
        """
        Takes sorted list of (region, district) pairs and identifies the administrative state that it represents.
        """
        # Check that all district names in r_d_aim_list exist
        #   and change them to basic names if they are alternative district names.

        r_d_aim_new = []
        d_not_in_registry = []
        for region, dist_aim in r_d_aim_list:
            dist_name = self.district_registry.find_district(dist_aim)
            if dist_name is None:
                d_not_in_registry.append(dist_aim)
            elif dist_name != dist_aim:
                print(f"Warning: name {dist_aim} is an alternative district name. Processing further as {dist_name}")
            r_d_aim_new.append((region, dist_name))

        #print(f"List to identify: {r_d_aim_new}")

        if d_not_in_registry:
            raise ValueError(f"District names {d_not_in_registry} do not exist in the district registry.")
            
        # Find the closest district list:
        d_lists_proximity = []
        state_proximity = []
        for state in self.states_list:
            list_comparison, state_comparison = state.compare_to_r_d_list(r_d_aim_new)
            list_proximity, list_differences = list_comparison
            state_proximity, state_differences = state_comparison
            d_lists_proximity.append((list_proximity, list_differences, str(state)))
            state_proximity.append((proximity, differences, str(state)))
            if state_proximity == 0:
                print(f"The state identified as: {state}")
                return

        d_lists_proximity.sort()
        state_proximity.sort()

        print("No state identified.")
        
        print("The closest states in terms of district lists:")
        for i, (prox, diff, state) in enumerate (d_lists_proximity[:3]):
            diff_1, diff_2 = diff
            print(f"{i}. State {state} (proximity: {prox}).\n Absent in list to identify: {diff_1}.\n Absent in state: {diff_2}.")
        
        print("The closest states:")
        for i, (prox, diff, state) in enumerate(state_proximity[:3]):
            diff_1, diff_2 = diff
            print(f"{i}. State {state} (proximity: {prox}).\n Absent in list to identify: {diff_1}.\n Absent in state: {diff_2}.")

class DistrictRegistry():
    """
    Stores the information on all districts in administrative history.
    """
    def __init__(self, initial_list):
        self.districts = initial_list

    def find_district(self, searched_name):
        """
        Find and return the district name by district name or district alternative name.
        Return None if the given district doesn't exist.
        
        Returns:
            district["district_name"] or None if not found
        """
        for district in self.districts:
            if district["district_name"] == searched_name:
                return district["district_name"]
            alt_names = district.get("alternative_names")
            if alt_names:
                if searched_name in alt_names:
                    return district["district_name"]
        return None
    
    def names_list(self):
        self.districts.sort(key=lambda district: district["district_name"])
        return [district["district_name"] for district in self.districts]
    
    def summary(self, with_alt_names = False):
        self.districts.sort(key=lambda district: district["district_name"])
        print("All districts that historically existed:")
        for district in self.districts:
            to_print = district["district_name"]
            if with_alt_names and district.get("alternative_names"):
                to_print += ", " + ", ".join(district["alternative_names"])
            print(to_print)