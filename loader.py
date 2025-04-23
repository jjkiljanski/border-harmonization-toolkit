import json
from pathlib import Path
from pydantic import parse_obj_as
from typing import List
from data_models import ChangeEntry

def load_changes_from_json(file_path: str) -> List[ChangeEntry]:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Expected a list of changes in the JSON file")

    # Use pydantic to parse and validate the list
    return parse_obj_as(List[ChangeEntry], data)