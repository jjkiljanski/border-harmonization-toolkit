from pydantic import BaseModel, model_validator, Field
from typing import Union, Optional, Literal, List, Dict, Annotated, Any
from abc import ABC, abstractmethod
from datetime import datetime

from adm_unit import *

#############################################################################################
# Models to store information about current region-districts relations.
# AdministrativeState is a list of (region name, list of districts) pairs.

DistAddress = Tuple[Literal["Poland", "Abroad"], str]              # For regions"
RegionAddress = Tuple[Literal["Poland", "Abroad"], str, str]         # For districts
Address = Union[DistAddress, RegionAddress]

class AdminitrativeState(BaseModel):
    timespan = Optional[TimeSpan] = None
    unit_hierarchy: Dict[str, Dict[str, Dict[str, Any]]]

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
        current_parent = None
        for i, attr in enumerate(address):
            current_parent = current
            if attr not in current.keys():
                raise ValueError(f"Unit '{attr}' does not belong to {address[:i]}")
            current = current[attr]
        current_parent[address[-1]] = content
        return 
