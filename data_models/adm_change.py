from pydantic import BaseModel, model_validator, field_validator, Field
from typing import Union, Optional, Literal, List, Dict, Annotated, Any
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from data_models.adm_timespan import *
from data_models.adm_unit import *
from data_models.adm_state import *
from utils.helper_functions import load_config
from utils.exceptions import ConsistencyError

# Load the configuration
config = load_config("config.json")

#####################################################################################
#                            Data models for changes                                #
#####################################################################################

class BaseChangeMatter(BaseModel, ABC):

    @abstractmethod
    def echo(self, date, source) -> str:
        pass

    @abstractmethod
    def districts_involved(self) -> list[str]:
        pass

    @abstractmethod
    def apply(self, adm_state: AdministrativeState, region_registry: RegionRegistry, dist_registry: DistrictRegistry) -> None:
        pass

    @abstractmethod
    def fill_units_affected_current_names(self):
        pass

# Definition of the data model for the matter of UnitReform change.

class UnitReform(BaseChangeMatter):
    change_type: Literal["UnitReform"]
    unit_type: Literal["Region", "District"]
    current_name: str
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
        
    def fill_units_affected_current_names(self) -> Dict[Literal["Region", "District"], Dict[Literal["before", "after"], List[str]]]:
        if "current_name" in self.after_reform.keys():
            after = self.after_reform["current_name"]
        else:
            after = self.current_name
        return {
            self.unit_type: {
                "before": [self.current_name],
                "after": [after]
            }
        }
    
    def verify_and_standardize_all_addresses(self, change, adm_state, region_registry, dist_registry):
        """No address used as input in this change type. Return."""
        return
    
    def verify_att_to_reform(self, change, adm_state, region_registry, dist_registry):
        if self.unit_type == "Region":
            _, unit_state, _ = region_registry.find_unit_state_by_date(self.current_name, change.date)
        else:
            _, unit_state, _ = dist_registry.find_unit_state_by_date(self.current_name, change.date)
        for key, value in self.to_reform.items():
            if not hasattr(unit_state, key):
                raise ConsistencyError(f"Change {str(change)} applied to attribute {key} of state of {self.unit_type} {self.current_name}, but the attribute doesn't exist.")
            if getattr(unit_state, key) != value:
                raise ConsistencyError(
                    f"Change {str(change)} expects the {self.unit_type.lower()} {self.current_name} state to have key '{value}', "
                    f"but found '{getattr(unit_state, key)}' instead."
                )
    
    def echo(self, date, source, lang = "pol"):
        if lang == "pol":
            if self.unit_type == "Region": jednostka = "województwa"
            else: jednostka = "powiatu"
            print(f"{date.date()} dokonano reformy {jednostka} {self.current_name}. Przed reformą: {self.to_reform.items()} vs po reformie: {self.after_reform.items()} ({source}).")
        elif lang == "eng":
            print(f"{date.date()} {self.unit_type.lower()} {self.current_name} was reformed. Before the reform: {self.to_reform.items()} vs after the reform: {self.after_reform.items()} ({source}).")
        else:
            raise ValueError("Wrong value for the lang parameter.")
        
    def apply(self, change, adm_state, region_registry, dist_registry):
        if(self.unit_type=="Region"):
            unit = region_registry.find_unit(self.current_name)
        else:
            unit = dist_registry.find_unit(self.current_name)
        if unit is None:
            raise ValueError(f"Change ({change.date.date()}, {str(self)}) applied to the unit {self.current_name} that doesn't exist in the registry")
        # Create a new unit state
        new_state = change.create_next_state(unit)

        for key, value in self.to_reform.items():
            if not hasattr(new_state, key):
                raise ValueError(f"Change ({change.date}, {str(self)}) applied to {self.unit_type.lower()} attribute that doesn't exist. Current {self.unit_type.lower()} state: {new_state}")
            if getattr(new_state, key) != value:
                raise ValueError(
                    f"Change on {change.date} ({self}) expects the {self.unit_type.lower()} to have key '{value}', "
                    f"but found '{getattr(new_state, key)}' instead."
                )
            setattr(new_state, key, self.after_reform[key])
        unit.changes.append(("reform", change))
        change.units_affected[self.unit_type].append(("reform", unit))
        return
    
    def __repr__(self):
        return f"<UnitReform ({self.unit_type}:{self.current_name}) attributes {', '.join(self.to_reform.keys())}>"
    
    def districts_involved(self) -> list[str]:
        pass
    
# Definition of the data model for the matter of OneToMany change.
    
class OneToManyTakeFrom(BaseModel):
    current_name: str
    delete_unit: bool

class OneToManyTakeTo(BaseModel):
    create: bool
    current_name: Optional[str] = None
    weight_from: Optional[float] = None
    weight_to: Optional[float] = None
    district: Optional[District] = None
    new_district_address: Optional[DistAddress] = None

    @model_validator(mode="after")
    def validate_create_fields(self):
        if self.create:
            if not self.district:
                raise ValueError(f"A dict coherent with District data model must be passed as 'district' attribute when 'create' is True.")
            if not self.new_district_address:
                raise ValueError(f"The address of the new district must be passed as 'new_district_address' attribute when 'create' is True.")
        else:
            if not self.current_name:
                raise ValueError(f"A string must be passed as 'name_id' attribute when 'create' is False.")
        
        return self
    
class OneToMany(BaseChangeMatter):
    change_type: Literal["OneToMany"]
    unit_attribute: str # Defines what is transfered between units. In the toolkit, only "territory" on the district level is implemented.
    unit_type: Literal["Region", "District"] # The change happens on one "level" i.e. can be only an exchange between regions OR between districts, not between regions AND districts.
    take_from: OneToManyTakeFrom
    take_to: List[OneToManyTakeTo]

    def fill_units_affected_current_names(self) -> Dict[Literal["Region", "District"], Dict[Literal["before", "after"], List[str]]]:
        unit_type = self.unit_type  # "District" or "Region"
        before_current_names = [self.take_from.current_name]
        after_current_names = []
        if not self.take_from.delete_unit:
            after_current_names.append(self.take_from.current_name)
        
        for take_to_dict in self.take_to:
            after_current_names.append(take_to_dict.current_name)
            if not take_to_dict.create:
                before_current_names.append(take_to_dict.current_name)

        return {
            unit_type: {
                "before": before_current_names,
                "after": after_current_names
            }
        }
    
    def verify_and_standardize_all_addresses(self, change, adm_state, region_registry, dist_registry):
        for take_to_dict in self.take_to:
            if take_to_dict.create:
                # Correct only country and region names, the new district is not yet created.
                new_address = take_to_dict.new_district_address
                c_name, r_name, d_name = new_address # Assuming address is of length 3
                c_name_new, r_name_new = adm_state.verify_and_standardize_address((c_name, r_name), region_registry, dist_registry, change.date)
                take_to_dict.new_district_address = (c_name_new, r_name_new, d_name)

    def verify_att_to_reform(self, change, adm_state, region_registry, dist_registry):
        """Doesn't apply to the change. Return."""
        return

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
        if(self.unit_type=="Region"):
            raise ValueError(f"Method OneToMany not implemented for regions.")
        
        unit_from = dist_registry.find_unit(self.take_from.current_name)

        if self.take_from.delete_unit:
            change.abolish(unit_from)
            unit_from.changes.append(("abolished", change))
            change.units_affected[self.unit_type].append(("abolished", unit_from))
            adm_state.find_and_pop(unit_from.name_id, self.unit_type)
        else:
            change.create_next_state(unit_from)
            unit_from.changes.append(("territory", change))
            change.units_affected[self.unit_type].append(("territory", unit_from))
        for take_to_dict in self.take_to:
            if take_to_dict.create:
                # Check if the unit existed in the past
                unit = dist_registry.find_unit(take_to_dict.district.name_id)
                if unit is not None:
                    unit_state = take_to_dict.district.states[0]
                    unit.states.append(unit_state)
                    print(f"New state {unit_state} appended to states of unit {unit.name_id}.")
                else:
                    unit = dist_registry.add_unit(take_to_dict.district)
                    unit_state = unit.states[0]
                unit_state.previous_change = change
                change.next_states.append(unit_state)
                adm_state.add_address(take_to_dict.new_district_address, {})
                unit_state.timespan = TimeSpan(**{"start": change.date, "end": config["global_timespan"]["end"]})
                unit.changes.append(("created", change)) # 'created' changed is always a 'territory' change - districts can only be created by giving them some territory.
                change.units_affected[self.unit_type].append(("created", unit))
            else:
                unit = dist_registry.find_unit(take_to_dict.current_name)
                if(unit is None):
                    raise ValueError(f"OneToMany change applied to district {take_to_dict.current_name} that doesn't exist in the registry with 'create'=False.")
                change.create_next_state(unit)
                unit.changes.append(("territory", change))
                change.units_affected[self.unit_type].append(("territory", unit))
        return
    
    def districts_involved(self) -> list[str]:
        pass
    
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
    new_district_address: Optional[DistAddress] = None

    @model_validator(mode="after")
    def validate_create_fields(self):
        if self.create:
            if not self.district:
                raise ValueError(f"A dict coherent with District data model must be passed as 'district' attribute when 'create' is True.")
            if not self.new_district_address:
                raise ValueError(f"The address of the new district must be passed as 'new_district_address' attribute when 'create' is True.")
        else:
            if not self.current_name:
                raise ValueError(f"A string must be passed as 'name_id' attribute when 'create' is False.")
        return self

class ManyToOne(BaseModel):
    change_type: Literal["ManyToOne"]
    unit_attribute: str # Defines what is transfered between units. In the toolkit, only "territory" on the district level is implemented.
    unit_type: Literal["Region", "District"]
    take_from: List[ManyToOneTakeFrom]
    take_to: ManyToOneTakeTo

    def fill_units_affected_current_names(self) -> Dict[Literal["Region", "District"], Dict[Literal["before", "after"], List[str]]]:
        unit_type = self.unit_type  # Should be "District" or "Region"
        before_current_names = [take_from_dict.current_name for take_from_dict in self.take_from]
        if not self.take_to.create:
            before_current_names.append(self.take_to.current_name)
        
        after_current_names = [self.take_to.current_name]
        for take_from_dict in self.take_from:
            if not take_from_dict.delete_unit:
                after_current_names.append(take_from_dict.current_name)

        return {
            unit_type: {
                "before": before_current_names,
                "after": after_current_names
            }
        }
    
    def verify_and_standardize_all_addresses(self, change, adm_state, region_registry, dist_registry):
        if self.take_to.create:
            # Correct only country and region names, the new district is not yet created.
            c_name, r_name, d_name = self.take_to.new_district_address # Assuming address is of length 3
            c_name_new, r_name_new = adm_state.verify_and_standardize_address((c_name, r_name), region_registry, dist_registry, change.date)
            self.take_to.new_district_address = (c_name_new, r_name_new, d_name)

    def verify_att_to_reform(self, change, adm_state, region_registry, dist_registry):
        """Doesn't apply to the change. Return."""
        return

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
        if(self.unit_type=="Region"):
            raise ValueError(f"Method OneToMany not implemented for regions.")
        for unit_dict in self.take_from:
            unit = dist_registry.find_unit(unit_dict.current_name)
            if unit_dict.delete_unit:
                change.abolish(unit)
                unit.changes.append(("abolished", change))
                change.units_affected[self.unit_type].append(("abolished", unit))
                adm_state.find_and_pop(unit.name_id, self.unit_type)
            else:
                change.create_next_state(unit)
                unit.changes.append(("territory", change))
                change.units_affected[self.unit_type].append(("territory", unit))

        if self.take_to.create:
            unit_to = dist_registry.find_unit(self.take_to.current_name)
            if unit_to is not None:
                unit_to_state = DistState(**self.take_to.district.states[0])
                unit_to.states.append(unit_to_state)
                print(f"New state {unit_to_state} appended to states of unit {unit.name_id}.")
            else:
                unit_to = dist_registry.add_unit(self.take_to.district)
                unit_to_state = unit_to.states[0]
            unit_to_state.previous_change = change
            change.next_states.append(unit_to_state)
            adm_state.add_address(self.take_to.new_district_address, {})
            unit_to_state.timespan = TimeSpan(**{"start": change.date, "end": config["global_timespan"]["end"]})
            unit_to.changes.append(("created", change)) # 'created' changed is always a 'territory' change - districts can only be created by giving them some territory.
            change.units_affected[self.unit_type].append(("created", unit_to))
        else:
            unit_to = dist_registry.find_unit(self.take_to.current_name)
            change.create_next_state(unit_to)
            unit_to.changes.append(("territory", change))
            change.units_affected[self.unit_type].append(("territory", unit_to))

        return
    
    def districts_involved(self) -> list[str]:
        pass
        
    def __repr__(self):
        return f"<ManyToOne: {', '.join(d.current_name for d in self.take_from)} → {self.take_to.current_name}>"

# Definition of the data model for the matter of ChangeAdmState change.

class ChangeAdmState(BaseChangeMatter):
    """
    Represents a change in administrative structure involving movement of either:
    - a **region** (described by a 2-tuple address: (HOMELAND/ABROAD, region_name_id)), or
    - a **district** (described by a 3-tuple address: (HOMELAND/ABROAD, region_name_id, district_name_id)).

    Both `take_from` and `take_to` must be of the same structure (i.e., both 2-tuples or both 3-tuples).
    """
    change_type: Literal["ChangeAdmState"]
    take_from: Address
    take_to: Address

    @model_validator(mode="after")
    def validate_matching_address_type(self):
        if len(self.take_from) != len(self.take_to):
            raise ValueError(
                f"'take_from' and 'take_to' must be the same length: "
                f"got {len(self.take_from)} and {len(self.take_to)}"
            )
        return self

    def fill_units_affected_current_names(self) -> Dict[Literal["Region", "District"], Dict[Literal["before", "after"], List[str]]]:
        affected: Dict[Literal["Region", "District"], Dict[Literal["before", "after"], List[str]]] = {
            "Region": {
                "before": [self.take_from[1]],
                "after": [self.take_to[1]],
            }
        }

        # If address is a district-level address (i.e., 3-tuple), include District-level info
        if len(self.take_from) == 3:
            affected["District"] = {
                "before": [self.take_from[2]],
                "after": [self.take_to[2]],
            }
        return affected
    
    def verify_and_standardize_all_addresses(self, change, adm_state, region_registry, dist_registry):
        self.take_from = adm_state.verify_and_standardize_address(self.take_from, region_registry, dist_registry, change.date)
        if len(self.take_to) == 3:
            c_name, r_name, d_name = self.take_to
            c_name_new, r_name_new = adm_state.verify_and_standardize_address((c_name, r_name), region_registry, dist_registry, change.date)
            self.take_to = (c_name_new, r_name_new, d_name)

    def verify_att_to_reform(self, change, adm_state, region_registry, dist_registry):
        """Doesn't apply to the change. Return."""
        return
    
    def echo(self, date, source, lang = "pol"):
        if lang == "pol":
            if len(self.take_from) == 2:
                z_kraj, z_woj = self.take_from
                z_adres = z_woj
                if z_kraj=="ABROAD":
                    do_adres = "Polski"
                    jednostka = "region"
            else:
                z_kraj, z_woj, z_powiat = self.take_from
                do_kraj, do_woj, do_powiat = self.take_to
                jednostka = "powiat"
                if(z_kraj=="HOMELAND"):
                    z_adres = z_powiat
                    do_adres = f"województwa {do_woj}"
                else:
                    z_adres = f"{z_powiat} ({z_woj})"
                    do_adres = f"Polski (woj. {do_woj})"
            print(f"Od {date} {jednostka} {': '.join(self.take_from)} należał do {': '.join(self.take_to[:-1])}")
        elif lang == "eng":
            print(f"From {date} on, the district {self.take_from[-1]} belonged to {': '.join(self.take_to[:-1])} ({source}).")
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
        region_from_affected = region_registry.find_unit(address_from[1])
        region_from_affected.changes.append(("adm_affiliation", change))
        change.units_affected["Region"].append(("adm_affiliation", region_from_affected))
        region_to_affected = region_registry.find_unit(address_to[1])
        region_to_affected.changes.append(("adm_affiliation", change))
        change.units_affected["Region"].append(("adm_affiliation", region_to_affected))
        if len(self.take_from)==3:
            district_affected = dist_registry.find_unit(address_to[2])
            district_affected.changes.append(("adm_affiliation", change))
            change.units_affected["District"].append(("adm_affiliation", district_affected))
        return
    
    def districts_involved(self) -> list[str]:
        pass
    
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
    order: Optional[int] = None
    matter: ChangeMatter
    units_affected: Optional[Dict[Literal["Region", "District"], List[Unit]]] = {"Region": [], "District": []}
    units_affected_current_names: Optional[Dict[Literal["Region", "District"], Dict[Literal["before", "after"], List[str]]]] = {"Region": {"before": [], "after": []}, "District": {"before": [], "after": []}} # Dict with values: "District" or "Region", the value is dict with values: "before" or "after", its values are lists of affected units.
    units_affected_ids: Optional[Dict[Literal["Region", "District"], Dict[Literal["before", "after"], List[str]]]] = {"Region": {"before": [], "after": []}, "District": {"before": [], "after": []}} # The attribute is created based on units_created_current_names during change application.

    previous_states: Optional[List] = []
    next_states: Optional[List] = []

    def echo(self) -> str:
        return self.matter.echo(self.date, self.source)

    def districts_involved(self) -> list[str]:
        return self.matter.districts_involved()
    
    def create_next_state(self, unit: Unit) -> UnitState:
        """
        Creates a next state of a given unit on the self.date,
        and links the previous state and the next state to self"""
        # Create a new unit state
        old_state, new_state = unit.create_next_state(self.date)
        
        # Link the states to each other:
        old_state.next = new_state
        new_state.previous = old_state

        # Link old state to change:
        old_state.next_change = self
        self.previous_states.append(old_state)

        # Link new state to change:
        new_state.previous_change = self
        self.next_states.append(new_state)

        return new_state

    def abolish(self, unit: Unit) -> None:
        """
        Abolished the given unit and links its state before abolishmend
        to itself."""
        old_state = unit.abolish(self.date)
        old_state.next_change = self
        self.previous_states.append(old_state)


    def verify_consistency(self, adm_state, region_registry, dist_registry):
        # First, verify the consistency between administrative state, region registry and district registry.
        try:
            adm_state.verify_consistency(region_registry, dist_registry, check_date = self.date)
        except Exception as e:
                raise RuntimeError(f"Error in consistency verification of {str(self)}: {str(e)}") from e
        
        # Then, use the self.units_affected_current_names attribute to verify which units
        # have to be present in the registries for the correct application.
        for unit_type in ['Region', 'District']:
            for unit_current_name in self.units_affected_current_names[unit_type]["before"]:
                if unit_type=="Region":
                    unit, unit_state, _ = region_registry.find_unit_state_by_date(unit_current_name, self.date)
                else:
                    unit, unit_state, _ = dist_registry.find_unit_state_by_date(unit_current_name, self.date)
                if unit is None: # Check if unit exists in the proper registry
                    raise ConsistencyError(f"Change {str(self)} applied to {unit_type.lower()} {unit_current_name} but no unit with this name variant exists in the {unit_type.lower()} registry.")
                if unit_state is None: # Check if state exists for the unit for the given date.
                    raise ConsistencyError(f"Change {str(self)} applied to {unit_type.lower()} {unit_current_name} but no unit state for this unit exists in the {unit_type.lower()} registry.")
                
        # Verify and standardize all addresses
        self.matter.verify_and_standardize_all_addresses(self, adm_state, region_registry, dist_registry)

        # Verify the existence of all reformed attributes
        self.matter.verify_att_to_reform(self, adm_state, region_registry, dist_registry)


    def apply(self, adm_state: AdministrativeState, region_registry: RegionRegistry, dist_registry: DistrictRegistry, plot_change = False) -> None:
        self.verify_consistency(adm_state, region_registry, dist_registry)
        print(f"Applying change {str(self)}.")
        # Create self.units_affected_ids["before"] for plotting.
        self.units_affected_ids['Region']["before"] = [region_registry.find_unit(current_name).name_id for current_name in self.units_affected_current_names['Region']["before"]]
        # print(f"(District, {before_or_after}): {[current_name for current_name in self.units_affected_current_names['District'][before_or_after]]}")
        self.units_affected_ids['District']["before"] = [dist_registry.find_unit(current_name).name_id for current_name in self.units_affected_current_names['District']["before"]]

        # If plot_change is True, prepare plot before the application.
        if plot_change:
            plot_before = self._plot(adm_state, region_registry, dist_registry, before_or_after="before")
            print(f"Change {self.matter.change_type} before plot created.")
        
        # Apply change
        self.matter.apply(self, adm_state, region_registry, dist_registry)
        
        # If plot_change is True, prepare plot after the application.
        if plot_change:
            plot_after = self._plot(adm_state, region_registry, dist_registry, before_or_after="after")
            print(f"Change {self.matter.change_type} after plot created.")
            from utils.helper_functions import combine_figures
            return combine_figures(plot_before, plot_after)
        return
    
    @field_validator("date", mode="before")
    @classmethod
    def parse_non_iso_date(cls, value):
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%d.%m.%Y")
            except ValueError:
                raise ValueError(f"Date format must be DD.MM.YYYY, got: {value}")
        return value

    @model_validator(mode="after")
    def ensure_complete_units_affected_current_names(self):
        # Start with what's already provided (if any)
        affected_current_names = self.matter.fill_units_affected_current_names()

        # Ensure top-level keys exist
        for unit_type in ("Region", "District"):
            if unit_type not in affected_current_names:
                affected_current_names[unit_type] = {}

            # Ensure both 'before' and 'after' lists exist
            for when in ("before", "after"):
                if when not in affected_current_names[unit_type]:
                    affected_current_names[unit_type][when] = []

        # Update the internal state of the model instance directly
        self.units_affected_current_names = affected_current_names
        
        # Return `self` (the model instance itself)
        return self
    
    def _plot(self, adm_state, region_registry, dist_registry, before_or_after):
        """
        This method is PRIVATE as it makes sense to call it only in connection with
        'apply' method to verify the consistency of the change with existing administrative
        state and unit registries and use the newly created states and registries through
        the change application.
        
        The method should be called only through using the 'apply' method with the 'plot'
        argument set to 'True'. """

        from utils.helper_functions import build_plot_from_layers

        if before_or_after=="before":
            time_shift = -timedelta(hours=12)
        else:
            time_shift = timedelta(hours=12)

        # Prepare the layers
        country_layer = adm_state._country_plot_layer(dist_registry, self.date + time_shift)
        region_layer = adm_state._region_plot_layer(region_registry, dist_registry, self.date + time_shift)
        district_layer = adm_state._district_plot_layer(dist_registry, self.date + time_shift)
        
        # Extract all rows where 'region_name_id' is in the list of regions affected
        change_region_layer = region_layer[region_layer['name_id'].isin(self.units_affected_ids["Region"][before_or_after])].copy()
        change_region_layer['edgecolor'] = 'red'
        change_region_layer['color'] = 'red'
        change_district_layer = district_layer[district_layer['name_id'].isin(self.units_affected_ids["District"][before_or_after])].copy()
        change_district_layer['edgecolor'] = 'red'
        change_district_layer['color'] = 'darkred'

        # For debugging, uncomment:
        # if before_or_after == "after":
            # print(f"country_layer ({before_or_after}): {country_layer.to_string()}")
            # print(f"change_region_layer ({before_or_after}): {change_region_layer.to_string()}")
            # print(f"change_district_layer ({before_or_after}): {change_district_layer.to_string()}")
            #print(f"district_layer ({before_or_after}): {district_layer.to_string()}")
            # print(f"region_layer ({before_or_after}): {region_layer.to_string()}")

        # Build the figure
        fig = build_plot_from_layers(country_layer, change_region_layer, change_district_layer, district_layer, region_layer)
        return fig
    
    def __str__(self):
        if self.matter.change_type == "UnitReform":
            return f"<Change type={self.matter.change_type}, ({self.units_affected_current_names[self.matter.unit_type]['before']}), date={self.date.date()}>"
        if self.matter.change_type == "ManyToOne":
            return f"<Change type={self.matter.change_type}, (... -> {self.units_affected_current_names['District']['after']}), date={self.date.date()}>"
        if self.matter.change_type == "OneToMany":
            return f"<Change type={self.matter.change_type}, ({self.units_affected_current_names['District']['before']} -> ...), date={self.date.date()}>"
        if self.matter.change_type == "ChangeAdmState":
            return f"<Change type={self.matter.change_type}, ({self.matter.take_from} -> ...), date={self.date.date()}>"