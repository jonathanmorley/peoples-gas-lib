"""Standalone web client for Peoples Gas portal - testable without Home Assistant."""

import logging
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)

# URLs for Peoples Gas portal
LOGIN_URL = "https://peopleseaccount.com/portal/"
VALIDATE_URL = "https://peopleseaccount.com/Portal/Default.aspx/validateLogin"
DASHBOARD_URL = "https://peopleseaccount.com/portal/Dashboard.aspx"
BILLING_URL = "https://peopleseaccount.com/portal/Billing.aspx"


class PeoplesGasClient:
    """Client for interacting with the Peoples Gas web portal."""

    def __init__(self) -> None:
        self.session: Optional[aiohttp.ClientSession] = None
        self._logged_in = False

    async def __aenter__(self) -> "PeoplesGasClient":
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.session:
            await self.session.close()
            self.session = None
        self._logged_in = False

    async def login(self, username: str, password: str) -> bool:
        if self._logged_in:
            return True
        if self.session is None:
            self.session = aiohttp.ClientSession()

        try:
            async with self.session.get(LOGIN_URL) as resp:
                resp.raise_for_status()
                login_page = await resp.text()

            soup = BeautifulSoup(login_page, "html.parser")
            csrf_input = soup.find("input", {"name": "hdnCSRFToken"})
            csrf_value = csrf_input.get("value") if csrf_input else None
            csrf_token: str = csrf_value if isinstance(csrf_value, str) else ""

            login_json = {
                "username": username,
                "password": password,
                "rememberme": False,
                "calledFrom": "LN",
                "ExternalLoginId": "",
                "LoginMode": "1",
            }
            post_headers: dict[str, str] = {
                "Content-Type": "application/json; charset=utf-8",
                "csrftoken": csrf_token,
                "X-Requested-With": "XMLHttpRequest",
            }
            async with self.session.post(
                VALIDATE_URL, json=login_json, headers=post_headers
            ) as response:
                _LOGGER.debug("Login POST status=%s", response.status)
                try:
                    result = await response.json()
                    if "d" in result:
                        import json

                        data = json.loads(result["d"])
                        if isinstance(data, list) and data:
                            data = data[0]
                        if isinstance(data, dict):
                            if "dtResponse" in data and data["dtResponse"]:
                                if data["dtResponse"][0].get("Status") == "0":
                                    return False
                            elif data.get("STATUS") == "0" or data.get("Status") == "0":
                                return False
                except (ValueError, KeyError, json.JSONDecodeError):
                    pass

            async with self.session.get(DASHBOARD_URL) as dash_resp:
                dashboard_text = await dash_resp.text()
                if (
                    "logout" in dashboard_text.lower()
                    or "dashboard" in dashboard_text.lower()
                ):
                    self._logged_in = True
                    return True
            return False
        except aiohttp.ClientError as err:
            _LOGGER.error("Login failed: %s", err)
            return False

    async def fetch_billing_data(self) -> dict:
        """Fetch billing data from the portal. Must be logged in first."""
        if not self._logged_in or not self.session:
            raise RuntimeError("Must login first")

        try:
            async with self.session.get(BILLING_URL, raise_for_status=True) as response:
                text = await response.text()
                soup = BeautifulSoup(text, "html.parser")
                balance_due = None
                balance_elem = soup.find(
                    "span", {"id": "ctl00_ContentPlaceHolder1_lblBalance"}
                )
                if balance_elem:
                    balance_due = balance_elem.text.strip().replace("$", "")
                usage_mcf = None
                usage_elem = soup.find(
                    "span", {"id": "ctl00_ContentPlaceHolder1_lblUsage"}
                )
                if usage_elem:
                    usage_text = usage_elem.text.strip()
                    usage_mcf = float(usage_text.replace("MCF", "").strip())
                return {
                    "balance_due": float(balance_due) if balance_due else None,
                    "usage_mcf": usage_mcf,
                }
        except aiohttp.ClientError as err:
            _LOGGER.error("Failed to fetch billing data: %s", err)
            raise
