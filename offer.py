from typing import List, Optional

from pydantic import BaseModel


# Add class
class JobOffer(BaseModel):
    title: str
    company: str
    location: str
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    date: Optional[str] = None


class OffersResponse(BaseModel):
    offers: List[JobOffer]
