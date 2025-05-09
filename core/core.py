import json
from pathlib import Path
from datetime import datetime
from pydantic import parse_obj_as, ValidationError
from typing import List
import shutil

from data_models.adm_timespan import *
from data_models.adm_unit import *
from data_models.adm_state import *
from data_models.adm_change import *

from utils.helper_functions import load_config

class AdministrativeHistory():
    def __init__(self, config):
        # Load the configuration
        config = load_config("config.json")
        
        # Input files' paths
        self.changes_list_path = config["changes_list_path"]
        self.initial_adm_state_path = config["initial_adm_state_path"]
        self.initial_region_list_path = config["initial_region_list_path"]
        self.initial_dist_list_path = config["initial_dist_list_path"]

        # Output files' paths
        self.adm_states_output_path = config["adm_states_output_path"]

        self.timespan = TimeSpan(start = config["global_timespan"]["start"], end = config["global_timespan"]["end"])

        # Create lists to store Change objects and Administrative State objects
        self.changes_list = []
        self.states_list = []
        
        # Create empty attribute to store district and region registries
        self.dist_registry = None
        self.region_registry = None

        # Create changes list
        self._load_changes_from_json()

        # Create AdministrativeState object for the initial state
        self._load_state_from_json()

        # Load district and region registries
        self._load_dist_registry()
        self._load_region_registry()

        # Create chronological changes dict {[date]: List[Change]}
        self._create_changes_dates_list()
        self._create_changes_chronology()

        # Create states for the whole timespan
        self._create_history()

    def _load_dist_registry(self):
        """
        Load the initial list of district from a JSON file and validate according to a Pydantic
        data model defined in data_models module.

        Args:
            file_path (str): Path to the JSON file containing the list of changes.
        """
        with open(self.initial_dist_list_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("Expected a list of District dicts in the JSON file")

        # Use pydantic to parse and validate the list
        try:
            self.dist_registry = parse_obj_as(DistrictRegistry, {"unit_list": data})
            for dist in self.dist_registry.unit_list:
                dist.states[0].timespan = TimeSpan(start = self.timespan.start, end = self.timespan.end)
            n_districts = len(self.dist_registry.unit_list)
            print(f"✅ Loaded {n_districts} validated districts. Set their initial state timespands to {TimeSpan(start = self.timespan.start, end = self.timespan.end)}")
        except ValidationError as e:
            print(e.json(indent=2))

    def _load_region_registry(self):
        """
        Load the initial list of district from a JSON file and validate according to a Pydantic
        data model defined in data_models module.

        Args:
            file_path (str): Path to the JSON file containing the list of changes.
        """
        with open(self.initial_region_list_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("Expected a list of Region dicts in the JSON file")

        # Use pydantic to parse and validate the list
        try:
            self.region_registry = parse_obj_as(RegionRegistry, {"unit_list": data})
            for region in self.region_registry.unit_list:
                region.states[0].timespan = TimeSpan(start = self.timespan.start, end = self.timespan.end)
            n_regions = len(self.region_registry.unit_list)
            print(f"✅ Loaded {n_regions} validated regions. Set their initial state timespands to {TimeSpan(start = self.timespan.start, end = self.timespan.end)}")
        except ValidationError as e:
            print(e.json(indent=2))

    def _load_changes_from_json(self):
        """
        Load a list of changes from a JSON file and validate according to a Pydantic
        data model defined in data_models module.

        Args:
            file_path (str): Path to the JSON file containing the list of changes.
        """
        with open(self.changes_list_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("Expected a list of changes in the JSON file")

        # Use pydantic to parse and validate the list
        try:
            self.changes_list = parse_obj_as(List[Change], data)
            self.changes_list.sort(key=lambda change: (change.order is None, change.order)) # Changes with change.order = None, will be moved to the end of the list.
            n_changes = len(self.changes_list)
            print(f"✅ Loaded {n_changes} validated changes.")
        except ValidationError as e:
            print(e.json(indent=2))

    def _load_state_from_json(self):
        """
        Load the administrative state from a JSON file and validate according to the AdministrativeState model.
        """
        with open(self.initial_adm_state_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        try:
            initial_adm_state = AdministrativeState(**data)
            initial_adm_state.timespan = self.timespan.model_copy(deep=True)
            self.states_list.append(initial_adm_state)
            print("✅ Loaded initial state.")
        except ValidationError as e:
            print("❌ Validation error:")
            print(e.json(indent=2))

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
        # Delete and recreate the entire folder
        if os.path.exists(self.adm_states_output_path):
            shutil.rmtree(self.adm_states_output_path)
        os.makedirs(self.adm_states_output_path)

        for i, date in enumerate(self.changes_dates):
            changes_list = self.changes_chron_dict[date]
            old_state = self.states_list[-1]
            new_state, all_units_affected = old_state.apply_changes(changes_list, self.region_registry, self.dist_registry)
            self.states_list.append(new_state)

            csv_filename = "/state" + new_state.timespan.start.strftime("%Y-%m-%d")
            new_state.to_csv(self.adm_states_output_path + csv_filename)
        
    def standardize_address(self):
        """
        To implement later. Every address should be standardized before any use."""
        pass

    def list_change_dates(self, lang = "pol"):
        # Lists all the dates of administrative changes.
        if lang == "pol":
            print("Wszystkie daty zmian granic:")
        elif lang == "eng":
            print("All dates of administrative changes:")
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
        Takes sorted list of (region, district) pairs and identifies the HOMELAND administrative state that it represents.
        """
        # Find the closest district list:
        r_lists_distance = []
        d_lists_distance = []
        state_distances = []
        for state in self.states_list:
            r_list_comparison, d_list_comparison, state_comparison = state.compare_to_r_d_list(r_d_aim_list)
            r_list_distance, r_list_differences = r_list_comparison
            d_list_distance, d_list_differences = d_list_comparison
            state_distance, state_differences = state_comparison
            r_lists_distance.append((r_list_distance, r_list_differences, str(state)))
            d_lists_distance.append((d_list_distance, d_list_differences, str(state)))
            state_distances.append((state_distance, state_differences, str(state)))
            if state_distance == 0:
                print(f"The state identified as: {state}")
                return

        r_lists_distance.sort()
        d_lists_distance.sort()
        state_distances.sort()

        print("No state identified.")

        print("The closest states in terms of region lists:")
        for i, (distance, diff, state) in enumerate (r_lists_distance[:3]):
            diff_1, diff_2 = diff
            print(f"{i}. State {state} (distance: {distance}).\n Absent in list to identify: {diff_1}.\n Absent in state: {diff_2}.")
        
        print("The closest states in terms of district lists:")
        for i, (distance, diff, state) in enumerate (d_lists_distance[:3]):
            diff_1, diff_2 = diff
            print(f"{i}. State {state} (distance: {distance}).\n Absent in list to identify: {diff_1}.\n Absent in state: {diff_2}.")
        
        print("The closest states:")
        for i, (distance, diff, state) in enumerate(state_distances[:3]):
            diff_1, diff_2 = diff
            print(f"{i}. State {state} (distance: {distance}).\n Absent in list to identify: {diff_1}.\n Absent in state: {diff_2}.")