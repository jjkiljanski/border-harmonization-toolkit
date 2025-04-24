from border_changes import *
from state import *
from data_models import *
from core import *

########## Load and initiate administrative changes list ###########
# Load changes json

changes_path = "data_input/district_changes.json"
state_path = "data_input/initial_state.json"
administrative_history = AdministrativeHistory(changes_path, state_path)

administrative_history.list_change_dates()
#administrative_history.summarize_by_date()

########## Load and initiate the initial state of administrative division ##########

print(administrative_history.states_list[0])
administrative_history.states_list[0].valid_to = '1921.08.01'
administrative_history.states_list[0].to_csv()

# current_state = administrative_states[0]

# for change in changes_list:
#     if change.change_type == "RChange":
#         current_state = change.apply(current_state)
#         administrative_states.append(current_state)

# for state in administrative_states:
#     print(state)
