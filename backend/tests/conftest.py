import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import get_settings
from app.services.ai import instruction_safety, llm
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
    # 마무리 대기창을 기본 30초 그대로 두면 테스트마다 실제로 30초를 기다린다.
    # 대기창 길이 자체를 검증하는 테스트는 각자 이 값을 다시 올려 쓴다.
    monkeypatch.setattr(settings, "final_instruction_window_seconds", 0)
    monkeypatch.setattr(settings, "final_instruction_poll_seconds", 0.05)
    monkeypatch.setattr(llm, "_generator", None)
    instruction_safety.reset_reviewer_cache()
    monkeypatch.setattr(analyzer, "_analyzer", None)
    monkeypatch.setattr(studies, "get_slot_generator", lambda: _NoopSlotGenerator())
    with TestClient(app) as test_client:
        yield test_client
    monkeypatch.setattr(store_module, "_store", None)
