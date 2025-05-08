from pydantic import BaseModel
from typing import Union, Optional, Literal, Dict, Any, Tuple
from datetime import datetime

from data_models.adm_timespan import TimeSpan
from data_models.adm_unit import *
from utils.exceptions import ConsistencyError

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.ops import unary_union
from shapely.geometry import Polygon
import base64
import io
import os
import csv

#############################################################################################
# Models to store information about current region-districts relations.
# AdministrativeState is a list of (region name, list of districts) pairs.
# Every timespan between two consecutive changes has a different adm. state,
# i.e. NO REGION OR DISTRICT should have a state timespan that ends in the middle
# of an administrative states timespans.
# EVERY EXISTENT DISTRICT in timepoint t must be present in the hierarchy of adm_state
# with a timespan encompassing t.

RegionAddress = Tuple[Literal["HOMELAND", "ABROAD"], str]              # For regions"
DistAddress = Tuple[Literal["HOMELAND", "ABROAD"], str, str]         # For districts
Address = Union[DistAddress, RegionAddress]

class AdministrativeState(BaseModel):
    timespan: Optional[TimeSpan] = None
    unit_hierarchy: Dict[Literal["HOMELAND", "ABROAD"], Dict[str, Dict[str, Any]]]

    def create_new(self, date):
        # Create a deep copy of itself
        new_state = self.model_copy(deep=True)
        # Define the end and origin of states
        self.timespan.end = date
        new_state.timespan.start = date

        # Correct the timespan 'middle' attribute:
        self.timespan.update_middle()
        new_state.timespan.update_middle()
        return new_state
    
    def all_region_names(self):
        all_region_names = [
            region
            for _, country_dict in self.unit_hierarchy.items()
            for region in country_dict.keys()
        ]
        return all_region_names
    
    def all_district_names(self):
        all_district_names = [
            district
            for _, country_dict in self.unit_hierarchy.items()
            for _, region_dict in country_dict.items()
            for district in region_dict.keys()
        ]
        return all_district_names
    
    def pop_address(self, address):
        """
        Pops adm_state[address[0]][address[1]]...[address[n]].
        """
        current = self.unit_hierarchy
        current_parent = None
        for i, attr in enumerate(address):
            current_parent = current
            if attr not in current.keys():
                raise ValueError(f"Unit '{attr}' does not belong to {address[:i]}")
            current = current[attr]
        
        return current_parent.pop(address[-1])
        
    def add_address(self, address, content):
        """
        Adds address[n]:content (a key:value pair) at the address adm_state[address[0]][address[1]]...[address[n-1]].
        """
        current = self.unit_hierarchy
        for i, attr in enumerate(address[:-1]):
            if attr not in current.keys():
                raise ValueError(f"Unit '{attr}' does not belong to {address[:i]}")
            current = current[attr]
        current[address[-1]] = content
        return
    
    def get_address(self, address):
        """
        Returns True if the address exists or False otherwise.
        """
        current = self.unit_hierarchy
        for i, attr in enumerate(address):
            if attr not in current.keys():
                return False
            current = current[attr]
        return True
    
    def find_address(self, unit_name_id, unit_type):
        """
        Returns the address of a unit, given its name (unit_name_id) and type ('District' or 'Region') 
        """
        if unit_type not in ['District', 'Region']:
            raise ValueError(f"Argument 'unit_type' of method 'AdministrativeState.find_address' must be 'District' or 'Region'. Passed: {unit_type}.")
        for country_name, country_dict in self.unit_hierarchy.items():
            for region_name, region_dict in country_dict.items():
                if unit_type=='Region':
                    if unit_name_id==region_name:
                        return (country_name, region_name)
                else:
                    for district_name, district_dict in region_dict.items():
                        if unit_type == 'District':
                            if unit_name_id == district_name:
                                return (country_name, region_name, district_name)
        return None
    
    def find_and_pop(self, unit_name_id, unit_type):
        """
        Pops a unit, given its name (unit_name_id) and type ('District' or 'Region').
        """
        address = self.find_address(unit_name_id, unit_type)
        if address is None:
            raise ValueError(f"{unit_type} {unit_name_id} doesn't exist in the AdministrativeState.unit_hierarchy.")
        return self.pop_address(address)
    
    def verify_and_standardize_address(self, address, region_registry, dist_registry, check_date = None):
        """
        1. Checks that all units in the address exist in their registry,
        2. Substitutes current unit names in the address to unit name_ids,
        3. Verifies that such standardized address exists.

        If check_date passed, uses check_date for checks. If not, uses check_date = self.timespan.middle.
        """
        if check_date is None:
            check_date = self.timespan.middle # Set check_date if not passed
        
        # Verify and standardize region address
        region_current_name = address[1]
        region, region_state, _ = region_registry.find_unit_state_by_date(region_current_name, check_date)
        if region is None:
            raise ConsistencyError(
                f"Change {str(self)} applied to {address} address, but no region with name variant '{region_current_name}' exists in the region registry."
            )
        if region_state is None:
            raise ConsistencyError(
                f"Change {str(self)} applied to {address} address, but no region state for region '{region_current_name}' exists in the region registry."
            )

        if len(address) == 2:
            address = (address[0], region.name_id)
        else:
            address = (address[0], region.name_id, address[2])

        # Verify and standardize district if exists in address
        if len(address) == 3:  # If district
            dist_current_name = address[2]
            dist, dist_state, _ = dist_registry.find_unit_state_by_date(dist_current_name, check_date)
            if dist is None:
                raise ConsistencyError(
                    f"Change {str(self)} applied to {address} address, but no district with name variant '{dist_current_name}' exists in the district registry."
                )
            if dist_state is None:
                raise ConsistencyError(
                    f"Change {str(self)} applied to {address} address, but no district state for district '{dist_current_name}' exists in the district registry."
                )

            address = (address[0], address[1], dist.name_id)  # Modify district name_id

        # Check if the address exists:
        if not self.get_address(address):
            raise ConsistencyError(f"Address {address} doesn't exist in the administrative state {str(self)}.")
        return address

    def verify_consistency(self, region_registry, dist_registry, check_date = None, timespan_registry = None):
        """
        Verifies the consistency of the current administrative state.

        Parameters:
            region_registry (RegionRegistry)
            dist_registry (DistrictRegistry)
            check_date (Optional[datetime]): Optional
            timespan_registry (Optional[TimeSpanRegistry]): Optional

        Raises:
            ValueError: If:
                1) any region or district listed in self.hierarchy doesn't exist in the registry,
                2) a region or districts exists in the hierarchy, but doesn't have a state defined at the self.timespan.middle timepoint,
                3) the timespan of any of a the state existant doesn't contain the self.timespan wholly.

        If check_date is passed as argument, check_date instead of self.timespan.middle is used as date for verification.
        """
        if check_date:
            if check_date not in self.timespan:
                raise ValueError(f"Wrong 'checkdate' argument: {check_date.date()}, 'checkdate' must be contained in self.timespan: {self.timespan}.")
        else:
            check_date = self.timespan.middle
                
        for country_name, region_dict in self.unit_hierarchy.items():
            for region_name_id, district_dict in region_dict.items():
                # Check if Region registry correctly passed and contains info coherent with the info in adm. state.
                region, region_state, region_timespan = region_registry.find_unit_state_by_date(region_name_id, check_date)
                if region is None:
                    raise ConsistencyError(f" Region {region_name_id} exists in the administrative state, but doesn't exist in the RegionRegistry.")
                if region_state is None:
                    raise ConsistencyError(f"Region {region_name_id} exists in the administrative state with timespan {str(self.timespan)}, but the the region's state for the date {check_date.date()} doesn't exist in the region registry.")
                if self.timespan not in region_timespan:
                    raise ConsistencyError(f"Region {region_name_id} exists in the administrative state, but the administrative state's timespan ({self.timespan}) is not contained in its timespan ({region_timespan}).")
                for district_name_id in district_dict.keys():
                    # Check if District registry correctly passed and contains info coherent with the info in adm. state.
                    district, district_state, district_timespan = dist_registry.find_unit_state_by_date(district_name_id, check_date)
                    if district is None:
                        raise ConsistencyError(f"District {district_name_id} exists in the administrative state, but doesn't exist in the DistrictRegistry.")
                    if district_state is None:
                        raise ConsistencyError(f"District {district_name_id} exists in the administrative state with timespan {str(self.timespan)}, but the the district's state for the date {check_date.date()} doesn't exist in the district registry. District states: {district.states}")
                    if self.timespan not in district_timespan:
                        raise ConsistencyError(f"District {district_name_id} exists in the administrative state, but the administrative state's timespan ({self.timespan}) is not contained in its timespan ({district_timespan}).")
                    
        for region, region_state in region_registry.all_unit_states_by_date(check_date):
            if region.name_id not in self.all_region_names():
                raise ConsistencyError(f"Region {region.name_id} exists on {check_date.date()}, but doesn't belong to the current administrative state hierarchy.")
        for district, district_state in dist_registry.all_unit_states_by_date(check_date):
            if district.name_id not in self.all_district_names():
                raise ConsistencyError(f"District {district.name_id} exists on {check_date.date()}, but doesn't belong to the current administrative state hierarchy.")

    
    def to_address_list(self, only_homeland = False, with_variants = False, current_not_id = False, region_registry = None, dist_registry = None):
        """
        Returns a list of (country, region, district) tuples, sorted alphabetically.
        If only_homeland is true, the method returns only pairs of regions in homeland.
        If with_variants is True, the method returns the list with all region and district name variants.
        If current_not_id is True, the method returns the list with region and district current names and not id names.
        If with_variants or current_not_id is True, region_registry and dist_registry must be passed
        
        """
        if with_variants or current_not_id:
            if not (isinstance(region_registry, RegionRegistry) and isinstance(dist_registry, DistrictRegistry)):
                raise ValueError(
                    f"'with_variants=True' requires region_registry and dist_registry to be RegionRegistry and DistrictRegistry. "
                    f"Got types: region_registry={type(region_registry).__name__}, "
                    f"dist_registry={type(dist_registry).__name__}."
                )
            self.verify_consistency(region_registry=region_registry, dist_registry=dist_registry)

        address_list = []
        for country_name, country_dict in self.unit_hierarchy.items():
            if only_homeland:
                if country_name!='HOMELAND':
                    continue # Skip if not interested in addresses from abroad.
            for region_name_id, region_dict in country_dict.items():
                # Reset lists for the current region
                region_names_to_store = [] # All region name variants
                dist_names_to_store = [] # All district name variants for districts in the region

                # Create a list with all wanted name variants for the current region.
                if with_variants or current_not_id:
                    region, region_state, _ = region_registry.find_unit_state_by_date(region_name_id, self.timespan.middle)
                    if with_variants:
                        region_names_to_store = region.name_variants
                    else:
                        region_names_to_store = [region_state.current_name]
                else:
                    region_names_to_store = [region_name_id]
                # Iterate through the whole region_names_to_store list and add districts:
                for dist_name_id in region_dict.keys():
                    # Create a list with all wanted name variants for the current district.
                    if with_variants or current_not_id:
                        district, dist_state, _ = dist_registry.find_unit_state_by_date(dist_name_id, self.timespan.middle)
                        if with_variants:
                            dist_names_to_store += district.name_variants
                        else:
                            dist_names_to_store += [dist_state.current_name]
                    else:
                        dist_names_to_store += [dist_name_id]
                # For every region, append all combinations of (region_name, district_name) stored in the created lists.
                for region_name in region_names_to_store:
                    for dist_name in dist_names_to_store:
                        if only_homeland:
                            address_list.append((region_name, dist_name))
                        else:
                            address_list.append((country_name, region_name, dist_name))                    
        address_list.sort()
        return address_list

    def to_csv(self, csv_filepath, only_homeland = True):
        """
        Write the list returned by self.to_address_list(only_homeland=True)
        to a CSV file at the specified path.

        Args:
            csv_filepath (str): The file path to write the CSV to.
        """
        address_list = self.to_address_list(only_homeland)

        if not address_list:
            raise ValueError("Address list is empty; nothing to write.")

        with open(csv_filepath, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Location Type", "Region", "District"])  # Adjust header as needed

            for address in address_list:
                writer.writerow(address)

    def compare_to_r_d_list(self, r_d_list, verbose = False):
        """
        Takes a list of (region_name_id, dist_name_id) HOMELAND address pairs, estimates its own
        distance to the address list and returns distance measures.
        """
        # Comparison of the dist lists
        r_d_adm_state_list = self.to_address_list(only_homeland=True)
        d_adm_state_list = [district for region, district in r_d_adm_state_list]
        d_adm_state_set = set(d_adm_state_list)
        d_aim_list = [district for region, district in r_d_list]
        d_aim_set = set(d_aim_list)
        d_list_difference_1 = list(d_adm_state_set - d_aim_set)
        d_list_difference_1.sort()
        d_list_difference_2 = list(d_aim_set - d_adm_state_set)
        d_list_difference_2.sort()
        d_list_differences = (d_list_difference_1, d_list_difference_2)
        d_list_distance = len(d_list_difference_1) + len(d_list_difference_2)
        d_list_comparison = d_list_distance, d_list_differences

        # Comparison of the region lists
        r_d_adm_state_list = self.to_address_list(only_homeland=True)
        r_adm_state_list = [region for region, district in r_d_adm_state_list]
        r_adm_state_set = set(r_adm_state_list)
        r_aim_list = [region for region, district in r_d_list]
        r_aim_set = set(r_aim_list)
        r_list_difference_1 = list(r_adm_state_set - r_aim_set)
        r_list_difference_1.sort()
        r_list_difference_2 = list(r_aim_set - r_adm_state_set)
        r_list_difference_2.sort()
        r_list_differences = (r_list_difference_1, r_list_difference_2)
        r_list_distance = len(r_list_difference_1) + len(r_list_difference_2)
        r_list_comparison = r_list_distance, r_list_differences

        # Comparison of the region-district state
        r_d_adm_state_list = self.to_address_list(only_homeland=True)
        r_d_adm_state_set = set(r_d_adm_state_list)
        r_d_aim_set = set(r_d_list)
        state_difference_1 = list(r_d_adm_state_set - r_d_aim_set)
        state_difference_1.sort()
        state_difference_2 = list(r_d_aim_set - r_d_adm_state_set)
        state_difference_2.sort()
        state_differences = (state_difference_1, state_difference_2)
        state_distance = len(state_difference_1) + len(state_difference_2)
        state_comparison = state_distance, state_differences

        if verbose == True:
            print(f"State {self}:")
            print("District list comparison:")
            print(f"\tDistance from the d_list: {list_distance}")
            print(f"\tAbsent in d_list to identify: {list_difference_1}.\n Absent in state: {list_difference_2}.")
            print("(Region,district) pairs comparison:")
            print(f"\tDistance from the r_d_list: {state_distance}")
            print(f"\tAbsent in r_d_list to identify: {state_difference_1}.\n Absent in state: {state_difference_2}.")

        return r_list_comparison, d_list_comparison, state_comparison
    
    def _district_plot_layer(self, dist_registry: DistrictRegistry, date: datetime):
        gdf = dist_registry._plot_layer(date)
        gdf["color"] = "none"
        gdf["edgecolor"] = "black"
        gdf["linewidth"] = 1
        gdf["shownames"] = True
        return gdf
    
    def _region_plot_layer(self, region_registry, dist_registry: DistrictRegistry, date: datetime):
        records = []
        for area_type, regions in self.unit_hierarchy.items():
            for region_name, districts in regions.items():
                region_name_id = region_registry.find_unit(region_name).name_id
                district_geoms = []
                for district_name in districts:
                    d, d_state, _ = dist_registry.find_unit_state_by_date(district_name, date)
                    if(d.exists(date)):
                        if d_state.current_territory is not None:
                            district_geoms.append(d_state.current_territory)
                if district_geoms:  # Only proceed if there is at least one valid geometry
                    region_shape = unary_union(district_geoms)
                    records.append({
                        "name_id": region_name_id,
                        "geometry": region_shape,
                        "color": "none",
                        "edgecolor": "black",
                        "linewidth": 10,
                        "shownames": False
                    })
        return gpd.GeoDataFrame(
            records,
            columns=["name_id", "geometry", "color", "edgecolor", "linewidth", "shownames"]
        )
    
    def _country_plot_layer(self, dist_registry: DistrictRegistry, date: datetime):
        country_geoms = {}
        for country_name in self.unit_hierarchy.keys():
            country_geoms[country_name] = []
            for region_name, districts in self.unit_hierarchy[country_name].items():
                for district_name in districts:
                    district, dist_state, _ = dist_registry.find_unit_state_by_date(district_name, date)
                    if district.exists(date):
                        if dist_state.current_territory:
                            country_geoms[country_name].append(dist_state.current_territory)
        records = []
        if country_geoms.get("HOMELAND", None):
            records.append({
                "name_id": "HOMELAND",
                "geometry": unary_union(country_geoms["HOMELAND"]),
                "color": "green",
                "edgecolor": "black",
                "linewidth": 0.5,
                "shownames": False
            })
        if country_geoms.get("ABROAD", None):
            records.append({
                "name_id": "HOMELAND",
                "geometry": unary_union(country_geoms["ABROAD"]),
                "color": "blue",
                "edgecolor": "black",
                "linewidth": 0.5,
                "shownames": False
            })
        return gpd.GeoDataFrame(
            records,
            columns=["name_id", "geometry", "color", "edgecolor", "linewidth", "shownames"]
        )
    
    def plot(self, region_registry, dist_registry, date):
        from utils.helper_functions import build_plot_from_layers

        # Prepare the layers
        country_layer = self._country_plot_layer(dist_registry, date)
        region_layer = self._region_plot_layer(region_registry, dist_registry, date)
        district_layer = self._district_plot_layer(dist_registry, date)

        # Build the figure
        fig = build_plot_from_layers(country_layer, district_layer, region_layer)
        return fig
    
    def apply_changes(self, changes_list, region_registry, dist_registry):
        # Creates a copy of itself, applies all changes to the copy and returns it as a new state.

        # Take the date of the change and ensure that all changes have the same date.
        change_date = changes_list[0].date
        for change in changes_list:
            if change.date != change_date:
                raise ValueError(f"Changes applied to the state {self} have different dates!")
            
        changes_list.sort(key=lambda change: (change.order is None, change.order))

        # Create a new state such that change_date marks the transition between the old and the new one.
        new_state = self.create_new(change_date)
        
        all_units_affected = {"Region": [], "District": []}
            
        for change in changes_list:
            try:
                # Apply change and store information on the affected districts
                change.apply(new_state, region_registry, dist_registry, plot_change = False)
                all_units_affected["Region"] += change.units_affected["Region"]
                all_units_affected["District"] += change.units_affected["District"]
            except Exception as e:
                raise RuntimeError(f"Error during the application of change {str(change)}: {str(e)}") from e
        
        new_state.verify_consistency(region_registry, dist_registry)
        
        return new_state, all_units_affected
    
    def __str__(self):
        regions_len = len(self.all_region_names())
        districts_len = len(self.all_district_names())
        return f"<AdministrativeState timespan={self.timespan}, regions={regions_len}, districts={districts_len}>"