from pydantic import BaseModel, model_validator, field_validator, Field
from typing import Union, Optional, Literal, List, Dict, Annotated, Any
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

class ColumnMetadata(BaseModel):
    unit: str
    subcategory: str
    subsubcategory: Optional[str] = "Together"
    data_type: str
    completeness: Optional[float] = None
    n_na: Optional[int] = None
    n_not_na: Optional[int] = None
    completeness_after_imputation: Optional[float] = None
    n_na_after_imputation: Optional[int] = None
    n_not_na_after_imputation: Optional[int] = None
class DataTableMetadata(BaseModel):
    data_table_id: str
    adm_level: Union[Literal['District'], Literal['Region']]
    category: str
    source: Optional[str] = ""
    link: Optional[str] = ""
    table: Optional[str] = ""
    page: Optional[Union[int, str]] = None
    pdf_page: Optional[int] = None
    description: Dict[Union[Literal["pol", "eng"]], str]
    date: str
    orig_adm_state_date: datetime = None  # parsed from multiple formats
    adm_state_date: Optional[datetime]
    standardization_comments: Optional[str] = ""
    harmonization_method: Literal["proportional_to_territory"]
    imputation_method: Optional[Literal["take_from_closest_centroid"]] = None
    columns: Dict[str, ColumnMetadata] = {}

    @model_validator(mode="before")
    @classmethod
    def parse_flexible_date(cls, data: Any) -> Any:
        if isinstance(data, dict):
            adm_date = data.get("orig_adm_state_date")
            if isinstance(adm_date, str):
                for fmt in ("%d.%m.%Y", "%Y-%m-%dT%H:%M:%S"):
                    try:
                        data["orig_adm_state_date"] = datetime.strptime(adm_date, fmt)
                        if data.get("adm_state_date", None) is None:
                            data["adm_state_date"] = data["orig_adm_state_date"]
                        break
                    except ValueError:
                        continue
                else:
                    raise ValueError(f"Date format must be DD.MM.YYYY or ISO 8601, got: {adm_date}")
        return data