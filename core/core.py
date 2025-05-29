import json
from pathlib import Path
from datetime import datetime
from pydantic import parse_obj_as, ValidationError
from typing import List
import shutil
import geopandas as gpd
import pandas as pd
import os
from collections import defaultdict
import plotly.express as px

from data_models.adm_timespan import *
from data_models.adm_unit import *
from data_models.adm_state import *
from data_models.adm_change import *

from utils.helper_functions import load_config, standardize_df

class AdministrativeHistory():
    def __init__(self, config, load_territories=True):
        # Load the configuration
        config = load_config("config.json")
        
        # Input files' paths
        self.changes_list_path = config["changes_list_path"]
        self.initial_adm_state_path = config["initial_adm_state_path"]
        self.initial_region_list_path = config["initial_region_list_path"]
        self.initial_dist_list_path = config["initial_dist_list_path"]
        self.territories_path = config["territories_path"]

        self.load_territories = load_territories

        # Output files' paths
        self.adm_states_output_path = config["adm_states_output_path"]

        # Define the administrative history timespan
        self.timespan = TimeSpan(start = config["global_timespan"]["start"], end = config["global_timespan"]["end"])

        # Create lists to store Change objects and Administrative State objects
        self.changes_list = []
        self.states_list = []
        
        # Create empty attribute to store district and region registries
        self.dist_registry = None
        self.region_registry = None

        # Create changes list
        self._load_changes_from_json()

        # Create AdministrativeState object for the initial state
        self._load_state_from_json()

        # Load district and region registries
        self._load_dist_registry()
        self._load_region_registry()

        # Create chronological changes dict {[date]: List[Change]}
        self._create_changes_dates_list()
        self._create_changes_chronology()

        # Create states for the whole timespan
        self._create_history()
        print(f"self.dist_registry.unique_name_variants: {self.dist_registry.unique_name_variants}")
        print(f"self.dist_registry.unique_seat_names: {self.dist_registry.unique_seat_names}")

        # Initiate list with all states for which territory is loaded from GeoJSON
        self.states_with_loaded_territory = []
        if self.load_territories:
            # Load the territories
            self._load_territories()
        # Deduce information about district territories where possible
        self._deduce_territories()


    def _load_dist_registry(self):
        """
        Load the initial list of district from a JSON file and validate according to a Pydantic
        data model defined in data_models module.

        Args:
            file_path (str): Path to the JSON file containing the list of changes.
        """
        with open(self.initial_dist_list_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("Expected a list of District dicts in the JSON file")

        # Use pydantic to parse and validate the list
        try:
            self.dist_registry = parse_obj_as(DistrictRegistry, {"unit_list": data})
            # Set initial timespans
            for dist in self.dist_registry.unit_list:
                dist.states[0].timespan = TimeSpan(start = self.timespan.start, end = self.timespan.end)
            # Set CRS
            n_districts = len(self.dist_registry.unit_list)
            print(f"✅ Loaded {n_districts} validated districts. Set their initial state timespands to {TimeSpan(start = self.timespan.start, end = self.timespan.end)}.")
        except ValidationError as e:
            print(e.json(indent=2))

    def _load_region_registry(self):
        """
        Load the initial list of district from a JSON file and validate according to a Pydantic
        data model defined in data_models module.

        Args:
            file_path (str): Path to the JSON file containing the list of changes.
        """
        with open(self.initial_region_list_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("Expected a list of Region dicts in the JSON file")

        # Use pydantic to parse and validate the list
        try:
            self.region_registry = parse_obj_as(RegionRegistry, {"unit_list": data})
            for region in self.region_registry.unit_list:
                region.states[0].timespan = TimeSpan(start = self.timespan.start, end = self.timespan.end)
            n_regions = len(self.region_registry.unit_list)
            print(f"✅ Loaded {n_regions} validated regions. Set their initial state timespands to {TimeSpan(start = self.timespan.start, end = self.timespan.end)}")
        except ValidationError as e:
            print(e.json(indent=2))

    def _load_changes_from_json(self):
        """
        Load a list of changes from a JSON file and validate according to a Pydantic
        data model defined in data_models module.

        Args:
            file_path (str): Path to the JSON file containing the list of changes.
        """
        with open(self.changes_list_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("Expected a list of changes in the JSON file")

        # Check for non-string elements in links before parsing
        for i, change in enumerate(data):
            links = change.get("links", "MISSING")
            #print(f"Change {i} links type: {type(links).__name__}, value: {links}")
            if isinstance(links, list):
                for j, link in enumerate(links):
                    if not isinstance(link, str):
                        print(f"{change.get('date')}: {change.get('sources')} - Non-string link at index {j}: {link} (type: {type(link).__name__})")
            else:
                print(f"{change.get('date')}: {change.get('sources')} - Links is not a list!")

        # Use pydantic to parse and validate the list
        try:
            self.changes_list = parse_obj_as(List[Change], data)
            self.changes_list.sort(key=lambda change: (change.order is None, change.order))  # Moves None order to end
            n_changes = len(self.changes_list)
            print(f"✅ Loaded {n_changes} validated changes.")
        except ValidationError as e:
            print(e.json(indent=2))


    def _load_state_from_json(self):
        """
        Load the administrative state from a JSON file and validate according to the AdministrativeState model.
        """
        with open(self.initial_adm_state_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        try:
            initial_adm_state = AdministrativeState(**data)
            initial_adm_state.timespan = self.timespan.model_copy(deep=True)
            self.states_list.append(initial_adm_state)
            print("✅ Loaded initial state.")
        except ValidationError as e:
            print("❌ Validation error:")
            print(e.json(indent=2))

    def _create_changes_dates_list(self):
        self.changes_dates = [change.date for change in self.changes_list]
        self.changes_dates = list(set(self.changes_dates))
        self.changes_dates.sort()

    def _create_changes_chronology(self):
        self.changes_chron_dict = {}
        for change in self.changes_list:
            if change.date in self.changes_chron_dict.keys():
                self.changes_chron_dict[change.date].append(change)
            else:
                self.changes_chron_dict[change.date] = [change]

        for date, change_list in self.changes_chron_dict.items():
            # Sort changes for every date according to the order.
            # change.order = None puts the changes at the end of the list.
            change_list.sort(key=lambda change: (change.order is None, change.order))

        # Check if all changes are there
        assert set(self.changes_chron_dict.keys()) == set(self.changes_dates), f"Lists not equal!\nset(self.changes_chron_dict.keys()):\n {set(self.changes_chron_dict.keys())};\nset(self.changes_dates):\n{set(self.changes_dates)}."

        # Uncomment for debugging only
        # for date, change_list in self.changes_chron_dict.items():
        #     for change in change_list:
        #         print(f"{date}: {change.change_type}, order: {change.order}")
        #         change.echo()

    def _create_history(self):
        # Delete and recreate the entire folder
        if os.path.exists(self.adm_states_output_path):
            shutil.rmtree(self.adm_states_output_path)
        os.makedirs(self.adm_states_output_path)

        for i, date in enumerate(self.changes_dates):
            changes_list = self.changes_chron_dict[date]
            old_state = self.states_list[-1]
            new_state, all_units_affected = old_state.apply_changes(changes_list, self.region_registry, self.dist_registry)
            self.states_list.append(new_state)

            csv_filename = "/state" + new_state.timespan.start.strftime("%Y-%m-%d")
            new_state.to_csv(self.adm_states_output_path + csv_filename)
        
        # Sort district list in the district registry by name_id
        self.dist_registry.unit_list.sort(key=lambda dist: dist.name_id)
        self.dist_registry.unique_name_variants.sort()
        self.dist_registry.unique_seat_names.sort()
        self.region_registry.unique_name_variants.sort()
        self.region_registry.unique_seat_names.sort()

    def _load_territories(self):
        """
        Loads a territories from an external JSON file to a Geopandas dataframe
         and asigns them to the district states based on the name_id in the 'District'
         column and a date in the district state's timespan defined in the 'ter_date'
         column.
        """
        print("Loading territories...")
        # Initialize list to store individual territories GeoDataFrames
        gdf_list = []

        # Loop through all files in the directory
        for filename in os.listdir(self.territories_path):
            if filename.endswith((".json", ".geojson", ".shp")):
                file_path = os.path.join(self.territories_path, filename)
                try:
                    gdf = gpd.read_file(file_path)
                    print(f"Loaded: {filename} ({len(gdf)} rows)")

                    # Check for CRS
                    if gdf.crs is None:
                        raise ValueError(f"Geometry loaded from '{file_path}' has no defined CRS.")

                    # Reproject if necessary
                    if gdf.crs != "EPSG:4326":
                        original_crs = gdf.crs
                        gdf = gdf.to_crs("EPSG:4326")
                        print(f"CRS of the geometry loaded from file '{file_path}' converted. Original: {original_crs}. New: 'EPSG:4326'.")

                    gdf_list.append(gdf)

                except Exception as e:
                    print(f"Failed to load {filename}: {e}")

        # Combine all into a single GeoDataFrame
        if gdf_list:
            try:
                territories_gdf = gpd.GeoDataFrame(pd.concat(gdf_list, ignore_index=True), crs=gdf_list[0].crs)
                print(f"\n✅ Combined GeoDataFrame has {len(territories_gdf)} rows. CRS: 'EPSG:4326'")
            except ValueError as e:
                print("❌ Failed to concatenate GeoDataFrames:", e)
                raise  # Don't assign the error to `territories_gdf`
        else:
            territories_gdf = gpd.GeoDataFrame()
            print("⚠️ No valid GeoJSON files found.")

        # Standardize district and region names to name_ids in the registries
        try:
            territories_gdf, unit_suggestions = standardize_df(territories_gdf, self.region_registry, self.dist_registry, columns = ["District"])
        except ValueError as e:
            print("❌ Failed during standardization:", e)
            raise  # Do NOT assign the error to territories_gdf!

        # Set the territories of the appropriate states
        for idx, row in territories_gdf.iterrows():
            # Retrieve the district name and territory date
            district_name_id = str(row.get("District", ""))
            ter_date = str(row.get("ter_date", ""))
            ter_date = datetime.strptime(ter_date, "%d.%m.%Y")

            # Find the appropriate unit state in the registry
            unit, unit_state, _ = self.dist_registry.find_unit_state_by_date(district_name_id, ter_date)
            if unit_state is None:
                print(f"No match found for district '{district_name_id}' on {ter_date.date()}")
                continue
            
            # Set the territory of the appropriate unit state.
            unit_state.current_territory = row.geometry

            # Store the information that the state has territory loaded
            self.states_with_loaded_territory.append(unit_state)

    def _deduce_territories(self):
        """
        This function takes the list of unit states with territory geometries
        loaded for GeoJSON and deduces the territory for all other states
        where it is possible.
        """
        for unit_state in self.states_with_loaded_territory:
            unit_state.spread_territory_info()
    
    def _populate_territories_fallback(self):
        """
        Fills fallback district state territories for all states with missing territory information.
        Uses simply the next later existing state with territory, or the last earlier one if no later one exists.
        """
        for dist in self.dist_registry.unit_list:
            n_last_state_with_ter = None # Index of the last state with defined territory in the dist.states list.
            current_ter = None

            # Backward pass: fill with next known territory
            for i in range(len(dist.states)-1, -1, -1): # Loop descending from len(dist.states)-1 to 0
                # If the dist state has a defined territory, save it as the best guess for the previous territories
                if dist.states[i].current_territory is not None:
                    current_ter = dist.states[i].current_territory
                    if n_last_state_with_ter is None:
                        n_last_state_with_ter = i
                else: # If not, use the currently best guess as the state territory
                    if current_ter is not None:
                        dist.states[i].current_territory = current_ter
                        dist.states[i].territory_is_fallback = True
            
            # Forward fill for states after the last one with known territory
            if n_last_state_with_ter is not None:
                current_ter = dist.states[n_last_state_with_ter].current_territory
                for i in range(n_last_state_with_ter, len(dist.states)):
                    dist.states[i].current_territory = current_ter
            else:
                print(f"[Warning] The district '{dist.name_id}' has no defined territory in any state. All states' territories left as undefined (None).")   
        
    def standardize_address(self):
        """
        To implement later. Every address should be standardized before any use."""
        pass

    def list_change_dates(self, lang = "pol"):
        # Lists all the dates of administrative changes.
        if lang == "pol":
            print("Wszystkie daty zmian granic:")
        elif lang == "eng":
            print("All dates of administrative changes:")
        else:
            raise ValueError("Wrong value for the lang parameter.") 
        for date in self.changes_dates: print(date)

    def summarize_by_date(self, lang = "pol"):
        # Prints all changes ordered by date.
        for change in self.changes_list:
            change.echo(lang)

    def print_all_states(self):
        for state in self.states_list:
            print(state)

    def find_adm_state_by_date(self, date: datetime) -> AdministrativeState:
        """
        Returns an administrative state with date encompassing the passed date or None if such state was not found.
        """
        for adm_state in self.states_list:
            if date in adm_state.timespan:
                return adm_state
        return None

    def identify_state(self, r_d_aim_list):
        """
        Takes sorted list of (region, district) pairs and identifies the HOMELAND administrative state that it represents.
        """
        # Find the closest district list:
        r_lists_distance = []
        d_lists_distance = []
        state_distances = []
        for state in self.states_list:
            r_list_comparison, d_list_comparison, state_comparison = state.compare_to_r_d_list(r_d_aim_list)
            r_list_distance, r_list_differences = r_list_comparison
            d_list_distance, d_list_differences = d_list_comparison
            state_distance, state_differences = state_comparison
            r_lists_distance.append((r_list_distance, r_list_differences, str(state)))
            d_lists_distance.append((d_list_distance, d_list_differences, str(state)))
            state_distances.append((state_distance, state_differences, str(state)))
            if state_distance == 0:
                print(f"The state identified as: {state}")
                return

        r_lists_distance.sort()
        d_lists_distance.sort()
        state_distances.sort()

        print("No state identified.")

        print("The closest states in terms of region lists:")
        for i, (distance, diff, state) in enumerate (r_lists_distance[:3]):
            diff_1, diff_2 = diff
            print(f"{i}. State {state} (distance: {distance}).\n Absent in list to identify: {diff_1}.\n Absent in state: {diff_2}.")
        
        print("The closest states in terms of district lists:")
        for i, (distance, diff, state) in enumerate (d_lists_distance[:3]):
            diff_1, diff_2 = diff
            print(f"{i}. State {state} (distance: {distance}).\n Absent in list to identify: {diff_1}.\n Absent in state: {diff_2}.")
        
        print("The closest states:")
        for i, (distance, diff, state) in enumerate(state_distances[:3]):
            diff_1, diff_2 = diff
            print(f"{i}. State {state} (distance: {distance}).\n Absent in list to identify: {diff_1}.\n Absent in state: {diff_2}.")

    def plot_dist_changes_by_year(self, homeland_only = True, black_and_white=False):
        """
        Counts the number of districts that were ever changed in administrative history.
        Plots the number of districts with borders changed by year and returns the plot.

        If homeland_only is True, counts only districts that were ever in 'HOMELAND'
        during self.timespan.

        If black_and_white is True, plots in black and white.
        """
        n_dist_changed = 0 # Total number of districts that were changed
        n_districts = 0

        # List of (datetime(year,1,1), datetime(year+1,1,1)) pairs
        year_timespans = [TimeSpan(start = datetime(year, 1, 1), end = datetime(year + 1, 1, 1)) for year in range(self.timespan.start.year, self.timespan.end.year+1)]
        # List to store change type, number of changes and districts affected per year.
        change_records = []
        # Convert each timespan to a label like "1921–1922" (for plotting)
        timespan_labels = [str(year_timespan.start.year) for year_timespan in year_timespans]

        for district in self.dist_registry.unit_list:
            # Check if district was ever homeland:
            was_homeland = False
            for year_timespan in year_timespans:
                current_dist_address = self.find_adm_state_by_date(year_timespan.middle).find_address(district.name_id, 'District')
                if current_dist_address:
                    if current_dist_address[0] == 'HOMELAND':
                        was_homeland = True
            # Count districts if homeland_only is False or the district ever was in 'HOMELAND'
            if not homeland_only or was_homeland:
                n_districts += 1
                print(f"District {district.name_id} belonged to homeland. Num changes: {len(district.changes)}")
                # Count changes per year. We use the 'district.changes', not the 'self.changes_list' list, because we want to count only districts that were ever in 'homeland'.
                # Start with assuring that district changes are sorted. Every element in the district.changes is a pair (change_type, change). We sort first by 'date', then by 'order' attribute.
                district.changes.sort(key=lambda change_pair: (change_pair[1].date, change_pair[1].order is None, change_pair[1].order))
                for i, year_timespan in enumerate(year_timespans):
                    for j, (change_type, change) in enumerate(district.changes):
                        if max(year_timespan.start, self.timespan.start)<change.date<year_timespan.end:
                            # Omit changes if another change followed on the same day (this is simply an artefact of how we describe changes in the toolkit)
                            if j<len(district.changes)-1:
                                if change.date!=district.changes[j+1]:
                                    print(f"Change of type {change_type} was applied to district {district.name_id} on {change.date}.")
                                    change_records.append({
                                        'Year': year_timespan.start.year,
                                        'District': district.name_id,
                                        'Change Type': change_type
                                    })
                            else:
                                print(f"Change of type {change_type} was applied to district {district.name_id} on {change.date}.")
                                change_records.append({
                                        'Year': year_timespan.start.year,
                                        'District': district.name_id,
                                        'Change Type': change_type
                                })
                # Count the district, it it was ever changed or created
                if len(district.changes)>0:
                    n_dist_changed += 1

        print(f"{n_dist_changed}/{n_districts} ({round(n_dist_changed/n_districts*100, 2)}%) of districts{' in homeland' if homeland_only else ''} had their borders changed, were created, abolished, or moved between regions in the given period.")
        
        # Convert the list of change records into a DataFrame
        df_changes = pd.DataFrame(change_records)

        # Group by Year and Change Type to get:
        # - Count of changes
        # - List of district names
        grouped = df_changes.groupby(['Year', 'Change Type']).agg(
            Change_Count=('District', 'count'),
            Districts_List = (
                'District',
                # Truncate the list if it's too long
                lambda districts: (
                    '<br>'.join(sorted(set(districts))[:10]) + 
                    (f"<br>... (+{len(set(districts)) - 10} more)" if len(set(districts)) > 10 else '')
                )

            )
        ).reset_index()

        color_sequence = ['black'] if black_and_white else px.colors.qualitative.Set2 # or any other color scale

        # Create the stacked bar chart with custom hover text
        fig = px.bar(
            grouped,
            x='Year',
            y='Change_Count',
            color='Change Type',
            hover_data={'Districts_List': True, 'Year': False, 'Change_Count': True},
            title='District Changes by Year and Type',
            labels={'Change_Count': 'Number of Districts Affected'},
            color_discrete_sequence=color_sequence,
            barmode='stack'  # <- Use stacked mode
        )

        fig.update_layout(
            xaxis_title='Year',
            yaxis_title='Number of Districts Affected',
            bargap=0.1
        )


        # Customize hover template to display just the districts
        fig.update_traces(
            hovertemplate='<b>%{x}</b><br>%{customdata[0]}<extra></extra>'
        )

        return fig