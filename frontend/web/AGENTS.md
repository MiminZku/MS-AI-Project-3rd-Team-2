# 작업 지침 및 이행 계획 (AGENTS.md)

## 0-2. 금지 사항
- `backend/` 폴더의 **어떤 파일도 수정·삭제하지 않는다.**
- `frontend/dashboard/`, `frontend/interviewee/` 의 **어떤 파일도 수정·삭제하지 않는다.**
- 기존 GitHub Actions 워크플로 파일(`azure-static-web-apps-orange-sand-*.yml`, `azure-static-web-apps-victorious-pond-*.yml`)을 **수정하지 않는다.** 새 워크플로가 필요하면 기존 파일을 복제해 경로만 바꾼 **새 파일**을 추가한다.
- 루트 `README.md`, `Architecture.md` 는 이번 작업에서 **건드리지 않는다.** (문서 갱신은 김은향이 팀 합의 후 별도 진행)
- **백엔드 API를 실제로 호출하지 않는다.** 이번 MVP는 100% 목업. 세션/트랜스크립트/리포트가 필요한 화면은 전부 `src/mock/` 더미 데이터로 채운다.
- 외부 CDN 폰트를 쓰지 않는다. (팀에서 이미 CDN 서브셋 로딩 문제를 겪어 npm 자체 호스팅으로 전환한 이력 있음 — 박성은 8/14 로그)

## 0-3. 허용 범위
- `frontend/web/` 폴더 **신설 및 그 안의 모든 파일 작성** — 이 폴더는 전부 자유롭게 작업 가능.
- `.github/workflows/` 에 **새 파일 1개 추가** (기존 파일 복제 후 path filter만 교체).

---

## 5. 단계별 이행 계획 (파일 단위 구체적 경로)

### STEP 1: 기반 설정 및 스캐폴딩
다음 설정 파일 및 프로젝트 메인 진입점, 스타일 토큰을 정의하고 빈 라우터를 설정하여 개발/빌드 가능 상태를 만듭니다.
- [x] `frontend/web/package.json`
- [x] `frontend/web/vite.config.ts`
- [x] `frontend/web/tsconfig.json`
- [ ] `frontend/web/tsconfig.node.json`
- [x] `frontend/web/staticwebapp.config.json`
- [x] `frontend/web/.env.example`
- [x] `frontend/web/index.html`
- [x] `frontend/web/src/main.tsx`
- [x] `frontend/web/src/styles/tokens.css`
- [x] `frontend/web/src/styles/global.css`
- [x] `frontend/web/src/App.tsx`

### STEP 2: 공통 레이아웃 및 범용 컴포넌트 구현
전체 페이지에 공통 적용되는 레이아웃(헤더, 푸터, 네비게이션) 및 재사용 컴포넌트들을 제작합니다.
- [x] `frontend/web/src/layout/Header.tsx`
- [x] `frontend/web/src/layout/Nav.tsx`
- [x] `frontend/web/src/layout/Footer.tsx`
- [x] `frontend/web/src/layout/Layout.tsx`
- [x] `frontend/web/src/components/Button.tsx`
- [x] `frontend/web/src/components/Card.tsx`
- [x] `frontend/web/src/components/SectionHeading.tsx`
- [x] `frontend/web/src/components/PageHeader.tsx`

### STEP 3: Home (랜딩 페이지) 구현
랜딩 페이지 구성 요소들을 컴포넌트로 분리 구현 후 Home 페이지를 조립합니다.
- [x] `frontend/web/src/sections/home/Hero.tsx`
- [x] `frontend/web/src/sections/home/ProblemSection.tsx`
- [x] `frontend/web/src/sections/home/SolutionSection.tsx`
- [x] `frontend/web/src/sections/home/DifferentiatorSection.tsx`
- [x] `frontend/web/src/sections/home/HowItWorksSection.tsx`
- [x] `frontend/web/src/sections/home/CtaSection.tsx`
- [x] `frontend/web/src/pages/Home.tsx`

### STEP 4: About + Team 페이지 구현
팀원 데이터 및 약력/기능 소개 페이지를 구현하고 조립합니다.
- [x] `frontend/web/src/mock/team.ts`
- [x] `frontend/web/src/components/TeamCard.tsx`
- [x] `frontend/web/src/sections/about/MissionSection.tsx`
- [x] `frontend/web/src/sections/about/MarketSection.tsx`
- [x] `frontend/web/src/sections/about/BackgroundSection.tsx`
- [x] `frontend/web/src/sections/about/TrustSection.tsx`
- [x] `frontend/web/src/pages/About.tsx`
- [x] `frontend/web/src/pages/Team.tsx`

### STEP 5: Services (인터뷰 & 리포트/산출물 분석) 페이지 구현
핵심 기능 화면 목업, 인라인 SVG 차트, 텍스트 스크립트 출력 컴포넌트를 구현하고 조립합니다.
- [x] `frontend/web/src/mock/transcript.ts`
- [x] `frontend/web/src/mock/analysis.ts`
- [x] `frontend/web/src/components/report/TranscriptExportCard.tsx`
- [x] `frontend/web/src/components/report/AnalysisDashboardPreview.tsx`
- [x] `frontend/web/src/sections/services/QualitativeInterview.tsx`
- [x] `frontend/web/src/sections/services/RoomDiagram.tsx`
- [x] `frontend/web/src/sections/services/ReportAnalysis.tsx`
- [x] `frontend/web/src/pages/Services.tsx`

### STEP 6: Contact + Login 페이지 구현 및 배포 구성
마무리 문의 폼, 시각 목업 로그인 페이지 작성 및 GitHub Actions 배포 파일을 추가합니다.
- [x] `frontend/web/src/pages/Contact.tsx`
- [x] `frontend/web/src/pages/Login.tsx`
- [x] `.github/workflows/azure-static-web-apps-web.yml`

### STEP 7: Apple (España) 전역 톤 통일
전역 중심 디자인을 Apple (España) 레퍼런스 기준으로 통일하고 디자인 시스템 토큰 및 정렬 스케일을 정비합니다.
- [x] `frontend/web/src/styles/tokens.css` 재정비
- [x] `frontend/web/src/styles/global.css` 및 전 컴포넌트 토큰 점검

### STEP 8: 팀 캐릭터 아바타
오리지널 캐릭터 아바타(인라인 SVG)를 적용하여 팀원별 카드에 렌더링되게 합니다.
- [x] `frontend/web/src/components/AvatarCharacter.tsx` 신규
- [x] `frontend/web/src/mock/team.ts` 데이터 확장 (avatarVariant)
- [x] `frontend/web/src/components/TeamCard.tsx` 바인딩 적용

### STEP 9: 하이브리드 컬러 + Gromit 브랜드 오프닝
메인룸(interviewee)의 다크 톤 팔레트를 동기화하여 하이브리드 섹션 톤 배정 및 랜딩 브랜드 오프닝 애니메이션을 적용합니다.
- [x] `frontend/interviewee/src/styles.css` 다크 팔레트 값 동기화
- [x] `frontend/web/src/styles/tokens.css` 에 다크 토큰 추가 및 액센트 통일
- [x] `global.css` 에 `.section--dark` 재사용 클래스 및 폼 입력 스타일 추가
- [x] 페이지 및 섹션별 톤 배정 (Home, Services, About, Team, Contact, Login)
- [x] Hero 컴포넌트 Gromit 워드마크 오프닝 애니메이션 재구성
- [x] BrandIntro 및 Hero 분리를 통한 2단계 오프닝 랜딩 구현 (brand-intro-section, 100dvh)

### STEP 10: 랜딩 첫 화면 교체: 음성 파형 히어로
기존 BrandIntro 첫 화면을 인사이트와 니즈의 만남을 표현한 오리지널 음성 파형 일러스트 및 은은한 글로우를 탑재한 화면으로 교체합니다.
- [x] `sections/home/BrandIntro.tsx` 및 `sections/home/HandsMeetHero.tsx` 삭제/정리
- [x] `sections/home/WaveMeetHero.tsx` 신규 생성 및 sin/cos 기반 파형 SVG 적용
- [x] 카피 문구 3줄 원문 반영
- [x] `pages/Home.tsx` 조립 구성 업데이트
