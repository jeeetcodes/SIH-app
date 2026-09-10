from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    # Enter the client context so FastAPI's lifespan creates all ORM tables.
    with TestClient(app) as test_client:
        yield test_client
