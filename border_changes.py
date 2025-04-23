from abc import ABC, abstractmethod

class Change(ABC):
    # Base Change class
    required_attributes = ["type", "date", "source", "description", "matter"]

    def __init__(self, change_dict):
        # Validate the structure of the change_dict for initiation
        self.change_dict = change_dict
        self.validate_base_struct()

        # Initiate Change class with the required attributes
        self.type = self.change_dict["type"]
        self.date = self.change_dict["date"]
        self.source = self.change_dict["source"]
        self.description = self.change_dict["description"]
        self.matter = self.change_dict["matter"]

    def validate_base_struct(self):
        # Raise value error if some attributes are missing
        missing_attributes = [att for att in self.required_attributes if att not in self.change_dict]
        present_attributes = [self.change_dict[att] for att in self.required_attributes if att not in missing_attributes]
        if missing_attributes:
            present_attributes = [self.change_dict[att] for att in self.required_attributes if att not in missing_attributes]
            raise ValueError(f"Missing required change attributes: {', '.join(missing_attributes)} for change {', '.join(present_attributes)}")
        
        # Raise a warning if there are some unexpected attributes
        extra_attributes = list(set(self.change_dict.keys())-set(self.required_attributes))
        if extra_attributes:
            print(f"Change {', '.join(present_attributes)} has unexpected attribute(s): {', '.join(extra_attributes)}.")
        

    @abstractmethod
    def validate_matter_struct(self):
        """Abstract method for validating change matter dict structure during class initiation."""
        pass

    @abstractmethod
    def echo(self, lang = "pol"):
        """Abstract method for printing or returning change description."""
        pass

class vChange(Change):
    # Class describing the change of voivodship for a district.
    def __init__(self, change_dict):
        super().__init__(change_dict)  # Assign standard general Change description attributes

        # Check if subclass-specific fields are present
        self.validate_matter_struct()

        # Initiate vChange-specific attributes
        self.v_from = self.matter['from']['voivodship']
        self.d_from = self.matter['from']['district']
        self.v_to = self.matter['to']

    def validate_matter_struct(self):
        # Helper function to assure correct attributes for the vChange initiation.

        ##### Check the dict structure #####
        exp_matter_keys = {"from", "to"} # Expected self.matter keys
        if set(self.matter.keys()) != exp_matter_keys:
            raise ValueError (f"Wrong structure of the vChange.matter attribute: {self.matter}.")
        
        exp_from_keys = {"voivodship", "district"} # Expected self.matter["from"] keys
        if set(self.matter["from"].keys()) != exp_from_keys:
            raise ValueError (f"Wrong structure of the vChange.matter[\"from\"] attribute: {self.matter}.")

        ##### Check the keys' types #####
        if not isinstance(self.matter["from"]["voivodship"], str):
            raise ValueError (f"self.matter[\"from\"][\"voivodship\"] attrib. must be string in {self.matter}.")
        if not isinstance(self.matter["from"]["district"], str):
            raise ValueError (f"self.matter[\"from\"][\"district\"] attrib. must be string in {self.matter}.")
        if not isinstance(self.matter["to"], str):
            raise ValueError (f"self.matter[\"to\"] attrib. is not string in {self.matter}.")


    def echo(self, lang = "pol"):
        if lang == "pol":
            print(f"{self.date} przeniesiono powiat {self.d_from} z woj. \"{self.v_from}\" do woj. \"{self.v_to}\" ({self.source}).")
        elif lang == "eng":
            print(f"{self.date} moved district {self.d_from} from voiv. \"{self.v_from}\" to voiv. \"{self.v_to}\" ({self.source}).")
        else:
            raise ValueError("Wrong value for the lang parameter.") 
