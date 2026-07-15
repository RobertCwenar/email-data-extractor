from datetime import date as Date
from typing import List, Optional

from pydantic import BaseModel


# Add class
class JobOffer(BaseModel):
    date: Date
    title: str
    company: str
    location: str
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None


class OffersResponse(BaseModel):
    offers: List[JobOffer]
