"""환경설정. 값은 .env 또는 Container Apps 환경변수/시크릿에서 주입된다."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ai-interviewer-backend"
    environment: str = "local"
    log_level: str = "INFO"

    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175,https://victorious-pond-0765baa0f.7.azurestaticapps.net,https://orange-sand-0bb92740f.7.azurestaticapps.net"

    # 참관자가 세션을 만들면 발급되는 응답자용 링크의 base URL
    interviewee_base_url: str = "http://localhost:5173"

    # 대시보드 REST API 보호용. 비어 있으면 인증을 건너뛴다(로컬/데모).
    admin_token: str = ""

    # Client 프로젝트 범위 토큰 서명 키. 운영 환경에서는 반드시 환경 변수로 주입한다.
    client_access_token_secret: str = ""
    client_access_token_ttl_seconds: int = 60 * 60 * 8

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

    # 실시간 웹소켓 모델 (GPT-4o Realtime 또는 GPT-Live-Transcribe)
    azure_openai_realtime_api_version: str = "2026-06-01-preview"
    azure_openai_realtime_stt_deployment: str = "gpt-live-transcribe"
    azure_openai_realtime_translate_deployment: str = "gpt-realtime-translate"

    # STT 모델 (D8): gpt-transcribe | gpt-live-transcribe
    stt_model: str = "whisper"

    # D5: 타임키퍼 폴링 주기(초)
    timekeeper_interval_seconds: int = 60

    # 인터뷰 마무리 직전, 참관자가 추가 지시를 넣을 수 있도록 기다리는 시간(초).
    # 이 시간 안에 지시가 들어오면 그 질문을 하고 대기창을 한 번 더 연다.
    final_instruction_window_seconds: int = 30
    # 대기창 동안 지시 큐를 확인하는 주기(초). 지시가 들어오면 남은 시간을 기다리지 않는다.
    final_instruction_poll_seconds: float = 2.0

    # Azure Communication Services (WebRTC)
    acs_connection_string: str = ""

    # Azure Blob Storage (녹화 영상, 질문 파일, 리포트 저장용)
    azure_storage_connection_string: str = ""
    azure_storage_container_name: str = "recordings"

    # 녹화본 전용 컨테이너 이름.
    # recordings.py가 이 이름으로 참조하는데 정의가 없어 Blob 업로드 경로에서
    # AttributeError -> 500 이 났고, 녹화가 한 건도 저장되지 않았다.
    azure_storage_recordings_container: str = "recordings"

    # Azure Cosmos DB (NoSQL 데이터베이스)
    azure_cosmos_endpoint: str = ""
    azure_cosmos_key: str = ""
    azure_cosmos_database: str = "InterviewDB"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def use_redis(self) -> bool:
        return bool(self.redis_url)

    @property
    def use_cosmos(self) -> bool:
        return bool(self.azure_cosmos_endpoint and self.azure_cosmos_key)

    @property
    def use_azure_openai(self) -> bool:
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
