from typing import List, Optional

from pydantic import BaseModel, Field


# Add class
class JobOffer(BaseModel):
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    title: str
    company: str
    location: str
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None


class OffersResponse(BaseModel):
    offers: List[JobOffer]
