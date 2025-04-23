from pydantic import BaseModel, Field
from typing import Union, Optional, Literal, List


# VChange data model

class VChangeMatterFromInfo(BaseModel):
    region: str
    district: str

class VChangeMatter(BaseModel):
    from_: VChangeMatterFromInfo = Field(alias="from")
    to: str

class VChangeEntry(BaseModel):
    type: Literal["VChange"]
    date: str
    source: str
    description: str
    matter: VChangeMatter

# OneToMany model

class DOneToManyMatterFrom(BaseModel):
    region: str
    district: str
    delete_district: bool

class DOneToManyMatterTo(BaseModel):
    region: str
    district: str
    weight_from: Optional[float] = None
    weight_to: Optional[float] = None

class DOneToManyMatter(BaseModel):
    from_: DOneToManyMatterFrom = Field(alias="from")
    to: List[DOneToManyMatterTo]

class DOneToManyEntry(BaseModel):
    type: Literal["DOneToMany"]
    date: str
    source: str
    description: str
    matter: DOneToManyMatter

# DManyToOne model

class ManyToOneMatterFrom(BaseModel):
    region: str
    district: str
    weight_from: Optional[float] = None
    weight_to: Optional[float] = None


class ManyToOneMatterTo(BaseModel):
    region: str
    district: str


class ManyToOneMatter(BaseModel):
    from_: List[ManyToOneMatterFrom] = Field(alias="from")
    to: ManyToOneMatterTo


class DManyToOneEntry(BaseModel):
    type: Literal["DManyToOne"]
    date: str
    source: str
    description: str
    matter: ManyToOneMatter

# Create combined change entry using a discriminated union.
ChangeEntry = Union[VChangeEntry, DOneToManyEntry, DManyToOneEntry]
 
 
