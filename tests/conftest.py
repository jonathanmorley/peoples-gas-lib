import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


def _sanitize_response(response):
    """Remove sensitive data from recorded responses."""
    username = os.getenv("PEOPLES_GAS_USERNAME", "")
    password = os.getenv("PEOPLES_GAS_PASSWORD", "")
    if not username or not password:
        return response
    body = response["body"].get("string", b"").decode("utf-8", errors="ignore")
    body = body.replace(username, "test_user").replace(password, "test_pass")
    response["body"]["string"] = body.encode("utf-8")
    return response


@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_headers": ["authorization", "csrftoken", "cookie", "set-cookie"],
        "filter_query_parameters": ["t"],
        "before_record_response": _sanitize_response,
        "match_on": ["uri", "method"],
    }


@pytest.fixture(scope="module")
def vcr_cassette_dir(request):
    return str(Path(__file__).parent / "fixtures" / "vcr")


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "vcr: mark test as using pytest-recording for HTTP recording/replay"
    )
