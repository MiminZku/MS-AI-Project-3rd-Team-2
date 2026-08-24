# 세션 생성 페이지 개편 — 프로젝트 드롭다운(스텁) + 세션 목록

## 배경

`SessionForm.tsx`가 지금 3개 섹션(목데이터 미리보기 / 새 인터뷰 세션 / 기존 세션 열기[ID 직접 입력])으로 되어 있는데, PM이 매번 세션 ID를 직접 타이핑해야 이전 세션에 다시 들어갈 수 있어 실사용성이 떨어진다. 또한 팀원이 최근 `docs/md/nosql_schema.md`(Cosmos DB 기준 `projects`/`interviews` 2단 컬렉션 스키마)를 문서화했고, 세션 생성 시 자유 텍스트 "세션 이름" 대신 "프로젝트" 드롭다운을 선택하는 구조로 가야 한다는 피드백을 받았다.

다만 `nosql_schema.md`는 문서만 존재하고 백엔드에 Project 모델/API가 전혀 구현되어 있지 않다(현재 백엔드는 여전히 Redis 기반 단일 `Session`만 있음). Project 실연동은 이번 범위 밖 — 백엔드 팀원이 나중에 처리한다.

## 목표

- PM이 새 인터뷰를 만들 때 "세션 이름" 자유 입력 대신 "프로젝트" 드롭다운에서 선택하게 한다 (지금은 프론트엔드 목업 데이터).
- PM이 이미 만든 세션들을 목록에서 찾아 클릭 한 번으로 백룸에 재진입할 수 있게 한다 (실제 백엔드 기능).
- 안 쓰는 기능(목데이터 미리보기, 세션 ID 직접 입력, 임시 저장)을 제거해 화면을 정리한다.

## 범위 (In Scope)

1. `frontend/dashboard/src/components/SessionForm.tsx` 재구성
2. `frontend/dashboard/src/api.ts`에 `listSessions()` 추가
3. `backend/app/services/store.py` — `Store` 프로토콜에 `list_sessions()` 추가, `InMemoryStore`/`RedisStore` 둘 다 구현
4. `backend/app/api/routes/sessions.py` — `GET /api/sessions` (목록) 라우트 추가

## 비목표 (Out of Scope)

- `docs/md/nosql_schema.md`의 실제 `projects`/`interviews` Cosmos DB 스키마 구현 — Project 모델, Project CRUD API, `Session`에 `project_id` 필드 추가 등은 전부 범위 밖. 이번엔 프론트엔드 목업 드롭다운으로만 스텁한다.
- 로그인 페이지 — 사용자가 명시적으로 보류함 (별도 스펙으로 나중에 진행)
- `Monitor.tsx`의 데모 모드 코드(`DEMO_SESSION` 등) 자체 제거 — 진입 버튼만 없애고 코드는 남겨둔다 (자연히 도달 불가능해짐, 별도 정리 요청 없으면 그대로 둠)

## SessionForm 재구성

### 제거

- "목데이터 미리보기" 섹션 전체 (`onCreated(DEMO_SESSION, "")` 버튼 포함)
- "기존 세션 열기" 섹션 전체 (`joinId` 세션 ID 직접 입력 + `fetchSession` 호출 버튼)
- "임시 저장" 버튼 (이미 `disabled` 스텁이었음)

### "세션 이름" → "프로젝트" 드롭다운 (목업)

```ts
const MOCK_PROJECTS = [
  { id: "proj_delivery_ux", label: "배달앱 UX 사용성 조사" },
  { id: "proj_subscription", label: "무료배달 구독제 만족도 조사" },
] as const;
```

- `title` 텍스트 `useState`를 제거하고 `projectId` `useState<string>("")` 로 교체 (빈 문자열 = 미선택)
- `<select>`로 렌더링, 첫 옵션은 `disabled` `"프로젝트를 선택하세요"` 플레이스홀더
- 드롭다운 아래에 안내 문구: `실제 프로젝트 연동은 백엔드 준비 중 — 지금은 목업 목록입니다.`
- "세션 생성" 버튼은 `projectId`가 빈 문자열이면 `disabled`
- 세션 생성 시 `createSession({ title: selectedProject.label, ... })` — 선택된 프로젝트의 `label`을 그대로 세션 `title`로 사용 (백엔드 스키마 변경 없이 기존 필드 재사용)

### "세션 목록" 신규 섹션 (실제 기능, "기존 세션 열기" 자리 대체)

- `SessionForm` 마운트 시 `listSessions()` 한 번 호출해 `sessions: Session[]` state에 저장
- 각 세션을 카드로 렌더링: 제목(`title`) + 상태 뱃지(`status`: `created`→"대기", `running`→"진행중", `ended`→"종료") + 생성일시(`created_at`, `toLocaleString("ko-KR")`) + 화살표
- 최근 생성순 정렬 (백엔드가 이미 정렬해서 내려줌 — 프론트에서 재정렬 안 함)
- 카드 클릭 시 기존 `fetchSession(session.id)` 호출 → `onCreated(result.session, result.interviewee_url)` (기존 "기존 세션 열기"가 하던 것과 동일한 로직, 입력 방식만 타이핑 → 클릭으로 교체)
- 목록이 비어있으면 "아직 생성된 세션이 없습니다." 안내 텍스트

## 백엔드: `list_sessions()`

### `Store` 프로토콜에 추가

```python
async def list_sessions(self) -> list[Session]: ...
```

### `InMemoryStore`

```python
async def list_sessions(self) -> list[Session]:
    return sorted(self._sessions.values(), key=lambda s: s.created_at, reverse=True)
```

### `RedisStore`

세션 ID를 인덱싱하는 정렬된 셋(`sessions:index`, score=생성 시각 epoch)이 없으므로 새로 추가한다. `save_session`에서 저장할 때 이 인덱스에도 등록하고, `list_sessions`는 최근순으로 ID를 꺼내 각 세션을 조회한다. 이미 TTL로 만료된 세션은 `get_session`이 `None`을 반환하므로 결과에서 걸러낸다 (인덱스 자체의 stale entry는 이번 범위에서 정리하지 않음 — 조회할 때마다 걸러지므로 사용자에게 보이는 목록에는 영향 없음).

```python
async def save_session(self, session: Session) -> None:
    key = self._key(session.id)
    await self._redis.set(key, session.model_dump_json(), ex=self._ttl)
    await self._redis.zadd("sessions:index", {session.id: session.created_at.timestamp()})

async def list_sessions(self) -> list[Session]:
    ids = await self._redis.zrevrange("sessions:index", 0, -1)
    sessions = []
    for session_id in ids:
        session = await self.get_session(session_id)
        if session is not None:
            sessions.append(session)
    return sessions
```

## `GET /api/sessions` 라우트

```python
@router.get("", response_model=list[Session])
async def list_sessions() -> list[Session]:
    return await get_store().list_sessions()
```

(`@router.post("")`인 `create_session`과 경로가 겹치지만 HTTP 메서드가 다르므로 충돌 없음. `/sessions/{session_id}`류 라우트와도 정확한 문자열 매칭이라 순서 무관.)

## 검증 방법

- 백엔드: `cd backend && python -m pytest` (있다면), 로컬 `uvicorn` 기동 후 `curl http://127.0.0.1:8000/api/sessions` 로 목록이 배열로 오는지 확인 — 세션 여러 개 생성 후 최근순인지 확인
- 프론트: `cd frontend/dashboard && npm run build` — exit 0
- 로컬 dev 서버에서:
  - 세션 생성 폼에 프로젝트 드롭다운이 보이고, 미선택 상태면 "세션 생성" 버튼이 비활성화되는지
  - 프로젝트 선택 후 세션 생성 → 생성된 세션의 제목이 선택한 프로젝트명과 같은지
  - 페이지 새로고침 후 "세션 목록"에 방금 만든 세션이 카드로 보이는지, 상태 뱃지가 "대기"로 보이는지
  - 카드 클릭 시 바로 백룸으로 진입하는지 (기존 링크 복사 등도 정상 동작하는지)
  - "목데이터 미리보기"/"기존 세션 열기"/"임시 저장"이 화면에서 완전히 사라졌는지
