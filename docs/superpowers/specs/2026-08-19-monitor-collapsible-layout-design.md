# 백룸(Monitor) 접이식 레이아웃 재구성

## 배경

지금 백룸 화면(`frontend/dashboard/src/components/Monitor.tsx`)은 3단 고정 그리드(질문 트리 / 응답자 화면+실시간 진행상황 / 실시간 지시+지시 이력)라 응답자 화면이 좁고, 세션 생성 직후에만 잠깐 보여주는 인터뷰이/클라이언트 링크는 백룸에 들어오면 다시 볼 방법이 없다. 순수 CSS 리스킨이 아니라 실제 컴포넌트 구조·상태 변경이 필요하다.

## 목표

- 질문 트리를 파일탐색기(VSCode 탐색기)처럼 접었다 펼 수 있게 해서, 접으면 응답자 화면이 넓어지게 한다
- 백룸에서도 인터뷰이/클라이언트 링크를 다시 열어볼 수 있는 접이식 섹션을 추가한다
- 오른쪽 컬럼을 "실시간 지시(+지시 이력 토글)"와 "실시간 진행 상황"만 남도록 재배치한다
- 타이머/연결 상태 배지를 상단바에서 응답자 화면 패널로 옮긴다

## 범위 (In Scope)

- `frontend/dashboard/src/components/Monitor.tsx` — 레이아웃 재구성, 접기 상태(`useState`) 추가, JSX 재배치
- `frontend/dashboard/src/App.tsx` — topbar에서 타이머/connected 배지 렌더링 제거
- `frontend/dashboard/src/styles.css` — 아코디언/접힘 레일 스타일 신규 추가 (진행 중인 macOS 라이트 스펙과 같은 톤)

## 비목표 (Out of Scope)

- 클라이언트 링크 실제 발급 기능 구현 — 지금처럼 "준비 중" 표시만 유지
- 접기/펼치기 상태의 localStorage 영구 저장 — 새로고침하면 기본값으로 리셋 (이 화면은 PM이 인터뷰 내내 탭을 열어두는 용도라 불필요하다고 판단)
- `frontend/interviewee` 수정
- 색상/타이포 토큰 자체 변경 (이건 별도 진행 중인 macOS 라이트 스펙의 몫)

## 레이아웃 구조

### 좌측 컬럼 — 아코디언 사이드바 (`col-questions` 재활용)

두 개의 접이식 섹션이 세로로 쌓인다:

1. **질문 트리** — 기본 펼침(`treeOpen` 초기값 `true`). 지금의 `<ol className="tree">`, "+질문 편집" 버튼, 타임키퍼 힌트를 그대로 포함.
2. **세션 링크** — 기본 접힘(`linksOpen` 초기값 `false`). 펼치면 인터뷰이 링크(`intervieweeUrl` + 복사 버튼, 지금 응답자 화면 위에 있던 `link-row`를 여기로 이전)와 클라이언트 링크("준비 중" 표시, 신규 기능 없음)가 보인다.

각 섹션 헤더는 클릭 가능한 토글 버튼(`h2` + 화살표 아이콘)이다. **둘 다 접혔을 때**, 좌측 컬럼은 아이콘 두 개만 세로로 남는 56px 폭의 좁은 레일로 줄어든다 (VSCode 탐색기 접었을 때의 액티비티 바와 동일한 패턴) — 각 아이콘을 다시 누르면 해당 섹션이 펼쳐진다.

### 가운데 컬럼 — 응답자 화면 단독

기존 `col-transcript`에서 "실시간 진행 상황" 패널을 오른쪽으로 옮기고, 응답자 화면(`resp-stage`)만 남는다. 컬럼 폭이 넓어진다.

패널 헤더의 "실시간 상태 · {phaseLabel}" 캡션 옆에 타이머(`{timerLabel}`)와 연결 상태 배지(`{status}` → `connected`/`connecting`/`closed`/`error`)를 인라인으로 붙인다. 이 값들은 지금도 Monitor 내부 state(`timerLabel`, `status`)로 이미 계산되어 있으므로 `TopbarStatus`로 끌어올려 App.tsx에 전달할 필요가 없어진다 — 그냥 이 자리에서 직접 렌더링한다.

### 우측 컬럼 — 지시 + 진행상황

1. **실시간 지시** 패널 — 입력창/보내기 버튼/빠른 지시 버튼들은 그대로. 그 아래에 "지시 이력" 토글 버튼(기본 접힘, `historyOpen` 초기값 `false`)을 추가하고, 펼치면 지금의 `<ul className="hist">` 목록이 나온다. 지금처럼 별도 `<section className="panel">`이 아니라 같은 패널 안의 하위 섹션이 된다.
2. **실시간 진행 상황** 패널 — 지금 가운데 컬럼에 있던 것을 그대로 옮겨온다 (원문/원문+번역 토글, `.turns` 스크롤 목록, 리포트 노트/하이라이트 포함).

## 상단바(App.tsx) 변경

`TopbarStatus` 인터페이스(`Monitor.tsx`)에서 `timerLabel`/`phaseLabel`/`connectionStatus` 세 필드를 제거한다 (App.tsx에서 이 값들을 렌더링하는 곳이 이 셋뿐이라 안전하게 지울 수 있음 — 버튼 표시 조건에 쓰이는 `phase`, `role`, `ending`, `hasReport`는 그대로 남긴다). App.tsx의 `<header className="topbar">`에서 이 값을 렌더링하던 `<span className="timer">...</span>`과 `<span className={`badge ${connectionStatus}`}>...</span>` JSX 블록을 통째로 삭제한다. 인터뷰 시작/종료 버튼, PM/클라이언트 모드 전환, 세션 목록으로 버튼은 topbar에 그대로 남는다.

## 상태 관리

`Monitor.tsx`에 로컬 `useState` 3개 추가:

```ts
const [treeOpen, setTreeOpen] = useState(true);
const [linksOpen, setLinksOpen] = useState(false);
const [historyOpen, setHistoryOpen] = useState(false);
```

좌측 컬럼 폭은 `treeOpen || linksOpen` 여부로 결정한다. `.monitor` 엘리먼트에 조건부 클래스(`monitor--sidebar-collapsed`)를 붙여 `grid-template-columns`를 스위칭한다:

- 펼침 상태 (기본): `grid-template-columns: minmax(240px, 0.8fr) minmax(0, 1.7fr) minmax(320px, 1fr);`
- 둘 다 접힘 (`monitor--sidebar-collapsed`): `grid-template-columns: 56px minmax(0, 1.7fr) minmax(320px, 1fr);`

가운데(응답자 화면)·우측(지시+진행상황) 컬럼 폭은 접힘 여부와 무관하게 고정이다 — 좌측이 줄어든 만큼 가운데 컬럼(`1.7fr`)이 넓어지는 건 그리드의 `fr` 단위가 자동으로 흡수하므로 별도 분기가 필요 없다.

## 검증 방법

- `cd frontend/dashboard && npm run build` — exit 0
- 로컬 dev 서버에서 백룸 진입 후:
  - 질문 트리 접기 → 응답자 화면이 넓어지는지, 좌측이 아이콘 레일로 줄어드는지
  - 세션 링크 섹션 펼치기 → 인터뷰이 링크 복사 버튼이 동작하는지 (클립보드)
  - 질문 트리·세션 링크 둘 다 접었을 때 레일이 56px로 줄고, 아이콘 클릭 시 다시 펼쳐지는지
  - 우측에 "실시간 지시"(+ 지시 이력 토글) → "실시간 진행 상황" 순서로 보이는지
  - 응답자 화면 패널 헤더에 타이머/연결 배지가 표시되고, topbar에서는 사라졌는지
  - 세션 상태 미리보기 탭(대기/입장함/진행중/종료)을 눌러 phase가 바뀌어도 레이아웃이 안 깨지는지
