from typing import List, Literal, Optional

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
    salary_status: Optional[str] = None


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


class Category(BaseModel):
    id: Optional[int] = None
    name: str


class JobClassification(BaseModel):
    offer_id: int
    clean_title: Optional[str] = None
    level: Optional[str] = None
    category: Optional[str] = None


class CategoryValidationResponse(BaseModel):
    category: Literal[
        "data_analytics",
        "software_it",
        "it_support",
        "finance_accounting",
        "hr_payroll",
        "logistics_supply_chain",
        "administration",
        "sales_customer_service",
        "marketing",
        "project_management",
        "engineering_production",
        "legal_compliance_risk",
        "procurement",
        "customer_operations",
        "unknown",
    ]
