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


class SalaryStatisticsOffer(BaseModel):
    count_min: int
    count_max: int
    avg_min: Optional[float] = None
    avg_max: Optional[float] = None
    median_min: Optional[float] = None
    median_max: Optional[float] = None
    std_dev_min: Optional[float] = None
    std_dev_max: Optional[float] = None


class SalaryHistoryRecord(BaseModel):
    id: int
    title: str
    company: str
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    date: Optional[str] = None
    category: Optional[str] = None
    level: Optional[str] = None


class SalaryRule(BaseModel):
    base: float
    range: float


class JobContract(BaseModel):
    offer_id: int
    contract_type: Optional[str] = None
    salary_currency: Optional[str] = None
    salary_period: Optional[str] = None
    salary_min_offer: Optional[float] = None
    salary_max_offer: Optional[float] = None
    salary_min_monthly: Optional[float] = None
    salary_max_monthly: Optional[float] = None


class JobContractResponse(BaseModel):
    contracts: list[JobContract]


class CategoryValidationResponse(BaseModel):
    category: Literal[
        "data_analytics",
        "software_it",
        "it_support",
        "finance_accounting",
        "hr",
        "logistics_supply_chain",
        "administration",
        "sales_customer_service",
        "marketing",
        "project_management",
        "engineering_production",
        "legal_compliance_risk",
        "procurement",
        "customer_operations",
        "medical",
        "unknown",
    ]
