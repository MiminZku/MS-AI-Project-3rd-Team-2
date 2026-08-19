# 대시보드 타이포그래피 위계 강화 — 다크 리스킨 후속 보정

## 배경

`docs/superpowers/specs/2026-08-19-dashboard-dark-reskin-design.md`에서 대시보드를 인터뷰이와 같은 다크 팔레트로 리스킨했지만, 색상/반경/그림자만 바꾸고 글자 크기·여백은 손대지 않아서 "색만 바뀐 것 같다"는 피드백을 받았다. 레퍼런스(`styles.refero.design`)와 인터뷰이 프론트의 정체성은 색상뿐 아니라 큼직한 타이포그래피와 넉넉한 여백에서도 나온다.

이 스펙은 그 갭을 메우기 위한 후속 보정을 정의한다.

## 목표

- 패널 타이틀·현재 질문·타이머 숫자·주요 CTA 버튼처럼 "헤드라인급" 요소를 키워서 인터뷰이 쪽 존재감에 맞춘다
- 3단 레이아웃의 정보 밀도(질문 트리 항목, 대화 말풍선, 지시 이력 등 반복되는 데이터 행)는 그대로 유지한다 — 무한정 키우면 화면당 정보량이 줄고 스크롤이 늘어남
- 패널 내부/외부 여백을 1.5배로 넓혀 숨 쉴 공간을 준다

## 범위 (In Scope)

`frontend/dashboard/src/styles.css`의 아래 규칙만 수정한다 (색상은 이미 이전 스펙에서 완료, 이번엔 `font-size`/`padding`/`gap`만):

- `.p-head h2` — 패널 타이틀
- `.timer b` — 타이머 숫자
- `.tree li.current` — 현재 질문 (신규로 font-size 추가)
- 전역 `button`, `.sess-btn`, `.composer > button` — 주요 CTA
- `.monitor` — 3단 레이아웃 바깥 gap/padding
- `.panel-head, .p-head`, `.p-body`, `.tree`, `.turns` — 패널 내부 padding

## 비목표 (Out of Scope)

- 트리 항목(현재 질문 제외)·대화 말풍선·지시 이력·뱃지·캡션 등 반복 데이터 행의 font-size — 지금 값(11.5~13.5px) 유지
- `.rationale`/`.report-note`/`.linkrow`/`.modal`/`.form-page` 등 이미 색상만 리스킨된 중첩 박스의 padding — 이번엔 안 건드림 (밀도 유지 대상)
- 레이아웃 구조(3단 그리드 컬럼 수, breakpoint) 변경
- 색상/반경/그림자 재변경 — 이전 스펙에서 이미 완료됨

## 변경 값

| 요소 | 현재 | 변경 |
|---|---|---|
| `.p-head h2` font-size | 13px | 17px |
| `.timer b` font-size | 14px | 20px |
| `.tree li.current` font-size | (없음, 12px 상속) | 15px 명시 추가 |
| 전역 `button` padding / font-size | `10px 18px` / 12.5px | `14px 24px` / 15px |
| `.sess-btn` padding / font-size | `8px 15px` / 12px | `14px 24px` / 15px |
| `.composer > button` padding / font-size | `10px 16px` / 12px | `14px 24px` / 15px |
| `.monitor` gap / padding | `16px` / `16px 20px 40px` | `24px` / `24px 30px 60px` |
| `.panel-head, .p-head` padding | `13px 16px` | `20px 24px` |
| `.p-body` padding | `14px 16px` | `21px 24px` |
| `.tree` padding | `14px 16px` | `21px 24px` |
| `.turns` padding | `4px 16px 16px` | `6px 24px 24px` |

## 검증 방법

- `cd frontend/dashboard && npm run build` — exit 0
- 로컬 dev 서버(`localhost:5174`)에서 세션 생성 폼 + 백룸(Monitor) 화면 육안 확인:
  - 패널 타이틀·타이머·현재 질문·주요 버튼이 눈에 띄게 커졌는지
  - 질문 트리 나머지 항목/대화창/지시 이력은 크기 변화 없이 촘촘함을 유지하는지
  - 60px 고정 탑바 안에서 `.sess-btn`이 커져도 레이아웃이 깨지지 않는지 (topbar는 `align-items: center`라 자식 높이 차이는 흡수됨)
