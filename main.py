from border_changes import *
from state import *
from data_models import *
from core import *
from helper_functions import *

import os
import csv
import pandas as pd

########## Load and initiate administrative changes list ###########
# Load changes json

changes_path = "input/district_changes.json"
state_path = "input/initial_state.json"
timespan = ("19.02.1921", "01.09.1939")
administrative_history = AdministrativeHistory(changes_path, state_path, timespan)

#administrative_history.list_change_dates()
#administrative_history.summarize_by_date()

########## Load and initiate the initial state of administrative division ##########

administrative_history.print_all_states()

#administrative_history.district_registry.summary(with_alt_names=True)

# Loop through all files in the input/states_to_identify folder
folder_path = 'input/states_to_identify'
for filename in os.listdir(folder_path):
    if filename.endswith(".csv"):
        file_path = os.path.join(folder_path, filename)
        # Read the CSV
        df = load_and_clean_csv(file_path, administrative_history.district_registry)
        # Create list of (REGION, DISTRICT) pairs in uppercase
        r_d_pairs = list(zip(df['region'], df['district']))

        print(f"Running {filename} identification.")
        #print(file_pairs)
        #administrative_history.identify_state(r_d_pairs)
        administrative_history.states_list[23].compare_to_r_d_list(r_d_pairs, verbose = True)