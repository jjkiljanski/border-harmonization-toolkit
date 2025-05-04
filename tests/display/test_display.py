from ...data_models.adm_change import *
from ...data_models.adm_timespan import TimeSpan
from ...data_models.adm_state import AdministrativeState

import pytest
import os
import re

def test_district_registry_plot(change_test_setup):
    # Extract the district_registry instance from the fixture
    district_registry = change_test_setup["district_registry"]

    # Define a path for the HTML output (temporary file for the test)
    output_html_path = "./tests/display/initial_state_plot_test.html"

    # Invoke the plot method
    district_registry.plot(output_html_path)

    # Verify that the HTML file has been created
    assert os.path.exists(output_html_path), f"Plot file was not created at {output_html_path}"

def test_administrative_state_plot_appends(change_test_setup):

    district_registry = change_test_setup["district_registry"]
    administrative_state = change_test_setup["administrative_state"]
    output_html_path = "./tests/display/initial_state_plot_test.html"

    assert os.path.exists(output_html_path), "Expected base HTML file to exist before appending."

    # Count images before
    with open(output_html_path, "r", encoding="utf-8") as f:
        html_content_before = f.read()
    initial_img_count = html_content_before.count("<img src=")

    # Append new plot
    administrative_state.plot(
        district_registry=district_registry,
        html_file_path=output_html_path,
        append=True
    )

    # Read content after
    with open(output_html_path, "r", encoding="utf-8") as f:
        html_content_after = f.read()

    # Log for debugging
    print("\n=== HTML Content After Plot ===\n")
    print(html_content_after[-1000:])  # Show only the last 1000 chars for context

    # Improved checks
    assert html_content_after.count("<img src=") > initial_img_count, "New <img> tag not found"
    assert re.search(r"<h1>.*Administrative State Plot.*</h1>", html_content_after, re.IGNORECASE), \
        "Expected plot title not found (case or tag mismatch)"

