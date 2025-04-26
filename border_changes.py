from abc import ABC, abstractmethod
from datetime import datetime
from copy import deepcopy

from data_models import DistrictEventLog

class Change(ABC):
    # Base Change class
    def __init__(self, change_entry):
        # Validate the structure of the change_dict for initiation
        self.change_dict = change_entry.model_dump()

        # Initiate Change class with the required attributes
        self.change_type = self.change_dict["change_type"]
        self.date = datetime.strptime(self.change_dict["date"], "%d.%m.%Y").date()
        self.order = self.change_dict["order"]
        self.source = self.change_dict["source"]
        self.description = self.change_dict["description"]
        self.matter = self.change_dict["matter"]

    @abstractmethod
    def echo(self, lang = "pol"):
        """Abstract method for printing or returning change description."""
        pass

    @abstractmethod
    def districts_involved(self):
        """Abstract method for listing districts involved in the change."""
        pass
    
    @abstractmethod
    def apply(self, administrative_state):
        """
        Abstract method for applying the change to the currect administrative state.
        It should return (self.d_created, self.d_abolished, self.d_b_changed, self.r_changed) quadruple.
        """
        pass

    @abstractmethod
    def log_district_history(self):
        """Abstract method for logging the change from the perspective of single districts"""
        pass

    @abstractmethod
    def _districts_affected(self):
        """
        Abstract method that returns districts created, abolished,
        with territory changed and with region changed.
        """
        return (None, None, None, None)

class RCreate(Change):
    # Class describing the Creation of a new region out of many districts.
    def __init__(self, change_dict):
        super().__init__(change_dict)  # Assign standard general Change description attributes

        # Initiate subclass-specific attributes
        self.take_from = self.matter['take_from']
        self.r_to = self.matter['take_to']['region_name']

        # Information on the districts affected
        d_created, d_abolished, d_b_changed, d_r_changed = self._districts_affected()
        self.d_created = d_created
        self.d_abolished = d_abolished
        self.d_b_changed = d_b_changed
        self.d_r_changed = d_r_changed

    def echo(self, lang = "pol"):
        if lang == "pol":
            print(f"{self.date} utworzono jednostkę administracyjną na prawach województwa {self.r_to}. ({self.source}).")
        elif lang == "eng":
            print(f"{self.date} the region {self.r_to} was created ({self.source}).")
        else:
            raise ValueError("Wrong value for the lang parameter.")
        
    def districts_involved(self):
        # Legacy function - to change or delete
        # Returns the list of (district, its_region) for all districts involved in the change
        return [(unit["district_name"], unit["region"]) for unit in self.take_from]
    
    def log_district_history(self):
        # Legacy function - to change or delete
        logs = []
        for district_name, region in self.districts_involved():
            single_log = {"district_name": district_name, "date": self.date, "event_type": "r_change", "change_ref": self}
            logs.append(single_log)
            # Try to create the log
            try:
                # Use Pydantic to parse and validate the data
                validated_log = DistrictEventLog(log=logs)
                print("Log is valid:", validated_log)
            except Exception as e:
                print("Validation failed:", e)
        return logs
    
    def _districts_affected(self):
        """
        Abstract method that returns quadruple:
            d_created (list of dicts)           # districts created)
            d_abolished (list of names)         # districts abolished
            d_b_changed (list of names)         # districts with borders changed
            r_changed (list of (name, (old_region, new_region)) pairs)
                                                # districts that changed regions
        """
        d_created = None
        d_abolished = None
        d_b_changed = None
        r_changed = [(unit["district_name"], (unit["region"], self.r_to)) for unit in self.take_from]
        return (d_created, d_abolished, d_b_changed, r_changed)
    
    def apply(self, state):
        if self.r_to not in state.structure.keys():
            state.structure[self.r_to] = []

        for unit in self.take_from:
            # Remove district from the old region
            try:
                district_to_move = state.pop_district(unit["region"], unit["district_name"])
            except:
                raise ValueError(f"District {unit['district_name']} doesn't exist in the region {unit['region']}:\n{self.echo()}.")
            
            # Add district to the new region
            state.add_district_if_absent(self.r_to, district_to_move)

        return (self.d_created, self.d_abolished, self.d_b_changed, self.d_r_changed)

class RReform(Change):
    # Class describing the change of attributes for a region (e.g. region name).
    def __init__(self, change_dict):
        super().__init__(change_dict)  # Assign standard general Change description attributes

        # Initiate subclass-specific attributes
        self.to_reform = self.matter['to_reform']
        self.after_reform = self.matter['after_reform']

        # Information on the districts affected
        d_created, d_abolished, d_b_changed, d_r_changed = self._districts_affected()
        self.d_created = d_created
        self.d_abolished = d_abolished
        self.d_b_changed = d_b_changed
        self.d_r_changed = d_r_changed

    def echo(self, lang = "pol"):
        if lang == "pol":
            print(f"{self.date} dokonano reformy województwa {self.to_reform['region_name']}. Przed reformą: {self.to_reform.items()} vs po reformie: {self.after_reform.items()} ({self.source}).")
        elif lang == "eng":
            print(f"{self.date} the region {self.to_reform['region_name']} was reformed. Before the reform: {self.to_reform.items()} vs after the reform: {self.after_reform.items()} ({self.source}).")
        else:
            raise ValueError("Wrong value for the lang parameter.")
        
    def districts_involved(self):
        # Returns the list of (district, its_region) for all districts involved in the change
        return []
    
    def log_district_history(self):
        return super().log_district_history()
    
    def _districts_affected(self):
        """
        Abstract method that returns quadruple:
            d_created (list of dicts)           # districts created)
            d_abolished (list of names)         # districts abolished
            d_b_changed (list of names)         # districts with borders changed
            r_changed (list of (name, (old_region, new_region)) pairs)
                                                # districts that changed regions
        """
        d_created = None
        d_abolished = None
        d_b_changed = None
        r_changed = None
        return (d_created, d_abolished, d_b_changed, r_changed)
    
    def apply(self, state):
        # Remove district from the old region
        # Only name change is implemented for now.
        old_name = self.to_reform["region_name"]
        new_name = self.after_reform["region_name"]
        if old_name != new_name:
            try:
                new_region = state.structure.pop(old_name)
                state.structure[new_name] = new_region
            except:
                raise ValueError(f"The region {old_name} doesn't exist in the administrative state:\n{self.echo()}.")
            
        return (self.d_created, self.d_abolished, self.d_b_changed, self.d_r_changed)

class RChange(Change):
    # Class describing the change of region for a district.
    def __init__(self, change_dict):
        super().__init__(change_dict)  # Assign standard general Change description attributes

        # Initiate subclass-specific attributes
        self.r_from = self.matter['take_from']['region']
        self.d_from = self.matter['take_from']['district_name']
        self.r_to = self.matter['take_to']

        # Information on the districts affected
        d_created, d_abolished, d_b_changed, d_r_changed = self._districts_affected()
        self.d_created = d_created
        self.d_abolished = d_abolished
        self.d_b_changed = d_b_changed
        self.d_r_changed = d_r_changed

    def echo(self, lang = "pol"):
        if lang == "pol":
            print(f"{self.date} przeniesiono powiat {self.d_from} z reg. \"{self.r_from}\" do reg. \"{self.r_to}\" ({self.source}).")
        elif lang == "eng":
            print(f"{self.date} moved district {self.d_from} from region \"{self.r_from}\" to region \"{self.r_to}\" ({self.source}).")
        else:
            raise ValueError("Wrong value for the lang parameter.")
        
    def districts_involved(self):
        # Returns the list of (district, its_region) for all districts involved in the change
        return [(self.r_from, self.d_from), (self.r_to, self.d_from)]
    
    def log_district_history(self):
        return super().log_district_history()
    
    def _districts_affected(self):
        """
        Abstract method that returns quadruple:
            d_created (list of dicts)           # districts created)
            d_abolished (list of names)         # districts abolished
            d_b_changed (list of names)         # districts with borders changed
            r_changed (list of (name, (old_region, new_region)) pairs)
                                                # districts that changed regions
        """
        d_created = None
        d_abolished = None
        d_b_changed = None
        r_changed = [(self.d_from, (self.r_from, self.r_to))]
        return (d_created, d_abolished, d_b_changed, r_changed)
    
    def apply(self, state):
        # Remove district from the old region
        try:
            district_to_move = state.pop_district(self.r_from, self.d_from)
        except:
            raise ValueError(f"District {self.d_from} doesn't exist in the region {self.r_from}:\n{self.echo()}.")
        
        # Add district to the new region
        try:
            state.add_district_if_absent(self.r_to, district_to_move)
        except:
            raise ValueError(f"District {self.d_from} already exists in the region {self.r_to}:\n{self.echo()}.")
        
        return (self.d_created, self.d_abolished, self.d_b_changed, self.d_r_changed)
        

class DOneToManyChange(Change):
    # Class describing the change where the territory of one district is split between many.
    def __init__(self, change_dict):
        super().__init__(change_dict)  # Assign standard general Change description attributes

        # Initiate subclass-specific attributes
        self.r_from = self.matter['take_from']['region']
        self.d_from = self.matter['take_from']['district_name']
        self.delete_district = self.matter['take_from']['delete_district']
        self.take_to = self.matter['take_to']

        # Information on the districts affected
        d_created, d_abolished, d_b_changed, d_r_changed = self._districts_affected()
        self.d_created = d_created
        self.d_abolished = d_abolished
        self.d_b_changed = d_b_changed
        self.d_r_changed = d_r_changed

    def echo(self, lang = "pol"):
        destination_districts = ", ".join([f"{destination['district_name']} ({destination['region']})" for destination in self.take_to])
        if lang == "pol":
            if self.delete_district:
                print(f"{self.date} zniesiono powiat {self.d_from} ({self.r_from}), a jego terytorium włączono do powiatów: {destination_districts} ({self.source}).")
            else:
                print(f"{self.date} fragment terytorium powiatu {self.d_from} ({self.r_from}) włączono do powiatów: {destination_districts} ({self.source}).")
        elif lang == "eng":
            if self.delete_district:
                print(f"{self.date} the district {self.d_from} ({self.r_from}) was abolished and its territory was integrated into the districts: {destination_districts} ({self.source}).")
            else:
                print(f"{self.date} part of the territory of the district {self.d_from} ({self.r_from}) was integrated into the districts: {destination_districts} ({self.source}).")
        else:
            raise ValueError("Wrong value for the lang parameter.")
        
    def districts_involved(self):
        # Returns the list of (district, its_region) for all districts involved in the change
        all_districts_involved = [(self.r_from, self.d_from)]
        all_districts_involved += [(destination['region'], destination['district_name']) for destination in self.take_to]
        return all_districts_involved
    
    def log_district_history(self):
        return super().log_district_history()
    
    def _districts_affected(self):
        """
        Abstract method that returns quadruple:
            d_created (list of dicts)           # districts created)
            d_abolished (list of names)         # districts abolished
            d_b_changed (list of names)         # districts with borders changed
            r_changed (list of (name, (old_region, new_region)) pairs)
                                                # districts that changed regions
        """
        d_created = []
        for target_district in self.take_to:
            if target_district["create"]:
                new_district = deepcopy(target_district)
                new_district.pop("create") # Remove the 'create' key
                new_district.pop("region") # Remove the 'region' key
                d_created.append(new_district)

        d_abolished = []
        if self.delete_district:
            d_abolished = [self.d_from]

        d_b_changed = []
        d_b_changed.append(self.r_from)
        d_b_changed += [district["district_name"] for district in self.take_to]

        r_changed = None

        return (d_created, d_abolished, d_b_changed, r_changed)
    
    def apply(self, state):
        if self.delete_district:
            # Delete the old district
            try:
                state.pop_district(self.r_from, self.d_from)
            except:
                raise ValueError(f"District {self.d_from} doesn't exist in the region {self.r_from}:\n{self.echo()}.")
            
        for target_district in self.take_to:
            if target_district["create"]:
                new_district = deepcopy(target_district)
                new_district.pop("create") # Remove the 'create' key
                region_name = new_district.pop("region") # Remove the 'region' key
                # Add the new district to the state
                try:
                    state.add_district_if_absent(region_name, new_district)
                except:
                    raise ValueError(f"District {new_district['district_name']} already exists in the region {region_name}:\n{self.echo()}.")

        return (self.d_created, self.d_abolished, self.d_b_changed, self.d_r_changed)  
            

class DManyToOneChange(Change):
    # Class describing the change where the territory of one district is split between many.
    def __init__(self, change_dict):
        super().__init__(change_dict)  # Assign standard general Change description attributes

        # Initiate subclass-specific attributes
        self.take_from = self.matter['take_from']
        self.take_to = self.matter['take_to']

        # Information on the districts affected
        d_created, d_abolished, d_b_changed, d_r_changed = self._districts_affected()
        self.d_created = d_created
        self.d_abolished = d_abolished
        self.d_b_changed = d_b_changed
        self.d_r_changed = d_r_changed

    def echo(self, lang = "pol"):
        origin_districts_partial = ", ".join([f"{origin['district_name']} ({origin['region']})" for origin in self.take_from if not origin["delete_district"]])
        origin_districts_whole = ", ".join([f"{origin['district_name']} ({origin['region']})" for origin in self.take_from if origin["delete_district"]])
        if "create" not in self.take_to:
            print(self.description)
        if lang == "pol":
            if self.take_to["create"]:
                print(f"{self.date} utworzono powiat {self.take_to['district_name']} ({self.take_to['region']}) z części powiatów: {origin_districts_partial} oraz z całego terytorium powiatów: {origin_districts_whole} ({self.source}).")
            else:
                print(f"{self.date} do powiatu {self.take_to['district_name']} ({self.take_to['region']}) włączono części powiatów: {origin_districts_partial} oraz całe terytorium powiatów: {origin_districts_whole} ({self.source}).")
        elif lang == "eng":
            if self.take_to["create"]:
                print(f"{self.date} the district {self.take_to['district_name']} ({self.take_to['region']}) was created out of the fragments of districts: {origin_districts_partial} and from the whole territories of the districts: {origin_districts_whole} ({self.source}).")
            else:
                print(f"{self.date} the district {self.take_to['district_name']} ({self.take_to['region']}) was enlarged by the fragments of districts: {origin_districts_partial} and the whole territories of the districts: {origin_districts_whole} ({self.source}).")
        else:
            raise ValueError("Wrong value for the lang parameter.")
        
    def districts_involved(self):
        # Returns the list of (district, its_region) for all districts involved in the change
        all_districts_involved = [(origin['region'], origin['district_name']) for origin in self.take_from]
        all_districts_involved += [(self.take_to["region"], self.take_to["district_name"])]
        return all_districts_involved
    
    def log_district_history(self):
        return super().log_district_history()
    
    def _districts_affected(self):
        """
        Abstract method that returns quadruple:
            d_created (list of dicts)           # districts created)
            d_abolished (list of names)         # districts abolished
            d_b_changed (list of names)         # districts with borders changed
            r_changed (list of (name, (old_region, new_region)) pairs)
                                                # districts that changed regions
        """
        d_created = []
        if self.take_to["create"]:
            new_district = deepcopy(self.take_to)
            new_district.pop("create") # Remove the 'create' key
            new_district.pop("region") # Remove the 'region' key
            d_created = [new_district]

        d_abolished = []
        for district in self.take_from:
            if district["delete_district"]:
                d_abolished.append(district["district_name"])

        d_b_changed = []
        d_b_changed += [district["district_name"] for district in self.take_from]
        d_b_changed.append(self.take_to["district_name"])

        r_changed = None
        
        return (d_created, d_abolished, d_b_changed, r_changed)
    
    def apply(self, state):
        for source_district in self.take_from:
            if source_district["delete_district"]:
                # Delete the old district
                try:
                    state.pop_district(source_district["region"], source_district["district_name"])
                except:
                    raise ValueError(f"District {source_district['district_name']} doesn't exist in the region {source_district['region']}:\n{self.echo()}.")

        if self.take_to["create"]:
            new_district = deepcopy(self.take_to)
            new_district.pop("create") # Remove the 'create' key
            region_name = new_district.pop("region") # Remove the 'region' key
            # Add the new district to the state
            try:
                state.add_district_if_absent(region_name, new_district)
            except:
                raise ValueError(f"District {new_district['district_name']} already exists in the region {region_name}:\n{self.echo()}.")
            

        return (self.d_created, self.d_abolished, self.d_b_changed, self.d_r_changed)


