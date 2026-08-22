# 백룸 독 업그레이드 설계

## 배경

백룸(Monitor.tsx)에 "줌미팅 + 카카오톡 + 애플 생태계" 느낌을 더한다. 4가지 변경을 묶는다:

1. 케밥(⋮) 호버 드로어 → Mac 독 스타일 아이콘 3개(클릭식)
2. STT 자막이 응답자 영상 위를 덮는 문제 → 영상 아래 고정 자막 바로 이동
3. 상단 PM/Observer 칩·스위치 제거, 클라이언트 모드에서도 실시간 진행상황 노출
4. 실시간 진행상황을 카카오톡식 좌/우 말풍선으로

## 1. 독 아이콘

**현재**: `.kebab-wrap`에 `⋮` 버튼 하나, hover/focus/pinned 시 `.hover-drawer` 전체(질문트리+세션링크 두 섹션)가 슬라이드 인.

**변경**: 아이콘 3개(`Q`/`L`/`A` 모노그램, 36px 원형 버튼)를 가로로 나열. 클릭으로만 열림(호버 제거), 한 번에 하나만 열림, 바깥 클릭 시 닫힘.

- **Q (질문트리)**: 클릭 → 슬라이드 패널에 질문트리 + "질문 등록 및 편집" 버튼만 (기존 첫 번째 섹션 내용 그대로 이동)
- **L (세션 링크)**: 클릭 → 슬라이드 패널에 세션 링크만 (기존 두 번째 섹션 내용 그대로 이동)
- **A (분석)**: 분석 앱(팀원 A 담당) URL이 아직 없어 **disabled 스텁**. 기존 "+10분"/"리포트 열기" 버튼과 같은 패턴 — `title="분석 앱 연동 전 · URL 확정 후 연결"`

상태: `drawerPinned: boolean` + `historyOpen`(별개, 유지) → `activePanel: "tree" | "link" | null` 로 교체. 슬라이드 애니메이션(`position:fixed`, `translateX`, `opacity`)은 그대로 재사용하되 트리거를 `:hover`/`:focus-within`에서 React 상태 기반 `.dock-panel.open` 클래스로 교체.

`body:has(.kebab-wrap.pinned) .monitor` 밀어주기 규칙도 `.dock-panel.open` 기준으로 교체.

## 2. 자막 위치

**현재**: `liveTextKo`/`liveTextEn`이 `.rs-figure`(영상 컨테이너) 내부에 `position:absolute; bottom:16px`로 떠서 얼굴을 가림.

**변경**: 오버레이 제거. `.resp-stage` 아래에 항상 자리를 차지하는 자막 바(`.caption-bar`, min-height 고정, 텍스트 없어도 공간 유지)를 새로 추가. 원문(ko)은 위 줄, 통역(en)은 아래 줄(강조색), 기존과 동일한 두 줄 표시 유지.

## 3. PM/Observer 칩 제거 + 클라이언트 노출

**App.tsx**: `.role-switch`(PM 모드/클라이언트 모드 버튼)와 `.role-chip`(현재 역할 표시) JSX 삭제. 역할 전환 수단이 없어지므로, `role` 초기값을 URL 쿼리(`?role=client`)에서 읽도록 변경(기존 `session` 쿼리 파싱과 동일한 패턴) — 화면엔 안 보이지만 개발 중 테스트는 가능.

**Monitor.tsx**: 현재 `{role === "pm" && <div className="col-instructions">...실시간지시...실시간진행상황...</div>}` 로 오른쪽 컬럼 전체가 PM 전용. `col-instructions`는 양쪽 역할에 렌더링하되, 그 안의 "실시간 지시" `<section>`만 `role === "pm"` 로 감싼다. "실시간 진행 상황" `<section>`은 무조건 렌더링. 응답자 화면(`col-transcript`)은 이미 역할 구분 없이 보이므로 변경 없음.

## 4. 카카오톡 말풍선

**현재**: `.turn` (assistant/interviewee 공통) 이 풀와이드 블록, 위아래로 쌓이고 좌우 구분 없음.

**변경**: `.turn.assistant`는 왼쪽 정렬(최대폭 75%, 왼쪽에 붙음), `.turn.interviewee`는 오른쪽 정렬(최대폭 75%, 오른쪽에 붙음). 배경색은 기존 강조색 재사용 — assistant는 회색조 배경, interviewee는 primary 톤 배경 말풍선. `turn-head`(라벨+시간)도 같은 정렬 방향을 따름. `rationale`(AI 판단 근거)은 assistant 말풍선 내부에 그대로 유지.

## 파일 범위

프론트엔드만 — `Monitor.tsx`, `App.tsx`, `styles.css`. 백엔드 변경 없음(A 아이콘은 스텁, role 전환은 프론트 로컬 상태).

## 테스트

브라우저 육안 확인 위주(레이아웃/애니메이션 변경이 대부분). 빌드(`npm run build`)로 타입 에러만 방지.
