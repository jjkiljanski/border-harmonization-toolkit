# streamlit_app.py
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import io

from core.core import AdministrativeHistory
from utils.helper_functions import load_config, standardize_df, load_uploaded_csv

from visualization.adm_unit_plots import (
    plot_dist_history,
    plot_dist_ter_info_history,
    plot_district_map
)

# Set layout and title
st.set_page_config(page_title="District Timeline Viewer", layout="wide")
st.title("District Visualization Dashboard")

# Load data
@st.cache_resource
def load_history():
    config = load_config("config.json")
    return AdministrativeHistory(config)

administrative_history = load_history()
dist_registry = administrative_history.dist_registry

# Generate middle dates for timeline slider
adm_state_middles = [adm_state.timespan.middle for adm_state in administrative_history.states_list]

# Generate middle dates for timeline slider
# Uncomment only for testing
# adm_state_middles = [datetime(1925,1,1), datetime(1931,1,1), datetime(1935,1,1)]

# Sidebar plot selector
plot_type = st.sidebar.selectbox("Choose Plot Type", [
    "District History Plot",
    "Territorial State Information Plot",
    "District Maps",
    "Administrative States History"
])

# Dynamic plotting based on selection
if plot_type == "District History Plot":
    start_date = administrative_history.timespan.start
    end_date = administrative_history.timespan.end
    fig = plot_dist_history(dist_registry, start_date, end_date)
    st.plotly_chart(fig, use_container_width=True)

elif plot_type == "Territorial State Information Plot":
    start_date = administrative_history.timespan.start
    end_date = administrative_history.timespan.end
    fig = plot_dist_ter_info_history(dist_registry, start_date, end_date)
    st.plotly_chart(fig, use_container_width=True)

elif plot_type == "District Maps":
    st.subheader("District Maps Over Time")

    @st.cache_resource
    def get_cached_district_registry_maps():
        # Only runs once when "District Maps" is selected for the first time
        return {date: plot_district_map(dist_registry, date) for date in adm_state_middles}

    with st.spinner("Generating district maps..."):
        district_registry_plots = get_cached_district_registry_maps()

    selected_date = st.slider(
        "Select Date",
        min_value=adm_state_middles[0],
        max_value=adm_state_middles[-1],
        value=datetime(1931, 1, 1),
        format="YYYY-MM-DD"
    )

    fig = district_registry_plots[selected_date]
    st.plotly_chart(fig, use_container_width=True)

elif plot_type == "Administrative States History":
    st.subheader("Administrative States History Viewer")

    # Create container placeholders for flexible layout
    upload_container = st.container()
    state_df_container = st.container()
    uploaded_df_container = st.container()
    editor_container = st.container()

    with state_df_container:
        selected_date = st.slider(
            "Select Date",
            min_value=adm_state_middles[0],
            max_value=adm_state_middles[-1],
            value=adm_state_middles[len(adm_state_middles)//2],
            format="YYYY-MM-DD"
        )

    # Get administrative state for selected date
    adm_state = administrative_history.find_adm_state_by_date(selected_date)

    if not adm_state or "HOMELAND" not in adm_state.unit_hierarchy:
        st.warning("No administrative data available for selected date.")
    else:
        homeland_hierarchy = adm_state.unit_hierarchy["HOMELAND"]
        region_district_map = {
            region_key: list(region_value.keys())
            for region_key, region_value in homeland_hierarchy.items()
        }

        # Create a DataFrame where each column is a region, and rows are district keys
        max_rows = max(len(districts) for districts in region_district_map.values())
        df_data = {
            region: districts + [""] * (max_rows - len(districts))
            for region, districts in region_district_map.items()
        }

        adm_state_df = pd.DataFrame(df_data)

    st.markdown("### Upload CSV to Compare Against Administrative State")

    uploaded_file = st.file_uploader("Upload a CSV with columns 'Region' and 'District'", type=["csv"])

    if uploaded_file:
        try:
            uploaded_df = load_uploaded_csv(uploaded_file)
            if uploaded_df is None:
                st.stop()

            # Validate columns
            required_cols = {'Region', 'District'}
            if not required_cols.issubset(uploaded_df.columns):
                st.error(f"CSV must contain columns: {required_cols}. Found: {list(uploaded_df.columns)}")
            else:
                # Copy original values for comparison
                uploaded_df['Standardized Region Name'] = uploaded_df['Region']
                uploaded_df['Standardized District Name'] = uploaded_df['District']

                # Standardize names
                try:
                    # Use a copy to preserve original for highlighting if needed
                    standard_df = uploaded_df.copy()
                    standard_df = standardize_df(
                        standard_df,
                        region_registry=administrative_history.region_registry,
                        district_registry=administrative_history.dist_registry,
                        raise_errors=False,  # We handle errors below
                        use_unique_seat_names=True
                    )

                    # Reassign standardized columns
                    uploaded_df['Standardized Region Name'] = standard_df['Region']
                    uploaded_df['Standardized District Name'] = standard_df['District']

                    # Desired column order
                    priority_cols = ["Region", "Standardized Region Name", "District", "Standardized District Name"]

                    # Reorder: put priority_cols first, then all remaining columns
                    other_cols = [col for col in uploaded_df.columns if col not in priority_cols]
                    uploaded_df = uploaded_df[priority_cols + other_cols]

                    # Sort uploaded_df by region, then by district (case insensitive)
                    uploaded_df = uploaded_df.sort_values(
                        by=["Region", "District"],
                        key=lambda col: col.str.lower() if col.dtype == "object" else col
                    )

                    # Extract all district values for comparison
                    adm_state_dist_ids = set(
                        district
                        for region in adm_state_df.columns
                        for district in adm_state_df[region].dropna()
                    )

                    with editor_container:
                        st.markdown(f"#### Edit Dataframe - Define Missing Standardized District Name")
                        # Use st.data_editor and capture the edited version of uploaded_df
                        edited_df = st.data_editor(uploaded_df, hide_index=True)

                    loaded_file_dist_ids = set(edited_df['Standardized District Name'].dropna())

                    # Apply conditional formatting to the DataFrame

                    # Function to paint the DataFrame
                    def style_cells(val, ref_list, color_if_found, color_if_not_found):
                        if val in ref_list and val != "":
                            return f"background-color: {color_if_found}"
                        elif val == "":
                            return ""
                        else: 
                            return f"background-color: {color_if_not_found}"

                    # Format first DataFrame (adm_state) - light green for matches and light blue for others
                    def highlight_cells_adm_state_dataframe(val):
                        return style_cells(val, loaded_file_dist_ids, "#90EE90", "#ADD8E6")

                    # Format second DataFrame (uploaded_df) - light green for matches and light red for others
                    def highlight_cells_uploaded_dataframe(val):
                        return style_cells(val, adm_state_dist_ids, "#90EE90", "#FFB6C1")

                    # Use edited_df to create a dataframe with region names as column names and district names in the colums.
                    # Use standardized names where possible and non-standardized names where they were not recognized.
                    names_standardized_where_possible = [
                        row["Standardized District Name"] if row["Standardized District Name"] in adm_state_dist_ids else row["District"]
                        for _, row in edited_df.iterrows()
                    ]
                    new_r_d_list = list(zip(list(edited_df["Standardized Region Name"]), list(names_standardized_where_possible)))
                    loaded_region_district_map = {}
                    for region_name, dist_name in new_r_d_list:
                        if region_name not in loaded_region_district_map:
                            loaded_region_district_map[region_name] = []
                        if dist_name:
                            loaded_region_district_map[region_name].append(dist_name)

                    # Create a DataFrame where each column is a region, and rows are district keys
                    max_rows = max(len(districts) for districts in loaded_region_district_map.values())
                    df_data = {
                        region: districts + [""] * (max_rows - len(districts))
                        for region, districts in loaded_region_district_map.items()
                    }

                    edited_df_display = pd.DataFrame(df_data)

                    # Now use edited_df to create styled_uploaded_df
                    styled_uploaded_df = edited_df_display.style.applymap(highlight_cells_uploaded_dataframe)

                    with uploaded_df_container:
                        st.markdown(f"#### Names Recognized in the Uploaded File")
                        # Show the second dataframe, now reflecting edits
                        st.dataframe(styled_uploaded_df, hide_index=True)

                    with state_df_container:
                        # Generate CSV string in-memory using the new version of to_csv
                        csv_data = adm_state.to_csv(csv_filepath=None, only_homeland=True)

                        # Show the first dataframe with styles
                        styled_df_first = adm_state_df.style.applymap(highlight_cells_adm_state_dataframe)
                        st.markdown(f"#### Administrative State {adm_state.timespan}")
                        st.dataframe(styled_df_first, hide_index=True)

                        st.caption(f"Download CSV template for administrative state {adm_state.timespan} of (Region, District) pairs.")

                        st.download_button(
                            label="Download",
                            data=csv_data,
                            file_name="region_district_template.csv",
                            mime="text/csv"
                        )


                except Exception as e:
                    st.error(f"An error occurred during standardization: {str(e)}")

        except Exception as e:
            st.error(f"Could not process uploaded file: {str(e)}")
    else:
        # If file not uploaded, create adm_state_df without styling.
        with state_df_container:
            # Generate CSV string in-memory using the new version of to_csv
            csv_data = adm_state.to_csv(csv_filepath=None, only_homeland=True)

            # Show the adm state dataframe with styles
            st.markdown(f"#### Administrative State {adm_state.timespan}")
            st.dataframe(adm_state_df, hide_index=True)

            st.caption(f"Download CSV template for administrative state {adm_state.timespan} of (Region, District) pairs.")

            st.download_button(
                label="Download",
                data=csv_data,
                file_name="region_district_template.csv",
                mime="text/csv"
            )

else:
    st.warning("Unsupported plot type selected.")