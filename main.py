from data_models import *
from core.core import AdministrativeHistory
from helper_functions import *

import os
import csv
import pandas as pd

########## Load and initiate administrative changes list ###########
# Load changes json

changes_list_path = "input/changes_list.json"
initial_adm_state_path = "input/initial_adm_state.json"
region_list = "input/initial_region_state_list.json"
dist_list = "input/initial_dist_state_list.json"
timespan = (datetime(1921,2,19), datetime(1939,9,1))

administrative_history = AdministrativeHistory(changes_list_path, initial_adm_state_path, region_list, dist_list, timespan)

#administrative_history.list_change_dates()
#administrative_history.summarize_by_date()

########## Load and initiate the initial state of administrative division ##########

administrative_history.print_all_states()

#administrative_history.district_registry.summary(with_alt_names=True)

# # Loop through all files in the input/states_to_identify folder
# folder_path = 'input/states_to_identify'
# for filename in os.listdir(folder_path):
#     if filename.endswith(".csv"):
#         file_path = os.path.join(folder_path, filename)
#         # Read the CSV
#         df = load_and_clean_csv(file_path, administrative_history.district_registry)
#         # Create list of (REGION, DISTRICT) pairs in uppercase
#         r_d_pairs = list(zip(df['region'], df['district']))

#         print(f"Running {filename} identification.")
#         #print(file_pairs)
#         #administrative_history.identify_state(r_d_pairs)
#         administrative_history.states_list[23].compare_to_r_d_list(r_d_pairs, verbose = True)