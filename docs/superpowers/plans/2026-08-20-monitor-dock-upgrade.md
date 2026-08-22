# 백룸 독 업그레이드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 백룸(Monitor.tsx)의 케밥 호버 드로어를 Mac 독 스타일 클릭 아이콘 3개로 교체하고, STT 자막을 영상 오버레이에서 하단 고정 바로 옮기고, 상단 PM/Observer 칩을 제거하며, 클라이언트 모드에서도 실시간 진행상황이 보이게 하고, 실시간 진행상황을 카카오톡식 좌/우 말풍선으로 바꾼다.

**Architecture:** 순수 프론트엔드 변경. React state 한 개(`activePanel`)가 케밥의 `drawerPinned`를 대체하고, 기존 슬라이드 애니메이션 CSS(`position:fixed` + `transform`)는 클래스명만 바꿔 재사용한다. 나머지는 JSX 재배치(자막 위치, 컬럼 역할 분리)와 CSS 전용 변경(말풍선)이다.

**Tech Stack:** React 18 + TypeScript, 순수 CSS(라이브러리 없음).

## Global Constraints

- 백엔드 코드는 건드리지 않는다 (분석 아이콘은 disabled 스텁, role 전환은 프론트 로컬 상태로만 처리).
- 각 태스크는 `npm run build` 통과 + 브라우저 육안 확인 후 커밋한다.
- 기존에 동작하던 기능(질문트리 표시, 세션 링크 표시, 지시 이력 아코디언, 리포트 표시)은 그대로 유지 — 위치/트리거만 바뀐다.

---

### Task 1: 케밥 → 독 아이콘 3개

**Files:**
- Modify: `frontend/dashboard/src/components/Monitor.tsx:82-101` (state + outside-click effect), `:262-337` (JSX)
- Modify: `frontend/dashboard/src/styles.css:259-263` (`:has()` 규칙), `:312-359` (`.kebab-wrap`/`.kebab-btn`/`.hover-drawer`)

**Interfaces:**
- Produces: `activePanel: "tree" | "link" | null` state, `dockRef` ref — Task 4는 이 state를 쓰지 않으므로 이후 태스크에 영향 없음.

- [ ] **Step 1: state와 outside-click 이펙트 교체**

`Monitor.tsx:82-90`을 다음으로 교체 (기존 `historyOpen`, `editModalOpen`, `fileFormat`, `selectedFile`, `uploadingGuide`, `socketRef`, `reportRef`는 그대로 두고 `drawerPinned`/`kebabWrapRef`만 바꾼다):

```tsx
  const [historyOpen, setHistoryOpen] = useState(false);
  const [activePanel, setActivePanel] = useState<"tree" | "link" | null>(null);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [fileFormat, setFileFormat] = useState<FileFormat>("md");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadingGuide, setUploadingGuide] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const reportRef = useRef<HTMLDivElement | null>(null);
  const dockRef = useRef<HTMLDivElement | null>(null);
```

`Monitor.tsx:92-101`을 다음으로 교체:

```tsx
  useEffect(() => {
    if (!activePanel) return;
    const handleOutsideClick = (event: MouseEvent) => {
      if (dockRef.current && !dockRef.current.contains(event.target as Node)) {
        setActivePanel(null);
      }
    };
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, [activePanel]);
```

- [ ] **Step 2: JSX 교체**

`Monitor.tsx:262-337`(기존 `<div ref={kebabWrapRef} className={...kebab-wrap...}>` 전체 블록)을 다음으로 교체:

```tsx
        <div ref={dockRef} className="dock">
          <button
            type="button"
            className={`dock-icon ${activePanel === "tree" ? "on" : ""}`}
            title="질문 트리 · 질문 등록/편집"
            onClick={() => setActivePanel((v) => (v === "tree" ? null : "tree"))}
          >
            Q
          </button>
          <button
            type="button"
            className={`dock-icon ${activePanel === "link" ? "on" : ""}`}
            title="세션 링크"
            onClick={() => setActivePanel((v) => (v === "link" ? null : "link"))}
          >
            L
          </button>
          <button type="button" className="dock-icon" disabled title="분석 앱 연동 전 · URL 확정 후 연결">
            A
          </button>

          <div className={`dock-panel ${activePanel === "tree" ? "open" : ""}`}>
            <div className="hover-drawer-section">
              <div className="hover-drawer-label">• 질문 트리</div>
              <div className="accordion-actions">
                {role === "pm" ? (
                  <button type="button" className="btn-sm solid" onClick={() => setEditModalOpen(true)}>
                    ＋ 질문 등록 및 편집
                  </button>
                ) : (
                  <span className="role-chip" style={{ fontSize: "10px" }}>
                    참관 전용
                  </span>
                )}
              </div>
              <ol className="tree">
                {questions.map((question, index) => {
                  const current = index === session?.current_question_index;
                  const done = session != null && index < session.current_question_index;
                  return (
                    <li key={question.id} className={current ? "current" : done ? "done" : ""}>
                      <span className="q-num">{index + 1}</span>
                      <div className="q-body">
                        {question.text}
                        {Object.entries(question.branches).map(([condition, followUp]) => (
                          <div key={condition} className="branch">
                            <span className="cond">{condition}</span>
                            {followUp}
                          </div>
                        ))}
                      </div>
                    </li>
                  );
                })}
              </ol>

              {timekeeper && (
                <div className={`timekeeper ${timekeeper.should_move_on ? "warn" : ""}`} style={{ margin: "0 16px 16px" }}>
                  <strong>타임키퍼</strong>
                  <p>{timekeeper.hint}</p>
                </div>
              )}
            </div>
          </div>

          <div className={`dock-panel ${activePanel === "link" ? "open" : ""}`}>
            <div className="hover-drawer-section">
              <div className="hover-drawer-label">• 세션 링크</div>
              <div className="p-body">
                {role === "pm" ? (
                  <>
                    {intervieweeUrl && (
                      <p className="link-row">
                        인터뷰이: <code>{intervieweeUrl}</code>
                        <button className="ghost" onClick={() => navigator.clipboard.writeText(intervieweeUrl)}>
                          복사
                        </button>
                      </p>
                    )}
                    <p className="link-row">
                      클라이언트: <span className="muted">준비 중</span>
                    </p>
                  </>
                ) : (
                  <p className="muted small">참관 전용 — 링크는 PM만 볼 수 있습니다.</p>
                )}
              </div>
            </div>
          </div>
        </div>
```

- [ ] **Step 3: CSS 교체 — `:has()` 규칙**

`styles.css:259-263`:

```css
/* 독 패널이 열려있는 동안엔 콘텐츠를 오른쪽으로 밀어줘서 응답자 화면(영상)을 가리지 않게 함 */
body:has(.dock-panel.open) .monitor {
  padding-left: calc(30px + min(360px, 88vw));
}
```

- [ ] **Step 4: CSS 교체 — 독/패널 스타일**

`styles.css:312-359`(`.kebab-wrap`부터 `.hover-drawer` 관련 규칙 전체)을 다음으로 교체:

```css
.dock {
  position: relative;
  display: flex;
  gap: 8px;
}

.dock-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: 1px solid var(--panel-border);
  background: var(--panel);
  color: var(--text);
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dock-icon.on {
  background: var(--primary);
  color: var(--text-white);
  border-color: var(--primary);
}

.dock-icon:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.dock-panel {
  position: fixed;
  top: 132px;
  left: 0;
  bottom: 0;
  z-index: 41;
  width: min(360px, 88vw);
  background: var(--panel);
  border-right: 1px solid var(--panel-border);
  border-top: 1px solid var(--panel-border);
  box-shadow: 0 0 30px rgba(0, 0, 0, 0.4);
  overflow-y: auto;
  padding-top: 8px;
  opacity: 0;
  visibility: hidden;
  transform: translateX(-16px);
  pointer-events: none;
  transition: opacity 0.18s ease, transform 0.18s ease, visibility 0.18s;
}

.dock-panel.open {
  opacity: 1;
  visibility: visible;
  transform: translateX(0);
  pointer-events: auto;
}
```

- [ ] **Step 5: 빌드 + 육안 확인**

```bash
cd frontend/dashboard && npm run build
```

Expected: 타입 에러 없이 빌드 성공. 브라우저에서 백룸 진입 → 탭바에 `Q`/`L`/`A` 원형 버튼 3개 보임 → `Q` 클릭 시 왼쪽에서 질문트리 패널이 슬라이드 인, 다시 클릭하면 닫힘 → `L` 클릭 시 같은 자리에 세션 링크 패널, `Q`는 자동으로 닫힘(한 번에 하나만) → 패널 열린 상태에서 패널 바깥 클릭하면 닫힘 → `A`는 클릭 안 되고 툴팁만 뜸.

- [ ] **Step 6: 커밋**

```bash
git add frontend/dashboard/src/components/Monitor.tsx frontend/dashboard/src/styles.css
git commit -m "feat: replace kebab hover drawer with clickable dock icons"
```

---

### Task 2: 자막을 영상 오버레이 → 하단 고정 바로 이동

**Files:**
- Modify: `frontend/dashboard/src/components/Monitor.tsx:412-419`, 그리고 `.resp-stage` 닫는 지점(현재 445번째 줄 부근)
- Modify: `frontend/dashboard/src/styles.css` (`.resp-stage` 블록 뒤, 대략 541번째 줄 부근에 신규 규칙 추가)

**Interfaces:**
- Consumes: 기존 `liveTextKo`, `liveTextEn` state (Monitor.tsx:74-75, 변경 없음)

- [ ] **Step 1: 오버레이 제거**

`Monitor.tsx`에서 `.rs-figure` 내부의 아래 블록(자막 오버레이, 412-418번째 줄)을 삭제:

```tsx
                {/* 실시간 자막 UI */}
                {(liveTextKo || liveTextEn) && (
                  <div style={{ position: "absolute", bottom: "16px", left: "16px", right: "16px", background: "rgba(0,0,0,0.7)", color: "white", padding: "12px", borderRadius: "8px", fontSize: "14px", lineHeight: 1.5, zIndex: 10 }}>
                    {liveTextKo && <div style={{ marginBottom: liveTextEn ? "4px" : 0 }}>{liveTextKo}</div>}
                    {liveTextEn && <div style={{ color: "#ffd54f" }}>{liveTextEn}</div>}
                  </div>
                )}
```

- [ ] **Step 2: `.resp-stage` 바깥에 자막 바 추가**

`.resp-stage`의 닫는 `</div>`(444번째 줄 근처, `</main>`이 아니라 `resp-stage`의 그것) 바로 뒤 — 즉 `<section className="panel">` 안, `.resp-stage` div 다음 형제로 추가:

```tsx
        </div>

        {phase !== "wait" && (
          <div className="caption-bar">
            {liveTextKo && <div className="caption-line ko">{liveTextKo}</div>}
            {liveTextEn && <div className="caption-line en">{liveTextEn}</div>}
            {!liveTextKo && !liveTextEn && <div className="caption-line placeholder">자막 대기 중…</div>}
          </div>
        )}
      </section>
```

(기존 `</div>{'\n'}      </section>` 두 줄을 위 블록으로 교체 — `.resp-stage`를 닫는 `</div>`는 그대로 유지하고 그 다음에 `caption-bar` 조건부 렌더링을 넣은 뒤 `</section>`으로 닫는다.)

- [ ] **Step 3: CSS 추가**

`styles.css`의 `.resp-stage` 관련 규칙 블록 끝(대략 541번째 줄, `.resp-stage b { ... }` 다음)에 추가:

```css
.caption-bar {
  min-height: 56px;
  margin: 0 16px 16px;
  padding: 10px 14px;
  border-radius: 12px;
  background: #1d1d1f;
  color: #eaf0f8;
  font-size: 13px;
  line-height: 1.5;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
}

.caption-line.en {
  color: #ffd54f;
}

.caption-line.placeholder {
  color: #86868b;
  font-size: 12px;
}
```

- [ ] **Step 4: 빌드 + 육안 확인**

```bash
cd frontend/dashboard && npm run build
```

Expected: 빌드 성공. 백룸에서 응답자 접속 후 STT 자막이 뜰 때 영상 위에 안 겹치고 영상 아래 별도 바에 표시됨. 자막이 없을 때도 "자막 대기 중…"으로 바 높이가 유지되어 레이아웃이 안 튐.

- [ ] **Step 5: 커밋**

```bash
git add frontend/dashboard/src/components/Monitor.tsx frontend/dashboard/src/styles.css
git commit -m "fix: move live captions from video overlay to fixed bar below"
```

---

### Task 3: 상단 PM/Observer 칩·스위치 제거

**Files:**
- Modify: `frontend/dashboard/src/App.tsx:14,28-40`

**Interfaces:**
- Produces: `role: Role`(읽기 전용, setter 없음) — Task 4가 그대로 소비.

- [ ] **Step 1: role 초기값을 URL 쿼리에서 읽도록 교체**

`App.tsx:18`(`const [role, setRole] = useState<Role>("pm");`)을 다음으로 교체:

```tsx
  const [role] = useState<Role>(
    () => (new URLSearchParams(window.location.search).get("role") as Role) || "pm",
  );
```

- [ ] **Step 2: role-switch / role-chip JSX 삭제**

`App.tsx:28-40`(아래 두 블록)을 삭제:

```tsx
          {sessionId && (
            <div className="role-switch">
              <button className={role === "pm" ? "on" : ""} onClick={() => setRole("pm")}>
                PM 모드
              </button>
              <button className={role === "client" ? "on" : ""} onClick={() => setRole("client")}>
                클라이언트 모드
              </button>
            </div>
          )}
          {sessionId && (
            <span className="role-chip">{role === "pm" ? "PM · Observer" : "클라이언트 · Observer"}</span>
          )}
```

- [ ] **Step 3: 빌드 확인**

```bash
cd frontend/dashboard && npm run build
```

Expected: `setRole` 미사용으로 인한 타입 에러 없이(위에서 setter 자체를 안 꺼내므로) 빌드 성공.

- [ ] **Step 4: 육안 확인**

세션 진입 후 상단바에 PM 모드/클라이언트 모드 버튼과 "PM · Observer" 칩이 더 이상 안 보임. `?role=client`를 URL에 붙여 재접속하면 클라이언트 모드로 진입되는지 확인(Task 4 완료 후 최종 확인 예정이므로 지금은 role 값 변화만 확인하면 됨 — 아직 우측 컬럼 자체가 안 보이는 게 정상).

- [ ] **Step 5: 커밋**

```bash
git add frontend/dashboard/src/App.tsx
git commit -m "feat: remove PM/observer role chip, drive role from URL query instead"
```

---

### Task 4: 클라이언트 모드에서도 실시간 진행상황 노출

**Files:**
- Modify: `frontend/dashboard/src/components/Monitor.tsx:449,585` (col-instructions 감싸는 조건문)

**Interfaces:**
- Consumes: `role: Role`(Task 3에서 그대로 유지된 prop, 변경 없음)

- [ ] **Step 1: 여는 태그 순서 교체 (`Monitor.tsx:449-450`)**

현재:

```tsx
      {role === "pm" && (
        <div className="col-instructions">
          <section className={`panel ${phase !== "live" ? "locked" : ""}`}>
```

교체 후:

```tsx
      <div className="col-instructions">
        {role === "pm" && (
          <section className={`panel ${phase !== "live" ? "locked" : ""}`}>
```

- [ ] **Step 2: "실시간 지시" 섹션 닫는 지점에 조건 닫기 추가 (`Monitor.tsx:518` 직후)**

현재 "실시간 지시" `<section>`의 닫는 태그와 "실시간 진행 상황" `<section>`이 시작하는 부분:

```tsx
          </section>

          <section className="panel">
```

교체 후 (역할 조건을 여기서 닫고, 실시간 진행 상황은 조건 밖에 둔다):

```tsx
          </section>
        )}

        <section className="panel">
```

- [ ] **Step 3: 컬럼 닫는 지점에서 남는 조건 괄호 제거 (`Monitor.tsx:583-585`)**

현재 "실시간 진행 상황" `<section>`이 끝나고 `col-instructions`가 닫히는 부분:

```tsx
          </section>
        </div>
      )}
```

교체 후 (더 이상 바깥을 감싸는 조건이 없으므로 `)}` 제거):

```tsx
        </section>
      </div>
```

- [ ] **Step 2: 빌드 확인**

```bash
cd frontend/dashboard && npm run build
```

Expected: JSX 중첩 에러 없이 빌드 성공.

- [ ] **Step 3: 육안 확인**

`?role=client`로 접속 → 오른쪽 컬럼에 "실시간 지시"는 안 보이고 "실시간 진행 상황"만 보임. `?role=pm`(또는 role 쿼리 없이)으로 접속 → 기존처럼 "실시간 지시" + "실시간 진행 상황" 둘 다 보임.

- [ ] **Step 4: 커밋**

```bash
git add frontend/dashboard/src/components/Monitor.tsx
git commit -m "feat: show live transcript to client role, keep instructions PM-only"
```

---

### Task 5: 실시간 진행상황 카카오톡식 좌/우 말풍선

**Files:**
- Modify: `frontend/dashboard/src/styles.css:709-758` (`.turns`, `.turn`, `.turn-head`, `.turn strong`, `.turn.assistant strong`, `.turn p`)

**Interfaces:**
- Consumes: 기존 JSX 클래스 `turn assistant` / `turn interviewee` (Monitor.tsx, 변경 없음 — CSS만 추가)

- [ ] **Step 1: CSS 교체**

`styles.css:709-758`을 다음으로 교체:

```css
.turns {
  display: flex;
  flex-direction: column;
  padding: 6px 24px 24px;
  gap: 12px;
  max-height: 70vh;
  overflow-y: auto;
}

.turn {
  max-width: 75%;
  padding: 10px 14px;
  border-radius: 14px;
}

.turn.assistant {
  align-self: flex-start;
  background: rgba(0, 113, 227, 0.08);
  border-bottom-left-radius: 4px;
}

.turn.interviewee {
  align-self: flex-end;
  background: rgba(52, 199, 89, 0.1);
  border-bottom-right-radius: 4px;
}

.turn-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.turn.interviewee .turn-head {
  flex-direction: row-reverse;
}

.turn strong {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(16, 185, 129, 0.15);
  color: var(--success);
}

.turn.assistant strong {
  background: rgba(0, 113, 227, 0.15);
  color: var(--primary);
}

.turn-head time {
  font-size: 10px;
  color: var(--muted);
}

.turn p {
  margin: 4px 0 0;
  font-size: 13.5px;
  line-height: 1.62;
  color: var(--text);
}
```

(`.rationale`, `.rationale .ai-label` 규칙은 뒤에 그대로 남겨둔다 — 변경 없음.)

- [ ] **Step 2: 빌드 + 육안 확인**

```bash
cd frontend/dashboard && npm run build
```

Expected: 빌드 성공. 백룸에서 AI 질문(assistant) 말풍선은 왼쪽 정렬 + 파란 톤, 응답자 답변(interviewee) 말풍선은 오른쪽 정렬 + 초록 톤으로 카톡처럼 좌우로 갈라져 보임. AI 판단 근거(rationale)는 assistant 말풍선 안에 그대로 표시됨.

- [ ] **Step 3: 커밋**

```bash
git add frontend/dashboard/src/styles.css
git commit -m "style: render live transcript as left/right chat bubbles"
```
