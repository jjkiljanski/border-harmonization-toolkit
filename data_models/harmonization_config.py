from pydantic import BaseModel, model_validator, field_validator, Field
from typing import Union, Optional, Literal, List, Dict, Annotated, Any
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing_extensions import Annotated


# --- Argument models for each method ---
class SumUpDatasetsArgs(BaseModel):
    datasets_list: List[str]
    new_dataset_name: str


# --- Reorganize method models with discriminated union ---
class SumUpDatasets(BaseModel):
    method_name: Literal["sum_up_datasets"]
    arguments: SumUpDatasetsArgs


# Annotated discriminated union
ReorganizeMethod = Annotated[
    Union[
        SumUpDatasets,
        # Add more methods here later
    ],
    Field(discriminator="method_name")
]


# --- Top-level config model ---
class HarmonizationConfig(BaseModel):
    post_harmonization_reorganize_datasets: List[ReorganizeMethod]