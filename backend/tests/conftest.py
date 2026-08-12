import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import store as store_module


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch):
    # 테스트는 항상 인메모리 스토어에서 시작 (REDIS_URL 유무와 무관하게 격리)
    monkeypatch.setattr(store_module, "_store", store_module.InMemoryStore())
    with TestClient(app) as test_client:
        yield test_client
    monkeypatch.setattr(store_module, "_store", None)
