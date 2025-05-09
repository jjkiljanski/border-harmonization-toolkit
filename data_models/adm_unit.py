from __future__ import annotations
from pydantic import BaseModel, model_validator
from typing import Optional, Literal, List, Tuple, Any, TYPE_CHECKING

from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import geopandas as gpd

from data_models.adm_timespan import TimeSpan

if TYPE_CHECKING: # Using TYPE_CHECKING to postpone Change import and avoid circular imports
    from data_models.adm_change import Change
    
#####################################################################################
#                   Data models for states of administrative units                  #
#####################################################################################

#############################################################################################
# Hierarchy of models to store information about administrative units:
#       UnitState ∈ Unit (stores chronological sequence of its states) ∈ UnitRegistry

class UnitState(BaseModel):
    """
    Represents the state of an administrative unit (e.g., district, region) at a specific time.
    """
    current_name: str
    current_seat_name: str
    timespan: Optional[TimeSpan] = None

    # Self-references
    next: Optional[UnitState] = None
    previous: Optional[UnitState] = None

    # Forward references to Change
    next_change: Optional[Any] = None
    previous_change: Optional[Any] = None

    # Custon __repr__ magic method to avoid infinite recursion loop between Change and UnitState that hold each other as parameters.
    def __repr__(self):
        return (
            f"UnitState(current_name={self.current_name!r}, "
            f"current_seat_name={self.current_seat_name!r}, "
            f"timespan={self.timespan!r}, "
            f"next=..., "
            f"previous=..., "
            f"next_change=..., previous_change=...)"
        )



# This replaces `update_forward_refs()` in Pydantic v2
UnitState.model_rebuild()

class Unit(BaseModel):
    """
    Represents one administrative unit (district or region for the current version).
    The class's attributes describe unit attributes that don't change through time (e.g. name_variants).
    Attributes that do change through time (e.g. current_name should be handled as UnitState attributes)"""
    name_id: str
    name_variants: List[str]
    seat_name_variants: Optional[List[str]] = None # Optional
    states: List[UnitState]
    changes: Optional[List] = []

    @model_validator(mode="after")
    def check_unit_name_in_variants(self) -> "Unit":
        """
        Ensures that name_id in the name_variants list.
        """
        if self.name_id not in self.name_variants:
            raise ValueError(f"name_id '{self.name_id}' must be in name_variants {self.name_variants}")
        return self
    
    def find_state_by_date(self, date: datetime) -> Optional[UnitState]:
        """Returns the state for the unit at a specific date, or None if no match is found."""
        for unit_state in self.states:
            if unit_state.timespan and date in unit_state.timespan:
                return unit_state
        return None  # Return None if no match is found
    
    def find_state_by_timespan(self, timespan: TimeSpan) -> Optional[UnitState]:
        """Returns the state for the unit within a specific timespan, or None if no match is found."""
        for unit_state in self.states:
            if unit_state.timespan:
                # Compare start and end dates directly
                if unit_state.timespan.start == timespan.start and unit_state.timespan.end == timespan.end:
                    return unit_state
        return None  # Return None if no matching timespan is found
    
    def create_next_state(self, date):
        """
        Creates a new state starting at the given date, ending the previous state, 
        and sorting the states list. The date must fall within an existing state's timespan.
        """
        last_state = self.find_state_by_date(date)
        if last_state is None:
            raise ValueError(f"Invalid date: {date.date()}. No state covers this date.")
            
        new_state = last_state.model_copy(deep=True)
        last_state.timespan.end = date
        last_state.timespan.update_middle()
        new_state.timespan.start = date
        new_state.timespan.update_middle()
        self.states.append(new_state)
        self.states.sort(key=lambda state: state.timespan.start)

        return last_state, new_state
    
    def abolish(self, date):
        """Sets the end of the timespan covering the given date to the passed date, marking the unit's abolition."""
        last_state = self.find_state_by_date(date)
        last_state.timespan.end = date
        last_state.timespan.update_middle()
        return last_state

    def exists(self, date):
        """Returns True if the state exists for a given date or False if it doesn't."""
        searched_state = self.find_state_by_date(date)
        if searched_state is None:
            return False
        else:
            return True


class UnitRegistry(BaseModel):
    """
    A registry to manage a list of one type of units (districts/regions) and handle unit state transitions.
    """
    unit_list: List[Unit]

    def find_unit(self, unit_name: str) -> Optional[Unit]:
        """
        Finds a unit by its name or variant.

        Args:
            unit_name: The name to search for.

        Returns:
            Optional[Unit]: The unit if found, or None.
        """
        for unit in self.unit_list:
            if unit_name in unit.name_variants:
                return unit
        return None
    
    def find_unit_state_by_date(self, unit_name: str, date: datetime) -> Tuple[Unit, UnitState, TimeSpan]:
        """
        Finds the unit, its state, and timespan for a given date.

        Args:
            unit_name: The unit's name.
            date: The date for the state.

        Returns:
            Tuple: Unit, UnitState, and its TimeSpan.
        """
        unit = self.find_unit(unit_name)
        if unit is None:
            return None, None, None
        else:
            unit_state = unit.find_state_by_date(date)
            if unit_state is None:
                return unit, None, None
            else:
                timespan = unit_state.timespan
                return unit, unit_state, timespan
    
    def create_next_unit_state(self, unit_name: str, date: datetime) -> UnitState:
        """
        Creates the next state for a unit at a given date.

        Args:
            unit_name: The unit's name.
            date: The date for the next state.

        Returns:
            UnitState: The newly created unit state.
        """
        unit, unit_state, timespan = self.find_unit_state_by_date(unit_name, date)
        if unit is None:
            raise ValueError(f"Invalid unit_name: {unit_name}. This unit is not in the registry.")
        elif unit_state is None:
            raise ValueError(f"Invalid date: {date.date()}. No state covers this date.")
        else:
            return unit.create_next_state(date)
        
    def all_unit_states_by_date(self, date):
        all_existent = []
        for unit in self.unit_list:
            if unit.exists(date):
                all_existent.append((unit, unit.find_state_by_date(date)))
        return all_existent

    
#############################################################################################
# Hierarchy of models to store districts states: DistrictState ∈ District ∈ DistrictRegistry

class DistState(UnitState):
    current_dist_type: Literal["w", "m"]
    current_territory: Optional[Any] = None

    def spread_territory_info(self):
        """
        This method searches recursively through the graph of all links between district states
        and fills all district territories that can be deduced on the basis of type of district
        changes linking the consecutive states and the territories of the consecutive states.

        The logic of the method:
        The method tries to get the territory of the state before and after itself.
        1. If the state was created by a district attribute reform, the territory is same as of the state before.
        2. If the state was created by the change of unit address, the territory is the same as of the state before.
        3. If the state was created by a OneToMany or ManyToOne change involving n districts (including itself), then
            the state's territory can be deduced if the territories of the n-1 others are knowned.
        
        The method reaches to the states before and afterwards (in case of OneToMany and ManyToOne it reaches also to the
        states of other units involved in the change), and:
        1. Either retreives their territory,
        2. Or 
            a. Verifies that they haven't been checked yet - if yes, it returns None,
            b. if no, it calls the 'get_territory' method
        """
        # This function should be called only for states that have the current_territory attribute defined
        if self.next_change:
            if len(self.next_change.next_states) == 1 and len(self.next_change.previous_states)==1:
                next_state = self.next_change.next_states[0]
                if next_state.current_territory is None:
                    next_state.current_territory = self.current_territory
                    next_state.spread_territory_info()
            else:
                all_next_change_states = self.next_change.previous_states + self.next_change.next_states
                num_ter_unknown = 0
                for unit_state in all_next_change_states:
                    if unit_state.current_territory is None:
                        num_ter_unknown += 1
                if num_ter_unknown>1:
                    return
                else:
                    # Not implemented yet.
                    # Here comes the logic of deduction of the n-th territory on the basis of n-1 territories
                    #  involved in the change.
                    return
        # The logic for backward info share mirrors the forward info share logic.
        if self.previous_change:
            if len(self.previous_change.previous_states) == 1 and len(self.previous_change.next_states) == 1:
                previous_state = self.previous_change.previous_states[0]
                if previous_state.current_territory is None:
                    previous_state.current_territory = self.current_territory
                    previous_state.spread_territory_info()
            else:
                all_previous_change_states = self.previous_change.previous_states + self.previous_change.next_states
                num_ter_unknown = 0
                for unit_state in all_previous_change_states:
                    if unit_state.current_territory is None:
                        num_ter_unknown += 1
                if num_ter_unknown > 1:
                    return
                else:
                    # Not implemented yet.
                    # Here comes the logic of deduction of the n-th territory on the basis of n-1 territories
                    #  involved in the change.
                    return
                
        if self.current_territory is not None:
            return self.current_territory
        else:
            if self.territory_checked:
                return None
            else:
                self.territory_checked = True
                if len(self.next_change.next_states) == 1 and len(self.next_change.previous_states)==1:
                    new_territory = self.next_state.get_territory()
                    if new_territory is not None:
                        return new_territory
                elif len(self.previous_change.previous_states) == 1 and len(self.previous_change.next_states)==1:
                    return self.previous_state.get_territory()
                else:
                    other_change_states = self.next_change.previous_states + self.next_change.next_states

class District(Unit):
    """
    Represents one district. The attributes of this class describe district attributes that don't change through time (e.g. dist_name_variants).
    Attributes that do change through time (e.g. current_dist_name should be handled as DistStateDict attributes)
    """
    states: List[DistState]
            

class DistrictRegistry(UnitRegistry):
    """
    Registry of districts.
    """
    unit_list: List[District]

    def add_unit(self, district_data):
        if isinstance(district_data, District):
            district = district_data
        elif isinstance(district_data, dict):
            district = District(**district_data)
        else:
            raise TypeError("add_unit expects a District instance or a dictionary of District parameters.")

        self.unit_list.append(district)
        return district
    
    def _plot_layer(self, date: datetime):
    # Collect district states and names for districts that exist on the given date
        states_and_names = [(district.find_state_by_date(date), district.name_id) for district in self.unit_list if district.exists(date)]
        # Extract geometries and district names
        geometries = [state.current_territory for state, _ in states_and_names if state.current_territory is not None]
        dist_name_id = [name for state, name in states_and_names if state.current_territory is not None]  # Extract names for each district
        
        # Return a GeoDataFrame with district names and corresponding geometries
        return gpd.GeoDataFrame({'name_id': dist_name_id, 'geometry': geometries})

    
    def plot(self, html_file_path, date):
        from utils.helper_functions import build_plot_from_layers

        layer = self._plot_layer(date)
        layer["color"] = "none"
        layer["edgecolor"] = "black"
        layer["linewidth"] = 1
        layer["shownames"] = True

        fig = build_plot_from_layers(layer)
        return fig

#############################################################################################
# Hierarchy of models to store Region states: RegionState ∈ Region ∈ RegionRegistry

class RegionState(UnitState):
    """
    State of a region.
    """

class Region(Unit):
    is_homeland: bool
    states: List[RegionState]

class RegionRegistry(UnitRegistry):
    unit_list: List[Region]

    def add_unit(self, region_data):
        if isinstance(region_data, Region):
            region = region_data
        elif isinstance(region_data, dict):
            region = Region(**region_data)
        else:
            raise TypeError("add_unit expects a Region instance or a dictionary of Region parameters.")

        self.unit_list.append(region)
        return region

################################## DistrictEventLog model ##################################

class DistrictEvent(BaseModel):
    """ Represents the log of a change from the perspective of a district """
    district_name: str
    date: datetime
    event_type: str  # e.g. "created", "abolished", "moved", etc.
    change_ref: Optional['Change'] = None  # optional reference to the actual change

class DistrictEventLog(BaseModel):
    log: List[DistrictEvent]