from pydantic import BaseModel
from typing import List

from datetime import datetime

#############################
# Models to store timespans #
#############################

class TimeSpan(BaseModel):
    start: datetime
    end: datetime

    def contains(self, date: datetime) -> bool:
        """Check if a date is within the timespan."""
        return self.start <= date <= self.end

class TimeSpanRegistry(BaseModel):
    """
    A model to store all periods between two sequential administrative changes.
    """
    registry = List[TimeSpan] 
