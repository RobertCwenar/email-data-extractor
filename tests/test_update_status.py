from unittest.mock import AsyncMock, Mock, patch

import pytest

from modules.salary_recovery import SalaryRecovery


@pytest.mark.asyncio
async def test_recover_salary_from_mail():
    db_query = Mock()
    db_insert = Mock()
    db_update = Mock()
    ai = Mock()
    salary_processor = Mock()

    db_query.get_job_contracts.return_value = []

    db_query.get_offer.return_value = (
        20,
        "Data Analyst",
        "ABC",
        "Wrocław",
        None,
        None,
        "2026-09-22",
        "RocketJobs",
        None,
        "new",
    )

    contract = Mock(
        offer_id=None,
        salary_min_monthly=8000,
        salary_max_monthly=10000,
    )

    salary_processor.get_salary_status.return_value = "offer"

    recovery = SalaryRecovery(
        db_query=db_query,
        db_insert=db_insert,
        db_update=db_update,
        ai=ai,
        email_config={},
        salary_processor=salary_processor,
    )

    setattr(recovery, "_recover_from_mail", AsyncMock(return_value=[contract]))

    result = await recovery.recover(20)

    assert result is True

    assert contract.offer_id == 20

    db_insert.save_job_contract.assert_called_once_with(contract)

    db_update.update_offer_salary.assert_called_once_with(
        20,
        8000,
        10000,
        "offer",
    )


@pytest.mark.asyncio
async def test_recover_does_nothing_when_salary_not_found():
    db_query = Mock()
    db_insert = Mock()
    db_update = Mock()
    ai = Mock()
    salary_processor = Mock()

    db_query.get_job_contracts.return_value = []

    db_query.get_offer.return_value = (
        20,
        "Data Analyst",
        "ABC",
        "Wrocław",
        None,
        None,
        "2026-09-22",
        "RocketJobs",
        None,
        "new",
    )

    db_query.get_previous_offer_with_salary.return_value = None

    recovery = SalaryRecovery(
        db_query=db_query,
        db_insert=db_insert,
        db_update=db_update,
        ai=ai,
        email_config={},
        salary_processor=salary_processor,
    )

    with patch.object(
        recovery,
        "_recover_from_mail",
        new=AsyncMock(return_value=[]),
    ):
        result = await recovery.recover(20)

    assert result is True

    db_insert.save_job_contract.assert_called_once()
    db_update.update_offer_salary.assert_not_called()


@pytest.mark.asyncio
async def test_recover_does_nothing_when_offer_does_not_exist():
    db_query = Mock()
    db_insert = Mock()
    db_update = Mock()
    ai = Mock()
    salary_processor = Mock()

    db_query.get_job_contracts.return_value = []
    db_query.get_offer.return_value = None

    recovery = SalaryRecovery(
        db_query=db_query,
        db_insert=db_insert,
        db_update=db_update,
        ai=ai,
        email_config={},
        salary_processor=salary_processor,
    )

    result = await recovery.recover(20)

    assert result is False

    db_insert.save_job_contract.assert_not_called()
    db_update.update_offer_salary.assert_not_called()


@pytest.mark.asyncio
async def test_recover_does_nothing_when_contract_already_exists():
    db_query = Mock()
    db_insert = Mock()
    db_update = Mock()
    ai = Mock()
    salary_processor = Mock()

    db_query.get_job_contracts.return_value = [
        (
            1,
            "UoP",
            "PLN",
            "monthly",
            8000,
            10000,
            8000,
            10000,
        )
    ]

    recovery = SalaryRecovery(
        db_query=db_query,
        db_insert=db_insert,
        db_update=db_update,
        ai=ai,
        email_config={},
        salary_processor=salary_processor,
    )

    result = await recovery.recover(20)

    assert result is False

    db_query.get_offer.assert_not_called()
    db_insert.save_job_contract.assert_not_called()
    db_update.update_offer_salary.assert_not_called()


@pytest.mark.asyncio
async def test_recover_uses_folder_from_source():
    db_query = Mock()
    db_insert = Mock()
    db_update = Mock()
    ai = Mock()
    salary_processor = Mock()

    db_query.get_job_contracts.return_value = []
    db_query.get_offer.return_value = (
        14453,
        "Kontroler Finansowy",
        "Benefit Systems",
        "Wrocław, Krzyki",
        None,
        None,
        "2026-10-01",
        "Pracuj.pl",
        None,
        "new",
    )

    contract = Mock(
        offer_id=None,
        salary_min_monthly=8000,
        salary_max_monthly=12000,
    )

    salary_processor.get_salary_status.return_value = "offer"

    recovery = SalaryRecovery(
        db_query=db_query,
        db_insert=db_insert,
        db_update=db_update,
        ai=ai,
        email_config={},
        salary_processor=salary_processor,
    )

    with patch.object(
        recovery,
        "_recover_from_mail",
        new=AsyncMock(return_value=[contract]),
    ) as recover_from_mail:
        result = await recovery.recover(14453)

        recover_from_mail.assert_awaited_once_with(
            title="Kontroler Finansowy",
            company="Benefit Systems",
            mail_date="2026-10-01",
            folder_name="PRACA",
        )

    assert result is True


@pytest.mark.asyncio
async def test_recover_salary_from_previous_offer():
    db_query = Mock()
    db_insert = Mock()
    db_update = Mock()
    ai = Mock()
    salary_processor = Mock()

    db_query.get_job_contracts.return_value = []

    db_query.get_offer.return_value = (
        14453,
        "Kontroler Finansowy",
        "Benefit Systems",
        "Wrocław, Krzyki",
        None,
        None,
        "2026-10-01",
        "Pracuj.pl",
        None,
        "new",
    )

    db_query.get_previous_offer_with_salary.return_value = (
        123,
        7450,
        11100,
        "estimated",
        "UoP",
        "PLN",
        "monthly",
        7450,
        11100,
        7450,
        11100,
    )

    recovery = SalaryRecovery(
        db_query=db_query,
        db_insert=db_insert,
        db_update=db_update,
        ai=ai,
        email_config={},
        salary_processor=salary_processor,
    )

    with patch.object(
        recovery,
        "_recover_from_mail",
        new=AsyncMock(return_value=[]),
    ):
        result = await recovery.recover(14453)

    assert result is True

    db_update.update_offer_salary.assert_called_once_with(
        14453,
        7450,
        11100,
        "estimated",
    )
