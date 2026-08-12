# 3자 개입형 실시간 AI 인터뷰 시스템

인터뷰이는 AI 진행자와 대화하고, 뒤에서 참관자(리서처)가 실시간으로 AI에게 지시를 주입해
인터뷰 방향을 조종한다. 설계 근거와 결정사항은 [Architecture.md](Architecture.md)가 단일 소스다.

- Azure 리소스 생성 + CI/CD 연결: **[docs/azure-setup.md](docs/azure-setup.md)**

---

## 저장소 구조

```
.
├── .github/workflows/
│   ├── deploy-backend.yml                 # backend/ 변경 시: 테스트 → ACR 빌드 → Container Apps
│   ├── deploy-frontend-interviewee.yml    # 인터뷰이 웹 → Static Web App
│   └── deploy-frontend-dashboard.yml      # 참관자 대시보드 → 별도 Static Web App
├── backend/                               # FastAPI (WebSocket 오케스트레이터)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                        # 엔트리포인트, 라우터 등록
│   │   ├── core/config.py                 # 환경설정 (.env / Container Apps 환경변수)
│   │   ├── api/
│   │   │   ├── deps.py                    # 관리자 인증, 세션 로딩
│   │   │   ├── routes/                    # /health, /api/sessions
│   │   │   └── ws/                        # /ws/interview/{id}, /ws/observer/{id}
│   │   ├── schemas/                       # 도메인 모델 + WebSocket 메시지 계약
│   │   └── services/
│   │       ├── store.py                   # 세션 상태 + 지시 큐 (Redis / 인메모리 폴백)
│   │       ├── orchestrator.py            # 핑퐁 루프 ①~⑥
│   │       ├── connections.py             # 세션별 소켓 레지스트리
│   │       ├── question_script.py         # 질문 트리 파서
│   │       └── ai/                        # prompts / llm / stt / tts / timekeeper 어댑터
│   └── tests/
├── frontend/
│   ├── interviewee/                       # React + Vite — 응답자 화면
│   └── dashboard/                         # React + Vite — 참관자 대시보드
├── infra/azure-setup.sh                   # Azure 데모 리소스 일괄 생성 스크립트
└── docs/azure-setup.md
```

---

## 로컬 실행

### 백엔드

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env              # 값 없이도 그대로 동작한다
uvicorn app.main:app --reload --port 8000
```

- API 문서: http://localhost:8000/docs
- 헬스체크: http://localhost:8000/health
- 테스트: `pytest -q`

### 프론트엔드 (터미널 2개)

```bash
cd frontend/interviewee && npm install && npm run dev   # http://localhost:5173
cd frontend/dashboard   && npm install && npm run dev   # http://localhost:5174
```

`.env.example`을 `.env.local`로 복사하면 백엔드 주소를 바꿀 수 있다(기본값은 localhost:8000).

### 확인 시나리오

1. 대시보드(5174)에서 질문 리스트를 넣고 **세션 생성** → 응답자 링크 발급
2. 그 링크(5173)로 접속해 답변 입력
3. 대시보드에서 지시 입력 (`경쟁사 대비 장점을 물어봐`) → `queued`
4. 응답자가 다음 답변을 보내면 지시가 다음 질문에 반영되고 → `applied`
5. 응답자 화면에는 AI 판단 근거가 나오지 않는다 (Architecture C5)

---

## 지금 동작하는 것 / 아직 아닌 것

| | 상태 |
|---|---|
| 세션 생성 + 응답자 링크 발급 | 동작 |
| 참관자 지시 큐 → 다음 질문 주입 → ack (핵심 차별점) | 동작 |
| 질문 트리 파싱 + 대시보드 렌더링 | 동작 |
| AI 판단 근거 참관자 전용 노출 | 동작 |
| 타임키퍼 1분 폴링 | 룰 기반으로 동작 (gpt-4o-mini 호출로 교체 예정) |
| 질문 생성 | `AZURE_OPENAI_*` 있으면 GPT-4o, 없으면 스텁 |
| 세션 저장소 | `REDIS_URL` 있으면 Redis, 없으면 인메모리 |
| **STT (gpt-transcribe)** | 미구현 — 지금은 텍스트 입력으로 대체 |
| **TTS / 아바타 (Azure Speech)** | 미구현 — 지금은 텍스트 표시 |
| **리포트 (Event Grid → Functions → Cosmos)** | 미착수 (후순위, D6) |

> Azure 리소스가 하나도 없어도 파이프라인 전체가 스텁으로 돌아간다.
> CI/CD를 먼저 붙이고 AI를 나중에 채우는 순서를 의도한 설계다.

---

## 작업 규칙

- WebSocket 메시지 계약은 `backend/app/schemas/messages.py`와 `frontend/*/src/types.ts`를 **항상 같이** 수정한다.
- AI 판단 근거(`rationale`)는 참관자 페이로드에만 넣는다.
- 새 기능/수정 전에 [Architecture.md](Architecture.md)의 결정사항(D1~D11)과 제약(C1~C9)을 먼저 확인한다.
