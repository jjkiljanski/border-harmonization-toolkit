from data_models import *
from core.core import AdministrativeHistory
from utils.helper_functions import *

import os
import csv
import pandas as pd

########## Load and initiate administrative changes list ###########
# Load config

# Load the configuration
config = load_config("config.json")

administrative_history = AdministrativeHistory(config)

#administrative_history.list_change_dates()
#administrative_history.summarize_by_date()

########## Load and initiate the initial state of administrative division ##########

administrative_history.print_all_states()

#administrative_history.dist_registry.summary(with_alt_names=True)

# Loop through all files in the input/states_to_identify folder
folder_path = 'input/states_to_identify/'
state_info = [
    ('powiaty_1921.csv', datetime(1921,2,20)),
    ('powiaty_1931.csv', datetime(1931,4,18))
    ]
for filename, state_date in state_info:
    file_path = folder_path + filename
    # Read the CSV
    df = load_and_standardize_csv(file_path, administrative_history.region_registry, administrative_history.dist_registry)
    # Create list of (REGION, DISTRICT) pairs in uppercase
    r_d_pairs = list(zip(df['Region'], df['District']))

    # Find relevant administrative state:
    state_to_compare = administrative_history.find_adm_state_by_date(state_date)

    # Compare the state with the list of addresses from csv:
    state_to_compare.compare_to_r_d_list(r_d_pairs, verbose=True)
    #administrative_history.identify_state(r_d_pairs)
    #administrative_history.states_list[23].compare_to_r_d_list(r_d_pairs, verbose = True)