from pydantic import BaseModel, model_validator, Field
from typing import Union, Optional, Literal, List, Dict, Annotated, Any
from abc import ABC, abstractmethod
from datetime import datetime

from adm_timespan import *
from adm_unit import *
from adm_state import *

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
        
    def apply(self, change, adm_state, region_registry, dist_registry):
        # In the current version of the toolkit it is assumed that the OneToMany change
        # describes ONLY exchange of territories between administrative units.
        # It is however very easy to extend the toolkit to work with exchange of other
        # administrative unit stock variables - above all this method has to be rewritten.
        
        address_from = self.take_from
        address_to = self.take_to
        address_content = adm_state.pop_address(address_from)
        adm_state.add_address(address_to, address_content)
        if len(self.take_from)==2:
            unit = region_registry.find_unit(address_from[1])
        else:
            unit = dist_registry.find_unit(address_from[2])
        unit.changes.append(("adm_affiliation", change))
        change.unit_affected.append(("adm_affiliation", unit))
        return
    
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
