import os
import json
from datetime import datetime

from border_changes import *
from summarize import *

# Load changes json
json_changes = []
with open("district_changes.json", 'r', encoding='utf-8') as file:
    json_changes = json.load(file)

changes_list = []
for change in json_changes:
    if change["type"] == "v_change":
        changes_list.append(VChange(change))
    if change["type"] == "d_one_to_many":
        changes_list.append(DOneToManyChange(change))

summarize_by_date(changes_list)


 
