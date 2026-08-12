"""환경설정. 값은 .env 또는 Container Apps 환경변수/시크릿에서 주입된다."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ai-interviewer-backend"
    environment: str = "local"
    log_level: str = "INFO"

    cors_origins: str = "http://localhost:5173,http://localhost:5174,https://victorious-pond-0765baa0f.7.azurestaticapps.net,https://orange-sand-0bb92740f.7.azurestaticapps.net"

    # 참관자가 세션을 만들면 발급되는 응답자용 링크의 base URL
    interviewee_base_url: str = "http://localhost:5173"

    # 대시보드 REST API 보호용. 비어 있으면 인증을 건너뛴다(로컬/데모).
    admin_token: str = ""

    # D4: 세션 상태 + 지시 큐 외부화. 비어 있으면 인메모리 폴백.
    redis_url: str = ""
    session_ttl_seconds: int = 60 * 60 * 4

    # Azure OpenAI — 비어 있으면 스텁 생성기로 폴백
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_chat_deployment: str = "gpt-4o"
    azure_openai_timekeeper_deployment: str = "gpt-4o-mini"

    # Azure Speech: TTS + TTS Avatar 전용 (STT는 미사용, D9)
    azure_speech_key: str = ""
    azure_speech_region: str = ""

    # D8: gpt-transcribe | gpt-live-transcribe (한국어 실측 후 결정)
    stt_model: str = "gpt-transcribe"

    # D5: 타임키퍼 폴링 주기(초)
    timekeeper_interval_seconds: int = 60

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def use_redis(self) -> bool:
        return bool(self.redis_url)

    @property
    def use_azure_openai(self) -> bool:
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
