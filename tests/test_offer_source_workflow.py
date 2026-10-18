from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.offer_source_workflow import OfferSourceWorkflow
from offer import JobContract, JobOffer


def make_workflow(*, email_parsers=None, scrapers=None):
    db_query = MagicMock()
    db_insert = MagicMock()
    db_insert.save_offers.return_value = 42
    filter_service = MagicMock()
    filter_service.should_save.return_value = True
    offer_status = MagicMock()
    ai = MagicMock()
    ai.validate_salary_api = AsyncMock(return_value=[])
    salary_processor = MagicMock()
    salary_processor.resolve_contract_type.side_effect = lambda contract, text: contract

    workflow = OfferSourceWorkflow(
        email_parsers=email_parsers or [],
        scrapers=scrapers or [],
        db_query=db_query,
        db_insert=db_insert,
        filter_service=filter_service,
        offer_status=offer_status,
        ai=ai,
        salary_processor=salary_processor,
    )
    return workflow, db_query, db_insert, filter_service, offer_status, ai, salary_processor


@pytest.mark.asyncio
async def test_filtered_offer_is_not_deduplicated_or_saved():
    offer = JobOffer(title="Analyst", company="Acme", location="Warsaw")
    parser = MagicMock(source="RocketJobs")
    parser.fetch_offers = AsyncMock(return_value=[(offer, "offer text", "cache-1")])
    workflow, db_query, db_insert, filter_service, _, ai, _ = make_workflow(email_parsers=[parser])
    filter_service.should_save.return_value = False

    result = await workflow.run()

    assert result == set()
    db_query.find_cross_source_duplicate_id.assert_not_called()
    db_insert.save_offers.assert_not_called()
    ai.validate_salary_api.assert_not_awaited()


@pytest.mark.asyncio
async def test_cross_source_duplicate_is_skipped():
    offer = JobOffer(title="Analyst", company="Acme", location="Warsaw")
    parser = MagicMock(source="RocketJobs")
    parser.fetch_offers = AsyncMock(return_value=[(offer, "offer text", None)])
    workflow, db_query, db_insert, _, _, ai, _ = make_workflow(email_parsers=[parser])
    db_query.find_cross_source_duplicate_id.return_value = 17

    result = await workflow.run()

    assert result == set()
    db_query.find_cross_source_duplicate_id.assert_called_once_with(offer, "email")
    db_insert.save_offers.assert_not_called()
    ai.validate_salary_api.assert_not_awaited()


@pytest.mark.asyncio
async def test_email_offer_without_validated_salary_gets_empty_uop_contract():
    offer = JobOffer(title="Analyst", company="Acme", location="Warsaw")
    parser = MagicMock(source="RocketJobs")
    parser.fetch_offers = AsyncMock(return_value=[(offer, "offer text", None)])
    workflow, db_query, db_insert, _, offer_status, ai, salary_processor = make_workflow(email_parsers=[parser])
    db_query.find_cross_source_duplicate_id.return_value = None

    result = await workflow.run()

    assert result == {42}
    offer_status.get_offer_status.assert_called_once_with(offer)
    db_insert.save_offers.assert_called_once_with(offer, source="RocketJobs")
    ai.validate_salary_api.assert_awaited_once_with("offer text")
    contract = db_insert.save_job_contract.call_args.args[0]
    assert contract == JobContract(offer_id=42, contract_type="UoP")
    salary_processor.resolve_contract_type.assert_called_once_with(contract, "offer text")
    salary_processor.normalize_salary.assert_called_once_with(contract)


@pytest.mark.asyncio
async def test_scraper_offer_keeps_scraper_contract_and_skips_ai_validation():
    record = {
        "title": "Engineer",
        "company": "Acme",
        "location": "Warsaw",
        "salary": "",
        "contract": "Umowa o pracę",
    }
    scraper = MagicMock(source="scraper_linkedin")
    scraper.run_scraper.return_value = [record]
    workflow, db_query, db_insert, _, _, ai, salary_processor = make_workflow(scrapers=[scraper])
    db_query.find_cross_source_duplicate_id.return_value = None

    result = await workflow.run()

    assert result == {42}
    db_query.find_cross_source_duplicate_id.assert_called_once()
    assert db_query.find_cross_source_duplicate_id.call_args.args[1] == "scraper"
    contract = db_insert.save_job_contract.call_args.args[0]
    assert contract.offer_id == 42
    assert contract.contract_type == "UoP"
    assert contract.salary_min_offer is None
    ai.validate_salary_api.assert_not_awaited()
    salary_processor.resolve_contract_type.assert_not_called()
    salary_processor.normalize_salary.assert_called_once_with(contract)
