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

class TimeSpanRegistry(BaseModel):
    """
    A model to store all periods between two sequential administrative changes.
    """
    registry = List[TimeSpan]

#############################################################################################
# Hierarchy of models to store district states: DistrictState ∈ District ∈ DistrictRegistry

class DistState(BaseModel):
    current_dist_name: str
    current_seat_name: str
    current_dist_type: Literal["w", "m"]

    # timespan: Defined during initialization as the global timespan.
    # Timespan end will be set to the date of application of the first administrative change for the district.
    timespan: Optional[TimeSpan] = None

class District(BaseModel):
    """
    Represents one district. The attributes of this class describe district attributes that don't change through time (e.g. dist_name_variants).
    Attributes that do change through time (e.g. current_dist_name should be handled as DistStateDict attributes)"""
    dist_name_id: str
    dist_name_variants: List[str]
    seat_name_variants: List[str]
    states: List[DistState]

    @model_validator(mode="after")
    def check_dist_name_in_variants(self) -> "District":
        if self.dist_name_id not in self.dist_name_variants:
            raise ValueError(f"dist_name_id '{self.dist_name_id}' must be in dist_name_variants {self.dist_name_variants}")
        return self

class DistrictRegistry(BaseModel):
    dist_list: List[District]

#############################################################################################
# Hierarchy of models to store Region states: RegionState ∈ Region ∈ RegionRegistry

class RegionState(BaseModel):
    region_name: str
    timespan: Optional[TimeSpan] = None

class Region(BaseModel):
    region_name_id: str
    region_name_variants: List[str]
    is_poland: bool
    states: List[RegionState]

    @model_validator(mode="after")
    def check_region_name_in_variants(self) -> "Region":
        if self.region_name_id not in self.region_name_variants:
            raise ValueError(f"region_name_id '{self.region_name_id}' must be in region_name_variants {self.region_name_variants}")
        return self

class RegionRegistry(BaseModel):
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