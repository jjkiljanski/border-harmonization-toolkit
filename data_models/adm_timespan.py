from pydantic import BaseModel, model_validator
from typing import List

from datetime import datetime

#############################
# Models to store timespans #
#############################

class TimeSpan(BaseModel):
    start: datetime
    end: datetime

    @model_validator(mode='before')
    def check_end_after_start(cls, values):
        """Check that end date is after start date."""
        start = values.get('start')
        end = values.get('end')

        if start and end and end <= start:
            raise ValueError('End date must be after the start date.')

        return values

    def contains(self, date: datetime) -> bool:
        """Check if a date is within the timespan."""
        return self.start <= date <= self.end

class TimeSpanRegistry(BaseModel):
    """
    A model to store all periods between two sequential administrative changes.
    """
    registry: List[TimeSpan] 
