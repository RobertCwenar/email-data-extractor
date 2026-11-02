from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.offer_source_workflow import OfferSourceWorkflow
from offer import JobContract, JobOffer


def make_workflow(*, email_parsers=None, scrapers=None, offline_scrapers=False):
    db_query = MagicMock()
    db_query.find_same_source_duplicate_id.return_value = None
    db_query.has_job_contract.return_value = False
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
        offline_scrapers=offline_scrapers,
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
    db_query.find_same_source_duplicate_id.assert_not_called()
    db_insert.save_offers.assert_not_called()
    ai.validate_salary_api.assert_not_awaited()


@pytest.mark.asyncio
async def test_offer_is_deduplicated_only_against_its_exact_source():
    offer = JobOffer(title="Analyst", company="Acme", location="Warsaw")
    parser = MagicMock(source="RocketJobs")
    parser.fetch_offers = AsyncMock(return_value=[(offer, "offer text", None)])
    workflow, db_query, db_insert, _, _, ai, _ = make_workflow(email_parsers=[parser])

    result = await workflow.run()

    assert result == {42}
    db_query.find_same_source_duplicate_id.assert_called_once_with(offer, "RocketJobs")
    db_insert.save_offers.assert_called_once_with(offer, source="RocketJobs")
    ai.validate_salary_api.assert_awaited_once_with("offer text")


@pytest.mark.asyncio
async def test_email_offer_without_validated_salary_gets_empty_uop_contract():
    offer = JobOffer(title="Analyst", company="Acme", location="Warsaw")
    parser = MagicMock(source="RocketJobs")
    parser.fetch_offers = AsyncMock(return_value=[(offer, "offer text", None)])
    parser.commit_processed_messages = MagicMock()
    workflow, db_query, db_insert, _, offer_status, ai, salary_processor = make_workflow(email_parsers=[parser])
    result = await workflow.run()

    assert result == {42}
    offer_status.get_offer_status.assert_called_once_with(offer)
    db_insert.save_offers.assert_called_once_with(offer, source="RocketJobs")
    ai.validate_salary_api.assert_awaited_once_with("offer text")
    contract = db_insert.save_job_contract.call_args.args[0]
    assert contract == JobContract(offer_id=42, contract_type="UoP")
    salary_processor.resolve_contract_type.assert_called_once_with(contract, "offer text")
    salary_processor.normalize_salary.assert_called_once_with(contract)
    parser.commit_processed_messages.assert_called_once_with()


@pytest.mark.asyncio
async def test_email_cache_is_not_committed_when_saving_contract_fails():
    offer = JobOffer(title="Analyst", company="Acme", location="Warsaw")
    parser = MagicMock(source="RocketJobs")
    parser.fetch_offers = AsyncMock(return_value=[(offer, "offer text", "cache-1")])
    parser.commit_processed_messages = MagicMock()
    workflow, db_query, db_insert, _, _, _, _ = make_workflow(email_parsers=[parser])
    db_insert.save_job_contract.side_effect = RuntimeError("temporary database failure")

    with pytest.raises(RuntimeError, match="temporary database failure"):
        await workflow.run()

    parser.commit_processed_messages.assert_not_called()


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
    result = await workflow.run()

    assert result == {42}
    same_source_args = db_query.find_same_source_duplicate_id.call_args.args
    assert same_source_args[0].title == "Engineer"
    assert same_source_args[1] == "scraper_linkedin"
    contract = db_insert.save_job_contract.call_args.args[0]
    assert contract.offer_id == 42
    assert contract.contract_type == "UoP"
    assert contract.salary_min_offer is None
    ai.validate_salary_api.assert_not_awaited()
    salary_processor.resolve_contract_type.assert_not_called()
    salary_processor.normalize_salary.assert_called_once_with(contract)


@pytest.mark.asyncio
async def test_existing_same_source_offer_with_contract_is_not_inserted_again():
    offer = JobOffer(title="Analyst", company="Acme", location="Warsaw")
    parser = MagicMock(source="RocketJobs")
    parser.fetch_offers = AsyncMock(return_value=[(offer, "offer text", "cache-1")])
    workflow, db_query, db_insert, _, _, ai, _ = make_workflow(email_parsers=[parser])
    db_query.find_same_source_duplicate_id.return_value = 42
    db_query.has_job_contract.return_value = True

    result = await workflow.run()

    assert result == {42}
    db_insert.save_offers.assert_not_called()
    db_insert.save_job_contract.assert_not_called()
    ai.validate_salary_api.assert_not_awaited()


@pytest.mark.asyncio
async def test_existing_same_source_offer_without_contract_is_completed_in_place():
    offer = JobOffer(title="Analyst", company="Acme", location="Warsaw")
    parser = MagicMock(source="RocketJobs")
    parser.fetch_offers = AsyncMock(return_value=[(offer, "offer text", "cache-1")])
    workflow, db_query, db_insert, _, _, ai, _ = make_workflow(email_parsers=[parser])
    db_query.find_same_source_duplicate_id.return_value = 42
    db_query.has_job_contract.return_value = False

    result = await workflow.run()

    assert result == {42}
    db_insert.save_offers.assert_not_called()
    ai.validate_salary_api.assert_awaited_once_with("offer text")
    contract = db_insert.save_job_contract.call_args.args[0]
    assert contract.offer_id == 42


@pytest.mark.asyncio
async def test_offline_scraper_loads_saved_offers_without_running_scraper():
    record = {
        "title": "Engineer",
        "company": "Acme",
        "location": "Warsaw",
        "salary": "",
        "contract": "Permanent",
    }
    scraper = MagicMock(source="scraper_linkedin")
    scraper.load_saved_offers.return_value = [record]
    workflow, _, db_insert, _, _, ai, _ = make_workflow(scrapers=[scraper], offline_scrapers=True)

    result = await workflow.run()

    assert result == {42}
    scraper.run_scraper.assert_not_called()
    scraper.load_saved_offers.assert_called_once_with()
    db_insert.save_offers.assert_called_once()
    ai.validate_salary_api.assert_not_awaited()


@pytest.mark.asyncio
async def test_failed_scraper_uses_saved_output_and_continues():
    record = {
        "title": "Engineer",
        "company": "Acme",
        "location": "Warsaw",
        "salary": "",
        "contract": "Permanent",
    }
    scraper = MagicMock(source="scraper_linkedin")
    scraper.run_scraper.side_effect = RuntimeError("site blocked the request")
    scraper.load_saved_offers.return_value = [record]
    workflow, _, db_insert, _, _, ai, _ = make_workflow(scrapers=[scraper])

    result = await workflow.run()

    assert result == {42}
    scraper.load_saved_offers.assert_called_once_with()
    db_insert.save_offers.assert_called_once()
    ai.validate_salary_api.assert_not_awaited()
