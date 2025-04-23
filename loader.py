import json
from pathlib import Path
from pydantic import parse_obj_as
from typing import List
from data_models import ChangeEntry, AdministrativeStateEntry

def load_changes_from_json(file_path: str) -> List[ChangeEntry]:
    """
    Load a list of changes from a JSON file and validate according to a Pydantic
    data model defined in data_models module.

    Args:
        file_path (str): Path to the JSON file containing the list of changes.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Expected a list of changes in the JSON file")

    # Use pydantic to parse and validate the list
    return parse_obj_as(List[ChangeEntry], data)

def load_state_from_json(file_path: str) -> AdministrativeStateEntry:
    """
    Load the administrative state from a JSON file and validate according to a Pydantic
    data model defined in data_models module.

    Args:
        file_path (str): Path to the JSON file containing the administrative state.
    """
    # Open the file and load the data
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Validate the data using Pydantic directly
    return AdministrativeStateEntry(**data)