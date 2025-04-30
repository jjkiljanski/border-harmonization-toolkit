from pydantic import BaseModel, model_validator
from typing import Optional, Literal, List, Tuple
from copy import deepcopy

from datetime import datetime

from adm_timespan import *
    
#####################################################################################
#                   Data models for states of administrative units                  #
#####################################################################################

#############################################################################################
# Hierarchy of models to store information about administrative units:
#       UnitState ∈ Unit (stores chronological sequence of its states) ∈ UnitRegistry

class UnitState(BaseModel):
    current_name: str
    current_seat_name: str
    current_dist_type: Literal["w", "m"]

    # timespan: Defined during initialization as the global timespan.
    # Timespan end will be set to the date of application of the first administrative change for the unit.
    timespan: Optional[TimeSpan] = None

class Unit(BaseModel):
    """
    Represents one district. The attributes of this class describe district attributes that don't change through time (e.g. dist_name_variants).
    Attributes that do change through time (e.g. current_dist_name should be handled as DistStateDict attributes)"""
    name_id: str
    name_variants: List[str]
    seat_name_variants: Optional[List[str]] = None # Optional
    states: List[UnitState]
    changes: Optional[List] = []

    @model_validator(mode="after")
    def check_unit_name_in_variants(self) -> "Unit":
        if self.name_id not in self.name_variants:
            raise ValueError(f"name_id '{self.name_id}' must be in name_variants {self.name_variants}")
        return self
    
    def find_state_by_date(self, date: datetime) -> Optional[UnitState]:
        for unit_state in self.states:
            if unit_state.timespan and unit_state.timespan.contains(date):
                return unit_state
        return None  # Return None if no match is found
    
    def find_state_by_timespan(self, timespan: TimeSpan) -> Optional[UnitState]:
        for unit_state in self.states:
            if unit_state.timespan:
                # Compare start and end dates directly
                if unit_state.timespan.start == timespan.start and unit_state.timespan.end == timespan.end:
                    return unit_state
        return None  # Return None if no matching timespan is found
    
    def create_next_state(self, date):
        """
        Copies the state with a timespan encompassing the date passed in 'date' argument,
        sets the state end to date and the new state start to 'date', appends the new state
        to the states list, sorts it according to timespan, and returns a copy of the state
        with timespan starting with 'date'.
        """
        last_state = self.find_state_by_date(date)
        new_state = deepcopy(last_state)
        last_state.timespan.end = date
        new_state.timespan.start = date
        self.states.append(new_state)
        self.states.sort(key=lambda state: state.timespan.start)
        return new_state
    
    def abolish(self, date):
        """
        Finds a timespan encompassing the date passed as argument and sets its end to the passed date.
        It is possible that there are states with timespans starting after the abolishment - if the unit
        was reestablished.
        """
        last_state = self.find_state_by_date(date)
        last_state.timespan.end = date


class UnitRegistry(BaseModel):
    unit_list: List[Unit]

    def find_unit(self, unit_name: str) -> Optional[Unit]:
        for unit in self.unit_list:
            if unit_name in unit.name_variants:
                return unit
        return None
    
    def find_unit_state_by_date(self, unit_name: str, date: datetime) -> Tuple[Unit, TimeSpan]:
        """
        Returns Unit, UnitState and (unitstate) TimeSpan objects for the given unit name and date.
        """
        unit = self.find_unit(unit_name)
        unit_state = unit.find_state_by_date(date)
        timespan = unit_state.timespan
        return unit, unit_state, timespan
    
    def create_next_unit_state(self, unit_name: str, date: datetime) -> UnitState:
        unit = self.find_unit_state_by_date(unit_name, date)
        return unit.create_next_state(date)
    
#############################################################################################
# Hierarchy of models to store districts states: DistrictState ∈ District ∈ DistrictRegistry

class DistState(UnitState):
    current_dist_type: Literal["w", "m"]
    current_territory: None

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

    def add_unit(self, district_data: dict):
        district = District(**district_data)
        if not isinstance(district, District):
            raise TypeError("Only District instances can be added.")
        self.unit_list.append(district)
        return district

#############################################################################################
# Hierarchy of models to store Region states: RegionState ∈ Region ∈ RegionRegistry

class RegionState(UnitState):
    """
    State of a region.
    """

class Region(Unit):
    is_poland: bool
    states: List[RegionState]

class RegionRegistry(UnitRegistry):
    unit_list: List[Region]

    def add_unit(self, region_data: dict):
        region = Region(**region_data)
        if not isinstance(region, Region):
            raise TypeError("Only Region instances can be added.")
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