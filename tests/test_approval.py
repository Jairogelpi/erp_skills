from datetime import UTC, datetime

import pytest

from erp_agent_os.approval import ApprovalService


def test_valid_before_expiry():
    now = [datetime(2026, 8, 5, 12, 0, tzinfo=UTC)]
    service = ApprovalService(clock=lambda: now[0])
    service.grant("manager1", "crm.create_opportunity", ttl_seconds=60)

    assert service.is_valid("crm.create_opportunity") is True


def test_invalid_after_expiry():
    now = [datetime(2026, 8, 5, 12, 0, tzinfo=UTC)]
    service = ApprovalService(clock=lambda: now[0])
    service.grant("manager1", "crm.create_opportunity", ttl_seconds=60)

    now[0] = datetime(2026, 8, 5, 12, 1, 1, tzinfo=UTC)

    assert service.is_valid("crm.create_opportunity") is False


def test_different_scope_not_valid():
    service = ApprovalService(clock=lambda: datetime(2026, 8, 5, tzinfo=UTC))
    service.grant("manager1", "crm.create_opportunity", ttl_seconds=60)

    assert service.is_valid("sales.update_amount") is False


def test_nonpositive_ttl_rejected():
    service = ApprovalService(clock=lambda: datetime(2026, 8, 5, tzinfo=UTC))
    with pytest.raises(ValueError):
        service.grant("manager1", "crm.create_opportunity", ttl_seconds=0)


def test_no_approval_ever_granted_is_invalid():
    service = ApprovalService(clock=lambda: datetime(2026, 8, 5, tzinfo=UTC))
    assert service.is_valid("crm.create_opportunity") is False
