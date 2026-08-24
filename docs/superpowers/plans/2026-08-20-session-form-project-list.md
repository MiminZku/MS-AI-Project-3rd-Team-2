# 세션 생성 페이지 개편 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 백엔드에 `list_sessions()` 기능을 추가하고, 대시보드 세션 생성 페이지를 프로젝트 드롭다운(목업)+실제 세션 목록 구조로 재구성한다.

**Architecture:** 백엔드(Store 프로토콜 확장 + 신규 라우트) → 프론트 API 클라이언트 → SessionForm 재구성, 3단계로 순차 진행. 백엔드는 기존 `tests/` 인프라(FastAPI TestClient + InMemoryStore fixture)를 그대로 써서 TDD로 진행.

**Tech Stack:** FastAPI + Pydantic + Redis(선택)/InMemory (백엔드), React 18 + TypeScript + Vite (프론트).

## Global Constraints

- 스펙: `docs/superpowers/specs/2026-08-20-session-form-project-list-design.md`.
- Project 모델/API 실제 구현은 범위 밖 — 프론트엔드 목업 드롭다운으로만 스텁.
- `Monitor.tsx`의 데모 모드 코드는 건드리지 않는다 (진입 버튼만 제거).
- 백엔드 검증: `cd backend && python -m pytest -v`
- 프론트 검증: `cd frontend/dashboard && npm run build`
- 로컬 백엔드(`127.0.0.1:8000`)는 이미 떠 있음 — Store/라우트 변경 후 재기동 필요 (`Ctrl+C` 후 `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`, 또는 background로 재시작).
- 커밋은 태스크 단위로.

---

### Task 1: 백엔드 `list_sessions()` (Store 프로토콜 + 라우트, TDD)

**Files:**
- Modify: `backend/app/services/store.py` (`Store` 프로토콜, `InMemoryStore`, `RedisStore`)
- Modify: `backend/app/api/routes/sessions.py`
- Create: `backend/tests/test_session_list.py`

**Interfaces:**
- Produces: `Store.list_sessions() -> list[Session]` (최근 생성순), `GET /api/sessions` 라우트 (동일 응답)

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_session_list.py` 새로 생성:

```python
"""세션 목록 조회 — 최근 생성순으로 내려오는지 확인."""


def _create(client, title: str) -> str:
    response = client.post(
        "/api/sessions",
        json={"title": title, "duration_minutes": 20, "question_script": ""},
    )
    assert response.status_code == 201
    return response.json()["session"]["id"]


def test_세션_목록은_최근_생성순으로_온다(client):
    first_id = _create(client, "첫 번째 세션")
    second_id = _create(client, "두 번째 세션")

    response = client.get("/api/sessions")
    assert response.status_code == 200

    body = response.json()
    ids = [item["id"] for item in body]
    assert ids.index(second_id) < ids.index(first_id)


def test_세션이_하나도_없으면_빈_목록이_온다(client):
    response = client.get("/api/sessions")
    assert response.status_code == 200
    assert response.json() == []
```

- [ ] **Step 2: 테스트 실행해서 실패 확인**

Run: `cd backend && python -m pytest tests/test_session_list.py -v`
Expected: FAIL — `GET /api/sessions`가 없어서 404 (또는 `list_sessions` 미정의로 인한 에러)

- [ ] **Step 3: `Store` 프로토콜에 `list_sessions` 추가**

`backend/app/services/store.py`에서:

```python
class Store(Protocol):
    async def save_session(self, session: Session) -> None: ...
    async def get_session(self, session_id: str) -> Session | None: ...
```
→
```python
class Store(Protocol):
    async def save_session(self, session: Session) -> None: ...
    async def get_session(self, session_id: str) -> Session | None: ...
    async def list_sessions(self) -> list[Session]: ...
```

- [ ] **Step 4: `InMemoryStore`에 구현 추가**

```python
    async def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)
```
바로 아래에 추가:
```python

    async def list_sessions(self) -> list[Session]:
        return sorted(self._sessions.values(), key=lambda s: s.created_at, reverse=True)
```

- [ ] **Step 5: `RedisStore`에 인덱스 + 구현 추가**

```python
    async def save_session(self, session: Session) -> None:
        key = self._key(session.id)
        await self._redis.set(key, session.model_dump_json(), ex=self._ttl)
```
→
```python
    async def save_session(self, session: Session) -> None:
        key = self._key(session.id)
        await self._redis.set(key, session.model_dump_json(), ex=self._ttl)
        await self._redis.zadd("sessions:index", {session.id: session.created_at.timestamp()})
```

`get_session` 메서드 바로 아래(같은 파일, `RedisStore` 클래스 안)에 추가:
```python

    async def list_sessions(self) -> list[Session]:
        ids = await self._redis.zrevrange("sessions:index", 0, -1)
        sessions = []
        for session_id in ids:
            session = await self.get_session(session_id)
            if session is not None:
                sessions.append(session)
        return sessions
```

- [ ] **Step 6: `GET /api/sessions` 라우트 추가**

`backend/app/api/routes/sessions.py`에서 `create_session` 함수 바로 뒤에 추가:

```python
@router.get("", response_model=list[Session])
async def list_sessions() -> list[Session]:
    return await get_store().list_sessions()
```

- [ ] **Step 7: 테스트 실행해서 통과 확인**

Run: `cd backend && python -m pytest tests/test_session_list.py -v`
Expected: PASS (2 passed)

- [ ] **Step 8: 전체 테스트 스위트 회귀 확인**

Run: `cd backend && python -m pytest -v`
Expected: 기존 테스트 전부 PASS (이번 변경으로 깨진 게 없는지 확인)

- [ ] **Step 9: 로컬 서버 재기동 + curl 스모크 확인**

기존 uvicorn 프로세스 종료 후:
```bash
cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Run: `curl -s http://127.0.0.1:8000/api/sessions`
Expected: JSON 배열 (기존에 만들어둔 세션들이 최근순으로 나열됨)

- [ ] **Step 10: 커밋**

```bash
git add backend/app/services/store.py backend/app/api/routes/sessions.py backend/tests/test_session_list.py
git commit -m "feat: 백엔드에 세션 목록 조회(list_sessions) 추가"
```

---

### Task 2: 프론트 `api.ts`에 `listSessions()` 추가

**Files:**
- Modify: `frontend/dashboard/src/api.ts`

**Interfaces:**
- Consumes: Task 1의 `GET /api/sessions` (응답: `Session[]`)
- Produces: `listSessions(): Promise<Session[]>` — Task 3이 사용

- [ ] **Step 1: 함수 추가**

`frontend/dashboard/src/api.ts`에서 `fetchSession` 함수 바로 위에 추가:

```ts
export async function listSessions(): Promise<Session[]> {
  const response = await fetch(`${API_BASE_URL}/api/sessions`, {
    headers: headers(),
  });
  if (!response.ok) throw new Error(`세션 목록 조회 실패 (${response.status})`);
  return response.json();
}

```

- [ ] **Step 2: 빌드 검증**

Run: `cd frontend/dashboard && npm run build`
Expected: exit code 0

- [ ] **Step 3: 커밋**

```bash
git add frontend/dashboard/src/api.ts
git commit -m "feat: api.ts에 listSessions() 추가"
```

---

### Task 3: `SessionForm.tsx` 재구성 (섹션 제거 + 프로젝트 드롭다운 + 세션 목록)

**Files:**
- Modify: `frontend/dashboard/src/components/SessionForm.tsx`

**Interfaces:**
- Consumes: Task 2의 `listSessions()`, 기존 `createSession()`/`fetchSession()`

- [ ] **Step 1: import 및 목업 데이터 추가, `DEMO_SESSION` import 제거**

```tsx
import { useState } from "react";
import { createSession, fetchSession } from "../api";
import { DEMO_SESSION } from "../demoData";
import type { Session } from "../types";
```
→
```tsx
import { useEffect, useState } from "react";
import { createSession, fetchSession, listSessions } from "../api";
import type { Session } from "../types";

const MOCK_PROJECTS = [
  { id: "proj_delivery_ux", label: "배달앱 UX 사용성 조사" },
  { id: "proj_subscription", label: "무료배달 구독제 만족도 조사" },
] as const;

const STATUS_LABEL: Record<Session["status"], string> = {
  created: "대기",
  running: "진행중",
  ended: "종료",
};
```

- [ ] **Step 2: state 교체 — `title`/`joinId` 제거, `projectId`/`sessions` 추가**

```tsx
export default function SessionForm({ onCreated }: Props) {
  const [title, setTitle] = useState("배달앱 사용성 인터뷰");
  const [duration, setDuration] = useState(60);
  const [language, setLanguage] = useState("ko");
  const [joinId, setJoinId] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<{ session: Session; intervieweeUrl: string } | null>(null);
  const [copied, setCopied] = useState(false);
```
→
```tsx
export default function SessionForm({ onCreated }: Props) {
  const [projectId, setProjectId] = useState("");
  const [duration, setDuration] = useState(60);
  const [language, setLanguage] = useState("ko");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<{ session: Session; intervieweeUrl: string } | null>(null);
  const [copied, setCopied] = useState(false);
  const [sessions, setSessions] = useState<Session[]>([]);

  useEffect(() => {
    listSessions()
      .then(setSessions)
      .catch((cause) => console.error("세션 목록 조회 실패", cause));
  }, []);
```

- [ ] **Step 3: "목데이터 미리보기" 섹션 삭제**

아래 블록을 통째로 삭제 (파일 맨 위, `<main className="form-page">` 여는 태그 바로 다음):

```tsx
      <section className="panel">
        <header className="p-head">
          <div>
            <h2>목데이터 미리보기</h2>
            <div className="sub">백엔드 연결 없이 화면만 확인</div>
          </div>
        </header>
        <div className="p-body">
          <p className="muted small" style={{ margin: "0 0 12px" }}>
            백엔드가 아직 준비되지 않았을 때, 목데이터로 관리자 대시보드 화면만 확인합니다.
          </p>
          <button className="ghost" onClick={() => onCreated(DEMO_SESSION, "")}>
            데모로 미리보기
          </button>
        </div>
      </section>

```

- [ ] **Step 4: "세션 이름" 입력을 "프로젝트" 드롭다운으로 교체**

```tsx
            <label>
              세션 이름
              <input value={title} onChange={(event) => setTitle(event.target.value)} />
            </label>
```
→
```tsx
            <label>
              프로젝트
              <p className="desc">실제 프로젝트 연동은 백엔드 준비 중 — 지금은 목업 목록입니다.</p>
              <select value={projectId} onChange={(event) => setProjectId(event.target.value)}>
                <option value="" disabled>
                  프로젝트를 선택하세요
                </option>
                {MOCK_PROJECTS.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.label}
                  </option>
                ))}
              </select>
            </label>
```

- [ ] **Step 5: "임시 저장" 버튼 제거 + 세션 생성 호출을 프로젝트 기반으로 교체**

```tsx
            <div className="form-actions">
              <button className="ghost" disabled title="곧 지원 예정">
                임시 저장
              </button>
              <button
                disabled={busy}
                onClick={() =>
                  run(async () => {
                    const result = await createSession({
                      title,
                      duration_minutes: duration,
                      question_script: SAMPLE_SCRIPT,
                    });
                    setCreated({ session: result.session, intervieweeUrl: result.interviewee_url });
                  })
                }
              >
                세션 생성
              </button>
            </div>
```
→
```tsx
            <div className="form-actions">
              <button
                disabled={busy || !projectId}
                onClick={() =>
                  run(async () => {
                    const project = MOCK_PROJECTS.find((p) => p.id === projectId);
                    const result = await createSession({
                      title: project?.label ?? "제목 없는 인터뷰",
                      duration_minutes: duration,
                      question_script: SAMPLE_SCRIPT,
                    });
                    setCreated({ session: result.session, intervieweeUrl: result.interviewee_url });
                  })
                }
              >
                세션 생성
              </button>
            </div>
```

- [ ] **Step 6: "기존 세션 열기" 섹션을 "세션 목록"으로 교체**

```tsx
      <section className="panel">
        <header className="p-head">
          <div>
            <h2>기존 세션 열기</h2>
            <div className="sub">세션 ID로 다시 접속</div>
          </div>
        </header>
        <div className="p-body">
          <label>
            세션 ID
            <input
              value={joinId}
              placeholder="ses_..."
              onChange={(event) => setJoinId(event.target.value)}
            />
          </label>
          <button
            className="ghost"
            disabled={busy || !joinId.trim()}
            onClick={() =>
              run(async () => {
                const result = await fetchSession(joinId.trim());
                onCreated(result.session, result.interviewee_url);
              })
            }
          >
            모니터링 시작
          </button>
        </div>
      </section>
```
→
```tsx
      <section className="panel">
        <header className="p-head">
          <div>
            <h2>세션 목록</h2>
            <div className="sub">이미 만든 세션에 다시 들어가기</div>
          </div>
        </header>
        <div className="p-body">
          {sessions.length === 0 ? (
            <p className="muted small">아직 생성된 세션이 없습니다.</p>
          ) : (
            sessions.map((session) => (
              <button
                key={session.id}
                type="button"
                className="link-row"
                style={{ width: "100%", cursor: "pointer", textAlign: "left" }}
                disabled={busy}
                onClick={() =>
                  run(async () => {
                    const result = await fetchSession(session.id);
                    onCreated(result.session, result.interviewee_url);
                  })
                }
              >
                <span className={`badge ${session.status === "running" ? "connected" : ""}`}>
                  {STATUS_LABEL[session.status]}
                </span>
                <code>{session.title}</code>
                <span className="desc" style={{ width: "100%", margin: "4px 0 0" }}>
                  {new Date(session.created_at).toLocaleString("ko-KR")}
                </span>
              </button>
            ))
          )}
        </div>
      </section>
```

- [ ] **Step 7: 빌드 검증**

Run: `cd frontend/dashboard && npm run build`
Expected: exit code 0 (TypeScript가 `title`/`joinId` 미사용 여부와 `Session["status"]` 타입 일치도 같이 체크함)

- [ ] **Step 8: 육안 확인**

`http://localhost:5174`에서:
- "목데이터 미리보기"/"기존 세션 열기"/"임시 저장"이 화면에서 사라졌는지
- "프로젝트" 드롭다운에 목업 2개가 보이고, 미선택 상태면 "세션 생성"이 비활성화되는지
- 프로젝트 선택 후 세션 생성 → 생성된 세션 링크 화면이 그대로 나오는지
- "세션 목록"에 방금 만든 세션이 카드로 보이고, "대기" 상태 뱃지와 생성일시가 보이는지
- 그 카드를 클릭하면 바로 백룸으로 진입하는지

- [ ] **Step 9: 커밋**

```bash
git add frontend/dashboard/src/components/SessionForm.tsx
git commit -m "feat: 세션 생성 페이지를 프로젝트 드롭다운(목업)+세션 목록 구조로 재구성"
```
