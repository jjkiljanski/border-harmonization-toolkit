from border_changes import *
from summarize import *
from state import *
from data_models import *
from loader import *

########## Load and initiate administrative changes list ###########
# Load changes json
json_changes = load_changes_from_json("data_input/district_changes.json")
print(f"✅ Loaded {len(json_changes)} validated changes.")

changes_list = []
for change in json_changes:
    if isinstance(change, VChangeEntry):
        changes_list.append(VChange(change))
    if isinstance(change, DOneToManyEntry):
        changes_list.append(DOneToManyChange(change))
    if isinstance(change, DManyToOneEntry):
        changes_list.append(DManyToOneChange(change))

changes_list.sort(key=lambda change: change.date)

list_change_dates(changes_list)
summarize_by_date(changes_list)

########## Load and initiate the initial state of administrative division ##########

initial_state = load_state_from_json("data_input/initial_state.json")
initial_state_dict = initial_state.model_dump()

administrative_states = []
administrative_states.append(AdministrativeState(initial_state_dict))
print(administrative_states[0])
administrative_states[0].valid_to = '1921.08.01'
administrative_states[0].to_csv()

# current_state = administrative_states[0]

# for change in changes_list:
#     if change.type == "VChange":
#         current_state = change.apply(current_state)
#         administrative_states.append(current_state)

# for state in administrative_states:
#     print(state)
