from pydantic import BaseModel, model_validator, field_validator, Field
from typing import Union, Optional, Literal, List, Dict, Annotated, Any
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

class DataTableMetadata(BaseModel):
    dataset_id: str
    category: str
    description: Dict[Union[Literal["pol", "eng"]], str]
    date: str
    adm_state_date: datetime  # changed from str to datetime
    standardization_comments: Optional[str] = ""
    harmonization_method: Literal["proportional_to_territory"]
    imputation_method: Optional[Literal["take_from_closest_centroid"]] = None
    dict[str, dict[str, Any]]

    @model_validator(mode="before")
    @classmethod
    def parse_non_iso_date(cls, data: Any) -> Any:
        if isinstance(data, dict) and isinstance(data.get("adm_state_date"), str):
            try:
                data["adm_state_date"] = datetime.strptime(data["adm_state_date"], "%d.%m.%Y")
            except ValueError:
                raise ValueError(f"Date format must be DD.MM.YYYY, got: {data['adm_state_date']}")
        return data