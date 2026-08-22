# 대시보드 macOS 시스템 설정 스타일 전환 — 다크 리스킨 재보정

## 배경

`2026-08-19-dashboard-dark-reskin-design.md`에서 대시보드를 인터뷰이와 똑같은 "애플 마케팅 페이지"식 순검정 다크 테마로 만들었지만, 사용자 피드백은 "애플 = 무조건 검정은 아니다, macOS 시스템 설정 앱 같은 라이트 톤의 애플 느낌을 원한다"였다. 마케팅 페이지 레퍼런스(`styles.refero.design`)는 극장식 순검정 + 제로 섀도우 + 극단적 라운드가 원칙이었지만, macOS 시스템 설정/App Store Connect 같은 애플 "도구" UI는 밝은 배경 + 옅은 그림자 + 절제된 라운드가 특징이다.

이 스펙은 색상/그림자/라운드 방향을 라이트로 재반전한다. **타이포그래피 위계(`2026-08-19-dashboard-typography-hierarchy-design.md`에서 정한 패널 타이틀 17px, 타이머 20px, 현재 질문 15px, CTA 15px/24px, 여백 1.5배)는 그대로 유지** — 그 부분엔 이견이 없었다.

인터뷰이 프론트(`frontend/interviewee`)는 그대로 다크 유지 — 이번 변경 대상 아님. 대신 `--primary: #0071e3` 액센트와 폰트(Pretendard+SF Pro 혼합)를 공유해서 "같은 앱 패밀리, 다른 화면 성격(라이브 인터뷰 vs 모니터링 도구)"으로 묶는다.

## 목표

- 대시보드를 macOS 시스템 설정 앱처럼 밝고 절제된 애플 톤으로 재조정
- 응답자 비디오 영역(`.resp-stage`)만 화상통화 UI 관례대로 의도적으로 다크 유지 (Zoom/Meet처럼 라이트 앱 안에서도 비디오 캔버스는 어둡게)
- 라이트 전환 과정에서 다크 전용으로 골랐던 리터럴 색상(밝은 텍스트, 검정 배경, 흰색 포커스링 등)이 라이트에서 안 보이거나 대비가 깨지는 곳을 전부 찾아 고침

## 범위 (In Scope)

`frontend/dashboard/src/styles.css` 전체를 다시 훑되, 아래 카테고리만 수정한다:

1. `:root` 토큰 재정의 (라이트)
2. `.panel` 그림자 부활 + 카드/버튼/세그먼트 라운드 축소
3. 다크 전용으로 골랐던 값이 라이트에서 깨지는 지점 수정 (아래 "라이트 전환 시 깨지는 지점" 표)
4. `.resp-stage`를 토큰(`var(--panel)`)에서 분리해 고정 다크 컬러로 전환

## 비목표 (Out of Scope)

- 타이포그래피 크기/여백 (지난 스펙에서 이미 확정, 재변경 없음)
- 사이드바 내비게이션 도입, 레이아웃 구조 변경 — 대화에서 명시적으로 기각됨
- `frontend/interviewee` 수정
- 뱃지/태그류 라운드(9999px 필) — 애플도 이 형태 쓰므로 유지

## 토큰 매핑

| 토큰 | 현재 (다크) | 변경 (macOS 라이트) |
|---|---|---|
| `color-scheme` | `dark` | `light` |
| `--bg` | `#000000` | `#f5f5f7` |
| `--panel` | `#1d1d1f` | `#ffffff` |
| `--panel-border` | `rgba(255, 255, 255, 0.08)` | `rgba(0, 0, 0, 0.08)` |
| `--text` | `#f5f5f7` | `#1d1d1f` |
| `--text-white` | `#ffffff` | `#ffffff` (그대로 — "블루 버튼 위 흰 글자"용으로 계속 필요) |
| `--muted` | `#86868b` | `#6e6e73` |
| `--primary` | `#0071e3` | `#0071e3` (변경 없음 — 인터뷰이와 공유하는 유일한 연결고리) |
| `--success` | `#10b981` | `#34c759` (Apple System Green) |
| `--error` | `#ef4444` | `#ff3b30` (Apple System Red) |
| `--warning` | `#f59e0b` | `#ff9500` (Apple System Orange) |

## 그림자/라운드

| 대상 | 현재 | 변경 |
|---|---|---|
| `.panel`, `.modal` 그림자 | 없음 | `box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06), 0 1px 6px rgba(0, 0, 0, 0.04);` 추가 |
| `.panel`, `.modal` 라운드 | 28px | 14px |
| `.linkrow`/`.rationale`/`.report-note`/`.report-highlight`/`.link-row` 등 서브 블록 라운드 | 20px | 14px |
| 전역 `button`, `.sess-btn`, `.composer > button`, `.btn-sm`, `.btn-ghost` 라운드 | 28px(캡슐) | 8px |
| `.role-switch`, `.swg` (세그먼트 컨테이너) 라운드 | 9999px | 8px |
| `input`/`select`/`textarea` 라운드 | 14px | 8px |
| `.composer textarea` 라운드 | 20px | 10px |
| 뱃지/태그(`.badge`, `.role-chip`, `.lk-tag`, `.timer` 등) | 9999px | 9999px 유지 |

## 라이트 전환 시 깨지는 지점 (다크 전용 리터럴 값 수정)

다크 리스킨 때 "다크 배경 위에서만" 성립하던 리터럴 색상들이 있다. 토큰 재정의만으로는 안 고쳐지므로 개별 수정이 필요하다.

| 위치 | 문제 | 수정 |
|---|---|---|
| `.resp-stage` | `background: var(--panel)`로 바뀌면 흰색이 됨 — 비디오 캔버스가 흰 배경이면 어색 (Zoom/Meet 등도 라이트 앱 안에서 비디오 영역은 항상 어둡게 유지하는 관례) | `var(--panel)` 대신 고정값 `background: #1d1d1f;` — 토큰과 분리해 항상 다크 유지 |
| `.resp-stage` 텍스트색 | `color: var(--muted)`가 라이트 값(`#6e6e73`)이 되면 다크 배경 위에서 대비 부족 | 고정값 `color: #86868b;` (다크 전용 muted, 토큰과 분리) |
| `.resp-stage b` | `color: var(--text-white)` | 그대로 유지 — 고정 다크 배경 위 흰 글자라 계속 맞음 |
| `.report-highlight b` | `color: var(--text-white)` — 흰 패널(var(--panel)) 위에서 흰 글자라 안 보임 | `color: var(--text);`로 수정 |
| `.q-num` 글자색 | `color: #5ac8fa` (밝은 하늘색, 다크 배경 전용) — 옅은 파랑 틴트 배경 위에서 라이트 모드는 대비 부족 | `color: var(--primary);` (`#0071e3`, 채도 높은 파랑이라 흰 배경에서도 잘 읽힘) |
| `.turn.assistant strong` 글자색 | 위와 동일한 `#5ac8fa` 문제 | `color: var(--primary);` |
| 전역 `input, select, textarea` 배경 | `background: #000000;` 고정 — 흰 패널 안에 검정 구멍처럼 보임 | `background: var(--bg);` (`#f5f5f7`, macOS의 "패널 안 오목한 입력창" 톤) |
| `.composer textarea` 배경 | `background: #000000;` | `background: var(--bg);` |
| `input:focus`/`select:focus`/`textarea:focus`, `.composer textarea:focus` | `border-color: rgba(255, 255, 255, 0.25);` — 흰 배경 위 흰 테두리라 안 보임 | `border-color: var(--primary); box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.25);` — 실제 macOS 포커스링(파란 halo)과 동일한 패턴 |
| `.locked::after` | `background: rgba(0, 0, 0, 0.82);` — 라이트 UI 안에서 시커먼 사각형이 튀어 보임. macOS는 비활성 영역을 검게 덮지 않고 흐리게(desaturate) 처리 | `background: rgba(255, 255, 255, 0.85);` (밝은 스크림으로 전환, `color: var(--muted)`는 유지) |
| `.cond` 배경 | `background: rgba(255, 255, 255, 0.08);` — 흰 패널(var(--panel)) 위에서 흰색 8% 틴트는 사실상 안 보임 | `background: rgba(0, 0, 0, 0.06);` |

`.audio-seg`(응답자 스테이지 안의 원문/원문+번역 토글)는 `.resp-stage` 위에 떠 있는 컨트롤이라 `rgba(255,255,255,...)` 흰색 반투명 값이 그대로 맞다 — `.resp-stage`가 고정 다크로 남기 때문에 수정하지 않는다.

## 검증 방법

- `cd frontend/dashboard && npm run build` — exit 0
- 로컬 dev 서버에서 세션 생성 폼 + 백룸(Monitor) 육안 확인:
  - 전체적으로 밝은 배경 + 흰 카드 + 옅은 그림자로 macOS 설정 앱 느낌이 나는지
  - `.resp-stage`(응답자 비디오 영역)만 의도적으로 어둡게 남아있는지, 그 위 텍스트/뱃지가 잘 보이는지
  - 폼 인풋/지시 입력창이 흰 카드 안에서 옅은 회색 오목한 필드로 보이는지, 포커스 시 파란 링이 보이는지
  - 인터뷰 시작 전 "잠긴 패널" 오버레이가 검정이 아니라 밝은 반투명 스크림으로 보이는지
  - `.q-num`, 어시스턴트 대화 뱃지 글자가 흰 배경에서도 또렷하게 읽히는지
