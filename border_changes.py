from abc import ABC, abstractmethod
from datetime import datetime

class Change(ABC):
    # Base Change class
    required_attributes = ["type", "date", "source", "description", "matter"]

    def __init__(self, change_entry):
        # Validate the structure of the change_dict for initiation
        self.change_dict = change_entry.model_dump()

        # Initiate Change class with the required attributes
        self.type = self.change_dict["type"]
        self.date = datetime.strptime(self.change_dict["date"], "%d.%m.%Y").date()
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
        """Abstract method for applying the change to the currect administrative state"""
        pass

class VChange(Change):
    # Class describing the change of region for a district.
    def __init__(self, change_dict):
        super().__init__(change_dict)  # Assign standard general Change description attributes

        # Initiate subclass-specific attributes
        self.v_from = self.matter['from_']['region']
        self.d_from = self.matter['from_']['district']
        self.v_to = self.matter['to']

    def echo(self, lang = "pol"):
        if lang == "pol":
            print(f"{self.date} przeniesiono powiat {self.d_from} z woj. \"{self.v_from}\" do woj. \"{self.v_to}\" ({self.source}).")
        elif lang == "eng":
            print(f"{self.date} moved district {self.d_from} from voiv. \"{self.v_from}\" to voiv. \"{self.v_to}\" ({self.source}).")
        else:
            raise ValueError("Wrong value for the lang parameter.")
        
    def districts_involved(self):
        # Returns the list of (district, its_region) for all districts involved in the change
        return [(self.v_from, self.d_from), (self.v_to, self.d_from)]
    
    def apply(self, administrative_state):
        administrative_state.valid_to = self.date

        new_administrative_state = administrative_state.copy()
        new_administrative_state.valid_from = self.date
        new_administrative_state.valid_to = None
        district_to_move = new_administrative_state.pop_district(self.v_from, self.d_from)
        new_administrative_state.add_district_if_absent(self.v_to, district_to_move)
        return new_administrative_state

class DOneToManyChange(Change):
    # Class describing the change where the territory of one district is split between many.
    def __init__(self, change_dict):
        super().__init__(change_dict)  # Assign standard general Change description attributes

        # Initiate subclass-specific attributes
        self.v_from = self.matter['from_']['region']
        self.d_from = self.matter['from_']['district']
        self.delete_district = self.matter['from_']['delete_district']
        self.many_to = self.matter['to']

    def echo(self, lang = "pol"):
        destination_districts = ", ".join([f"{destination['district']} ({destination['region']})" for destination in self.many_to])
        if lang == "pol":
            if self.delete_district:
                print(f"{self.date} zniesiono powiat {self.d_from} ({self.v_from}), a jego terytorium włączono do powiatów: {destination_districts} ({self.source}).")
            else:
                print(f"{self.date} fragment terytorium powiatu {self.d_from} ({self.v_from}) włączono do powiatów: {destination_districts} ({self.source}).")
        elif lang == "eng":
            if self.delete_district:
                print(f"{self.date} the district {self.d_from} ({self.v_from}) was abolished and its territory was integrated into the districts: {destination_districts} ({self.source}).")
            else:
                print(f"{self.date} part of the territory of the district {self.d_from} ({self.v_from}) was integrated into the districts: {destination_districts} ({self.source}).")
        else:
            raise ValueError("Wrong value for the lang parameter.")
        
    def districts_involved(self):
        # Returns the list of (district, its_region) for all districts involved in the change
        all_districts_involved = [(self.v_from, self.d_from)]
        all_districts_involved += [(destination['region'], destination['district']) for destination in self.many_to]
        return all_districts_involved
    
    def apply(self, administrative_state):
        pass

class DManyToOneChange(Change):
    # Class describing the change where the territory of one district is split between many.
    def __init__(self, change_dict):
        super().__init__(change_dict)  # Assign standard general Change description attributes

        # Initiate subclass-specific attributes
        self.many_from = self.matter['from_']
        self.v_to = self.matter['to']['region']
        self.d_to = self.matter['to']['district']

        # This variable is not defined in JSON. It is set only after the whole graph of border changes is created.
        self.create_district = None

    def echo(self, lang = "pol"):
        origin_districts = ", ".join([f"{origin['district']} ({origin['region']})" for origin in self.many_from])
        if lang == "pol":
            if self.create_district:
                print(f"{self.date} utworzono powiat {self.d_to} ({self.v_to}) z części powiatów: {origin_districts} ({self.source}).")
            else:
                print(f"{self.date} do powiatu {self.d_to} ({self.v_to}) włączono części powiatów: {origin_districts} ({self.source}).")
        elif lang == "eng":
            if self.delete_district:
                print(f"{self.date} the district {self.d_to} ({self.v_to}) was created out of the fragments of districts: {origin_districts} ({self.source}).")
            else:
                print(f"{self.date} the district {self.d_to} ({self.v_to}) was enlarged by the fragments of districts: {origin_districts} ({self.source}).")
        else:
            raise ValueError("Wrong value for the lang parameter.")
        
    def districts_involved(self):
        # Returns the list of (district, its_region) for all districts involved in the change
        all_districts_involved = [(origin['region'], origin['district']) for origin in self.many_from]
        all_districts_involved += [(self.v_to, self.d_to)]
        return all_districts_involved
    
    def apply(self, administrative_state):
        pass

