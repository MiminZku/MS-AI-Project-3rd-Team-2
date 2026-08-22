# 대시보드 타이포그래피 위계 강화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `frontend/dashboard/src/styles.css`에서 "헤드라인급" 요소(패널 타이틀, 타이머 숫자, 현재 질문, 주요 CTA 버튼)와 패널 여백을 키워서 인터뷰이/레퍼런스의 타이포그래피 존재감을 대시보드에도 반영한다.

**Architecture:** 순수 값 교체(font-size/padding/gap)만 하는 단일 CSS 패스. 색상/반경/그림자는 이전 다크 리스킨에서 이미 완료됐으므로 이번엔 건드리지 않는다. 변수명 변경이나 규칙 삭제가 없어 편집 순서에 의존성이 없고, 중간에 화면이 깨지는 단계도 없다.

**Tech Stack:** Vite 6 + React 18(빌드 검증용), 순수 CSS.

## Global Constraints

- 대상 파일은 오직 `frontend/dashboard/src/styles.css`.
- 스펙: `docs/superpowers/specs/2026-08-19-dashboard-typography-hierarchy-design.md` — 모든 값은 이 문서의 표와 일치해야 한다.
- 색상/`border-radius`/`box-shadow`는 이번 작업 범위 밖 — 건드리지 않는다.
- 질문 트리의 `.tree li`(현재 질문 제외)·`.turn p`·`.h-text`·뱃지류 font-size는 변경하지 않는다(밀도 유지).
- 빌드 검증: `cd frontend/dashboard && npm run build` — exit 0이어야 한다.
- 로컬 dev 서버(`http://localhost:5174`)가 이미 떠 있으면 저장 시 HMR로 자동 반영된다.

---

### Task 1: 헤드라인급 요소 + 패널 여백 값 교체 (단일 커밋)

10개 규칙이 서로 의존하지 않는 독립적인 값 교체이고, 전체를 한 화면(백룸)에서 한 번에 육안 검토하는 게 자연스러워 하나의 태스크로 묶는다.

**Files:**
- Modify: `frontend/dashboard/src/styles.css` (아래 10개 지점)

**Interfaces:**
- Consumes: 없음 (기존 `var(--*)` 토큰 값은 그대로 사용, 새 토큰 추가 없음)
- Produces: 없음 (leaf 값 교체)

- [ ] **Step 1: `.p-head h2` 폰트 크기**

```css
.p-head h2 {
  font-size: 13px;
}
```
→
```css
.p-head h2 {
  font-size: 17px;
}
```

- [ ] **Step 2: `.timer b` 폰트 크기**

```css
.timer b {
  font-size: 14px;
  font-variant-numeric: tabular-nums;
  color: var(--success);
  letter-spacing: 0.5px;
}
```
→
```css
.timer b {
  font-size: 20px;
  font-variant-numeric: tabular-nums;
  color: var(--success);
  letter-spacing: 0.5px;
}
```

- [ ] **Step 3: `.tree li.current` 폰트 크기 추가**

```css
.tree li.current {
  background: rgba(0, 113, 227, 0.15);
  border: 1px solid rgba(0, 113, 227, 0.4);
  font-weight: 600;
}
```
→
```css
.tree li.current {
  background: rgba(0, 113, 227, 0.15);
  border: 1px solid rgba(0, 113, 227, 0.4);
  font-weight: 600;
  font-size: 15px;
}
```

- [ ] **Step 4: 전역 `button` padding/font-size**

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
→
```css
button {
  padding: 14px 24px;
  border-radius: 28px;
  border: none;
  background: var(--primary);
  color: var(--text-white);
  font-family: inherit;
  font-weight: 700;
  font-size: 15px;
  cursor: pointer;
}
```

- [ ] **Step 5: `.sess-btn` padding/font-size**

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
→
```css
.sess-btn {
  border: none;
  border-radius: 28px;
  padding: 14px 24px;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
}
```

- [ ] **Step 6: `.composer > button` padding/font-size**

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
→
```css
.composer > button {
  align-self: flex-end;
  border: none;
  background: var(--primary);
  color: var(--text-white);
  padding: 14px 24px;
  border-radius: 28px;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
}
```

- [ ] **Step 7: `.monitor` gap/padding (1.5배)**

```css
.monitor {
  display: grid;
  grid-template-columns: minmax(280px, 0.9fr) minmax(0, 1.5fr) minmax(340px, 0.95fr);
  gap: 16px;
  padding: 16px 20px 40px;
  align-items: start;
}
```
→
```css
.monitor {
  display: grid;
  grid-template-columns: minmax(280px, 0.9fr) minmax(0, 1.5fr) minmax(340px, 0.95fr);
  gap: 24px;
  padding: 24px 30px 60px;
  align-items: start;
}
```

- [ ] **Step 8: `.panel-head, .p-head` padding (1.5배)**

```css
.panel-head,
.p-head {
  padding: 13px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--panel-border);
  gap: 10px;
}
```
→
```css
.panel-head,
.p-head {
  padding: 20px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--panel-border);
  gap: 10px;
}
```

- [ ] **Step 9: `.p-body`, `.tree` padding (1.5배)**

```css
.p-body {
  padding: 14px 16px;
}
```
→
```css
.p-body {
  padding: 21px 24px;
}
```

```css
.tree {
  list-style: none;
  margin: 0;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
}
```
→
```css
.tree {
  list-style: none;
  margin: 0;
  padding: 21px 24px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
}
```

- [ ] **Step 10: `.turns` padding (1.5배)**

```css
.turns {
  display: flex;
  flex-direction: column;
  padding: 4px 16px 16px;
  gap: 0;
  max-height: 70vh;
  overflow-y: auto;
}
```
→
```css
.turns {
  display: flex;
  flex-direction: column;
  padding: 6px 24px 24px;
  gap: 0;
  max-height: 70vh;
  overflow-y: auto;
}
```

- [ ] **Step 11: 빌드 검증**

Run: `cd frontend/dashboard && npm run build`
Expected: exit code 0

- [ ] **Step 12: 육안 확인**

`http://localhost:5174`에서 세션 생성 후 백룸(Monitor) 진입:
- 패널 타이틀("질문 트리", "응답자 화면", "실시간 지시")이 눈에 띄게 커졌는지
- 상단 타이머 숫자가 커졌는지
- 질문 트리에서 현재 질문(1번, 파란 배경)만 다른 항목보다 크게 보이는지 — 나머지 항목(2, 3번)과 하위 분기(branch)는 크기 변화 없어야 함
- "세션 생성", "지시 보내기" 버튼이 더 크고 여유 있게 보이는지
- 60px 고정 탑바 안에서 `.sess-btn`이 커져도 잘리거나 깨지지 않는지
- 패널들 사이 간격과 패널 내부 여백이 전체적으로 더 넓어졌는지

- [ ] **Step 13: 커밋**

```bash
git add frontend/dashboard/src/styles.css
git commit -m "style: 대시보드 타이포그래피 위계/여백 강화 (패널 타이틀·타이머·현재 질문·CTA 확대)"
```
