from data_models import *
from core.core import AdministrativeHistory
from utils.helper_functions import *

from visualization.adm_unit_plots import plot_district_map

import os
import csv
import pandas as pd

########## Load and initiate administrative changes list ###########
# Load config

# Load the configuration
config = load_config("config.json")

administrative_history = AdministrativeHistory(config, load_geometries=True)

########## Example uses of the implemented methods ##########

administrative_history.harmonize_data()


""" Print all adm. states in the adm. history
administrative_history.print_all_states()
"""


""" Create an administrative history summary
administrative_history.dist_registry.summary(with_alt_names=True)
"""


""" Plot changes histogram
dist_changes_hist_plot = administrative_history.plot_dist_changes_by_year(black_and_white=False)
dist_changes_hist_plot.write_html("output/dist_changes_hist_plot.html")
"""


""" Plotly district plot
fig_plotly = plot_district_map(administrative_history.dist_registry, datetime(1931,4,18))
fig_plotly.write_html("output/district_map_1931_plotly.html")
"""


""" Matplotlib district plot
fig_matplotlib = administrative_history.dist_registry.plot("abc", datetime(1931,4,18), shownames = False)
fig_matplotlib.savefig("output/district_map_1931_matplotlib.png", bbox_inches="tight", pad_inches=0.1)
"""


""" Example conversion matrix and conversion dict
############# Create an example conversion dict and conversion matrix and save them to CSV #############
date_from = datetime(1924,1,1)
date_to = datetime(1938,4,1)
conversion_dict = administrative_history._construct_conversion_dict(date_from, date_to, verbose = True)

# Ensure output directory for matrices exists
os.makedirs("output/conversion_matrices", exist_ok=True)

# Save an example conversion dict as CSV
with open('output/conversion_matrices/example_dict.csv', mode='w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['From_District', 'To_District', 'Proportion'])  # header
    for from_dist, to_dists in conversion_dict.items():
        for to_dist, proportion in to_dists.items():
            writer.writerow([from_dist, to_dist, proportion])

# Create an example conversion matrix
conversion_matrix = administrative_history.construct_conversion_matrix(date_from, date_to, verbose = True)

# Save to CSV
conversion_matrix.to_csv('output/conversion_matrices/example_matrix.csv', index=True)
"""


""" Identify state based on the (Region, District) csv column
# Loop through all files in the input/states_to_identify folder
folder_path = 'input/states_to_identify/'
state_info = [
    ('powiaty_1921.csv', datetime(1921,2,20)),
    ('powiaty_1931.csv', datetime(1931,4,18))
    ]

for filename, state_date in state_info:
    file_path = folder_path + filename
    # Read the CSV
    df = load_and_standardize_csv(file_path, administrative_history.region_registry, administrative_history.dist_registry, use_unique_seat_names = True)
    # Create list of (REGION, DISTRICT) pairs in uppercase
    r_d_pairs = list(zip(df['Region'], df['District']))

    # Find relevant administrative state:
    state_to_compare = administrative_history.find_adm_state_by_date(state_date)

    # Compare the state with the list of addresses from csv:
    state_to_compare.compare_to_r_d_list(r_d_pairs, verbose=True)
    #administrative_history.identify_state(r_d_pairs)
    #administrative_history.states_list[23].compare_to_r_d_list(r_d_pairs, verbose = True)
"""