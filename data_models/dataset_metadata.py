from pydantic import BaseModel, model_validator, field_validator, Field
from typing import Union, Optional, Literal, List, Dict, Annotated, Any
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

class DataTableMetadata(BaseModel):
    dataset_id: str
    category: str
    description: Dict[Union[Literal["pol", "eng"]], str]
    date: str
    adm_state_date: datetime  # parsed from multiple formats
    standardization_comments: Optional[str] = ""
    harmonization_method: Literal["proportional_to_territory"]
    imputation_method: Optional[Literal["take_from_closest_centroid"]] = None
    columns: List[Dict[str, Any]] = []

    @model_validator(mode="before")
    @classmethod
    def parse_flexible_date(cls, data: Any) -> Any:
        if isinstance(data, dict):
            adm_date = data.get("adm_state_date")
            if isinstance(adm_date, str):
                for fmt in ("%d.%m.%Y", "%Y-%m-%dT%H:%M:%S"):
                    try:
                        data["adm_state_date"] = datetime.strptime(adm_date, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    raise ValueError(f"Date format must be DD.MM.YYYY or ISO 8601, got: {adm_date}")
        return data