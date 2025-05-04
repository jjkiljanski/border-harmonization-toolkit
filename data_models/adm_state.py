from pydantic import BaseModel
from typing import Union, Optional, Literal, Dict, Any, Tuple

from border_harmonization_toolkit.data_models.adm_timespan import TimeSpan
from border_harmonization_toolkit.data_models.adm_unit import *

import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.ops import unary_union
from shapely.geometry import Polygon
import base64
import io
import os

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
        Adds address[n]:content key:value pair at the address adm_state[address[0]][address[1]]...[address[n-1]].
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

    def verify_consistency(self, region_registry, district_registry, timespan_registry = None):
        """
        Verifies the consistency of the current administrative state.

        Parameters:
            region_registry (RegionRegistry)
            district_registry (DistrictRegistry)
            timespan_registry (Optional[TimeSpanRegistry]): Optional

        Raises:
            ValueError: If:
                1) any region or district listed in self.hierarchy doesn't exist in the registry,
                2) a region or districts exists in the hierarchy, but doesn't have a state defined at the self.timespan.middle timepoint,
                3) the timespan of any of a the state existant doesn't contain the self.timespan wholly.
        """
        for country_name, region_dict in self.unit_hierarchy.items():
            for region_name_id, district_dict in region_dict.items():
                # Check if Region registry correctly passed and contains info coherent with the info in adm. state.
                region, region_state, region_timespan = region_registry.find_unit_state_by_date(region_name_id, self.timespan.middle)
                if region is None:
                    raise ValueError(f"Region {region_name_id} exists in the administrative state, but doesn't exist in the RegionRegistry.")
                if region_state is None:
                    raise ValueError(f"Region {region_name_id} exists in the administrative state with timespan {str(self.timespan)}, but the the region's state for the date {self.timespan.middle.date()} doesn't exist in the region registry.")
                if self.timespan not in region_timespan:
                    raise ValueError(f"Region {region_name_id} exists in the administrative state, but the administrative state's timespan ({self.timespan}) is not contained in its timespan ({region_timespan}).")
                for district_name_id in district_dict.keys():
                    # Check if District registry correctly passed and contains info coherent with the info in adm. state.
                    district, district_state, district_timespan = district_registry.find_unit_state_by_date(district_name_id, self.timespan.middle)
                    if district is None:
                        raise ValueError(f"District {district_name_id} exists in the administrative state, but doesn't exist in the DistrictRegistry.")
                    if district_state is None:
                        raise ValueError(f"District {district_name_id} exists in the administrative state with timespan {str(self.timespan)}, but the the district's state for the date {self.timespan.middle.date()} doesn't exist in the district registry.")
                    if self.timespan not in district_timespan:
                        raise ValueError(f"District {district_name_id} exists in the administrative state, but the administrative state's timespan ({self.timespan}) is not contained in its timespan ({district_timespan}).")
                    
        for region, region_state in region_registry.all_unit_states_by_date(self.timespan.middle):
            if region.name_id not in self.all_region_names():
                raise ValueError(f"Region {region.name_id} exists on {self.timespan.middle.date()}, but doesn't belong to the current administrative state hierarchy.")
        for district, district_state in district_registry.all_unit_states_by_date(self.timespan.middle):
            if district.name_id not in self.all_district_names():
                raise ValueError(f"District {district.name_id} exists on {self.timespan.middle.date()}, but doesn't belong to the current administrative state hierarchy.")

    
    def to_address_list(self, only_homeland = False, with_variants = False, current_not_id = False, region_registry = None, district_registry = None):
        """
        Returns a list of (country, region, district) tuples, sorted alphabetically.
        If only_homeland is true, the method returns only pairs of regions in homeland.
        If with_variants is True, the method returns the list with all region and district name variants.
        If current_not_id is True, the method returns the list with region and district current names and not id names.
        If with_variants or current_not_id is True, region_registry and district_registry must be passed
        
        """
        if with_variants or current_not_id:
            if not (isinstance(region_registry, RegionRegistry) and isinstance(district_registry, DistrictRegistry)):
                raise ValueError(
                    f"'with_variants=True' requires region_registry and district_registry to be RegionRegistry and DistrictRegistry. "
                    f"Got types: region_registry={type(region_registry).__name__}, "
                    f"district_registry={type(district_registry).__name__}."
                )
            self.verify_consistency(region_registry=region_registry, district_registry=district_registry)

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
                        district, dist_state, _ = district_registry.find_unit_state_by_date(dist_name_id, self.timespan.middle)
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

    def plot(self, district_registry, html_file_path: str, append: bool = False):
        homeland_districts = []
        abroad_districts = []
        district_geometries = []
        district_borders = []
        region_borders = []

        # Step 1: Accumulate all district geometries and categorize them
        for scope, regions in self.unit_hierarchy.items():
            for region, districts in regions.items():
                region_geometries = []

                for district_name in districts:
                    district, district_state, _ = district_registry.find_unit_state_by_date(
                        district_name, self.timespan.middle
                    )
                    geom = district_state.current_territory
                    district_geometries.append((geom, scope))
                    district_borders.append(geom)
                    region_geometries.append(geom)

                region_union = unary_union(region_geometries)
                region_borders.append(region_union)

        # Step 1: Plot country-level territories (HOMELAND in green, ABROAD in blue)
        fig, ax = plt.subplots(figsize=(10, 10))
        for geom, scope in district_geometries:
            color = "green" if scope == "HOMELAND" else "blue"
            gpd.GeoSeries([geom]).plot(ax=ax, color=color, edgecolor="none", alpha=0.5)

        # Step 2: Plot district borders
        gpd.GeoSeries(district_borders).plot(ax=ax, facecolor="none", edgecolor="black", linewidth=1)

        # Step 3: Plot bold region borders
        gpd.GeoSeries(region_borders).plot(ax=ax, facecolor="none", edgecolor="black", linewidth=10)

        # Final plot formatting
        ax.set_title("Administrative State: Homeland and Abroad", fontsize=16, fontweight="bold", ha="center")
        ax.set_axis_off()

        # Save figure to base64
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", bbox_inches="tight")
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode("utf-8")
        plt.close(fig)

        # Prepare HTML content
        html_block = f"""
        <div style="text-align: center; margin-top: 30px;">
            <h1>Administrative State Plot</h1>
            <p>This plot shows the district territories colored by country (green = HOMELAND, blue = ABROAD), 
            with region and district boundaries overlaid.</p>
            <img src="data:image/png;base64,{img_base64}" />
        </div>
        """

        # Write to file
        if append and os.path.exists(html_file_path):
            with open(html_file_path, "a") as f:
                f.write(html_block)
        else:
            with open(html_file_path, "w") as f:
                f.write(f"<html><body>{html_block}</body></html>")