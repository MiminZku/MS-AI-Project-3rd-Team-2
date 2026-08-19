# 백룸(Monitor) 접이식 레이아웃 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 백룸 화면을 접이식 좌측 사이드바(질문 트리+세션 링크) + 넓어진 응답자 화면(타이머/연결배지 내장) + 재배치된 우측 컬럼(실시간 지시+지시이력 토글, 실시간 진행상황)으로 재구성한다.

**Architecture:** `Monitor.tsx`에 로컬 `useState` 3개(`treeOpen`, `linksOpen`, `historyOpen`)를 추가해 접기 상태를 관리하고, JSX를 스펙대로 재배치한다. `App.tsx`는 더 이상 타이머/연결배지를 렌더링하지 않도록 `TopbarStatus`를 줄인다. 4개 태스크로 나누되, 각 태스크는 독립적으로 빌드+육안 확인 가능한 단위다.

**Tech Stack:** React 18 + TypeScript, Vite 6, 순수 CSS(styles.css).

## Global Constraints

- 대상 파일 3개만: `frontend/dashboard/src/components/Monitor.tsx`, `frontend/dashboard/src/App.tsx`, `frontend/dashboard/src/styles.css`.
- 스펙: `docs/superpowers/specs/2026-08-19-monitor-collapsible-layout-design.md`.
- 클라이언트 링크는 "준비 중" 표시만 유지 — 실제 발급 기능 구현 안 함.
- 접기 상태는 로컬 `useState`만 — localStorage 등 영구 저장 없음.
- 빌드 검증: `cd frontend/dashboard && npm run build` — exit 0.
- 로컬 dev 서버(`http://localhost:5174`)에서 세션 생성 후 백룸(`?session=<id>`)으로 접속해 육안 확인. 기존 로컬 백엔드(`127.0.0.1:8000`)가 떠 있어야 세션 생성이 된다 — 안 떠 있으면 `cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`으로 재기동.
- 커밋은 태스크 단위로, 매번 관련 파일만 스테이징.

---

### Task 1: TopbarStatus에서 타이머/배지 필드 제거 (topbar 정리)

**Files:**
- Modify: `frontend/dashboard/src/components/Monitor.tsx` (TopbarStatus 인터페이스, onStatusChange 호출부)
- Modify: `frontend/dashboard/src/App.tsx` (topbar JSX)

**Interfaces:**
- Produces: `TopbarStatus`가 `role`/`phase`/`ending`/`hasReport`/`onEndSession`/`onOpenReport` 6개 필드만 갖는다 (이후 태스크가 이 형태를 그대로 씀).

- [ ] **Step 1: `TopbarStatus` 인터페이스에서 3개 필드 제거**

`frontend/dashboard/src/components/Monitor.tsx`에서:

```ts
export interface TopbarStatus {
  role: Role;
  phase: Phase;
  timerLabel: string;
  phaseLabel: string;
  connectionStatus: string;
  ending: boolean;
  hasReport: boolean;
  onEndSession: () => void;
  onOpenReport: () => void;
}
```
→
```ts
export interface TopbarStatus {
  role: Role;
  phase: Phase;
  ending: boolean;
  hasReport: boolean;
  onEndSession: () => void;
  onOpenReport: () => void;
}
```

- [ ] **Step 2: `onStatusChange` 호출부에서 3개 필드 제거**

같은 파일에서:

```ts
  useEffect(() => {
    onStatusChange?.({
      role,
      phase,
      timerLabel,
      phaseLabel,
      connectionStatus: status,
      ending,
      hasReport: report != null,
      onEndSession: handleEndSession,
      onOpenReport: handleOpenReport,
    });
  }, [role, phase, timerLabel, phaseLabel, status, ending, report, handleEndSession, handleOpenReport, onStatusChange]);
```
→
```ts
  useEffect(() => {
    onStatusChange?.({
      role,
      phase,
      ending,
      hasReport: report != null,
      onEndSession: handleEndSession,
      onOpenReport: handleOpenReport,
    });
  }, [role, phase, ending, report, handleEndSession, handleOpenReport, onStatusChange]);
```

(`timerLabel`/`phaseLabel`/`status` 변수 자체는 이 컴포넌트 다른 곳에서 계속 쓰이므로 삭제하지 않는다 — 이 useEffect의 의존성 배열에서만 뺀다.)

- [ ] **Step 3: App.tsx에서 타이머/배지 JSX 삭제**

`frontend/dashboard/src/App.tsx`에서:

```tsx
          {topbarStatus && (
            <>
              <span className="timer">
                <span className="dot" />
                <b>{topbarStatus.timerLabel}</b>
                <small>{topbarStatus.phaseLabel}</small>
              </span>
              <span className={`badge ${topbarStatus.connectionStatus}`}>{topbarStatus.connectionStatus}</span>
              {topbarStatus.role === "pm" && (topbarStatus.phase === "wait" || topbarStatus.phase === "joined") && (
```
→
```tsx
          {topbarStatus && (
            <>
              {topbarStatus.role === "pm" && (topbarStatus.phase === "wait" || topbarStatus.phase === "joined") && (
```

- [ ] **Step 4: 빌드 검증**

Run: `cd frontend/dashboard && npm run build`
Expected: exit code 0 (TypeScript가 `TopbarStatus`의 남은 필드만 참조하는지도 같이 체크됨)

- [ ] **Step 5: 육안 확인**

`http://localhost:5174/?session=<세션ID>`에서 백룸 진입 → 상단바에 타이머/connected 배지가 더 이상 안 보이고, PM/클라이언트 모드 전환·인터뷰 시작/종료 버튼·세션 목록으로 버튼은 그대로 있는지 확인.

- [ ] **Step 6: 커밋**

```bash
git add frontend/dashboard/src/components/Monitor.tsx frontend/dashboard/src/App.tsx
git commit -m "refactor: topbar에서 타이머/연결배지 제거 (응답자화면으로 이전 예정)"
```

---

### Task 2: 응답자 화면 패널 헤더에 타이머/연결배지 인라인 추가

**Files:**
- Modify: `frontend/dashboard/src/components/Monitor.tsx`
- Modify: `frontend/dashboard/src/styles.css`

**Interfaces:**
- Consumes: Task 1에서 그대로 남아있는 로컬 변수 `timerLabel`(string), `status`(string: `"connecting"|"connected"|"closed"|"error"`)
- Produces: 없음

- [ ] **Step 1: 응답자 화면 헤더에 타이머/배지 삽입**

`frontend/dashboard/src/components/Monitor.tsx`에서:

```tsx
      <section className="panel">
        <header className="p-head">
          <div>
            <h2>응답자 화면</h2>
            <div className="sub">실시간 상태 · {phaseLabel}</div>
          </div>
        </header>
```
→
```tsx
      <section className="panel">
        <header className="p-head">
          <div>
            <h2>응답자 화면</h2>
            <div className="sub status-line">
              <span>실시간 상태 · {phaseLabel}</span>
              <span className="timer-inline">
                <span className="dot" />
                {timerLabel}
              </span>
              <span className={`badge ${status}`}>{status}</span>
            </div>
          </div>
        </header>
```

- [ ] **Step 2: CSS 추가**

`frontend/dashboard/src/styles.css`의 `.p-head .sub` 규칙 바로 아래에 추가:

```css
.status-line {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.timer-inline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  border: 1px solid rgba(16, 185, 129, 0.3);
  background: rgba(16, 185, 129, 0.08);
  font-size: 11px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--success);
}

.timer-inline .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--success);
  box-shadow: 0 0 8px var(--success);
}
```

- [ ] **Step 3: 빌드 검증**

Run: `cd frontend/dashboard && npm run build`
Expected: exit code 0

- [ ] **Step 4: 육안 확인**

백룸의 "응답자 화면" 패널 헤더에서 "실시간 상태 · 대기" 옆에 초록 타이머 캡슐(`00:00`)과 `connected` 배지가 나란히 보이는지 확인.

- [ ] **Step 5: 커밋**

```bash
git add frontend/dashboard/src/components/Monitor.tsx frontend/dashboard/src/styles.css
git commit -m "feat: 응답자 화면 패널 헤더에 타이머/연결배지 인라인 표시"
```

---

### Task 3: 좌측 아코디언 사이드바 전환 (질문 트리 + 세션 링크 + 접힘 레일)

**Files:**
- Modify: `frontend/dashboard/src/components/Monitor.tsx`
- Modify: `frontend/dashboard/src/styles.css`

**Interfaces:**
- Produces: `treeOpen`(boolean state), `linksOpen`(boolean state) — Task 4는 이 둘을 직접 쓰지 않지만 같은 파일의 `<main className="monitor">` 클래스 계산 로직이 참조한다.

- [ ] **Step 1: state 2개 추가**

`frontend/dashboard/src/components/Monitor.tsx`에서 `const [previewPhase, setPreviewPhase] = useState<Phase | null>(null);` 바로 아래에 추가:

```ts
  const [treeOpen, setTreeOpen] = useState(true);
  const [linksOpen, setLinksOpen] = useState(false);
```

- [ ] **Step 2: `<main>` 태그에 접힘 클래스 조건부 적용**

```tsx
      <main className="monitor">
```
→
```tsx
      <main className={`monitor ${treeOpen || linksOpen ? "" : "monitor--sidebar-collapsed"}`}>
```

- [ ] **Step 3: 질문 트리 섹션을 col-questions 래퍼 div + 아코디언 2개로 교체**

아래 전체 블록을:

```tsx
      <section className="panel col-questions">
        <header className="p-head">
          <div>
            <h2>질문 트리</h2>
            <div className="sub">답변 분기별 파생질문 트리</div>
          </div>
          {role === "pm" ? (
            <button type="button" className="btn-sm solid" disabled title="곧 지원 예정">
              ＋ 질문 편집
            </button>
          ) : (
            <span className="role-chip" style={{ fontSize: "10px" }}>
              참관 전용
            </span>
          )}
        </header>
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
      </section>
```

다음으로 교체한다:

```tsx
      <div className="col-questions">
        {treeOpen || linksOpen ? (
          <>
            <section className="panel accordion">
              <button type="button" className="accordion-head" onClick={() => setTreeOpen((v) => !v)}>
                <div>
                  <h2>질문 트리</h2>
                  <div className="sub">답변 분기별 파생질문 트리</div>
                </div>
                <span className="accordion-caret">{treeOpen ? "▾" : "▸"}</span>
              </button>
              {treeOpen && (
                <>
                  <div className="accordion-actions">
                    {role === "pm" ? (
                      <button type="button" className="btn-sm solid" disabled title="곧 지원 예정">
                        ＋ 질문 편집
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
                </>
              )}
            </section>

            <section className="panel accordion">
              <button type="button" className="accordion-head" onClick={() => setLinksOpen((v) => !v)}>
                <div>
                  <h2>세션 링크</h2>
                  <div className="sub">인터뷰이 · 클라이언트 접속 링크</div>
                </div>
                <span className="accordion-caret">{linksOpen ? "▾" : "▸"}</span>
              </button>
              {linksOpen && (
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
              )}
            </section>
          </>
        ) : (
          <div className="sidebar-rail">
            <button type="button" className="rail-btn" title="질문 트리 펼치기" onClick={() => setTreeOpen(true)}>
              🌳
            </button>
            <button type="button" className="rail-btn" title="세션 링크 펼치기" onClick={() => setLinksOpen(true)}>
              🔗
            </button>
          </div>
        )}
      </div>
```

- [ ] **Step 4: 응답자 화면 위 기존 링크 표시 제거**

같은 파일에서, "응답자 화면" 섹션 안 `<div className="resp-stage">` 바로 위에 있는 아래 블록을 통째로 삭제한다 (세션 링크 아코디언으로 옮겼으므로 중복):

```tsx
        {intervieweeUrl && role === "pm" && (
          <p className="link-row" style={{ margin: "12px 16px 0" }}>
            응답자 링크: <code>{intervieweeUrl}</code>
            <button className="ghost" onClick={() => navigator.clipboard.writeText(intervieweeUrl)}>
              복사
            </button>
          </p>
        )}

        <div className="resp-stage">
```
→
```tsx
        <div className="resp-stage">
```

- [ ] **Step 5: `.monitor` 그리드 컬럼 폭 갱신 + 접힘/아코디언/레일 CSS 추가**

`frontend/dashboard/src/styles.css`에서:

```css
.monitor {
  display: grid;
  grid-template-columns: minmax(280px, 0.9fr) minmax(0, 1.5fr) minmax(340px, 0.95fr);
  gap: 24px;
  padding: 24px 30px 60px;
  align-items: start;
}
```
→
```css
.monitor {
  display: grid;
  grid-template-columns: minmax(240px, 0.8fr) minmax(0, 1.7fr) minmax(320px, 1fr);
  gap: 24px;
  padding: 24px 30px 60px;
  align-items: start;
}

.monitor.monitor--sidebar-collapsed {
  grid-template-columns: 56px minmax(0, 1.7fr) minmax(320px, 1fr);
}
```

그 아래(같은 파일, `.col-questions,\n.col-transcript,\n.col-instructions { ... }` 규칙 뒤)에 새 규칙을 추가한다:

```css
.accordion-head {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 20px 24px;
  background: none;
  border: none;
  border-bottom: 1px solid var(--panel-border);
  cursor: pointer;
  text-align: left;
  font: inherit;
  color: inherit;
}

.accordion-caret {
  flex-shrink: 0;
  color: var(--muted);
  font-size: 12px;
}

.accordion-actions {
  padding: 12px 24px 0;
}

.sidebar-rail {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding-top: 12px;
}

.rail-btn {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  border: 1px solid var(--panel-border);
  background: var(--panel);
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
```

- [ ] **Step 6: 빌드 검증**

Run: `cd frontend/dashboard && npm run build`
Expected: exit code 0

- [ ] **Step 7: 육안 확인**

백룸에서:
- 질문 트리가 기본으로 펼쳐져 있는지 (지금과 동일한 내용)
- "질문 트리" 헤더를 클릭하면 접히는지, 응답자 화면이 넓어지는지
- "세션 링크" 헤더를 클릭하면 펼쳐지고 인터뷰이 링크+복사 버튼이 나오는지, 복사가 실제로 동작하는지
- 질문 트리·세션 링크를 둘 다 접으면 좌측이 56px 아이콘 레일로 줄어드는지, 🌳/🔗 아이콘을 누르면 다시 펼쳐지는지

- [ ] **Step 8: 커밋**

```bash
git add frontend/dashboard/src/components/Monitor.tsx frontend/dashboard/src/styles.css
git commit -m "feat: 좌측 사이드바를 질문트리/세션링크 아코디언 + 접힘 레일로 전환"
```

---

### Task 4: 실시간 진행상황을 우측으로 이동 + 지시이력을 실시간지시 안에 토글로 병합

**Files:**
- Modify: `frontend/dashboard/src/components/Monitor.tsx`
- Modify: `frontend/dashboard/src/styles.css`

**Interfaces:**
- Produces: `historyOpen`(boolean state) — 이 태스크 안에서만 쓰임

- [ ] **Step 1: `historyOpen` state 추가**

`frontend/dashboard/src/components/Monitor.tsx`에서 Task 3이 추가한 `const [linksOpen, setLinksOpen] = useState(false);` 바로 아래에 추가:

```ts
  const [historyOpen, setHistoryOpen] = useState(false);
```

- [ ] **Step 2: "실시간 진행 상황" 섹션을 `col-transcript`에서 삭제**

`col-transcript` div 안, "응답자 화면" `</section>` 바로 뒤에 있는 아래 블록을 **정확히 이 범위만** 삭제한다 — 마지막 `</section>` 다음에 오는 `</div>`(col-transcript를 닫는 태그)는 그대로 남겨둔다, 건드리지 않는다. (이 섹션 내용은 다음 스텝에서 `col-instructions`로 옮겨 붙인다 — 지금은 여기서 잘라내기만):

```tsx
      <section className="panel">
        <header className="p-head">
          <div>
            <h2>실시간 진행 상황</h2>
            <div className="sub">STT 변환 · AI 판단 · 질문/답변 순</div>
          </div>
          <div className="lang-toggle">
            <button type="button" className="active" disabled title="곧 지원 예정">
              원문
            </button>
            <button type="button" disabled title="곧 지원 예정">
              원문+번역
            </button>
          </div>
        </header>

        <div className="turns">
          {transcript.map((turn) => (
            <article key={`${turn.speaker}-${turn.index}`} className={`turn ${turn.speaker}`}>
              <div className="turn-head">
                <strong>{turn.speaker === "assistant" ? "AI 진행자" : "응답자"}</strong>
                <time>
                  {new Date(turn.created_at).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })}
                </time>
              </div>
              <p>{turn.text}</p>
              {/* AI 판단 근거는 참관자에게만 보인다 (C5) */}
              {turn.rationale && (
                <div className="rationale">
                  <div className="ai-label">AI 판단 근거</div>
                  {turn.rationale}
                </div>
              )}
            </article>
          ))}
          {transcript.length === 0 && (
            <p className="empty">
              {phase === "wait" && "인터뷰이가 입장하면 대화가 여기에 표시됩니다."}
              {phase === "joined" && "인터뷰이가 입장했습니다. 첫 발화가 오면 진행됩니다."}
              {(phase === "live" || phase === "end") && "아직 발화가 없습니다."}
            </p>
          )}
        </div>

        {phase === "end" && (
          <div className="report-note">
            {!report ? (
              <>세션이 종료되었습니다. <b>AI 리포트</b>를 생성하고 있습니다 — 완료되면 아래에 표시됩니다.</>
            ) : (
              <>
                <b>AI 리포트</b>가 생성되었습니다.
              </>
            )}
          </div>
        )}
        {report && (
          <div className="report-highlight" ref={reportRef}>
            {typeof report.data.summary === "string" && <p>{report.data.summary}</p>}
            <pre style={{ whiteSpace: "pre-wrap", margin: 0, fontSize: 11 }}>
              {JSON.stringify(report.data, null, 2)}
            </pre>
          </div>
        )}
      </section>
```

삭제 후 `col-transcript` div는 이렇게 짧아진다 (응답자 화면 섹션 바로 뒤에 div를 닫는 태그만 남음):

```tsx
        </div>
      </section>
      </div>
```

(맨 위 `</div>`는 응답자 화면 안 `.resp-stage`를 닫는 태그, 그 다음 `</section>`은 응답자 화면 패널 자체, 마지막 `</div>`가 `col-transcript`다 — 이 셋은 원래도 있던 태그라 손댈 필요 없다. 이번 스텝에서 지우는 건 오직 그 사이에 있던 "실시간 진행 상황" `<section>...</section>` 블록뿐이다.)

- [ ] **Step 3: `col-instructions` 안 "지시 이력" 별도 패널을 토글로 교체**

`col-instructions` div 안, "실시간 지시" 섹션의 아래 블록을:

```tsx
            <p className="muted small" style={{ padding: "10px 16px 16px" }}>
              응답자의 다음 발화가 끝나면 1건씩 순서대로 주입됩니다.
            </p>
          </section>

          <section className="panel">
            <header className="p-head">
              <div>
                <h2>지시 이력</h2>
                <div className="sub">보낸 지시와 반영 상태</div>
              </div>
            </header>
            <div className="p-body">
              <ul className="hist">
                {instructions.map((instruction) => (
                  <li key={instruction.id} className="h-item">
                    <time>
                      {new Date(instruction.created_at).toLocaleTimeString("ko-KR", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </time>
                    <span className={`h-dot ${instruction.status}`} />
                    <div className="h-body">
                      <div className={`h-state ${instruction.status}`}>
                        {instruction.status === "applied" ? "반영됨" : "대기 중"}
                      </div>
                      <div className="h-text">{instruction.text}</div>
                    </div>
                  </li>
                ))}
                {instructions.length === 0 && <p className="empty">아직 보낸 지시가 없습니다.</p>}
              </ul>
            </div>
          </section>
        </div>
      )}
```

다음으로 교체한다:

```tsx
            <p className="muted small" style={{ padding: "10px 16px 16px" }}>
              응답자의 다음 발화가 끝나면 1건씩 순서대로 주입됩니다.
            </p>

            <button
              type="button"
              className="accordion-head accordion-head--sub"
              onClick={() => setHistoryOpen((v) => !v)}
            >
              <h2>지시 이력</h2>
              <span className="accordion-caret">{historyOpen ? "▾" : "▸"}</span>
            </button>
            {historyOpen && (
              <div className="p-body">
                <ul className="hist">
                  {instructions.map((instruction) => (
                    <li key={instruction.id} className="h-item">
                      <time>
                        {new Date(instruction.created_at).toLocaleTimeString("ko-KR", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </time>
                      <span className={`h-dot ${instruction.status}`} />
                      <div className="h-body">
                        <div className={`h-state ${instruction.status}`}>
                          {instruction.status === "applied" ? "반영됨" : "대기 중"}
                        </div>
                        <div className="h-text">{instruction.text}</div>
                      </div>
                    </li>
                  ))}
                  {instructions.length === 0 && <p className="empty">아직 보낸 지시가 없습니다.</p>}
                </ul>
              </div>
            )}
          </section>

          <section className="panel">
            <header className="p-head">
              <div>
                <h2>실시간 진행 상황</h2>
                <div className="sub">STT 변환 · AI 판단 · 질문/답변 순</div>
              </div>
              <div className="lang-toggle">
                <button type="button" className="active" disabled title="곧 지원 예정">
                  원문
                </button>
                <button type="button" disabled title="곧 지원 예정">
                  원문+번역
                </button>
              </div>
            </header>

            <div className="turns">
              {transcript.map((turn) => (
                <article key={`${turn.speaker}-${turn.index}`} className={`turn ${turn.speaker}`}>
                  <div className="turn-head">
                    <strong>{turn.speaker === "assistant" ? "AI 진행자" : "응답자"}</strong>
                    <time>
                      {new Date(turn.created_at).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })}
                    </time>
                  </div>
                  <p>{turn.text}</p>
                  {/* AI 판단 근거는 참관자에게만 보인다 (C5) */}
                  {turn.rationale && (
                    <div className="rationale">
                      <div className="ai-label">AI 판단 근거</div>
                      {turn.rationale}
                    </div>
                  )}
                </article>
              ))}
              {transcript.length === 0 && (
                <p className="empty">
                  {phase === "wait" && "인터뷰이가 입장하면 대화가 여기에 표시됩니다."}
                  {phase === "joined" && "인터뷰이가 입장했습니다. 첫 발화가 오면 진행됩니다."}
                  {(phase === "live" || phase === "end") && "아직 발화가 없습니다."}
                </p>
              )}
            </div>

            {phase === "end" && (
              <div className="report-note">
                {!report ? (
                  <>세션이 종료되었습니다. <b>AI 리포트</b>를 생성하고 있습니다 — 완료되면 아래에 표시됩니다.</>
                ) : (
                  <>
                    <b>AI 리포트</b>가 생성되었습니다.
                  </>
                )}
              </div>
            )}
            {report && (
              <div className="report-highlight" ref={reportRef}>
                {typeof report.data.summary === "string" && <p>{report.data.summary}</p>}
                <pre style={{ whiteSpace: "pre-wrap", margin: 0, fontSize: 11 }}>
                  {JSON.stringify(report.data, null, 2)}
                </pre>
              </div>
            )}
          </section>
        </div>
      )}
```

- [ ] **Step 4: `.accordion-head--sub` CSS 추가**

`frontend/dashboard/src/styles.css`의 `.accordion-actions` 규칙 뒤에 추가:

```css
.accordion-head--sub {
  border-top: 1px solid var(--panel-border);
  border-bottom: none;
  margin-top: 8px;
  padding: 14px 16px;
}
```

- [ ] **Step 5: 빌드 검증**

Run: `cd frontend/dashboard && npm run build`
Expected: exit code 0

- [ ] **Step 6: 육안 확인**

백룸 우측 컬럼에서:
- 위에서부터 "실시간 지시"(입력창+버튼+빠른지시+"지시 이력" 토글) → "실시간 진행 상황"(대화 목록) 순서로 보이는지
- "지시 이력" 토글이 기본 접혀있고, 클릭하면 펼쳐지는지
- 가운데 컬럼엔 "응답자 화면"만 남고 넓어졌는지
- 세션 상태 미리보기 탭(대기/입장함/진행중/종료)을 눌러봐도 레이아웃이 안 깨지는지

- [ ] **Step 7: 커밋**

```bash
git add frontend/dashboard/src/components/Monitor.tsx frontend/dashboard/src/styles.css
git commit -m "feat: 실시간 진행상황을 우측으로 이동, 지시이력을 실시간지시 안 토글로 병합"
```
