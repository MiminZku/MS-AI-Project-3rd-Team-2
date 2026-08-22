# 대시보드 macOS 라이트 전환 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `frontend/dashboard/src/styles.css`를 다크 마케팅-페이지 톤에서 macOS 시스템 설정 앱 톤(밝은 배경 + 옅은 그림자 + 절제된 라운드)으로 재반전한다.

**Architecture:** 순수 값 교체 3단계. 변수 이름은 그대로 두고 값만 바꾸므로(다크 리스킨 때처럼 변수 rename이 없음) 중간 단계에서 TypeScript/빌드가 깨지는 일은 없다. (1) 루트 토큰 값 스왑 → (2) 그림자/라운드 규칙 적용 → (3) 다크 전용으로 하드코딩됐던 리터럴 값(라이트에서 안 보이거나 대비가 깨지는 곳) 수정.

**Tech Stack:** Vite 6 + React 18(빌드 검증용), 순수 CSS.

## Global Constraints

- 대상 파일은 오직 `frontend/dashboard/src/styles.css`.
- 스펙: `docs/superpowers/specs/2026-08-19-dashboard-macos-light-design.md`. 이 스펙 작성 이후 추가된 요소(케밥 버튼/호버 드로어/format-seg 등)에 스펙과 같은 원칙을 확장 적용하는 부분은 각 태스크에서 "스펙 이후 신규 요소" 라고 표시했다.
- 타이포그래피 크기/여백은 건드리지 않는다 (이미 확정).
- `--primary`(#0071e3), `--text-white`(#ffffff) 값은 변경 없음.
- `.resp-stage`와 그 위에 뜨는 컨트롤(`.rs-badge`, `.rs-strip`, `.rs-figure`, `.audio-seg`)은 의도적으로 다크로 고정 — 비디오 캔버스 관례.
- `.modal-bg`의 검정 반투명 배경은 테마 무관하게 유지 (모달 딤 처리는 라이트/다크 공통 관례).
- 빌드 검증: `cd frontend/dashboard && npm run build` — exit 0.
- 로컬 dev 서버(`http://localhost:5174`)에서 육안 확인. 로컬 백엔드(`127.0.0.1:8000`)가 안 떠 있으면 `cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`으로 재기동.
- 커밋은 태스크 단위로.

---

### Task 1: 루트 토큰을 라이트 값으로 스왑

**Files:**
- Modify: `frontend/dashboard/src/styles.css:1-28` (`:root`)

**Interfaces:**
- Produces: 토큰 이름은 그대로(`--bg`,`--panel`,`--panel-border`,`--text`,`--muted`,`--success`,`--error`,`--warning`), 값만 라이트로 바뀜. 이후 태스크는 이 값을 전제로 진행.

- [ ] **Step 1: `:root` 블록 값 스왑**

```css
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
```
→
```css
:root {
  color-scheme: light;
  --bg: #f5f5f7;
  --panel: #ffffff;
  --panel-border: rgba(0, 0, 0, 0.08);
  --text: #1d1d1f;
  --text-white: #ffffff;
  --muted: #6e6e73;
  --primary: #0071e3;
  --success: #34c759;
  --error: #ff3b30;
  --warning: #ff9500;
  font-family: "Pretendard Variable", Pretendard, "SF Pro Display", -apple-system, "Segoe UI",
    "Malgun Gothic", sans-serif;
  letter-spacing: -0.015em;
}
```

- [ ] **Step 2: 빌드 검증**

Run: `cd frontend/dashboard && npm run build`
Expected: exit code 0

- [ ] **Step 3: 육안 확인 (이 시점엔 그림자/라운드/일부 리터럴이 아직 안 맞아 어색해 보일 수 있음 — 정상)**

`http://localhost:5174` 접속 시 배경이 밝은 회백색으로 바뀌고 기본 텍스트가 짙은 회색으로 보이면 정상.

- [ ] **Step 4: 커밋**

```bash
git add frontend/dashboard/src/styles.css
git commit -m "style: 대시보드 루트 토큰을 macOS 라이트 값으로 전환"
```

---

### Task 2: 그림자 부활 + 라운드 축소

**Files:**
- Modify: `frontend/dashboard/src/styles.css` (`.panel`, `.modal`, 서브 블록, 버튼류, 세그먼트 컨테이너, 인풋류)

**Interfaces:**
- Consumes: Task 1의 라이트 토큰 값
- Produces: 없음

- [ ] **Step 1: `.panel` 그림자 부활 + 라운드 축소**

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
→
```css
.panel {
  background: var(--panel);
  border: 1px solid var(--panel-border);
  border-radius: 14px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06), 0 1px 6px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
```

- [ ] **Step 2: `.modal` 라운드 축소**

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
→
```css
.modal {
  width: min(560px, 92vw);
  max-height: 82vh;
  overflow: auto;
  background: var(--panel);
  border-radius: 14px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06), 0 1px 6px rgba(0, 0, 0, 0.04);
  padding: 22px;
}
```

- [ ] **Step 3: 서브 블록 라운드 20px → 14px (5곳)**

`.rationale`(원래 10px — 스펙 대상 아님, 스킵), `.linkrow`, `.report-note`, `.report-highlight`, `.link-row`을 각각 찾아 `border-radius: 20px;`를 `border-radius: 14px;`로 교체한다. 각 규칙의 나머지 속성은 그대로 둔다:

```css
.linkrow {
  ...
  border-radius: 20px;
  ...
}
```
→ `border-radius: 14px;`로만 교체 (나머지 동일), 아래 3곳도 동일하게:
```css
.report-note {
  ...
  border-radius: 20px;
  ...
}
.report-highlight {
  ...
  border-radius: 20px;
  ...
}
.link-row {
  ...
  border-radius: 20px;
  ...
}
```

- [ ] **Step 4: 버튼류 라운드 28px(캡슐) → 8px (5곳)**

전역 `button`, `.sess-btn`, `.composer > button`, `.btn-sm`, `.btn-ghost` 각각에서 `border-radius: 28px;`를 `border-radius: 8px;`로 교체 (다른 속성은 그대로):

```css
button {
  padding: 14px 24px;
  border-radius: 28px;
  ...
}
```
→ `border-radius: 8px;`로 교체. `.sess-btn`, `.composer > button`, `.btn-sm`, `.btn-ghost`도 각각 동일하게 `border-radius: 28px` → `8px`.

- [ ] **Step 5: 세그먼트 컨테이너 라운드 9999px → 8px (3곳, `.format-seg`는 스펙 작성 후 추가된 신규 요소에 같은 원칙 확장 적용)**

```css
.role-switch {
  display: flex;
  border: 1px solid var(--panel-border);
  border-radius: 9999px;
  overflow: hidden;
}
```
→ `border-radius: 8px;`

```css
.swg {
  display: flex;
  border: 1px solid var(--panel-border);
  border-radius: 9999px;
  overflow: hidden;
}
```
→ `border-radius: 8px;`

`.format-seg button`(스펙 작성 후 추가된 파일형식 선택 세그먼트)도 같은 원칙으로:
```css
.format-seg button {
  padding: 8px 16px;
  border-radius: 999px;
  ...
}
```
→ `border-radius: 8px;`

- [ ] **Step 6: 인풋류 라운드 축소 (전역 input/select/textarea 14px→8px, `.composer textarea` 20px→10px)**

```css
input,
select,
textarea {
  display: block;
  width: 100%;
  margin-top: 6px;
  padding: 10px 12px;
  border-radius: 14px;
  ...
}
```
→ `border-radius: 8px;`

```css
.composer textarea {
  width: 100%;
  min-height: 88px;
  resize: vertical;
  border: 1px solid var(--panel-border);
  border-radius: 20px;
  ...
}
```
→ `border-radius: 10px;`

- [ ] **Step 7: 빌드 검증**

Run: `cd frontend/dashboard && npm run build`
Expected: exit code 0

- [ ] **Step 8: 육안 확인**

카드/패널에 옅은 그림자가 보이는지, 버튼/세그먼트가 캡슐이 아니라 절제된 각진 라운드로 보이는지 확인 (badge/role-chip/lk-tag 등 태그류는 여전히 완전 필 모양이어야 함 — 이번 스텝에서 안 건드림).

- [ ] **Step 9: 커밋**

```bash
git add frontend/dashboard/src/styles.css
git commit -m "style: 대시보드 그림자 부활 + 카드/버튼/세그먼트 라운드 축소 (macOS 톤)"
```

---

### Task 3: 다크 전용 리터럴 값 수정

**Files:**
- Modify: `frontend/dashboard/src/styles.css`

**Interfaces:**
- Consumes: Task 1의 라이트 토큰
- Produces: 없음 (마지막 태스크 — 완료되면 라이트 전환 끝)

- [ ] **Step 1: `.resp-stage`를 고정 다크로 분리**

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
→
```css
.resp-stage {
  position: relative;
  aspect-ratio: 16 / 9;
  border-radius: 20px;
  overflow: hidden;
  background: #1d1d1f;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 14px 16px 16px;
  text-align: center;
  color: #86868b;
  font-size: 12.5px;
  line-height: 1.7;
}
```

(`.resp-stage b`는 `color: var(--text-white)`을 그대로 유지 — 고정 다크 배경 위 흰 글자라 계속 맞음, 수정 없음)

- [ ] **Step 2: `.report-highlight b` 수정**

```css
.report-highlight b {
  display: block;
  color: var(--text-white);
  margin-bottom: 4px;
}
```
→
```css
.report-highlight b {
  display: block;
  color: var(--text);
  margin-bottom: 4px;
}
```

- [ ] **Step 3: `.hover-drawer-label` 수정 (스펙 작성 후 추가된 신규 요소 — 같은 문제)**

```css
.hover-drawer-label {
  padding: 12px 24px 0;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-white);
}
```
→
```css
.hover-drawer-label {
  padding: 12px 24px 0;
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
}
```

- [ ] **Step 4: `.q-num`, `.turn.assistant strong` 글자색 수정 (밝은 하늘색 #5ac8fa → var(--primary))**

```css
.q-num {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  border-radius: 6px;
  background: rgba(0, 113, 227, 0.15);
  color: #5ac8fa;
  ...
}
```
→ `color: var(--primary);`

```css
.turn.assistant strong {
  background: rgba(0, 113, 227, 0.15);
  color: #5ac8fa;
}
```
→ `color: var(--primary);`

- [ ] **Step 5: 인풋 배경 `#000000` → `var(--bg)` (전역 input/select/textarea, `.composer textarea`)**

```css
input,
select,
textarea {
  ...
  background: #000000;
  color: var(--text);
  ...
}
```
→ `background: var(--bg);`

```css
.composer textarea {
  ...
  background: #000000;
  color: var(--text-white);
}
```
→ `background: var(--bg);` (color는 `var(--text-white)`가 아니라 `var(--text)`로도 바꿔야 흰 배경 근처 톤에서 자연스럽다 — 아래처럼 같이 수정):

```css
.composer textarea {
  width: 100%;
  min-height: 88px;
  resize: vertical;
  border: 1px solid var(--panel-border);
  border-radius: 10px;
  padding: 12px;
  outline: none;
  font-size: 12.5px;
  line-height: 1.55;
  font-family: inherit;
  background: var(--bg);
  color: var(--text);
}
```

- [ ] **Step 6: 포커스 링 수정 (전역 input/select/textarea, `.composer textarea`)**

```css
input:focus,
select:focus,
textarea:focus {
  outline: none;
  border-color: rgba(255, 255, 255, 0.25);
}
```
→
```css
input:focus,
select:focus,
textarea:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.25);
}
```

```css
.composer textarea:focus {
  border-color: rgba(255, 255, 255, 0.25);
}
```
→
```css
.composer textarea:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.25);
}
```

- [ ] **Step 7: `.locked::after` 오버레이를 밝은 스크림으로**

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
→ `background: rgba(255, 255, 255, 0.85);`로 교체 (나머지 동일)

- [ ] **Step 8: `.cond` 배경 수정**

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
→ `background: rgba(0, 0, 0, 0.06);`

- [ ] **Step 9: 빌드 검증**

Run: `cd frontend/dashboard && npm run build`
Expected: exit code 0

- [ ] **Step 10: 전체 통합 육안 확인**

`http://localhost:5174`에서 세션 생성 → 백룸까지 전체 훑기:
- 세션 생성 폼: 인풋이 흰 카드 안에서 옅은 회색 오목한 필드로 보이는지, 포커스 시 파란 링이 보이는지
- 백룸: 전체적으로 밝은 배경 + 흰 카드 + 옅은 그림자 (macOS 설정 앱 느낌)
- `.resp-stage`만 의도적으로 다크로 남아있는지, 그 위 텍스트/배지/음성 토글이 잘 보이는지
- 질문 트리 `q-num`, 어시스턴트 대화 뱃지 글자가 흰 배경에서 또렷하게 읽히는지
- 케밥(⋮) 호버 드로어 열어서 "질문 트리"/"세션 링크" 라벨 글자가 흰 드로어 배경에서 잘 보이는지
- 인터뷰 시작 전 "지시 이력"/"실시간 지시" 잠긴 패널 오버레이가 밝은 반투명으로 보이는지
- 질문 편집 모달 열어서 파일 형식 세그먼트/파일 선택창이 라이트 톤으로 잘 보이는지

- [ ] **Step 11: 커밋**

```bash
git add frontend/dashboard/src/styles.css
git commit -m "style: 다크 전용 리터럴 값을 macOS 라이트에 맞게 수정 (resp-stage 고정 다크 포함)"
```
