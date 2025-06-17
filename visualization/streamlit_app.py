# streamlit_app.py
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import json
import os
import sys

from typing import List

# Add the project root directory to sys.path to ensure that imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data_models.econ_data_metadata import DataTableMetadata
from core.core import AdministrativeHistory
from utils.helper_functions import load_config, standardize_df, load_uploaded_csv

from visualization.adm_state_database_views import (
    display_district_registry,
    display_territorial_state_info,
    display_adm_state_maps,
    display_changes_history
)
from visualization.standardize_data_view import standardize_data_view
from visualization.economic_database_views import display_data_map

# Set layout and title
st.set_page_config(page_title="District Timeline Viewer", layout="wide")
st.title("Interwar Poland Database")

# Load data
@st.cache_resource
def load_history():
    config = load_config("config.json")
    return AdministrativeHistory(config, load_geometries=False)

administrative_history = load_history()
dist_registry = administrative_history.dist_registry

# Top-level database selector
selected_database = st.sidebar.selectbox(
    "Choose Database",
    ["Administrative States Database", "Economic Database"]
)

# Dictionary to store loaded data_tables
harmonized_dataframes = {}

# If "Administrative States Database" is selected
if selected_database == "Administrative States Database":
    adm_database_view = st.sidebar.selectbox("Choose Database View", [
        "District History Plot",
        "Territorial State Information Plot",
        "Administrative State Maps",
        "Standardize Data",
        "View Change History"
    ])

    # Dynamic plotting based on selection
    if adm_database_view == "District History Plot":
        display_district_registry(administrative_history)

    elif adm_database_view == "Territorial State Information Plot":
        display_territorial_state_info(administrative_history)
        
    elif adm_database_view == "Administrative State Maps":
        display_adm_state_maps(administrative_history)

    elif adm_database_view == "Standardize Data":
        standardize_data_view(administrative_history)

    elif adm_database_view == "View Change History":
        display_changes_history(administrative_history)

    else:
        st.warning("Unsupported plot type selected.")

# If "Interwar Poland Economic Database" is selected
elif selected_database == "Economic Database":

    # Directory containing CSVs
    harmonized_data_dir = 'output/harmonized_data'

    # Collect and prefix all dataframes
    all_data_df = None
    n_loaded_data_tables = 0
    harmonized_dataframe_cols = {}
    for filename in os.listdir(harmonized_data_dir):
        if filename.endswith(".csv"):
            filepath = os.path.join(harmonized_data_dir, filename)
            key = filename[:-4]  # filename without .csv

            try:
                df = pd.read_csv(filepath)

                # Ensure 'District' column exists
                if 'District' not in df.columns:
                    continue
                else:
                    df_cols_without_district = [col for col in df.columns if col != 'District']
                    harmonized_dataframe_cols[key] = df_cols_without_district

                # Rename all columns except 'District'
                df = df.rename(columns={col: f"{key}:{col}" for col in df.columns if col != 'District'})

                # Merge into the main dataframe
                if all_data_df is None:
                    all_data_df = df
                else:
                    all_data_df = pd.merge(all_data_df, df, on='District', how='outer')

            except Exception as e:
                print(f"Failed to load {filename}: {e}")

    # # Load harmonization metadata
    # with open(harmonized_data_dir+'/harmonized_data_metadata.json', 'r', encoding='utf-8') as f:
    #     harmonized_data_metadata_raw = json.load(f)
    #     # Convert each dict to a DataTableMetadata instance
    #     harmonized_data_data_metadata: List[DataTableMetadata] = [
    #         DataTableMetadata(**metadata_dict) for metadata_dict in harmonized_data_metadata_raw
    #     ]

    # Get base GeoDataFrame (with geometries and name_id)
    gdf = administrative_history.dist_registry._plot_layer(administrative_history.harmonize_to_date)

    # Rename 'name_id' to 'District' so it matches with the column in your data
    gdf = gdf.rename(columns={'name_id': 'id'})

    # Ensure consistent types
    all_data_df['District'] = all_data_df['District'].astype(str)
    gdf['id'] = gdf['id'].astype(str)

    # Create GeoJSON from GeoDataFrame indexed by 'District'
    geojson = gdf.__geo_interface__

    # Create sorted list of unique categories
    categories = sorted(set([
        data_table_metadata.category
        for data_table_metadata in administrative_history.harmonized_data_metadata
    ]))

    # Create a dict with all data tables
    data_tables_dict = {
        category: {
meta.data_table_id: sorted([f'{c_name} (completeness: Undefined)' if c_dict.completeness is None else f'{c_name} (completeness: {c_dict.completeness*100:.2f}%)' for c_name, c_dict in meta.columns.items()])
            for meta in administrative_history.harmonized_data_metadata
            if meta.category == category
        }
        for category in {
            meta.category for meta in administrative_history.harmonization_metadata
        }
    }

    selected_category = st.sidebar.selectbox("Choose Data Category", categories, index = None)

    if selected_category is None:
        st.write("This streamlit view is only preliminary and will be removed in the future. In the later phase of the project, the python layer will serve only as a data standardization and injection layer to an underlying SQL database.")

        # n_data_points = [col.n_not_na for metadata_data_table in harmonized_data_metadata for col in metadata_data_table.columns]
        # n_na = [col.n_na for metadata_data_table in harmonization_data_metadata for col in metadata_data_table.columns]
        # st.write(f"### Total number of data points: {n_data_points+n_na}. Non-missing: {n_data_points}/{n_data_points+n_na} ({(n_data_points/(n_data_points+n_na))*100}%)")
        st.write(f"### Total number of data points: {all_data_df.size} ({all_data_df.shape[1]} standardized data sets for {all_data_df.shape[0]} districts).")

        st.write("### All data tables stored in the harmonized csv files.")
        st.write(data_tables_dict)
    else:
        # Filter and sort data table IDs for the selected category
        filtered_ids = sorted([
            data_table_metadata.data_table_id
            for data_table_metadata in administrative_history.harmonized_data_metadata
            if data_table_metadata.category == selected_category
        ])

        selected_data_table_id = st.sidebar.selectbox("Choose Dataset", filtered_ids, index = None)

        if selected_data_table_id is None:
            st.write(f"### Select dataset.")
        else:
            data_table_description = [data_table_metadata.description["eng"] for data_table_metadata in administrative_history.harmonized_data_metadata if data_table_metadata.data_table_id == selected_data_table_id][0]
            data_table_date = [data_table_metadata.date for data_table_metadata in administrative_history.harmonized_data_metadata if data_table_metadata.data_table_id == selected_data_table_id][0]

            st.write(f"### {data_table_description} ({data_table_date})")

            # Display column selector if data_table is found
            if selected_data_table_id in harmonized_dataframe_cols:
                available_columns = harmonized_dataframe_cols[selected_data_table_id]
                selected_column = st.sidebar.selectbox("Choose Dataset", available_columns, index = None)
                if selected_column is None:
                    st.write(f"### Select dataset.")
                else:
                    display_data_map(geojson, all_data_df, selected_data_table_id, selected_column)
            else:
                st.warning(f"The data table `{selected_data_table_id}` was not found in the loaded files.")
