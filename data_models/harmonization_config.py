from pydantic import BaseModel, model_validator, field_validator, Field
from typing import Union, Optional, Literal, List, Dict, Annotated, Any
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing_extensions import Annotated
from data_models.econ_data_metadata import DataTableMetadata


# --- Argument models for each method ---
class SumUpDataTablesArgs(BaseModel):
    data_tables_list: List[str]
    new_data_table_name: str

class CreateDistAreaDatasetArgs(BaseModel):
    data_table_metadata: DataTableMetadata

# --- Reorganize method models with discriminated union ---
class SumUpDataTables(BaseModel):
    method_name: Literal["sum_up_data_tables"]
    arguments: SumUpDataTablesArgs

class CreateDistAreaDataset(BaseModel):
    method_name: Literal["create_dist_area_dataset"]
    arguments: CreateDistAreaDatasetArgs


# Annotated discriminated union
ReorganizeMethod = Annotated[
    Union[
        SumUpDataTables,
        CreateDistAreaDataset
        # Add more methods here later
    ],
    Field(discriminator="method_name")
]


# --- Top-level config model ---
class HarmonizationConfig(BaseModel):
    post_harmonization_reorganize_data_tables: List[ReorganizeMethod]