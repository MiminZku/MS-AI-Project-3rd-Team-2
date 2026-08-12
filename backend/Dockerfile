# Azure Container Apps 배포용 이미지 (deploy-backend.yml에서 `az acr build`로 빌드)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# 의존성 레이어를 먼저 캐싱
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# 비루트 실행
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

# Container Apps는 PORT 환경변수를 주입한다. WebSocket 서버이므로 워커는 1개 유지(세션 sticky, C1).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1 --proxy-headers"]
