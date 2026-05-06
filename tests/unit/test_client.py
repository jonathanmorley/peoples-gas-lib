import json
from pathlib import Path

import pytest
import aiohttp
from bs4 import BeautifulSoup

from peoples_gas_lib.client import (
    PeoplesGasClient,
    LOGIN_URL,
    VALIDATE_URL,
    DASHBOARD_URL,
    BILLING_URL,
)


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text()


def extract_csrf_token(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    csrf_input = soup.find("input", {"name": "hdnCSRFToken"})
    return csrf_input.get("value", "") if csrf_input else ""


class FakeResponse:
    def __init__(self, text_value=None, json_value=None, status=200):
        self._text = text_value
        self._json = json_value
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def text(self):
        return self._text

    async def json(self):
        return self._json

    def raise_for_status(self):
        pass


class FakeSession:
    def __init__(self, get_responses=None, post_responses=None):
        self._get_responses = get_responses or []
        self._post_responses = post_responses or []
        self._get_count = 0
        self._post_count = 0
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def get(self, *args, **kwargs):
        if self._get_count < len(self._get_responses):
            resp = self._get_responses[self._get_count]
            self._get_count += 1
            return resp
        raise RuntimeError("No more GET responses")

    def post(self, *args, **kwargs):
        if self._post_count < len(self._post_responses):
            resp = self._post_responses[self._post_count]
            self._post_count += 1
            return resp
        raise RuntimeError("No more POST responses")

    async def close(self):
        self.closed = True


class TestLoginPageParsing:
    def test_extract_csrf_token_present(self):
        html = load_fixture("login_page.html")
        token = extract_csrf_token(html)
        assert token == "test_csrf_token_12345"

    def test_extract_csrf_token_missing(self):
        html = "<html><body>No CSRF token here</body></html>"
        token = extract_csrf_token(html)
        assert token == ""

    def test_extract_login_form_fields(self):
        html = load_fixture("login_page.html")
        soup = BeautifulSoup(html, "html.parser")
        login_input = soup.find("input", {"id": "txtLogin"})
        pwd_input = soup.find("input", {"id": "txtpwd"})
        assert login_input is not None
        assert pwd_input is not None


class TestLoginResponseHandling:
    def test_login_success_response(self):
        response_json = json.loads(load_fixture("login_success_response.json"))
        data = json.loads(response_json["d"])
        assert isinstance(data, list)
        assert data[0]["Status"] == "1"

    def test_login_failure_response(self):
        response_json = json.loads(load_fixture("login_failure_response.json"))
        data = json.loads(response_json["d"])
        assert isinstance(data, list)
        assert data[0]["Status"] == "0"


class TestDashboardParsing:
    def test_dashboard_logged_in(self):
        html = load_fixture("dashboard_logged_in.html")
        is_logged_in = "logout" in html.lower() or "dashboard" in html.lower()
        assert is_logged_in is True


class TestBillingDataParsing:
    def test_extract_balance_due(self):
        html = load_fixture("billing_page.html")
        soup = BeautifulSoup(html, "html.parser")
        balance_elem = soup.find("span", {"id": "ctl00_ContentPlaceHolder1_lblBalance"})
        balance_due = None
        if balance_elem:
            balance_due = balance_elem.text.strip().replace("$", "")
        assert balance_due == "123.45"

    def test_extract_usage_mcf(self):
        html = load_fixture("billing_page.html")
        soup = BeautifulSoup(html, "html.parser")
        usage_elem = soup.find("span", {"id": "ctl00_ContentPlaceHolder1_lblUsage"})
        usage_mcf = None
        if usage_elem:
            usage_text = usage_elem.text.strip()
            usage_mcf = float(usage_text.replace("MCF", "").strip())
        assert usage_mcf == 1234.56


class TestPeoplesGasClientUnit:
    @pytest.mark.asyncio
    async def test_client_initialization(self):
        client = PeoplesGasClient()
        assert client.session is None
        assert client._logged_in is False

    @pytest.mark.asyncio
    async def test_context_manager(self):
        client = PeoplesGasClient()
        async with client as c:
            assert c.session is not None
            assert isinstance(c.session, aiohttp.ClientSession)
        assert client.session is None
        assert client._logged_in is False

    @pytest.mark.asyncio
    async def test_login_already_logged_in(self):
        client = PeoplesGasClient()
        fake_session = FakeSession()
        client.session = fake_session
        client._logged_in = True
        result = await client.login("user", "pass")
        assert result is True

    @pytest.mark.asyncio
    async def test_login_success(self):
        login_page_html = load_fixture("login_page.html")
        login_success = json.loads(load_fixture("login_success_response.json"))
        dashboard_html = load_fixture("dashboard_logged_in.html")

        fake_session = FakeSession(
            get_responses=[
                FakeResponse(text_value=login_page_html),
                FakeResponse(text_value=dashboard_html),
            ],
            post_responses=[
                FakeResponse(json_value=login_success),
            ],
        )

        client = PeoplesGasClient()
        client.session = fake_session

        result = await client.login("test_user", "test_pass")

        assert result is True
        assert client._logged_in is True

    @pytest.mark.asyncio
    async def test_login_failure(self):
        login_page_html = load_fixture("login_page.html")
        login_failure = json.loads(load_fixture("login_failure_response.json"))

        fake_session = FakeSession(
            get_responses=[
                FakeResponse(text_value=login_page_html),
            ],
            post_responses=[
                FakeResponse(json_value=login_failure),
            ],
        )

        client = PeoplesGasClient()
        client.session = fake_session  # type: ignore[assignment]

        result = await client.login("wrong_user", "wrong_pass")

        assert result is False
        assert client._logged_in is False

    @pytest.mark.asyncio
    async def test_fetch_billing_data_not_logged_in(self):
        client = PeoplesGasClient()
        with pytest.raises(RuntimeError, match="Must login first"):
            await client.fetch_billing_data()

    @pytest.mark.asyncio
    async def test_fetch_billing_data_success(self):
        client = PeoplesGasClient()
        client._logged_in = True
        billing_html = load_fixture("billing_page.html")

        fake_session = FakeSession(
            get_responses=[
                FakeResponse(text_value=billing_html),
            ]
        )
        client.session = fake_session  # type: ignore[assignment]

        data = await client.fetch_billing_data()

        assert data["balance_due"] == 123.45
        assert data["usage_mcf"] == 1234.56

    @pytest.mark.asyncio
    async def test_http_error_handling(self):
        class ErrorSession:
            def get(self, *args, **kwargs):
                raise aiohttp.ClientError("Connection failed")

        client = PeoplesGasClient()
        client.session = ErrorSession()  # type: ignore[assignment]

        result = await client.login("user", "pass")
        assert result is False


class TestConstants:
    def test_urls_defined(self):
        assert LOGIN_URL == "https://peopleseaccount.com/portal/"
        assert (
            VALIDATE_URL
            == "https://peopleseaccount.com/Portal/Default.aspx/validateLogin"
        )
        assert DASHBOARD_URL == "https://peopleseaccount.com/portal/Dashboard.aspx"
        assert BILLING_URL == "https://peopleseaccount.com/portal/Billing.aspx"
