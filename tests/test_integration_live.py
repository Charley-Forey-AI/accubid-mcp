import os

import pytest

from src.main import client


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_list_databases_when_enabled() -> None:
    if os.getenv("ACCUBID_INTEGRATION", "").strip() != "1":
        pytest.skip("Set ACCUBID_INTEGRATION=1 to run live integration checks")
    data = await client.get_databases()
    assert isinstance(data, list) or isinstance(data, dict)
