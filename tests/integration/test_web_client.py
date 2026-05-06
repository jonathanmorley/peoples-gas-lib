"""Integration tests for PeoplesGasClient using pytest-recording."""

import os

import pytest

from peoples_gas_lib.client import PeoplesGasClient

USERNAME = os.getenv("PEOPLES_GAS_USERNAME", "test_user")
PASSWORD = os.getenv("PEOPLES_GAS_PASSWORD", "test_pass")


@pytest.mark.vcr("test_login_success.yaml")
async def test_login_success():
    async with PeoplesGasClient() as client:
        result = await client.login(USERNAME, PASSWORD)
        assert result is True
        assert client._logged_in is True


@pytest.mark.vcr("test_login_failure.yaml")
async def test_login_failure():
    async with PeoplesGasClient() as client:
        result = await client.login("wrong_user", "wrong_pass")
        assert result is False
        assert client._logged_in is False


@pytest.mark.vcr("test_full_flow.yaml")
async def test_full_flow():
    async with PeoplesGasClient() as client:
        login_result = await client.login(USERNAME, PASSWORD)
        assert login_result is True

        billing_data = await client.fetch_billing_data()
        assert "balance_due" in billing_data
        assert "usage_mcf" in billing_data


@pytest.mark.vcr("test_full_flow.yaml")
async def test_fetch_billing_data():
    async with PeoplesGasClient() as client:
        await client.login(USERNAME, PASSWORD)
        data = await client.fetch_billing_data()
        assert isinstance(data.get("balance_due"), (float, type(None)))
        assert isinstance(data.get("usage_mcf"), (float, type(None)))
