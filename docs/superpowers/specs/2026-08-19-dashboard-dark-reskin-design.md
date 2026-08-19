# 대시보드 다크 리스킨 — 인터뷰이 디자인 통일

## 배경

`frontend/interviewee`는 이미 Apple 스타일 다크 미니멀 시스템(레퍼런스: `styles.refero.design/style/764b6a64-c233-4e0f-b8e1-bc01e2f8aa16`)을 구현해뒀다. `frontend/dashboard`는 완전히 다른 라이트 테마(보라 그라디언트, Pretendard 단독, 그림자 있는 카드)로 되어 있어 같은 제품군처럼 보이지 않는다.

이 스펙은 대시보드의 시각 언어를 인터뷰이와 통일시키는 리스킨 작업 범위를 정의한다.

## 목표

- 대시보드가 인터뷰이와 "같은 제품군"으로 보이도록 색상/폰트/반경/그림자 규칙을 통일
- 대시보드 고유의 3단 정보 밀집 레이아웃(질문 트리 / 실시간 대화 / 지시 입력)과 기능은 그대로 유지
- 순수 CSS 리스킨 — 컴포넌트 구조·기능 변경 없음

## 범위 (In Scope)

- `frontend/dashboard/src/styles.css` 전체 재작성 (약 1073줄, `:root` 토큰 포함)
- 색상 토큰 교체, 폰트 스택 조정, 반경(radius) 스케일 조정, 카드 그림자 제거
- `App.tsx`, `Monitor.tsx`, `SessionForm.tsx`, `VideoSubscriber.tsx`가 참조하는 기존 클래스명은 유지 (CSS 값만 교체, JSX/클래스명 변경 없음)

## 비목표 (Out of Scope)

- 공유 디자인 토큰 파일/모노레포 워크스페이스 구축 — 두 프론트는 별도 Static Web Apps로 독립 배포되고 루트에 workspace 설정이 없어, 지금 범위에서는 각 앱 스타일시트를 독립적으로 유지한다 (B안 "공유 토큰 파일" 기각, A안 "각자 파일 직접 재작성" 채택)
- 레이아웃 구조 변경 (컬럼 수, 배치, 반응형 breakpoint 로직)
- `frontend/interviewee` 쪽 코드/스타일 수정 — 이미 완성된 상태이며 손대지 않는다
- 컴포넌트 신규 추가/삭제, 기능 변경, 데이터 흐름 변경
- WCAG 색상 대비 재감사 — 인터뷰이가 이미 검증한 토큰 값(`--text`, `--muted` 등)을 그대로 재사용하는 선에서만 커버하고 별도 감사는 하지 않는다

## 디자인 토큰 매핑

| 토큰 | 현재 (라이트) | 변경 (다크, 인터뷰이 값 그대로 재사용) |
|---|---|---|
| `--bg` | `#eef1f6` | `#000000` |
| `--panel` | `#fff` | `#1d1d1f` |
| `--line` → `--panel-border` | `#e2e7ef` | `rgba(255,255,255,0.08)` |
| `--text` | `#1a2233` | `#f5f5f7` |
| `--muted` | `#545b6b` | `#86868b` |
| `--primary` / `--primary2` (보라 그라디언트) | `#5b4de9` / `#8172fb` | 단일 `#0071e3` — 그라디언트 변수 폐기, 액센트는 항상 단색 |
| `--live` / `--ok` → `--success` | `#16a36a` | `#10b981` |
| `--danger` → `--error` | `#db4b50` | `#ef4444` |
| `--warn` → `--warning` | `#d98c16` | `#f59e0b` |
| `--shadow` | `0 10px 30px rgba(29,38,60,0.06)` | 변수 삭제 — 카드류에 그림자 금지 |
| `font-family` | `"Pretendard Variable", Pretendard, system-ui, ...` | `"Pretendard Variable", Pretendard, "SF Pro Display", -apple-system, "Segoe UI", "Malgun Gothic", sans-serif` (한글은 Pretendard 유지, 영문/숫자만 자연스럽게 SF Pro 계열로) |
| `letter-spacing` (전역) | 미지정 | `-0.015em` (인터뷰이와 동일) |
| `color-scheme` | `light` | `dark` |

## 반경(radius) 스케일 매핑

인터뷰이가 실제로 쓰는 반경 어휘(28px 카드/버튼, 20px 서브블록, 16px 상태필, 9999px 뱃지/필)를 대시보드 기존 요소 크기에 대응시킨다.

| 대시보드 요소 | 현재 | 변경 |
|---|---|---|
| `.panel` (3단 카드), `.modal` | 16-18px | 28px |
| `.linkrow`, `.rationale`, `.report-note`, `.report-highlight` 등 서브 블록 | 8-11px | 20px |
| `input`, `select`, `textarea` (일반) | 10px | 14px |
| `.composer textarea` (지시 입력창, 인터뷰이 텍스트 입력창과 대응) | 11px | 20px |
| `.badge`, `.role-chip`, `.timer`, `.lk-tag`, `.cond` (단독 뱃지/필류) | 6-999px 혼재 | 9999px 완전 필로 통일 |
| `.role-switch`, `.tabbar .swg` (세그먼트 토글 그룹) | 컨테이너 8px, 내부 버튼 각지게 이어붙임 | **컨테이너만** 9999px로 통일, 내부 개별 버튼은 반경 0 유지(붙어있는 세그먼트 모양 보존) — 인터뷰이의 `.toggle-switch-btn`(단독 토글, 28px)과는 다른 패턴이므로 그대로 세그먼트형 유지 |
| `.sess-btn`, `.btn-sm`, form 제출 버튼, `.btn-ghost` 등 버튼류 | 8-10px | 28px (작은 버튼은 시각적으로 캡슐 형태가 됨) |
| `.q-num`, `.crumb .glyph` 등 작은 정사각 아이콘 | 6-8px | 그대로 유지 — 인터뷰이에 직접 대응 요소가 없고, 밀집된 트리에서 과도한 라운드는 오히려 가독성을 해침 |

## 컴포넌트별 세부 규칙

- **상태 색상(success/error/warning)**: 색상 자체는 토큰 교체만 하고 그린/레드/오렌지의 의미 매핑은 유지
- **라이브 점 펄스** (`.timer .dot`, `.rs-badge .rs-dot`): 인터뷰이 `.live-dot` 패턴을 따라 `box-shadow: 0 0 12px var(--success)` 글로우 추가 (카드 그림자 금지 원칙과 별개로, 상태 표시용 글로우는 인터뷰이에서도 허용되는 예외)
- **`.resp-stage`** (응답자 영상 플레이스홀더): 현재 `linear-gradient(150deg, #22303f, #141c27)` → `var(--panel)` 단색 배경으로 교체, 그라디언트 제거 (순검정/무그라디언트 원칙)
- **폼(`SessionForm`) 관련 스타일**: 2단 그리드 등 레이아웃 구조는 유지하고 색상/반경만 교체
- **`focus` 상태** (`input:focus`, `textarea:focus` 등 현재 `box-shadow: 0 0 0 3px #f0eeff`): 보라 포커스 링 제거, 인터뷰이의 무섀도우 원칙에 맞춰 `border-color` 변화만으로 포커스 표시 (예: `border-color: rgba(255,255,255,0.25)`)

## 검증 방법

- `npm run dev` (또는 기존에 띄워둔 로컬 vite :5174)로 대시보드 실행 후 브라우저로 확인
  - 세션 생성 폼, 백룸(Monitor) 3단 레이아웃, 질문 트리, 실시간 대화, 지시 입력, 배지/상태 표시가 모두 다크 배경에서 읽기 가능한지 육안 확인
  - 인터뷰이(`frontend/interviewee`, 로컬 또는 배포된 `orange-sand` URL)와 나란히 띄워 색감/폰트/라운드가 "같은 제품군"으로 보이는지 비교
- 타입체크: `npm run build` (`tsc --noEmit && vite build`)로 빌드 에러 없는지 확인 — CSS만 바꾸는 작업이라 TS 에러는 발생하지 않아야 정상
