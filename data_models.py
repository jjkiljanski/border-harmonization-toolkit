from pydantic import BaseModel, model_validator, Field
from typing import Union, Optional, Literal, List, Dict, Annotated, Any

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

        if "name" not in to_reform:
            raise ValueError("`to_reform` must contain a 'name' field.")

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
    district: str

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
    district: str
    delete_district: bool

class DOneToManyMatterTakeTo(BaseModel):
    create: bool
    region: str
    district: str
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
    district: str
    weight_from: Optional[float] = None
    weight_to: Optional[float] = None
    delete_district: bool


class ManyToOneMatterTakeTo(BaseModel):
    """
    Required:
        create, region, and district
    Required only if create = true:
        district_type and seat
    Optional:
        alternative names and alternative_seat_names (lists of strings) (info on the created district)
    """
    create: bool
    region: str
    district: str
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
    Union[RChangeEntry, DOneToManyEntry, DManyToOneEntry, RReformEntry],
    Field(discriminator="change_type")
]

################# AdministrativeState model #################

class District(BaseModel):
    name: str
    alternative_names: Optional[List[str]] = None
    district_type: Literal["w", "m"]
    seat: str
    alternative_seat_names: Optional[List[str]] = None

class AdministrativeStateEntry(BaseModel):
    valid_from: str
    regions: Dict[str, List[District]]