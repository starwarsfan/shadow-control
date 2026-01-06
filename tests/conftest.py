"""Root conftest für alle Tests."""

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests automatically."""
    return


@pytest.fixture(autouse=True)
def expected_lingering_tasks() -> bool:
    """Allow lingering tasks in tests."""
    return True


@pytest.fixture(autouse=True)
def expected_lingering_timers() -> bool:
    """Allow lingering timers in tests."""
    return True
