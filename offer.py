from typing import List, Optional

from pydantic import BaseModel


# Add class
class JobOffer(BaseModel):
    id: Optional[int] = None

    title: str
    company: str
    location: str
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    date: Optional[str] = None
    url: Optional[str] = None


class OffersResponse(BaseModel):
    offers: List[JobOffer]


class Company(BaseModel):
    id: Optional[int] = None
    name: str


class JobLink(BaseModel):
    offer_id: int
    url: str
    source: str
    created_at: str


class JobDetails(BaseModel):
    offer_id: int

    description: Optional[str] = None
    requirements: list[str]

    employment_type: Optional[str] = None
    remote: Optional[bool] = None


class JobRawData(BaseModel):
    offer_id: int
    source: str
    raw_json: dict
    scraped_at: str
