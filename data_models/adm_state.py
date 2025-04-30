from pydantic import BaseModel
from typing import Union, Optional, Literal, Dict, Any, Tuple

from border_harmonization_toolkit.data_models.adm_timespan import TimeSpan
from border_harmonization_toolkit.data_models.adm_unit import *

#############################################################################################
# Models to store information about current region-districts relations.
# AdministrativeState is a list of (region name, list of districts) pairs.

RegionAddress = Tuple[Literal["HOMELAND", "ABROAD"], str]              # For regions"
DistAddress = Tuple[Literal["HOMELAND", "ABROAD"], str, str]         # For districts
Address = Union[DistAddress, RegionAddress]

class AdministrativeState(BaseModel):
    timespan: Optional[TimeSpan] = None
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
        for i, attr in enumerate(address[:-1]):
            if attr not in current.keys():
                raise ValueError(f"Unit '{attr}' does not belong to {address[:i]}")
            current = current[attr]
        current[address[-1]] = content
        return