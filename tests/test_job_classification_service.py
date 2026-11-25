from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.job_classification_service import JobClassificationService
from offer import JobContract


def make_service():
    queries = MagicMock()
    queries.db._connect.return_value.__enter__.return_value = MagicMock()
    updates = MagicMock()
    inserts = MagicMock()
    classifier = MagicMock()
    estimator = MagicMock()
    processor = MagicMock()

    def normalize(contract):
        if contract.salary_period == "hourly" and contract.salary_min_offer is not None:
            contract.salary_min_monthly = contract.salary_min_offer * 168
            contract.salary_max_monthly = contract.salary_max_offer * 168
        return contract

    processor.normalize_salary.side_effect = normalize
    processor.select_contract.side_effect = lambda contracts: contracts[0] if contracts else None
    processor.get_salary_status.return_value = "offer"

    return (
        JobClassificationService(queries, updates, inserts, classifier, estimator, processor),
        queries,
        updates,
        processor,
    )


@pytest.mark.asyncio
async def test_classification_reuses_title_lookup_and_avoids_rechecking_details():
    service, queries, updates, _ = make_service()
    queries.get_jobs_for_classification.return_value = [
        (1, "Junior Data Analyst", "Acme", "2026-11-25", False),
        (2, "Junior Data Analyst", "Other Co", "2026-11-25", False),
    ]
    queries.get_classification_by_title.return_value = None
    service.classifier.classify_level.return_value = "junior"
    service.classifier.classify_category = AsyncMock(return_value="data_analytics")

    await service.process_jobs()

    queries.get_classification_by_title.assert_called_once_with("Junior Data Analyst")
    queries.job_details_exists.assert_not_called()
    service.db_insert.save_job_details.assert_any_call(1, "Junior Data Analyst", "junior", "data_analytics")
    service.db_insert.save_job_details.assert_any_call(2, "Junior Data Analyst", "junior", "data_analytics")
    assert service.db_insert.save_job_details.call_count == 2
    updates.update_job_category.assert_not_called()


@pytest.mark.asyncio
async def test_salary_estimation_batches_updates_and_returns_affected_offer_ids():
    service, queries, updates, _ = make_service()
    queries.get_job_contracts_for_salary_estimator.return_value = [
        (8, 21, "Data Analyst", "Acme", "2026-11-25", "junior", "data_analytics"),
        (9, 21, "Data Analyst", "Acme", "2026-11-25", "junior", "data_analytics"),
    ]
    service.salary_estimator.salary_logic.return_value = (7000, 9000)
    conn = queries.db._connect.return_value.__enter__.return_value

    result = await service.process_salary_estimations()

    assert result == {21}
    updates.update_offer_salaries.assert_called_once_with([(7000, 9000, "estimated", 21)], conn)
    updates.update_job_contract_salaries.assert_called_once_with(
        [
            ("UoP", "PLN", "monthly", 7000, 9000, 8),
            ("UoP", "PLN", "monthly", 7000, 9000, 9),
        ],
        conn,
    )


@pytest.mark.asyncio
async def test_salary_selection_normalizes_contracts_updates_changed_rows_and_offer():
    service, queries, updates, processor = make_service()
    queries.get_job_contracts_for_offers.return_value = [
        (8, 21, "B2B", "PLN", "hourly", 50, 60, None, None),
    ]

    await service.process_salary_selection({21})

    contract = processor.normalize_salary.call_args.args[0]
    conn = queries.db._connect.return_value.__enter__.return_value
    assert contract == JobContract(
        offer_id=21,
        contract_type="B2B",
        salary_currency="PLN",
        salary_period="hourly",
        salary_min_offer=50,
        salary_max_offer=60,
        salary_min_monthly=8400,
        salary_max_monthly=10080,
    )
    updates.update_job_contract_monthlies.assert_called_once_with([(8400, 10080, 8)], conn)
    updates.update_offer_salaries.assert_called_once_with([(8400, 10080, "offer", 21)], conn)


@pytest.mark.asyncio
async def test_salary_selection_skips_offer_update_when_no_contract_is_selected():
    service, queries, updates, processor = make_service()
    queries.get_job_contracts_for_offers.return_value = []
    processor.select_contract.return_value = None

    await service.process_salary_selection({21})

    processor.select_contract.assert_called_once_with([])
    updates.update_offer_salaries.assert_not_called()
    updates.update_job_contract_monthlies.assert_not_called()
