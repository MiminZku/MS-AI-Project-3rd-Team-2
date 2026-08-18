# Team Rules & Conventions

이 문서는 **3자 개입형 실시간 AI 인터뷰 시스템** 개발 팀의 규칙과 협업 컨벤션을 정의합니다.

## 1. 깃 브랜치 전략 (Git Branch Strategy)

우리는 **Git Flow**의 간소화된 버전을 사용합니다.

- `main`: 프로덕션 배포 브랜치
- `develop`: 통합 개발 브랜치 (기본 브랜치)
- `feature/기능명`: 개별 기능 개발 브랜치
- `hotfix/이슈명`: 긴급 버그 수정 브랜치

### 브랜치 생명 주기
1. 새로운 기능 개발 시 `develop` 브랜치로부터 `feature/기능명` 브랜치를 생성합니다.
2. 기능 개발 완료 후 `develop` 브랜치로 Pull Request(PR)를 생성합니다.
3. 최소 1명 이상의 팀원 코드 리뷰 및 승인(Approve)을 받은 후 머지합니다.

---

## 2. 커밋 메시지 컨벤션 (Commit Message Convention)

커밋 메시지는 Gitmoji 또는 아래 접두사를 사용하여 직관적으로 작성합니다.

`접두사: 커밋 제목 (영문 또는 한글)`

- `feat`: 새로운 기능 추가
- `fix`: 버그 수정
- `docs`: 문서 수정 (Markdown 파일 등)
- `style`: 코드 포맷팅, 세미콜론 누락 등 (코드 변경 없음)
- `refactor`: 코드 리팩토링
- `test`: 테스트 코드 추가 및 수정
- `chore`: 빌드 업무 수정, 패키지 매니저 설정 등

---

## 3. 코드 스타일 및 기술 스택

### 프론트엔드 (React + Vite + TypeScript)
- **컴포넌트 선언**: 가능하면 함수형 컴포넌트 (`const Component = () => {}`) 사용
- **상태 관리**: 컴포넌트 내 Local State 위주로 작성하고, 전역 상태가 필요할 경우 Context API 또는 가벼운 상태 라이브러리 사용
- **포맷터**: ESLint & Prettier 적용

### 백엔드 (FastAPI + Python)
- **포맷터/린터**: `black`, `isort`, `flake8` 적용
- **타입 힌트**: Python의 Type Hinting을 적극 사용하여 자동 문서화(`Swagger`) 및 코드 안정성 확보
- **비동기 선언**: I/O Bound 작업은 `async def`를 사용하고, CPU Bound 작업은 동기 형태로 작성하거나 스레드 풀 활용

---

## 4. 아키텍처 원칙 (Architecture Principles)

- 시스템 설계 근거와 결정사항은 [Architecture.md](file:///c:/Github/MS-AI-Project-3rd-Team-2/Architecture.md)를 단일 소스(Single Source of Truth)로 합니다.
- **인터뷰이 프론트엔드**와 **참관자 대시보드**의 데이터 분리 및 역할 분담을 엄격히 준수합니다.
- Azure 리소스(Container Apps, Static Web Apps 등) 환경 설정과 배포에 관한 정보는 [docs/azure-setup.md](file:///c:/Github/MS-AI-Project-3rd-Team-2/docs/azure-setup.md)를 참고합니다.

---

# Team 2: AI Orchestration & Governance Rules

## 1. MISSION & ARCHITECTURE
- Core: AI Moderator (Main Room) + AI Translator (Back Room) w/ PM feedback loop.
- Constraint: Budget (1.1M KRW), Team (1 Dev, 3 Non-tech), Timeline (10 days).
- Hierarchy: Notion (SSOT) ↔ Antigravity (Execution) ↔ Claude (Backend) ↔ Gemini (Review).

## 2. WORKFLOW: DESIGN-FIRST & STEP-WISE APPROVAL
- Flow: 지시 접수 ➔ [작업 기획서] 제출 ➔ 김은향 승인 ➔ 스텝별 실행.
- Explanation: 선택한 기술/프롬프트 전략이 프로젝트에 미칠 영향과 이유를 김은향이 100% 이해하도록 설명.
- Approval Lock: 단계별 승인 필수. 김은향이 승인을 누락할 경우 Proactive 리마인드.

## 3. NOTION & DATA PROTOCOL
- SSOT: Notion "3차 프로젝트 - 2팀" 내 [김은향] 페이지/하위 토글만 작성/수정.
- Daily Log: 매일 새 페이지/토글 생성. [Task Checklist], [Log (`---`)], [Calendar Update] 구조 준수.
- Data Safety: Overwrite 금지. 수정 전 반드시 기존 데이터 확인 및 김은향 알림.

## 4. PERSISTENCE & GIT SAFETY
- Recovery: 매 세션 `session_recovery.md`로 상태 로컬 저장.
- Git Protocol: 커밋 준비는 Antigravity에서, 최종 `git push`는 김은향만 수행.
- Safety: 타 팀원 페이지 수정 엄금. 개발/기획 역할 분담(강민기/비개발팀) 철저 준수.

## 5. STYLE & REPORTING
- Communication: Caveman + ADHD Hybrid (간결, 구조적, Fluff 제거).
- Output: 모든 노션 업데이트 후 챗에 고정 보고 포맷(일시, 흐름, 상태, 승인, Git, 리스크) 필수 출력.

