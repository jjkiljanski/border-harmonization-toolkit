import os
import json

from border_changes import *
from summarize import *
from state import *

########## Load and initiate administrative changes list ###########
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
    if change["type"] == "d_many_to_one":
        changes_list.append(DManyToOneChange(change))

changes_list.sort(key=lambda change: change.date)

list_change_dates(changes_list)
#summarize_by_date(changes_list)

########## Load and initiate the initial state of administrative division ##########

initial_state_dict = {}
with open("initial_state.json", 'r', encoding='utf-8') as file:
    initial_state_dict = json.load(file)

administrative_states = []
administrative_states.append(AdministrativeState(initial_state_dict))
print(administrative_states[0])
administrative_states[0].valid_to = '1921.08.01'
administrative_states[0].to_csv()
