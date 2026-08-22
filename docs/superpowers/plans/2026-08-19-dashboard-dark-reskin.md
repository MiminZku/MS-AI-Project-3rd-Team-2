# 대시보드 다크 리스킨 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `frontend/dashboard/src/styles.css` 하나를 인터뷰이(`frontend/interviewee`)와 같은 Apple 스타일 다크 미니멀 토큰으로 재작성해서, 두 프론트가 시각적으로 같은 제품군처럼 보이게 한다.

**Architecture:** 순수 CSS 리스킨. `App.tsx`/`Monitor.tsx`/`SessionForm.tsx`/`VideoSubscriber.tsx`의 JSX·클래스명은 전혀 건드리지 않는다. `styles.css` 한 파일 안에서 (1) `:root` 토큰 재정의, (2) 전역 변수명 리네임(기계적 치환), (3) 화면 영역별로 하드코딩된 색상/반경/그림자를 새 토큰 기준으로 교체하는 순서로 진행한다.

**Tech Stack:** Vite 6 + React 18 + TypeScript(빌드 검증용), 순수 CSS(전처리기/CSS-in-JS 없음).

## Global Constraints

- 대상 파일은 오직 `frontend/dashboard/src/styles.css` 하나. 다른 파일은 수정하지 않는다.
- 스펙: `docs/superpowers/specs/2026-08-19-dashboard-dark-reskin-design.md` — 모든 토큰/반경 값은 이 문서와 일치해야 한다.
- **틴트 배경 파생 규칙** (스펙에 없는 세부 rgba 값을 정할 때 이 규칙을 따른다):
  - 카드형 틴트 배경(`.rationale`, `.report-note`, `.linkrow`, `.link-row` 등 박스형 요소): 배경 `rgba(<accent-rgb>, 0.08)`, 테두리 `rgba(<accent-rgb>, 0.2)`
  - 작은 뱃지/필 틴트(`.q-num`, `.cond`, `.turn strong`, `.badge.connected/error`, `.tree li.current .q-num` 계열, `.lk-tag`, `.audio-seg button.on`, `.lang-toggle button.active`): 배경 `rgba(<accent-rgb>, 0.15)`, 테두리/색 `rgba(<accent-rgb>, 0.3~0.4)` — 작은 크기라 채도를 더 준다
  - accent-rgb 매핑: 파랑(액센트) `0, 113, 227` / 초록(success) `16, 185, 129` / 빨강(error) `239, 68, 68` / 주황(warning) `245, 158, 11`
- **중간 상태 주의**: Task 1에서 `var(--primary2)`, `var(--shadow)` 정의를 `:root`에서 제거하지만, 이 두 변수를 실제로 사용하는 규칙(`.sess-btn.go`, `.composer > button`, `.btn-sm.solid`, 전역 `button`, `.panel`)은 각각 Task 2/3/5/6에서 고친다. 즉 Task 1 커밋 직후부터 Task 6 커밋 전까지는 해당 버튼들이 배경 없이 보일 수 있다 — 이건 이번 리스킨의 정상적인 중간 상태이며 버그가 아니다. `var()`에 정의되지 않은 커스텀 프로퍼티가 있어도 `vite build`는 실패하지 않는다(런타임에만 무시됨).
- 빌드 검증 명령(모든 태스크 공통): `cd frontend/dashboard && npm run build` — `tsc --noEmit && vite build`. CSS만 바꾸는 작업이므로 항상 exit 0이어야 하며, 실패하면 CSS 문법 오류(중괄호 누락 등)를 의심한다.
- 로컬 대시보드 dev 서버(`http://localhost:5174`)가 이미 떠 있다면 파일 저장 시 Vite HMR로 자동 반영된다. 안 떠 있으면 `cd frontend/dashboard && npm run dev`로 띄운다.
- 커밋은 태스크 단위로, 매번 `git add frontend/dashboard/src/styles.css`만 스테이징한다(다른 파일 실수로 포함 금지).

---

### Task 1: 루트 토큰 재정의 + 전역 변수명 리네임

**Files:**
- Modify: `frontend/dashboard/src/styles.css:1-29` (`:root`, `*`, `body`)
- Modify: `frontend/dashboard/src/styles.css` 전체 (변수명 기계적 치환, 5건)

**Interfaces:**
- Produces: 이후 모든 태스크가 참조하는 토큰 이름 — `--bg`, `--panel`, `--panel-border`, `--text`, `--text-white`, `--muted`, `--primary`, `--success`, `--error`, `--warning`. 이후 태스크는 이 이름들을 그대로 사용한다.

- [ ] **Step 1: `:root`/`*`/`body` 블록 교체**

`frontend/dashboard/src/styles.css`의 아래 블록(1~29번 줄)을:

```css
@import "pretendard/dist/web/variable/pretendardvariable.css";

:root {
  color-scheme: light;
  --bg: #eef1f6;
  --panel: #fff;
  --line: #e2e7ef;
  --text: #1a2233;
  --muted: #545b6b;
  --primary: #5b4de9;
  --primary2: #8172fb;
  --live: #16a36a;
  --danger: #db4b50;
  --ok: #16a36a;
  --warn: #d98c16;
  --shadow: 0 10px 30px rgba(29, 38, 60, 0.06);
  font-family: "Pretendard Variable", Pretendard, system-ui, -apple-system, "Segoe UI", "Malgun Gothic",
    sans-serif;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
}
```

다음으로 교체한다:

```css
@import "pretendard/dist/web/variable/pretendardvariable.css";

:root {
  color-scheme: dark;
  --bg: #000000;
  --panel: #1d1d1f;
  --panel-border: rgba(255, 255, 255, 0.08);
  --text: #f5f5f7;
  --text-white: #ffffff;
  --muted: #86868b;
  --primary: #0071e3;
  --success: #10b981;
  --error: #ef4444;
  --warning: #f59e0b;
  font-family: "Pretendard Variable", Pretendard, "SF Pro Display", -apple-system, "Segoe UI",
    "Malgun Gothic", sans-serif;
  letter-spacing: -0.015em;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
}
```

- [ ] **Step 2: 전역 변수명 기계적 치환 (파일 전체, `replace_all`)**

같은 파일에서 아래 5건을 각각 `replace_all`로 치환한다 (순서 무관):

1. `var(--line)` → `var(--panel-border)`
2. `var(--live)` → `var(--success)`
3. `var(--ok)` → `var(--success)`
4. `var(--danger)` → `var(--error)`
5. `var(--warn)` → `var(--warning)`

- [ ] **Step 3: 빌드 검증**

Run: `cd frontend/dashboard && npm run build`
Expected: exit code 0, 에러 없음

- [ ] **Step 4: 육안 확인 (선택 — 이 시점엔 페이지 전체가 아직 부분적으로 깨져 보일 수 있음)**

`http://localhost:5174` 접속 시 배경이 검은색으로 바뀌고 기본 텍스트가 밝은 회색으로 보이면 정상. 버튼/뱃지 색이 아직 안 맞는 건 이후 태스크에서 처리하므로 지금은 무시한다.

- [ ] **Step 5: 커밋**

```bash
git add frontend/dashboard/src/styles.css
git commit -m "style: 대시보드 루트 토큰을 다크 팔레트로 재정의"
```

---

### Task 2: 탑바 + 세션 상태 탭바

**Files:**
- Modify: `frontend/dashboard/src/styles.css:42-190` (`.topbar` ~ `.sess-btn.stop`)
- Modify: `frontend/dashboard/src/styles.css:192-245` (`.tabbar`, `.swg`)

**Interfaces:**
- Consumes: Task 1의 `--panel`, `--panel-border`, `--text`, `--text-white`, `--muted`, `--primary`, `--success`, `--error` 토큰
- Produces: 없음 (leaf 규칙들)

- [ ] **Step 1: `.topbar`, `.crumb .glyph`, `.role-switch`, `.role-chip` 교체**

아래 규칙들을 각각 찾아 교체한다 (Task 1 이후 상태 기준 — `var(--line)`은 이미 `var(--panel-border)`로 바뀌어 있음):

`.topbar`:
```css
.topbar {
  height: 60px;
  background: #fff;
  border-bottom: 1px solid var(--panel-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 22px;
  position: sticky;
  top: 0;
  z-index: 30;
}
```
→
```css
.topbar {
  height: 60px;
  background: var(--panel);
  border-bottom: 1px solid var(--panel-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 22px;
  position: sticky;
  top: 0;
  z-index: 30;
}
```

`.crumb .glyph`:
```css
.crumb .glyph {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: linear-gradient(135deg, #6c5df8, #57c9ff);
  display: grid;
  place-items: center;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
}
```
→
```css
.crumb .glyph {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: var(--primary);
  display: grid;
  place-items: center;
  color: var(--text-white);
  font-size: 12px;
  font-weight: 700;
}
```

`.role-switch`:
```css
.role-switch {
  display: flex;
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  overflow: hidden;
}
```
→
```css
.role-switch {
  display: flex;
  border: 1px solid var(--panel-border);
  border-radius: 9999px;
  overflow: hidden;
}
```

`.role-switch button`:
```css
.role-switch button {
  border: 0;
  border-right: 1px solid var(--panel-border);
  background: #fff;
  padding: 7px 12px;
  font-size: 11px;
  font-weight: 700;
  color: var(--muted);
  cursor: pointer;
}
```
→
```css
.role-switch button {
  border: 0;
  border-right: 1px solid var(--panel-border);
  background: var(--panel);
  padding: 7px 12px;
  font-size: 11px;
  font-weight: 700;
  color: var(--muted);
  cursor: pointer;
}
```

`.role-switch button.on`:
```css
.role-switch button.on {
  background: #eeeaff;
  color: #5c4ee5;
}
```
→
```css
.role-switch button.on {
  background: var(--primary);
  color: var(--text-white);
}
```

`.role-chip`:
```css
.role-chip {
  font-size: 11px;
  color: var(--muted);
  border: 1px solid var(--panel-border);
  background: #fff;
  padding: 7px 11px;
  border-radius: 8px;
  font-weight: 600;
  white-space: nowrap;
}
```
→
```css
.role-chip {
  font-size: 11px;
  color: var(--muted);
  border: 1px solid var(--panel-border);
  background: var(--panel);
  padding: 7px 11px;
  border-radius: 9999px;
  font-weight: 600;
  white-space: nowrap;
}
```

- [ ] **Step 2: `.timer` 계열 교체 (라이브 점 글로우 추가)**

`.timer`:
```css
.timer {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 8px 14px;
  border: 1px solid #cfe9dc;
  background: #f3fbf7;
  border-radius: 999px;
}
```
→
```css
.timer {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 8px 14px;
  border: 1px solid rgba(16, 185, 129, 0.3);
  background: rgba(16, 185, 129, 0.08);
  border-radius: 999px;
}
```

`.timer .dot`:
```css
.timer .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--success);
  animation: pulse 2.2s infinite;
}
```
→
```css
.timer .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--success);
  box-shadow: 0 0 12px var(--success);
  animation: pulse 2.2s infinite;
}
```

`@keyframes pulse`:
```css
@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(22, 163, 106, 0.5);
  }
  70% {
    box-shadow: 0 0 0 7px rgba(22, 163, 106, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(22, 163, 106, 0);
  }
}
```
→
```css
@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.5);
  }
  70% {
    box-shadow: 0 0 0 7px rgba(16, 185, 129, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
  }
}
```

`.timer b`:
```css
.timer b {
  font-size: 14px;
  font-variant-numeric: tabular-nums;
  color: #137a52;
  letter-spacing: 0.5px;
}
```
→
```css
.timer b {
  font-size: 14px;
  font-variant-numeric: tabular-nums;
  color: var(--success);
  letter-spacing: 0.5px;
}
```

`.timer small`:
```css
.timer small {
  font-size: 10px;
  color: #5aa588;
}
```
→
```css
.timer small {
  font-size: 10px;
  color: var(--muted);
}
```

- [ ] **Step 3: `.sess-btn` 계열 교체**

`.sess-btn`:
```css
.sess-btn {
  border: none;
  border-radius: 9px;
  padding: 8px 15px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
}
```
→
```css
.sess-btn {
  border: none;
  border-radius: 28px;
  padding: 8px 15px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
}
```

`.sess-btn.go`:
```css
.sess-btn.go {
  background: linear-gradient(135deg, var(--primary), var(--primary2));
  color: #fff;
}
```
→
```css
.sess-btn.go {
  background: var(--primary);
  color: var(--text-white);
}
```

`.sess-btn.go:disabled`:
```css
.sess-btn.go:disabled {
  background: #cdd2dc;
  cursor: not-allowed;
}
```
→
```css
.sess-btn.go:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
```

`.sess-btn.stop`:
```css
.sess-btn.stop {
  background: #fff;
  color: var(--error);
  border: 1px solid #f0c3c5;
}
```
→
```css
.sess-btn.stop {
  background: var(--panel);
  color: var(--error);
  border: 1px solid rgba(239, 68, 68, 0.3);
}
```

- [ ] **Step 4: `.tabbar`, `.swg` 교체**

`.tabbar`:
```css
.tabbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 20px;
  background: #fff;
  border-bottom: 1px solid var(--panel-border);
  flex-wrap: wrap;
  position: sticky;
  top: 60px;
  z-index: 25;
}
```
→
```css
.tabbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 20px;
  background: var(--panel);
  border-bottom: 1px solid var(--panel-border);
  flex-wrap: wrap;
  position: sticky;
  top: 60px;
  z-index: 25;
}
```

`.tabbar .tlab`:
```css
.tabbar .tlab {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.05em;
  color: #9aa2b1;
  text-transform: uppercase;
}
```
→
```css
.tabbar .tlab {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.05em;
  color: var(--muted);
  text-transform: uppercase;
}
```

`.swg`:
```css
.swg {
  display: flex;
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  overflow: hidden;
}
```
→
```css
.swg {
  display: flex;
  border: 1px solid var(--panel-border);
  border-radius: 9999px;
  overflow: hidden;
}
```

`.swg button`:
```css
.swg button {
  border: 0;
  background: #fff;
  padding: 7px 12px;
  font-size: 11px;
  font-weight: 700;
  color: var(--muted);
  border-right: 1px solid var(--panel-border);
}
```
→
```css
.swg button {
  border: 0;
  background: var(--panel);
  padding: 7px 12px;
  font-size: 11px;
  font-weight: 700;
  color: var(--muted);
  border-right: 1px solid var(--panel-border);
}
```

`.swg button.on`:
```css
.swg button.on {
  background: #eeeaff;
  color: #5c4ee5;
  cursor: default;
  opacity: 1;
}
```
→
```css
.swg button.on {
  background: var(--primary);
  color: var(--text-white);
  cursor: default;
  opacity: 1;
}
```

(`.swg button:disabled:not(.on)`은 색상 참조가 없어 변경 없음)

- [ ] **Step 5: 빌드 검증**

Run: `cd frontend/dashboard && npm run build`
Expected: exit code 0

- [ ] **Step 6: 육안 확인**

`http://localhost:5174`에서 세션 생성 후 백룸(Monitor)까지 진입해 상단 탑바(로고, 역할 전환, 타이머, 인터뷰 시작/종료 버튼)와 그 아래 세션 상태 탭바(대기/입장함/진행중/종료)가 검은 배경 위에서 파란 액센트로 잘 보이는지 확인.

- [ ] **Step 7: 커밋**

```bash
git add frontend/dashboard/src/styles.css
git commit -m "style: 대시보드 탑바/탭바 다크 리스킨"
```

---

### Task 3: 3단 레이아웃 패널 + 질문 트리

**Files:**
- Modify: `frontend/dashboard/src/styles.css:280-397` (`.panel` ~ `.cond`)

**Interfaces:**
- Consumes: Task 1 토큰

- [ ] **Step 1: `.panel` 그림자 제거 + 반경 확대**

```css
.panel {
  background: var(--panel);
  border: 1px solid var(--panel-border);
  border-radius: 16px;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
```
→
```css
.panel {
  background: var(--panel);
  border: 1px solid var(--panel-border);
  border-radius: 28px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
```

(`.panel-head`/`.p-head`/`.p-head h2`/`.p-head .sub`/`.p-body`는 색상 참조가 이미 Task 1에서 정리된 토큰(`var(--panel-border)`, `var(--muted)`)만 쓰므로 변경 없음)

- [ ] **Step 2: `.tree` 계열 색상 교체**

`.tree li`:
```css
.tree li {
  border-radius: 9px;
  padding: 9px 10px;
  color: #2c3547;
  line-height: 1.5;
}
```
→
```css
.tree li {
  border-radius: 9px;
  padding: 9px 10px;
  color: var(--text);
  line-height: 1.5;
}
```

`.tree li.current`:
```css
.tree li.current {
  background: #eef1fd;
  border: 1px solid #d3dbfa;
  font-weight: 600;
}
```
→
```css
.tree li.current {
  background: rgba(0, 113, 227, 0.15);
  border: 1px solid rgba(0, 113, 227, 0.4);
  font-weight: 600;
}
```

`.q-num`:
```css
.q-num {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  border-radius: 6px;
  background: #eef1fd;
  color: #4356b8;
  font-size: 10px;
  font-weight: 800;
  display: grid;
  place-items: center;
  margin-top: 1px;
}
```
→
```css
.q-num {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  border-radius: 6px;
  background: rgba(0, 113, 227, 0.15);
  color: #5ac8fa;
  font-size: 10px;
  font-weight: 800;
  display: grid;
  place-items: center;
  margin-top: 1px;
}
```

`.tree li.current .q-num`:
```css
.tree li.current .q-num {
  background: var(--primary);
  color: #fff;
}
```
→
```css
.tree li.current .q-num {
  background: var(--primary);
  color: var(--text-white);
}
```

`.tree li.done .q-num`:
```css
.tree li.done .q-num {
  background: #eafaf2;
  color: #178a5a;
}
```
→
```css
.tree li.done .q-num {
  background: rgba(16, 185, 129, 0.15);
  color: var(--success);
}
```

`.tree li.done`:
```css
.tree li.done {
  color: #8a92a2;
}
```
→
```css
.tree li.done {
  color: var(--muted);
}
```

`.branch`:
```css
.branch {
  margin: 6px 0 0 12px;
  padding: 6px 9px;
  border-radius: 8px;
  font-size: 11.5px;
  color: #4a5163;
  font-weight: 400;
  border-left: 1.5px dashed #d8dde8;
}
```
→
```css
.branch {
  margin: 6px 0 0 12px;
  padding: 6px 9px;
  border-radius: 8px;
  font-size: 11.5px;
  color: var(--text);
  font-weight: 400;
  border-left: 1.5px dashed var(--panel-border);
}
```

`.cond`:
```css
.cond {
  font-size: 9.5px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 5px;
  background: #eef1f5;
  color: #5a6475;
  margin-right: 6px;
}
```
→
```css
.cond {
  font-size: 9.5px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.08);
  color: var(--muted);
  margin-right: 6px;
}
```

- [ ] **Step 3: 빌드 검증**

Run: `cd frontend/dashboard && npm run build`
Expected: exit code 0

- [ ] **Step 4: 육안 확인**

백룸 좌측 "질문 트리" 패널이 28px 라운드 카드 안에서 그림자 없이 보이고, 현재 질문 하이라이트가 파란 틴트로, 완료된 질문이 회색으로 구분되는지 확인.

- [ ] **Step 5: 커밋**

```bash
git add frontend/dashboard/src/styles.css
git commit -m "style: 대시보드 3단 패널/질문 트리 다크 리스킨"
```

---

### Task 4: 응답자 스테이지 + 실시간 대화/AI 판단

**Files:**
- Modify: `frontend/dashboard/src/styles.css:399-577` (`.resp-stage` ~ `@keyframes talk`)
- Modify: `frontend/dashboard/src/styles.css:579-650` (`.turns` ~ `.rationale .ai-label`)

**Interfaces:**
- Consumes: Task 1 토큰

- [ ] **Step 1: `.resp-stage` 계열 — 그라디언트 제거, 단색화**

`.resp-stage`:
```css
.resp-stage {
  position: relative;
  aspect-ratio: 16 / 9;
  border-radius: 12px;
  overflow: hidden;
  background: linear-gradient(150deg, #22303f, #141c27);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 14px 16px 16px;
  text-align: center;
  color: #9fb3c8;
  font-size: 12.5px;
  line-height: 1.7;
}
```
→
```css
.resp-stage {
  position: relative;
  aspect-ratio: 16 / 9;
  border-radius: 20px;
  overflow: hidden;
  background: var(--panel);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 14px 16px 16px;
  text-align: center;
  color: var(--muted);
  font-size: 12.5px;
  line-height: 1.7;
}
```

`.resp-stage b`:
```css
.resp-stage b {
  display: block;
  color: #dbe6f2;
  font-size: 13.5px;
  margin-bottom: 4px;
}
```
→
```css
.resp-stage b {
  display: block;
  color: var(--text-white);
  font-size: 13.5px;
  margin-bottom: 4px;
}
```

`.rs-badge .rs-dot` (글로우 추가):
```css
.rs-badge .rs-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--success);
  animation: blink 1.1s infinite;
}
```
→
```css
.rs-badge .rs-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--success);
  box-shadow: 0 0 8px var(--success);
  animation: blink 1.1s infinite;
}
```

`.rs-figure svg`:
```css
.rs-figure svg {
  width: 100%;
  height: 100%;
  filter: drop-shadow(0 6px 22px rgba(87, 217, 163, 0.2));
}
```
→
```css
.rs-figure svg {
  width: 100%;
  height: 100%;
  filter: drop-shadow(0 6px 22px rgba(16, 185, 129, 0.25));
}
```

`.audio-seg button.on`:
```css
.audio-seg button.on {
  background: rgba(91, 77, 233, 0.85);
  color: #fff;
  opacity: 1;
}
```
→
```css
.audio-seg button.on {
  background: rgba(0, 113, 227, 0.85);
  color: var(--text-white);
  opacity: 1;
}
```

`.lang-toggle button`:
```css
.lang-toggle button {
  border: 1px solid var(--panel-border);
  background: #fff;
  border-radius: 8px;
  padding: 5px 10px;
  font-size: 10px;
  font-weight: 600;
  color: var(--muted);
}
```
→
```css
.lang-toggle button {
  border: 1px solid var(--panel-border);
  background: var(--panel);
  border-radius: 8px;
  padding: 5px 10px;
  font-size: 10px;
  font-weight: 600;
  color: var(--muted);
}
```

`.lang-toggle button.active`:
```css
.lang-toggle button.active {
  background: #eeeaff;
  color: #5c4ee5;
  border-color: #ded8ff;
  opacity: 1;
}
```
→
```css
.lang-toggle button.active {
  background: rgba(0, 113, 227, 0.15);
  color: var(--primary);
  border-color: rgba(0, 113, 227, 0.4);
  opacity: 1;
}
```

`.wave span`:
```css
.wave span {
  width: 3px;
  border-radius: 2px;
  background: var(--self, #1f9d6b);
  animation: talk 1s ease-in-out infinite;
}
```
→
```css
.wave span {
  width: 3px;
  border-radius: 2px;
  background: var(--self, #10b981);
  animation: talk 1s ease-in-out infinite;
}
```

- [ ] **Step 2: `.turns`/`.turn`/`.rationale` 계열 교체**

`.turn`:
```css
.turn {
  padding: 12px 4px;
  border-bottom: 1px solid #f0f2f6;
}
```
→
```css
.turn {
  padding: 12px 4px;
  border-bottom: 1px solid var(--panel-border);
}
```

`.turn strong`:
```css
.turn strong {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  background: #eafaf2;
  color: #178a5a;
}
```
→
```css
.turn strong {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(16, 185, 129, 0.15);
  color: var(--success);
}
```

`.turn.assistant strong`:
```css
.turn.assistant strong {
  background: #eef1fd;
  color: #4356b8;
}
```
→
```css
.turn.assistant strong {
  background: rgba(0, 113, 227, 0.15);
  color: #5ac8fa;
}
```

`.turn p`:
```css
.turn p {
  margin: 4px 0 0;
  font-size: 13.5px;
  line-height: 1.62;
  color: #2c3547;
}
```
→
```css
.turn p {
  margin: 4px 0 0;
  font-size: 13.5px;
  line-height: 1.62;
  color: var(--text);
}
```

`.rationale`:
```css
.rationale {
  margin: 8px 0 2px;
  padding: 9px 12px;
  border-radius: 10px;
  background: linear-gradient(180deg, #f6f4ff, #f1eeff);
  border: 1px solid #e2ddff;
  color: #4b4470;
  font-size: 11.5px;
  line-height: 1.5;
}
```
→
```css
.rationale {
  margin: 8px 0 2px;
  padding: 9px 12px;
  border-radius: 10px;
  background: rgba(0, 113, 227, 0.08);
  border: 1px solid rgba(0, 113, 227, 0.2);
  color: var(--text);
  font-size: 11.5px;
  line-height: 1.5;
}
```

`.rationale .ai-label`:
```css
.rationale .ai-label {
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #6a5cf0;
  margin-bottom: 3px;
}
```
→
```css
.rationale .ai-label {
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--primary);
  margin-bottom: 3px;
}
```

- [ ] **Step 3: 빌드 검증**

Run: `cd frontend/dashboard && npm run build`
Expected: exit code 0

- [ ] **Step 4: 육안 확인**

백룸 가운데 컬럼(응답자 스테이지 자리표시자)과 실시간 대화 리스트(응답자/AI 발화 뱃지, AI 판단 근거 박스)가 검은 배경에서 자연스럽게 보이는지 확인.

- [ ] **Step 5: 커밋**

```bash
git add frontend/dashboard/src/styles.css
git commit -m "style: 대시보드 응답자 스테이지/실시간 대화 다크 리스킨"
```

---

### Task 5: 지시 입력(Composer) + 히스토리 + 잠김/리포트

**Files:**
- Modify: `frontend/dashboard/src/styles.css:652-757` (`.composer textarea` ~ `.h-text`)
- Modify: `frontend/dashboard/src/styles.css:759-815` (`.locked::after` ~ `.empty`)

**Interfaces:**
- Consumes: Task 1 토큰

- [ ] **Step 1: `.composer` 계열 교체**

`.composer textarea`:
```css
.composer textarea {
  width: 100%;
  min-height: 88px;
  resize: vertical;
  border: 1px solid var(--panel-border);
  border-radius: 11px;
  padding: 12px;
  outline: none;
  font-size: 12.5px;
  line-height: 1.55;
  font-family: inherit;
}
```
→
```css
.composer textarea {
  width: 100%;
  min-height: 88px;
  resize: vertical;
  border: 1px solid var(--panel-border);
  border-radius: 20px;
  padding: 12px;
  outline: none;
  font-size: 12.5px;
  line-height: 1.55;
  font-family: inherit;
  background: #000000;
  color: var(--text-white);
}
```

`.composer textarea:focus`:
```css
.composer textarea:focus {
  border-color: #a99fff;
  box-shadow: 0 0 0 3px #f0eeff;
}
```
→
```css
.composer textarea:focus {
  border-color: rgba(255, 255, 255, 0.25);
}
```

`.composer > button`:
```css
.composer > button {
  align-self: flex-end;
  border: none;
  background: linear-gradient(135deg, var(--primary), var(--primary2));
  color: #fff;
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}
```
→
```css
.composer > button {
  align-self: flex-end;
  border: none;
  background: var(--primary);
  color: var(--text-white);
  padding: 10px 16px;
  border-radius: 28px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}
```

`.quick button`:
```css
.quick button {
  border: 1px solid var(--panel-border);
  background: #fbfbfe;
  border-radius: 999px;
  padding: 6px 11px;
  font-size: 10.5px;
  color: #5b6070;
  cursor: pointer;
}
```
→
```css
.quick button {
  border: 1px solid var(--panel-border);
  background: var(--panel);
  border-radius: 999px;
  padding: 6px 11px;
  font-size: 10.5px;
  color: var(--muted);
  cursor: pointer;
}
```

`.quick button:hover`:
```css
.quick button:hover {
  border-color: #cfc9ff;
  color: #5c4ee5;
}
```
→
```css
.quick button:hover {
  border-color: rgba(0, 113, 227, 0.4);
  color: var(--primary);
}
```

- [ ] **Step 2: `.h-item`/`.h-dot`/`.h-state`/`.h-text` 교체**

`.h-item time`:
```css
.h-item time {
  font-size: 10px;
  color: #9aa2b1;
  padding-top: 2px;
  font-variant-numeric: tabular-nums;
}
```
→
```css
.h-item time {
  font-size: 10px;
  color: var(--muted);
  padding-top: 2px;
  font-variant-numeric: tabular-nums;
}
```

`.h-dot`:
```css
.h-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 4px;
  background: #e0a52e;
}
```
→
```css
.h-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 4px;
  background: var(--warning);
}
```

`.h-state`:
```css
.h-state {
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  margin-bottom: 3px;
  color: #b7841f;
}
```
→
```css
.h-state {
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  margin-bottom: 3px;
  color: var(--warning);
}
```

`.h-state.applied`:
```css
.h-state.applied {
  color: #137a52;
}
```
→
```css
.h-state.applied {
  color: var(--success);
}
```

`.h-text`:
```css
.h-text {
  color: #4a5163;
  line-height: 1.5;
  font-size: 11.5px;
}
```
→
```css
.h-text {
  color: var(--text);
  line-height: 1.5;
  font-size: 11.5px;
}
```

(`.h-dot.applied`는 Task 1에서 `var(--live)`→`var(--success)`로 이미 치환됨, 변경 없음)

- [ ] **Step 3: `.locked::after`, `.report-*`, `.empty` 교체**

`.locked::after`:
```css
.locked::after {
  content: "인터뷰 시작 후 사용할 수 있습니다";
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.82);
  display: grid;
  place-items: center;
  text-align: center;
  padding: 16px;
  font-size: 11.5px;
  font-weight: 700;
  color: #8a92a2;
}
```
→
```css
.locked::after {
  content: "인터뷰 시작 후 사용할 수 있습니다";
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.82);
  display: grid;
  place-items: center;
  text-align: center;
  padding: 16px;
  font-size: 11.5px;
  font-weight: 700;
  color: var(--muted);
}
```

`.report-note`:
```css
.report-note {
  margin: 14px 16px;
  padding: 11px 13px;
  border-radius: 11px;
  border: 1px solid #ded8ff;
  background: #f7f5ff;
  font-size: 11.5px;
  color: #4a4468;
  line-height: 1.6;
}
```
→
```css
.report-note {
  margin: 14px 16px;
  padding: 11px 13px;
  border-radius: 20px;
  border: 1px solid rgba(0, 113, 227, 0.2);
  background: rgba(0, 113, 227, 0.08);
  font-size: 11.5px;
  color: var(--text);
  line-height: 1.6;
}
```

`.report-note b`:
```css
.report-note b {
  color: #5c4ee5;
}
```
→
```css
.report-note b {
  color: var(--primary);
}
```

`.report-highlight`:
```css
.report-highlight {
  margin: 0 16px 12px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--panel-border);
  font-size: 12px;
  line-height: 1.55;
}
```
→
```css
.report-highlight {
  margin: 0 16px 12px;
  padding: 10px 12px;
  border-radius: 20px;
  border: 1px solid var(--panel-border);
  font-size: 12px;
  line-height: 1.55;
}
```

`.report-highlight b`:
```css
.report-highlight b {
  display: block;
  color: #3a3363;
  margin-bottom: 4px;
}
```
→
```css
.report-highlight b {
  display: block;
  color: var(--text-white);
  margin-bottom: 4px;
}
```

`.empty`:
```css
.empty {
  padding: 26px 8px;
  text-align: center;
  color: #9aa2b1;
  font-size: 12px;
  line-height: 1.7;
}
```
→
```css
.empty {
  padding: 26px 8px;
  text-align: center;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.7;
}
```

- [ ] **Step 4: 빌드 검증**

Run: `cd frontend/dashboard && npm run build`
Expected: exit code 0

- [ ] **Step 5: 육안 확인**

백룸 우측 컬럼(실시간 지시 입력창, 지시 히스토리)이 검은 텍스트영역 + 파란 전송 버튼으로 보이고, 인터뷰 시작 전 잠긴 패널의 오버레이가 어둡게 보이는지 확인.

- [ ] **Step 6: 커밋**

```bash
git add frontend/dashboard/src/styles.css
git commit -m "style: 대시보드 지시입력/히스토리/리포트 다크 리스킨"
```

---

### Task 6: 세션 생성 폼 + 모달 + 전역 input/button/badge (최종 태스크)

**Files:**
- Modify: `frontend/dashboard/src/styles.css:854-1073` (`.btn-sm` ~ 파일 끝)

**Interfaces:**
- Consumes: Task 1 토큰
- Produces: 없음 — 이 태스크로 파일 전체 리스킨이 완료된다

- [ ] **Step 1: `.btn-sm`, `.modal-bg`, `.modal` 교체**

`.btn-sm`:
```css
.btn-sm {
  border: 1px solid var(--panel-border);
  background: #fff;
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 10.5px;
  cursor: pointer;
  color: #4a5163;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
```
→
```css
.btn-sm {
  border: 1px solid var(--panel-border);
  background: var(--panel);
  border-radius: 28px;
  padding: 6px 10px;
  font-size: 10.5px;
  cursor: pointer;
  color: var(--text);
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
```

`.btn-sm.solid`:
```css
.btn-sm.solid {
  background: linear-gradient(135deg, var(--primary), var(--primary2));
  color: #fff;
  border: none;
}
```
→
```css
.btn-sm.solid {
  background: var(--primary);
  color: var(--text-white);
  border: none;
}
```

`.modal-bg`:
```css
.modal-bg {
  position: fixed;
  inset: 0;
  background: rgba(20, 26, 40, 0.5);
  backdrop-filter: blur(3px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}
```
→
```css
.modal-bg {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}
```

`.modal`:
```css
.modal {
  width: min(560px, 92vw);
  max-height: 82vh;
  overflow: auto;
  background: #fff;
  border-radius: 18px;
  padding: 22px;
}
```
→
```css
.modal {
  width: min(560px, 92vw);
  max-height: 82vh;
  overflow: auto;
  background: var(--panel);
  border-radius: 28px;
  padding: 22px;
}
```

- [ ] **Step 2: `.linkrow`, `.btn-ghost` 교체**

`.linkrow`:
```css
.linkrow {
  display: flex;
  align-items: center;
  gap: 9px;
  border: 1px solid #ded8ff;
  background: #f7f5ff;
  border-radius: 10px;
  padding: 10px 12px;
  margin-bottom: 9px;
  flex-wrap: wrap;
}
```
→
```css
.linkrow {
  display: flex;
  align-items: center;
  gap: 9px;
  border: 1px solid rgba(0, 113, 227, 0.2);
  background: rgba(0, 113, 227, 0.08);
  border-radius: 20px;
  padding: 10px 12px;
  margin-bottom: 9px;
  flex-wrap: wrap;
}
```

`.linkrow .lk-tag`:
```css
.linkrow .lk-tag {
  font-size: 9px;
  font-weight: 800;
  background: #eeeaff;
  color: #5c4ee5;
  padding: 3px 8px;
  border-radius: 5px;
  white-space: nowrap;
}
```
→
```css
.linkrow .lk-tag {
  font-size: 9px;
  font-weight: 800;
  background: rgba(0, 113, 227, 0.15);
  color: var(--primary);
  padding: 3px 8px;
  border-radius: 9999px;
  white-space: nowrap;
}
```

`.linkrow code`:
```css
.linkrow code {
  flex: 1;
  font-size: 11.5px;
  color: #4a4468;
  word-break: break-all;
  min-width: 180px;
}
```
→
```css
.linkrow code {
  flex: 1;
  font-size: 11.5px;
  color: var(--text);
  word-break: break-all;
  min-width: 180px;
}
```

`.btn-ghost`:
```css
.btn-ghost {
  border: 1px solid var(--panel-border);
  background: #fff;
  border-radius: 10px;
  padding: 9px 15px;
  font-size: 12px;
  cursor: pointer;
  font-weight: 600;
  color: #4a5163;
}
```
→
```css
.btn-ghost {
  border: 1px solid var(--panel-border);
  background: var(--panel);
  border-radius: 28px;
  padding: 9px 15px;
  font-size: 12px;
  cursor: pointer;
  font-weight: 600;
  color: var(--text);
}
```

- [ ] **Step 3: 전역 `input`/`select`/`textarea`/`button` 교체**

`input, select, textarea`:
```css
input,
select,
textarea {
  display: block;
  width: 100%;
  margin-top: 6px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--panel-border);
  background: #fff;
  color: var(--text);
  font: inherit;
  font-size: 12.5px;
}
```
→
```css
input,
select,
textarea {
  display: block;
  width: 100%;
  margin-top: 6px;
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid var(--panel-border);
  background: #000000;
  color: var(--text);
  font: inherit;
  font-size: 12.5px;
}
```

`input:focus, select:focus, textarea:focus`:
```css
input:focus,
select:focus,
textarea:focus {
  outline: none;
  border-color: #a99fff;
  box-shadow: 0 0 0 3px #f0eeff;
}
```
→
```css
input:focus,
select:focus,
textarea:focus {
  outline: none;
  border-color: rgba(255, 255, 255, 0.25);
}
```

`button`:
```css
button {
  padding: 10px 18px;
  border-radius: 10px;
  border: none;
  background: linear-gradient(135deg, var(--primary), var(--primary2));
  color: #fff;
  font-family: inherit;
  font-weight: 700;
  font-size: 12.5px;
  cursor: pointer;
}
```
→
```css
button {
  padding: 10px 18px;
  border-radius: 28px;
  border: none;
  background: var(--primary);
  color: var(--text-white);
  font-family: inherit;
  font-weight: 700;
  font-size: 12.5px;
  cursor: pointer;
}
```

`button.ghost`:
```css
button.ghost {
  background: #fff;
  border: 1px solid var(--panel-border);
  color: var(--text);
  font-weight: 600;
}
```
→
```css
button.ghost {
  background: var(--panel);
  border: 1px solid var(--panel-border);
  color: var(--text);
  font-weight: 600;
}
```

- [ ] **Step 4: `.link-row`, `.badge` 계열 교체**

`.link-row`:
```css
.link-row {
  font-size: 11.5px;
  color: #4a4468;
  display: flex;
  align-items: center;
  gap: 9px;
  flex-wrap: wrap;
  border: 1px solid #ded8ff;
  background: #f7f5ff;
  border-radius: 10px;
  padding: 10px 12px;
}
```
→
```css
.link-row {
  font-size: 11.5px;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 9px;
  flex-wrap: wrap;
  border: 1px solid rgba(0, 113, 227, 0.2);
  background: rgba(0, 113, 227, 0.08);
  border-radius: 20px;
  padding: 10px 12px;
}
```

`.badge`:
```css
.badge {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 999px;
  border: 1px solid var(--panel-border);
  color: var(--muted);
  background: #fff;
}
```
→
```css
.badge {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 999px;
  border: 1px solid var(--panel-border);
  color: var(--muted);
  background: var(--panel);
}
```

`.badge.connected`:
```css
.badge.connected {
  color: var(--success);
  border-color: #b9e6cc;
  background: #f3fbf7;
}
```
→
```css
.badge.connected {
  color: var(--success);
  border-color: rgba(16, 185, 129, 0.3);
  background: rgba(16, 185, 129, 0.08);
}
```

`.badge.error, .badge.closed`:
```css
.badge.error,
.badge.closed {
  color: var(--error);
  border-color: #f0c3c5;
  background: #fdeeee;
}
```
→
```css
.badge.error,
.badge.closed {
  color: var(--error);
  border-color: rgba(239, 68, 68, 0.3);
  background: rgba(239, 68, 68, 0.08);
}
```

(`.error { color: var(--error); }`는 Task 1에서 이미 치환 완료, 변경 없음)

- [ ] **Step 5: 빌드 검증**

Run: `cd frontend/dashboard && npm run build`
Expected: exit code 0

- [ ] **Step 6: 전체 통합 육안 확인 (파일 전체 리스킨 완료 시점)**

`http://localhost:5174`에서 처음부터 끝까지 다시 훑는다:
1. 세션 생성 폼 화면 — 입력창/셀렉트/버튼이 모두 검은 배경에 파란 액센트로 통일됐는지
2. "질문 편집" 모달을 열어 모달 배경/카드가 다크로 보이는지
3. 세션 생성 후 발급된 링크 박스(`.linkrow`)가 파란 틴트 카드로 보이는지
4. 백룸(Monitor) 전체 — 탑바/탭바/3단 패널/응답자 스테이지/실시간 대화/지시 입력까지 색감·라운드·폰트가 인터뷰이와 같은 계열로 보이는지
5. 가능하면 인터뷰이(`frontend/interviewee`, 로컬 `npm run dev` 또는 배포된 `orange-sand` URL)와 나란히 띄워 톤이 맞는지 비교

- [ ] **Step 7: 커밋**

```bash
git add frontend/dashboard/src/styles.css
git commit -m "style: 대시보드 세션 생성 폼/모달/전역 요소 다크 리스킨 마무리"
```
