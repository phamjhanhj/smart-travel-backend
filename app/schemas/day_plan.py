from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import Date


class DayPlanOut(BaseModel):
    id: UUID
    trip_id: UUID
    day_number: int
    date: Date
