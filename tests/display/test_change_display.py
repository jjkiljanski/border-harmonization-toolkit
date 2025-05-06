from ...data_models.adm_change import *
from ...data_models.adm_timespan import TimeSpan
from ...data_models.adm_state import AdministrativeState

from helper_functions import save_plot_to_html

import pytest
import os
import re
from datetime import datetime

# @pytest.mark.parametrize(
#     "fixture_name",  # Parametrize only the fixture_name
#     [
#         ("region_reform_matter_fixture"),
#         ("district_reform_matter_fixture"),
#         ("one_to_many_matter_fixture"),
#         ("create_many_to_one_matter_fixture"),
#         ("reuse_many_to_one_matter_fixture"),
#         ("region_change_adm_state_matter_fixture"),
#         ("district_change_adm_state_matter_fixture"),
#     ]
# )
def test_change_plot_from_matter_fixtures(request, change_test_setup):

    # Define the output HTML path
    output_html_path = "./tests/display/change_plot_test.html"

    # 1. Ensure the HTML file is empty before starting
    if os.path.exists(output_html_path):
        os.remove(output_html_path)  # Remove the file if it exists to create a fresh one

    # Create a fresh, empty HTML file
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write("<html><head><title>Test Change Plots</title></head><body></body></html>")

    # 2. Add the plots for every fixture
    for fixture_name in ["region_reform_matter_fixture", "district_reform_matter_fixture",
                         "one_to_many_matter_fixture", "create_many_to_one_matter_fixture",
                         "reuse_many_to_one_matter_fixture", "region_change_adm_state_matter_fixture",
                         "district_change_adm_state_matter_fixture"]:
        
        # Retrieve the relevant registries and states from the setup
        region_registry = change_test_setup["region_registry"]
        dist_registry = change_test_setup["district_registry"]
        administrative_state = change_test_setup["administrative_state"]
        
        matter = request.getfixturevalue(fixture_name)
        change = Change(
            date=datetime(1930, 5, 1),
            source="Legal Act XYZ",
            description="Test change",
            order=1,
            matter=matter
        )

        change_plot = change.apply(administrative_state, region_registry, dist_registry, plot_change = True)

        title = f"Change Plot for {fixture_name}"
        description = f"Change description for {fixture_name} ({change.date.date()})"
        
        # Append the plot to the HTML file
        save_plot_to_html(change_plot, output_html_path, title, description, append=True)

    # 3. Read the HTML content and verify the number of plots
    with open(output_html_path, "r", encoding="utf-8") as f:
        html_content_after = f.read()

    # 4. Assert that 7 plots have been added
    assert html_content_after.count("<img src=") == 7, "Expected 7 plots in the HTML file"

    # Optionally, check for specific titles or other content to ensure each plot was appended correctly
    for fixture_name in ["region_reform_matter_fixture", "district_reform_matter_fixture",
                         "one_to_many_matter_fixture", "create_many_to_one_matter_fixture",
                         "reuse_many_to_one_matter_fixture", "region_change_adm_state_matter_fixture",
                         "district_change_adm_state_matter_fixture"]:
        assert re.search(f"<h2>{re.escape(f'Change Plot for {fixture_name}')}</h2>", html_content_after), \
            f"Plot title for {fixture_name} not found in the HTML content"

    print("Test passed: All plots successfully appended and verified.")
