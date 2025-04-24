import json
from pathlib import Path
from pydantic import parse_obj_as, ValidationError
from typing import List

from data_models import *
from border_changes import *
from state import *

class AdministrativeHistory():
    def __init__(self, border_changes_path, initial_state_path):
        self.border_changes_path = border_changes_path
        self.initial_state_path = initial_state_path

        # Create lists to store Change objects and Administrative State objects
        self.changes_list = []
        self.states_list = []

        # Create changes list
        self._load_changes_from_json()
        self._create_changes_list()

        # Create AdministrativeState object for the initial state
        self._load_state_from_json()
        self._create_initial_state()

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
            self._pydantic_initial_state = AdministrativeStateEntry(**data)
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

        self.changes_list.sort(key=lambda change: change.date)

        del self._pydantic_changes_list
        print("✅ Successfully created the list of Change objects.")

    def _create_initial_state(self):
        # Create a dict out of pydantic model
        self._initial_state_dict = self._pydantic_initial_state.model_dump()
        del self._pydantic_initial_state

        # Create an AdministrativeState object for the initial state
        self.states_list.append(AdministrativeState(self._initial_state_dict))
        del self._initial_state_dict
        print("✅ Successfully created AdministrativeState object for the initial state.")

    def list_change_dates(self, lang = "pol"):
        # Lists all the dates of border changes.
        dates = [change.date for change in self.changes_list]
        dates = list(set(dates))
        dates.sort()
        if lang == "pol":
            print("Wszystkie daty zmian granic:")
        elif lang == "eng":
            print("All dates of border changes:")
        else:
            raise ValueError("Wrong value for the lang parameter.") 
        for date in dates: print(date)

    def summarize_by_date(self, lang = "pol"):
        # Prints all changes ordered by date.
        for change in self.changes_list:
            change.echo(lang)
    

        

