# streamlit_app.py
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import io
import os
from collections import defaultdict

from core.core import AdministrativeHistory
from utils.helper_functions import load_config, standardize_df, load_uploaded_csv

from visualization.adm_unit_plots import (
    plot_dist_history,
    plot_dist_ter_info_history,
    plot_district_map
)

# Set layout and title
st.set_page_config(page_title="District Timeline Viewer", layout="wide")
st.title("Geographic Data Harmonization Toolkit")

# Load data
@st.cache_resource
def load_history():
    config = load_config("config.json")
    return AdministrativeHistory(config, load_territories=False)

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
    "Standardize Data",
    "View Change History"
])

# Dynamic plotting based on selection
if plot_type == "District History Plot":
    dist_changes_container = st.container()
    history_plot_container = st.container()

    # Collect district change data
    district_change_rows = []
    for dist in dist_registry.unit_list:
        change_entries = list(set([(change.date.strftime("%Y-%m-%d"), change_type) for change_type, change in dist.changes]))
        change_entries.sort()
        district_change_rows.append({
            "District": dist.name_id,
            "Changes": change_entries
        })

    # Create DataFrame
    district_changes_df = pd.DataFrame(district_change_rows)

    # Display table in container
    with dist_changes_container:
        st.subheader("District Changes Overview")
        st.dataframe(
            district_changes_df,
            use_container_width=True,
            column_config={
                "Changes": st.column_config.ListColumn(
                    label="Changes (Type, Date)",
                    help="List of (change_type, date) for each change affecting the district"
                )
            }
        )

    start_date = administrative_history.timespan.start
    end_date = administrative_history.timespan.end
    fig = plot_dist_history(dist_registry, start_date, end_date)
    with history_plot_container:
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

elif plot_type == "Standardize Data":
    ################# Create containers #################
    # Create container placeholders for flexible layout
    upload_container = st.container()
    slider_container = st.container()
    comparison_container = st.container()
    with comparison_container:
        state_df_col, uploaded_df_col = st.columns(2)
    editor_container = st.container()
    with editor_container:
        edit_dataframe_container = st.container()
        suggestions_container = st.container()
        download_edited_csv_container = st.container()

    with slider_container:
        selected_date = st.slider(
            "Select Date",
            min_value=adm_state_middles[0],
            max_value=adm_state_middles[-1],
            value=adm_state_middles[len(adm_state_middles)//2],
            format="YYYY-MM-DD"
        )

    ################ Prepare the data ###################

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

    with upload_container:
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
                    standard_df, unit_suggestions = standardize_df(
                        standard_df,
                        region_registry=administrative_history.region_registry,
                        district_registry=administrative_history.dist_registry,
                        raise_errors=False  # We handle errors below
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

                    # Initialize the edited dataframe and persist it in the session state
                    file_id = uploaded_file.name
                    if (
                        "uploaded_file_id" not in st.session_state
                        or st.session_state.uploaded_file_id != file_id
                    ):
                        st.session_state.uploaded_file_id = file_id
                        st.session_state.edited_df = uploaded_df.copy()

                    ###################### Create suggestions selectboxes ##################
                    with suggestions_container:
                        st.header("... or select suggested name:")
                        for (region_name, district_name), options in unit_suggestions["District"].items():
                            current_standard_name = st.session_state.edited_df.loc[st.session_state.edited_df["District"].str.upper() == district_name, "Standardized District Name"].values[0]
                            if current_standard_name is None or current_standard_name not in options:
                                selected = st.selectbox(
                                    f"Select standardized name for ({region_name}, {district_name})",
                                    options,
                                    index = None,
                                    key=f"{region_name}_{district_name}",
                                    placeholder = "Select the correct standardized name."
                                )
                                st.session_state.edited_df.loc[st.session_state.edited_df["District"].str.upper() == district_name, "Standardized District Name"] = selected
                            
                    ###################### Create editable dataframe #######################
                    with edit_dataframe_container:
                        st.markdown("#### Edit Dataframe - define missing standardized district names")
                        
                        # Let the user edit the dataframe
                        edited_df = st.data_editor(st.session_state.edited_df, hide_index=True)
                        st.session_state.edited_df = edited_df  # Save any edits the user makes

                    ###################### Prepare download edited CSV data #######################

                    # Prepare dataframe for download
                    download_df = edited_df.copy()
                    download_df["District"] = download_df["Standardized District Name"].where(
                        download_df["Standardized District Name"].notna(), download_df["District"]
                    )
                    download_df["Region"] = download_df["Standardized Region Name"].where(
                        download_df["Standardized Region Name"].notna(), download_df["Region"]
                    )

                    # Drop the standardized columns
                    download_df = download_df.drop(columns=["Standardized Region Name", "Standardized District Name"])

                    # Convert to CSV
                    csv_edited_data = download_df.to_csv(index=False, sep = ";")

                    # Append "_edited" to the file name before the extension
                    name, ext = os.path.splitext(uploaded_file.name)
                    edited_file_name = f"{name}_edited{ext}"

                    ###################### Prepare download ready CSV data #######################

                    # Extract all (region, district) pairs set from adm_state
                    adm_state_r_d_list = set(
                        (region, district)
                        for region in adm_state_df.columns
                        for district in adm_state_df[region].dropna()
                    )
                    adm_state_r_d_set = set(adm_state_r_d_list)

                    # Extract all (region, district) pairs set from the edited dataframe download_df
                    edited_df_r_d_list = list(zip(list(download_df["Region"]), list(download_df["District"])))
                    edited_df_r_d_set = set(edited_df_r_d_list)

                    # Find all missing pairs
                    missing_r_d_pairs = adm_state_r_d_set-edited_df_r_d_set
                    missing_r_d_pairs = {pair for pair in missing_r_d_pairs if pair[1] != ''}

                    # Create a DataFrame for the missing pairs
                    missing_df = pd.DataFrame(missing_r_d_pairs, columns=["Region", "District"])

                    # Append missing pairs to download_df (with other columns as NaN if not specified)
                    ready_df = pd.concat([download_df, missing_df], ignore_index=True)
                    ready_df = ready_df.sort_values(by=["Region", "District"])

                    # Convert to CSV
                    csv_ready_data = ready_df.to_csv(index=False, sep = ";")

                    # Append "_ready" to the file name before the extension
                    name, ext = os.path.splitext(uploaded_file.name)
                    ready_file_name = f"{name}_ready{ext}"

                    ########################## Create download CSV buttons ########################

                    with download_edited_csv_container:
                        # Download edited button
                        st.caption("Download edited dataframe as a CSV with standardized names where available.")
                        st.download_button(
                            label="Download Edited CSV",
                            data=csv_edited_data,
                            file_name=edited_file_name,
                            mime="text/csv",
                            key="download_edited_csv"  # Add a unique key
                        )

                        # Download ready button
                        st.caption("Download ready dataframe as a CSV with standardized names where available, and slots for missing data for the chosen administrative state.")
                        st.download_button(
                            label="Download Ready CSV",
                            data=csv_ready_data,
                            file_name=ready_file_name,
                            mime="text/csv",
                            key="download_ready_csv"  # Add a unique key
                        )

                    loaded_file_dist_ids = set(st.session_state.edited_df['Standardized District Name'].dropna())

                    ################## Apply conditional formatting to the dataframes #####################

                    # Function to paint the DataFrame
                    def style_cells(val, ref_list, color_if_found, color_if_not_found):
                        if val in ref_list:
                            return f"background-color: {color_if_found}"
                        elif val[0] == "":
                            return "" # Don't color if the cell is empty
                        else: 
                            return f"background-color: {color_if_not_found}"

                    # Format first DataFrame (adm_state) - light green for matches and light blue for others
                    def highlight_adm_state_dataframe(row):
                        return [
                            style_cells((col, row[col]), edited_df_r_d_set, "#90EE90", "#ADD8E6")
                            for col in row.index
                        ]

                    # Format second DataFrame (uploaded_df) - light green for matches and light red for others
                    def highlight_uploaded_dataframe(row):
                        return [
                            style_cells((col, row[col]), adm_state_r_d_set, "#90EE90", "#FFB6C1")
                            for col in row.index
                        ]

                    # Use st.session_state.edited_df to create a dataframe with region names as column names and district names in the colums.
                    # Use standardized names where possible and non-standardized names where they were not recognized.
                    new_r_d_list = [
                        (
                            row["Standardized Region Name"],
                            row["Standardized District Name"] if row["Standardized District Name"] is not None else row["District"]
                        )
                        for _, row in st.session_state.edited_df.iterrows()
                    ]

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
                    styled_uploaded_df = edited_df_display.style.apply(highlight_uploaded_dataframe, axis = 1)

                    with uploaded_df_col:
                        st.markdown(f"#### Names Recognized in the Uploaded File")
                        # Show the second dataframe, now reflecting edits
                        st.dataframe(styled_uploaded_df, hide_index=True)

                    with state_df_col:
                        # Generate CSV string in-memory using the new version of to_csv
                        csv_data = adm_state.to_csv(csv_filepath=None, only_homeland=True)

                        # Show the first dataframe with styles
                        styled_df_first = adm_state_df.style.apply(highlight_adm_state_dataframe, axis = 1)
                        st.markdown(f"#### Administrative State {adm_state.timespan}")
                        st.dataframe(styled_df_first, hide_index=True)

                        st.caption(f"Download CSV template for administrative state {adm_state.timespan} of (Region, District) pairs.")

                        st.download_button(
                            label="Download State Template",
                            data=csv_data,
                            file_name=f"{adm_state.timespan.middle.date()}-region_district_template.csv",
                            mime="text/csv"
                        )


                except Exception as e:
                    st.error(f"An error occurred during standardization: {str(e)}")

        except Exception as e:
            st.error(f"Could not process uploaded file: {str(e)}")
    else:
        # If file not uploaded, create adm_state_df without styling.
        with state_df_col:
            # Generate CSV string in-memory using the new version of to_csv
            csv_data = adm_state.to_csv(csv_filepath=None, only_homeland=True)

            # Show the adm state dataframe with styles
            st.markdown(f"#### Administrative State {adm_state.timespan}")
            st.dataframe(adm_state_df, hide_index=True)

            st.caption(f"Download CSV template for administrative state {adm_state.timespan} of (Region, District) pairs.")

            st.download_button(
                label="Download State Template",
                data=csv_data,
                file_name="region_district_template.csv",
                mime="text/csv"
            )
elif plot_type == "View Change History":
    st.subheader("Administrative Change History")

    change_plot_container = st.container()
    change_list_container = st.container()
    source_list_container = st.container()

    with change_plot_container:
        # Plot changes by year
        dist_changes_hist_plot = administrative_history.plot_dist_changes_by_year(black_and_white=False)
        st.plotly_chart(dist_changes_hist_plot, use_container_width=True)

    change_data = []
    for change in administrative_history.changes_list:
        date = change.date
        change_type = getattr(change.matter, "change_type", "Unknown")

        source_1_name = change.sources[0]
        source_1_link = change.links[0]

        source_2_name = change.sources[1]
        source_2_link = change.links[1]

        districts_before = change.units_affected_ids["District"].get("before", [])
        districts_after = change.units_affected_ids["District"].get("after", [])
        districts_affected = set(districts_before + districts_after)

        change_data.append({
            "date": date.date(),
            "Change Type": change_type,
            "districts affected": ", ".join(sorted(districts_affected)),
            "Source 1 Name": source_1_name,
            "Source 1 Link": source_1_link if source_1_link else "",
            "Source 2 Name": source_2_name,
            "Source 2 Link": source_2_link if source_2_link else "",
        })

    change_df = pd.DataFrame(change_data).sort_values("date")

    with change_list_container:
        st.markdown("### Summary of all single changes")
        st.dataframe(
            change_df,
            use_container_width=True,
            column_config={
                "Source 1 Link": st.column_config.LinkColumn(
                    label="Source 1 Link",
                    validate="^https?://.+$"
                ),
                "Source 2 Link": st.column_config.LinkColumn(
                    label="Source 2 Link",
                    validate="^https?://.+$"
                ),
            }
        )

    # Temporary dictionary keyed by (date, legal_act_name, legal_act_link)
    grouped_changes = defaultdict(set)

    for change in administrative_history.changes_list:
        change_date = change.date
        legal_act_name = change.sources[0] if change.sources else "Unknown"
        legal_act_link = change.links[0] if (change.links and change.links[0] and change.links[0] != "X") else ""

        districts_before = change.units_affected_ids["District"].get("before", [])
        districts_after = change.units_affected_ids["District"].get("after", [])
        affected_districts_set = set(districts_before + districts_after)

        key = (change_date, legal_act_name, legal_act_link)
        grouped_changes[key].update(affected_districts_set)

    # Build rows from grouped data
    aggregated_rows = []
    for (date, act_name, act_link), districts_set in grouped_changes.items():
        aggregated_rows.append({
            "Date": date.date(),
            "Legal Act": act_name,
            "Link": act_link,
            "Affected Districts": ", ".join(sorted(districts_set))
        })

    df_aggregated_changes = pd.DataFrame(aggregated_rows).sort_values(["Date", "Legal Act"])

    with source_list_container:
        st.markdown("### Summary of all changes by source")
        st.dataframe(
            df_aggregated_changes,
            use_container_width=True,
            column_config={
                "Link": st.column_config.LinkColumn(
                    label="Legal Act Link",
                    validate="^https?://.+$"
                )
            }
        )






else:
    st.warning("Unsupported plot type selected.")