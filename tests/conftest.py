"""
Shared pytest configuration and fixtures.
"""

from datetime import datetime
from pathlib import Path

import pytest

_RESULTS_DIR = Path(__file__).parent / "result"


def pytest_addoption(parser):
    parser.addoption(
        "--env-file",
        action="store",
        default=None,
        metavar="PATH",
        help="Path to .env file with API keys (enables integration tests)",
    )


@pytest.fixture
def env_file(request):
    """Path to .env file passed via --env-file, or None if not provided."""
    return request.config.getoption("--env-file")


@pytest.fixture
def local_tmp_path(request):
    """Creates tests/result/<test_name>_<timestamp>/ kept after the test for inspection."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_dir = _RESULTS_DIR / f"{request.node.name}_{timestamp}"
    test_dir.mkdir(parents=True)
    return test_dir
