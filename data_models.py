from pydantic import BaseModel, model_validator, Field
from typing import Union, Optional, Literal, List, Dict, Annotated, Any

from datetime import datetime

################################## Change models ##################################

# RCreate data model
# RCreate represents the creation of a new administrative region.

class RCreateMatterTakeFrom(BaseModel):
    region: str
    region_name: str

class RCreateMatter(BaseModel):
    take_from: List[RCreateMatterTakeFrom]
    take_to: Dict[str, Any]

    @model_validator(mode="before")
    @classmethod
    def ensure_keys_and_name(cls, values):
        take_to = values.get("take_to", {})
        if "region_name" not in take_to:
            raise ValueError("`take_to` must contain a 'region_name' field.")

        return values

class RCreateEntry(BaseModel):
    change_type: Literal["RCreate"]
    date: str
    order: Optional[int] = None
    source: str
    description: str
    matter: RCreateMatter

# RReform data model
# RReform represents the change of region attributes.

class RReformMatter(BaseModel):
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

        if "region_name" not in to_reform:
            raise ValueError("`to_reform` must contain a 'region_name' field.")

        return values

class RReformEntry(BaseModel):
    change_type: Literal["RReform"]
    date: str
    order: Optional[int] = None
    source: str
    description: str
    matter: RReformMatter

# RChange data model

class RChangeMatterFromInfo(BaseModel):
    region: str
    district_name: str

class RChangeMatter(BaseModel):
    take_from: RChangeMatterFromInfo
    take_to: str

class RChangeEntry(BaseModel):
    change_type: Literal["RChange"]
    date: str
    order: Optional[int] = None
    source: str
    description: str
    matter: RChangeMatter

# OneToMany model

class DOneToManyMatterTakeFrom(BaseModel):
    region: str
    district_name: str
    delete_district: bool

class DOneToManyMatterTakeTo(BaseModel):
    create: bool
    region: str
    district_name: str
    weight_from: Optional[float] = None
    weight_to: Optional[float] = None

class DOneToManyMatter(BaseModel):
    take_from: DOneToManyMatterTakeFrom
    take_to: List[DOneToManyMatterTakeTo]

class DOneToManyEntry(BaseModel):
    change_type: Literal["DOneToMany"]
    date: str
    order: Optional[int] = None
    source: str
    description: str
    matter: DOneToManyMatter

# DManyToOne model

class ManyToOneMatterTakeFrom(BaseModel):
    region: str
    district_name: str
    weight_from: Optional[float] = None
    weight_to: Optional[float] = None
    delete_district: bool


class ManyToOneMatterTakeTo(BaseModel):
    """
    Required:
        create, region, and district_name
    Required only if create = true:
        district_type and seat
    Optional:
        alternative names and alternative_seat_names (lists of strings) (info on the created district)
    """
    create: bool
    region: str
    district_name: str
    district_type: Optional[str] = None
    seat: Optional[str] = None
    alternative_names: Optional[List[str]] = None
    alternative_seat_names: Optional[List[str]] = None

    @model_validator(mode="after")
    def validate_create_fields(self):
        if self.create:
            missing = []
            if not self.district_type:
                missing.append("district_type")
            if not self.seat:
                missing.append("seat")
            if missing:
                raise ValueError(f"Fields {', '.join(missing)} are required when 'create' is True.")
        return self


class ManyToOneMatter(BaseModel):
    take_from: List[ManyToOneMatterTakeFrom]
    take_to: ManyToOneMatterTakeTo


class DManyToOneEntry(BaseModel):
    change_type: Literal["DManyToOne"]
    date: str
    order: Optional[int] = None
    source: str
    description: str
    matter: ManyToOneMatter

# Create combined change entry using a discriminated union.
ChangeEntry = Annotated[
    Union[RChangeEntry, DOneToManyEntry, DManyToOneEntry, RReformEntry, RCreateEntry],
    Field(discriminator="change_type")
]


#####################################################################################
# Data models for states of administrative units and their current mutual relations #
#####################################################################################


#############################
# Models to store timespans #

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

class RegionDistricts(BaseModel):
    region_name: str
    districts: List[str]

class AdminitrativeState(BaseModel):
    timespan = Optional[TimeSpan] = None
    regions: List[RegionDistricts]

################################## DistrictEventLog model ##################################

class DistrictEvent(BaseModel):
    """ Represents the log of a change from the perspective of a district """
    district_name: str
    date: datetime
    event_type: str  # e.g. "created", "abolished", "moved", etc.
    change_ref: Optional['Change'] = None  # optional reference to the actual change

class DistrictEventLog(BaseModel):
    log: List[DistrictEvent]