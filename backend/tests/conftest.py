import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import get_settings
from app.services.ai import llm
from app.services.report import analyzer
from app.services import store as store_module
from app.api.routes import studies


class _NoopSlotGenerator:
    async def generate(self, **_: object) -> list[object]:
        return []


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch):
    # 테스트는 항상 인메모리 스토어에서 시작 (REDIS_URL 유무와 무관하게 격리)
    monkeypatch.setattr(store_module, "_store", store_module.InMemoryStore())
    settings = get_settings()
    monkeypatch.setattr(settings, "azure_openai_endpoint", "")
    monkeypatch.setattr(settings, "azure_openai_api_key", "")
    monkeypatch.setattr(llm, "_generator", None)
    monkeypatch.setattr(analyzer, "_analyzer", None)
    monkeypatch.setattr(studies, "get_slot_generator", lambda: _NoopSlotGenerator())
    with TestClient(app) as test_client:
        yield test_client
    monkeypatch.setattr(store_module, "_store", None)
