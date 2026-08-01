# =====================
# File: fin-tests/PROD/conftest.py
# =====================
# Provides CLI options early (parse time) and a shared env_config fixture.

import os
import pytest


def pytest_addoption(parser):  # ensures options exist before tests collect
    try:
        parser.addoption(
            "--env",
            action="store",
            default=os.getenv("MF_ENV", "prod"),
            choices=["prod", "stg"],
            help="Target environment: prod or stg (default: prod)",
        )
    except ValueError:
        # A sibling/ancestor conftest.py (e.g. fin-tests/conftest.py) already
        # registered --env when both are loaded together; reuse that one.
        pass
    try:
        parser.addoption(
            "--base-url",
            action="store",
            default=None,
            help="Base URL for the test environment",
        )
    except ValueError:
        # pytest-playwright already registered --base-url, skip
        pass
    parser.addoption(
        "--swap-assets",
        action="store_true",
        default=bool(int(os.getenv("MF_SWAP_ASSETS", "0"))),
        help="Also rewrite asset URLs (wp-content) to chosen base host",
    )


@pytest.fixture(scope="session")
def env_config(pytestconfig):
    env = pytestconfig.getoption("--env")
    base_override: str = pytestconfig.getoption("--base-url")
    swap_assets: bool = pytestconfig.getoption("--swap-assets")
    if base_override:
        base = base_override.rstrip("/")
    else:
        base = "https://www.missionfed.com" if env == "prod" else "https://stage.missionfed.com"
    return {"env": env, "base_url": base, "swap_assets": swap_assets}
