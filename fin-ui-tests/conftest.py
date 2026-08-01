import pytest


def pytest_addoption(parser):
    try:
        parser.addoption(
            "--env",
            action="store",
            default="stg",
            choices=["stg", "prod"],
            help="Target environment: stg or prod (default: stg)",
        )
    except ValueError:
        pass


@pytest.fixture(scope="session")
def env(request):
    return request.config.getoption("--env")
