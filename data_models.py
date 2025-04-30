from pydantic import BaseModel, model_validator, Field
from typing import Union, Optional, Literal, List, Dict, Annotated, Any, Tuple
from abc import ABC, abstractmethod
from copy import deepcopy

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
    def echo(self, date, source) -> str:
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
    current_name = str
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
    
    def echo(self, date, source, lang = "pol"):
        if lang == "pol":
            if self.unit_type == "Region": jednostka = "województwa"
            else: jednostka = "powiatu"
            print(f"{date} dokonano reformy {jednostka} {self.current_name}. Przed reformą: {self.to_reform.items()} vs po reformie: {self.after_reform.items()} ({source}).")
        elif lang == "eng":
            print(f"{date} the {self.unit_type.lower()} {self.current_name} was reformed. Before the reform: {self.to_reform.items()} vs after the reform: {self.after_reform.items()} ({source}).")
        else:
            raise ValueError("Wrong value for the lang parameter.")
        
    def apply(self, change, adm_state, region_registry, dist_registry):
        if(self.unit_type=="Region"):
            unit = region_registry.find_unit(self.current_name)
        else:
            unit = dist_registry.find_unit(self.current_name)
        new_state = region_registry.create_next_unit_state(change.date)
        for key, value in self.to_reform:
            if not hasattr(new_state, key):
                raise ValueError(f"Change ({change.date}, {self}) applied to {self.unit_type.lower()} attribute that doesn't exist.")
            if new_state.key != value:
                raise ValueError(
                    f"Change on {change.date} ({self}) expects the {self.unit_type.lower()} to have key '{value}', "
                    f"but found '{new_state.key}' instead."
                )
            new_state.key = self.after_reform.key
        unit.changes.append(("reform", change))
        change.units_affected.append(("reform", unit))
        return
    
    def __repr__(self):
        return f"<UnitReform ({self.unit_type}:{self.current_name}) attributes {', '.join(self.to_reform.keys())}>"
    
# Definition of the data model for the matter of OneToMany change.
    
class OneToManyTakeFrom(BaseModel):
    current_name: str
    delete_unit: bool

class OneToManyTakeTo(BaseModel):
    create: bool
    current_name: str
    weight_from: Optional[float] = None
    weight_to: Optional[float] = None
    district: Optional[District] = None

    @model_validator(mode="after")
    def validate_create_fields(self):
        if self.create:
            if not self.district:
                raise ValueError(f"A dict coherent with District data model must be passed as 'district' attribute when 'create' is True.")
        else:
            if not self.current_name:
                raise ValueError(f"A string must be passed as 'name_id' attribute when 'create' is False.")
        return self
    
class OneToMany(BaseChangeMatter):
    change_type = Literal["OneToMany"]
    unit_attribute = str # Defines what is transfered between units. In the toolkit, only "territory" on the district level is implemented.
    unit_type = Literal["Region", "District"] # The change happens on one "level" i.e. can be only an exchange between regions OR between districts, not between regions AND districts.
    take_from: OneToManyTakeFrom
    take_to: List[OneToManyTakeTo]

    def echo(self, date, source, lang = "pol"):
        destination_districts = ", ".join([f"{destination.current_name}" for destination in self.take_to])
        if lang == "pol":
            if self.take_from.delete_unit:
                if self.unit_type == "District":
                    if len(self.take_to)>1: z_jednostki = "powiatów:"
                    else: z_jednostki = "powiatu"
                    do_jednostki = "powiat"
                else:
                    raise ValueError("Method 'echo' of class 'OneToMany' is only implemented for self.unit_type='District'.")
                print(f"{date} zniesiono {do_jednostki} {self.take_from.current_name}, a jego terytorium włączono do {z_jednostki} {destination_districts} ({source}).")
            else:
                print(f"{date} fragment terytorium {do_jednostki}u {self.takie_from.current_name} włączono do {z_jednostki} {destination_districts} ({source}).")
        elif lang == "eng":
            if self.take_from.delete_unit:
                if len(self.take_to)>1: s = "s:"
                else: s = ""
                print(f"{date} the district {self.take_from.current_name} was abolished and its territory was integrated into the district{s} {destination_districts} ({source}).")
            else:
                print(f"{date} part of the territory of the district {self.take_from.current_name} was integrated into the district{s} {destination_districts} ({source}).")
        else:
            raise ValueError("Wrong value for the lang parameter.")
        
    def apply(self, change, adm_state, region_registry, dist_registry):
        # In the current version of the toolkit it is assumed that the OneToMany change
        # describes ONLY exchange of territories between administrative units.
        # It is however very easy to extend the toolkit to work with exchange of other
        # administrative unit stock variables - above all this method has to be rewritten.
        units_to = []
        units_to_names = [unit.current_name for unit in self.take_to]
        units_new_states = []
        if(self.unit_type=="Region"):
            raise ValueError(f"Method OneToMany not implemented for regions.")
        unit_from = dist_registry.find_unit(self.take_from.current_name)
        if self.take_from.delete_unit:
            unit_from.abolish(change.date)
            unit_from.changes.append(("abolished", change))
            change.units_affected.append(("abolished", unit_from))
        else:
            units_new_states.append(unit_from.create_next_state(change.date))
            unit_from.changes.append(("territory", change))
            change.units_affected.append(("territory", unit_from))
        for take_to_dict in units_to_names:
            if take_to_dict.create:
                unit = dist_registry.add_unit(take_to_dict.district)
                unit_state = unit.states[0]
                unit_state.timespan = TimeSpan(**{"start": change.date, "end": config.global_timespan.end})
                units_new_states.append(unit_state)
                unit.changes.append(("created", change)) # 'created' changed is always a 'territory' change - districts can only be created by giving them some territory.
                change.units_affected.append(("created", unit))
            else:
                unit = dist_registry.find_unit(take_to_dict.current_name)
                units_new_states.append(unit.create_next_state(change.date))
                unit.changes.append(("territory", change))
                change.units_affected.append(("territory", unit))
        for state in units_new_states:
            state.territory = None # Territorial change to implement later
        return
    
    def __repr__(self):
        names_to = ', '.join(
                                d.current_name if hasattr(d, 'current_name') else d.district.states[0].current_name
                                for d in self.take_to
                            )
        return f"<OneToMany: {self.take_from.current_name} → {names_to}>"

# Definition of the data model for the matter of ManyToOne change.

class ManyToOneTakeFrom(BaseModel):
    current_name: str
    weight_from: Optional[float] = None
    weight_to: Optional[float] = None
    delete_unit: bool

class ManyToOneTakeTo(BaseModel):
    create: bool
    current_name: Optional[str] = None
    district: Optional[District] = None

    @model_validator(mode="after")
    def validate_create_fields(self):
        if self.create:
            if not self.district:
                raise ValueError(f"A dict coherent with District data model must be passed as 'district' attribute when 'create' is True.")
        else:
            if not self.current_name:
                raise ValueError(f"A string must be passed as 'name_id' attribute when 'create' is False.")
        return self

class ManyToOne(BaseModel):
    change_type: Literal["ManyToOne"]
    unit_attribute = str # Defines what is transfered between units. In the toolkit, only "territory" on the district level is implemented.
    unit_type = Literal["Region", "District"]
    take_from: List[ManyToOneTakeFrom]
    take_to: ManyToOneTakeTo

    def echo(self, date, source, lang = "pol"):
        origin_districts_partial = ", ".join([f"{origin.current_name}" for origin in self.take_from if not origin.delete_unit])
        origin_districts_whole = ", ".join([f"{origin.current_name}" for origin in self.take_from if origin.delete_unit])
        if lang == "pol":
            if self.unit_type != "District":
                raise ValueError("Method 'echo' of class 'ManyToOne' is only implemented for self.unit_type='District'.")
            z_cz_jednostki = ""
            z_calej_jednostki = ""
            oraz = ""
            if len(origin_districts_partial) >= 1:
                if len(origin_districts_partial) >=2:
                    if self.take_to.create:
                        z_cz_jednostki = f"z części powiatów {origin_districts_partial} "
                    else:
                        z_cz_jednostki = f"części powiatów {origin_districts_partial} "
                else:
                    if self.take_to.create:
                        z_cz_jednostki = f"z części powiatu {origin_districts_partial} "
                    else:
                        z_cz_jednostki = f"część powiatu {origin_districts_partial} "
            if len(origin_districts_whole) >= 1:
                if len(origin_districts_whole) >= 2:
                    if self.take_to.create:
                        z_calej_jednostki = f"z całego terytorium powiatów {origin_districts_whole} "
                    else:
                        z_calej_jednostki = f"całe terytorium powiatów {origin_districts_whole} "
                else:
                    if self.take_to.create:
                        z_calej_jednostki = f"z całego terytorium powiatu {origin_districts_whole} "
                    else:
                        z_calej_jednostki = f"całe terytorium powiatu {origin_districts_whole} "
            if len(origin_districts_whole)>0 and len(origin_districts_partial)>0:
                oraz = "oraz "
            if self.take_to.create:
                print(f"{date} {z_cz_jednostki}{oraz}{z_calej_jednostki} utworzono powiat {self.take_to.current_name} ({source})")
            else:
                print(f"{date} {z_cz_jednostki}{oraz}{z_calej_jednostki} włączono do powiatu {self.take_to.current_name} ({source})")
        elif lang == "eng":
            if lang == "eng":
                if self.unit_type != "District":
                    raise ValueError("Method 'echo' of class 'ManyToOne' is only implemented for self.unit_type='District'.")
                from_partial_unit = ""
                from_whole_unit = ""
                and_word = ""
                were_or_was = "were"
                if len(origin_districts_partial) >= 1:
                    if len(origin_districts_partial) >= 2:
                        if self.take_to.create:
                            from_partial_unit = f"from parts of the districts {origin_districts_partial} "
                        else:
                            from_partial_unit = f"parts of the districts {origin_districts_partial} "
                    else:
                        if self.take_to.create:
                            from_partial_unit = f"from part of the district {origin_districts_partial} "
                        else:
                            from_partial_unit = f"part of the district {origin_districts_partial} "
                            if len(origin_districts_whole)==0:
                                were_or_was = "was"
                else:
                    were_or_was = "was"
                if len(origin_districts_whole) >= 1:
                    if len(origin_districts_whole) >= 2:
                        if self.take_to.create:
                            from_whole_unit = f"from the entire territory of the districts {origin_districts_whole} "
                        else:
                            from_whole_unit = f"the entire territory of the districts {origin_districts_whole} "
                    else:
                        if self.take_to.create:
                            from_whole_unit = f"from the entire territory of the district {origin_districts_whole} "
                        else:
                            from_whole_unit = f"the entire territory of the district {origin_districts_whole} "
                if len(origin_districts_whole) > 0 and len(origin_districts_partial) > 0:
                    and_word = "and "
                if self.take_to.create:
                    print(f"{date} {from_partial_unit}{and_word}{from_whole_unit}the district {self.take_to.current_name} was created ({source})")
                else:
                    print(f"{date} {from_partial_unit}{and_word}{from_whole_unit}{were_or_was} merged into the district {self.take_to.current_name} ({source})")
        else:
            raise ValueError("Wrong value for the lang parameter.")

    def apply(self, change, adm_state, region_registry, dist_registry):
        # In the current version of the toolkit it is assumed that the OneToMany change
        # describes ONLY exchange of territories between administrative units.
        # It is however very easy to extend the toolkit to work with exchange of other
        # administrative unit stock variables - above all this method has to be rewritten.
        units_from = []
        units_from_names = [unit.current_name for unit in self.take_from]
        units_new_states = []
        if(self.unit_type=="Region"):
            raise ValueError(f"Method OneToMany not implemented for regions.")
        for unit_dict in self.take_from:
            unit = dist_registry.find_unit(unit_dict.current_name)
            if unit_dict.delete_unit:
                unit.abolish(change.date)
                unit.changes.append(("abolished", change))
                change.units_affected.append(("abolished", unit))
            else:
                units_new_states.append(unit)
                unit.changes.append(("territory", change))
                change.units_affected.append(("territory", unit))

        if self.take_to.create:
            unit_to = dist_registry.add_unit(self.take_to.district)
            unit_to_state = unit_to.states[0]
            unit_to_state.timespan = TimeSpan(**{"start": change.date, "end": config.global_timespan.end})
            units_new_states.append(unit_to_state)
            unit_to.changes.append(("created", change)) # 'created' changed is always a 'territory' change - districts can only be created by giving them some territory.
            change.units_affected.append(("created", unit_to))
        else:
            unit_to = dist_registry.find_unit(self.take_to.current_name)
            units_new_states.append(unit_to.create_next_state(change.date))
            unit_to.changes.append(("territory", change))
            change.units_affected.append(("territory", unit_to))

        for state in units_new_states:
            state.territory = None # Territorial change to implement later
        return
        
    def __repr__(self):
        return f"<ManyToOne: {', '.join(d.current_name for d in self.take_from)} → {self.take_to.current_name}>"

# Definition of the data model for the matter of ChangeAdmState change.

DistAddress = Tuple[Literal["Poland", "Abroad"], str]              # For regions"
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

    @model_validator("take_to")
    def validate_matching_address_type(cls, take_to, values):
        take_from = values.get("take_from")
        if take_from and len(take_from) != len(take_to):
            raise ValueError(
                f"'take_from' and 'take_to' must be the same length: "
                f"got {len(take_from)} and {len(take_to)}"
            )
        return take_to
    
    def echo(self, date, source, lang = "pol"):
        if lang == "pol":
            if len(self.take_from) == 2:
                z_kraj, z_woj = self.take_from
                z_adres = z_woj
                if z_kraj=="Abroad":
                    do_adres = "Polski"
                    jednostka = "region"
            else:
                z_kraj, z_woj, z_powiat = self.take_from
                do_kraj, do_woj, do_powiat = self.take_to
                jednostka = "powiat"
                if(z_kraj=="POLAND"):
                    z_adres = z_powiat
                    do_adres = f"województwa {do_woj}"
                else:
                    z_adres = f"{z_powiat} ({z_woj})"
                    do_adres = f"Polski (woj. {do_woj})"
            print(f"Od {date} {jednostka} {': '.join(self.take_from)} należał do {': '.join(self.take_to[:-1])}")
        elif lang == "eng":
            print(f"From {date} on, the district {self.take_from[-1]} belonged to {": ".join(self.take_to[:-1])} ({source}).")
        else:
            raise ValueError("Wrong value for the lang parameter.")
    
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
    units_affected: Optional[List[Unit]] = None

    def echo(self) -> str:
        return self.matter.echo(self.date, self.source)

    def districts_involved(self) -> list[str]:
        return self.matter.districts_involved()

    def apply(self, adm_state: AdminitrativeState, region_registry: RegionRegistry, dist_registry: DistrictRegistry) -> None:
        self.matter.apply(self, adm_state, region_registry, dist_registry)