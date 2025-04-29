from pydantic import BaseModel, model_validator, Field
from typing import Union, Optional, Literal, List, Dict, Annotated, Any, Tuple
from abc import ABC, abstractmethod

from datetime import datetime

#############################
# Models to store timespans #
#############################

class TimeSpan(BaseModel):
    start: datetime
    end: datetime

    def contains(self, date: datetime) -> bool:
        """Check if a date is within the timespan."""
        return self.start <= date <= self.end

class TimeSpanRegistry(BaseModel):
    """
    A model to store all periods between two sequential administrative changes.
    """
    registry = List[TimeSpan]
    
#####################################################################################
# Data models for states of administrative units and their current mutual relations #
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

class UnitRegistry(BaseModel):
    unit_list: List[Unit]

    def find_unit(self, unit_name: str) -> Optional[Unit]:
        for unit in self.unit_list:
            if unit_name in unit.name_variants:
                return unit
        return None
    
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
    region_list: List[Region]

#############################################################################################
# Models to store information about current region-districts relations.
# AdministrativeState is a list of (region name, list of districts) pairs.

class AdminitrativeState(BaseModel):
    timespan = Optional[TimeSpan] = None
    unit_hierarchy: List[Dict[List]]

################################## DistrictEventLog model ##################################

class DistrictEvent(BaseModel):
    """ Represents the log of a change from the perspective of a district """
    district_name: str
    date: datetime
    event_type: str  # e.g. "created", "abolished", "moved", etc.
    change_ref: Optional['Change'] = None  # optional reference to the actual change

class DistrictEventLog(BaseModel):
    log: List[DistrictEvent]



#####################################################################################
#                            Data models for changes                                #
#####################################################################################

class BaseChangeMatter(BaseModel, ABC):
    change_type: str

    @abstractmethod
    def echo(self) -> str:
        pass

    @abstractmethod
    def districts_involved(self) -> list[str]:
        pass

    @abstractmethod
    def apply(self, adm_state: AdminitrativeState, region_registry: RegionRegistry, dist_registry: DistrictRegistry) -> None:
        pass

# Definition of the data model for the matter of UnitReform change.

class UnitReform(BaseChangeMatter):
    change_type = Literal["UnitReform"]
    unit_type = Literal["Region", "District"]
    unit_name_id = str
    to_reform: Dict[str, Any]
    after_reform: Dict[str, Any]

    @model_validator(mode="before")
    @classmethod
    def ensure_keys_and_name(cls, values):
        to_reform = values.get("to_reform", {})
        after_reform = values.get("after_reform", {})

        if not isinstance(to_reform, dict) or not isinstance(after_reform, dict):
            raise TypeError("Both 'to_reform' and 'after_reform' must be dictionaries")

        if set(to_reform.keys()) != set(after_reform.keys()):
            raise ValueError(
                f"`to_reform` and `after_reform` must have the same keys. Got {set(to_reform.keys())} vs {set(after_reform.keys())}"
            )

        return values
    
# Definition of the data model for the matter of OneToMany change.
    
class OneToManyTakeFrom(BaseModel):
    name_id: str
    delete_unit: bool

class OneToManyTakeTo(BaseModel):
    create: bool
    name_id: str
    weight_from: Optional[float] = None
    weight_to: Optional[float] = None
    
class OneToMany(BaseChangeMatter):
    change_type = Literal["OneToMany"]
    unit_attribute = str # Defines what is transfered between units. In the toolkit, only "territory" on the district level is implemented.
    unit_type = Literal["Region", "District"] # The change happens on one "level" i.e. can be only an exchange between regions OR between districts, not between regions AND districts.
    take_from: OneToManyTakeFrom
    take_to: List[OneToManyTakeTo]

# Definition of the data model for the matter of ManyToOne change.

class ManyToOneTakeFrom(BaseModel):
    name_id: str
    weight_from: Optional[float] = None
    weight_to: Optional[float] = None
    delete_unit: bool


class ManyToOneTakeTo(BaseModel):
    create: bool
    name_id: Optional[str] = None
    district: Optional[District] = None

    @model_validator(mode="after")
    def validate_create_fields(self):
        if self.create:
            if not self.district:
                raise ValueError(f"A dict coherent with District data model must be passed as 'district' attribute when 'create' is True.")
        else:
            if not self.name_id:
                raise ValueError(f"A string must be passed as 'name_id' attribute when 'create' is False.")
        return self

class ManyToOne(BaseModel):
    change_type: Literal["ManyToOne"]
    unit_attribute = str # Defines what is transfered between units. In the toolkit, only "territory" on the district level is implemented.
    unit_type = Literal["Region", "District"]
    take_from: List[ManyToOneTakeFrom]
    take_to: ManyToOneTakeTo

# Definition of the data model for the matter of ChangeAdmState change.

DistAddress = Tuple[Literal["Poland", "Abroad"], str]              # For regions
RegionAddress = Tuple[Literal["Poland", "Abroad"], str, str]         # For districts
Address = Union[DistAddress, RegionAddress]

class ChangeAdmState(BaseChangeMatter):
    """
    Represents a change in administrative structure involving movement of either:
    - a **region** (described by a 2-tuple address: (Poland/Abroad, region_name_id)), or
    - a **district** (described by a 3-tuple address: (Poland/Abroad, region_name_id, district_name_id)).

    Both `take_from` and `take_to` must be of the same structure (i.e., both 2-tuples or both 3-tuples).
    """
    change_type: Literal["ChangeAdmState"]
    take_from: Address
    take_to: Address

    @field_validator("take_to")
    def validate_matching_address_type(cls, take_to, values):
        take_from = values.get("take_from")
        if take_from and len(take_from) != len(take_to):
            raise ValueError(
                f"'take_from' and 'take_to' must be the same length: "
                f"got {len(take_from)} and {len(take_to)}"
            )
        return take_to
    
###############################################################
# Definition of the base Change data model

# Create combined change entry using a discriminated union.
ChangeMatter = Annotated[
    Union[UnitReform, OneToMany, ManyToOne, ChangeAdmState],
    Field(discriminator="change_type")
]

class Change(BaseModel):
    date: datetime
    source: str
    description: str
    order: int
    matter: ChangeMatter

    def echo(self) -> str:
        return self.matter.echo()

    def districts_involved(self) -> list[str]:
        return self.matter.districts_involved()

    def apply(self, adm_state: AdminitrativeState, region_registry: RegionRegistry, dist_registry: DistrictRegistry) -> None:
        self.matter.apply(adm_state, region_registry, dist_registry)