# 🗄️ NoSQL 데이터베이스 스키마 설계서 (Azure Cosmos DB / NoSQL)

본 문서는 **AI 화상 인터뷰 솔루션**의 데이터 저장 및 조회를 위한 NoSQL 데이터 모델 표준 정의서입니다.  
프론트엔드, 백엔드 및 AI 에이전트 간의 데이터 통신과 Cosmos DB 저장은 본 스키마를 따릅니다.

---

## 1. 📂 컬렉션 구조 개요

* **데이터베이스**: `InterviewDB`
* **컬렉션 1**: `projects` (프로젝트 메타데이터 및 질문 템플릿 트리 관리)
* **컬렉션 2**: `interviews` (개별 인터뷰 세션, 대화 상세 로그, 녹화 영상, 요약 리포트 관리)
  * **Partition Key**: `/project_id` (프로젝트 단위 고속 쿼리 및 비용 최적화)

---

## 2. 📋 `projects` 컬렉션 스키마

하나의 인터뷰 주제(프로젝트) 단위로 생성되는 문서입니다.

```json
{
  "id": "proj_ai_ux_2026",
  "type": "project",
  "title": "2026 배달 플랫폼 UX 만족도 및 배달비 체감 조사",
  "description": "실제 배달 앱 주 사용 고객 20명 대상 심층 인터뷰",
  "created_by": "PM 김철수",
  "created_at": "2026-08-20T09:00:00Z",
  "updated_at": "2026-08-20T09:30:00Z",
  "status": "active", // "active" | "archived"
  "target_duration_minutes": 20, // 목표 인터뷰 시간 (분)
  
  // 📁 Blob Storage 파일 경로들
  "source_file_url": "https://<storage>.blob.core.windows.net/documents/proj_ai_ux_2026/interview_guide.docx", // 업로드한 원본 질문지 파일
  "project_report_url": "https://<storage>.blob.core.windows.net/reports/proj_ai_ux_2026/comprehensive_report.pdf", // 전체 인터뷰 종합 분석 리포트

  // 📊 집계 정보
  "interview_count": 5, // 진행된 총 인터뷰 수
  "completed_count": 4, // 완료된 인터뷰 수

  // 🌳 파싱된 표준 질문 트리 (Question Tree)
  "question_tree": [
    {
      "id": "q1",
      "order": 1,
      "text": "최근 배달 앱을 이용하면서 배달비 때문에 불편했던 경험이 있으신가요?",
      "intent": "배달비 인상에 대한 실제 체감 부담과 그에 따른 소비 행동 변화(주문 취소/포장 전환 등) 파악",
      "keywords": ["배달비", "포장", "주문 취소", "쿠폰", "무료배달"],
      "max_followups": 2,
      "branches": {
        "부담됨": "그 때문에 실제로 주문을 포기하거나 다른 앱으로 갈아탄 경험이 있나요?",
        "괜찮음": "그렇다면 배달 서비스를 선택할 때 배달비 외에 가장 중요하게 보는 요소는 무엇인가요?"
      }
    },
    {
      "id": "q2",
      "order": 2,
      "text": "새로 도입된 '무료 배달 구독제' 서비스를 이용해보신 적이 있나요?",
      "intent": "구독제 서비스의 인지도 및 실질적인 혜택 체감 여부 확인",
      "keywords": ["구독제", "패스", "멤버십", "가입"],
      "max_followups": 1,
      "branches": {}
    }
  ]
}
```

---

## 3. 🎙️ `interviews` 컬렉션 스키마

특정 프로젝트 하에서 **한 명의 인터뷰이와 진행한 1회의 인터뷰 전체 데이터**를 담는 문서입니다.

```json
{
  "id": "ses_abd23ab2f362",
  "type": "interview",
  "project_id": "proj_ai_ux_2026", // ⭐️ 외래키 & Partition Key
  
  // 👤 응답자 정보
  "interviewee_name": "홍길동",
  "interviewee_email": "gildong@example.com",
  "status": "completed", // "created" | "running" | "completed" | "abandoned"
  
  // ⏱️ 시간 정보
  "started_at": "2026-08-20T10:00:00Z",
  "ended_at": "2026-08-20T10:23:45Z",
  "duration_seconds": 1425, // 실제 진행 시간 (초)

  // 🎥 📁 멀티미디어 및 리포트 파일 경로 (Blob Storage)
  "video_recording_url": "https://<storage>.blob.core.windows.net/recordings/ses_abd23ab2f362/full_video.mp4", // 화상 녹화 영상(음성 포함)
  "individual_report_url": "https://<storage>.blob.core.windows.net/reports/ses_abd23ab2f362/interview_summary.pdf", // 개별 인터뷰 요약 리포트

  // 🧠 LLM 자동 분석 결과 (인터뷰 종료 시 생성)
  "summary": "응답자는 주 3~4회 배달 앱을 사용하는 헤비 유저이나, 최근 배달비 인상으로 인해 4,000원 이상 시 포장 주문으로 전환하는 경향을 보임. 무료 배달 구독제에 대해서는 긍정적이나 월 이용료에 대한 부담을 언급함.",
  "key_insights": [
    "배달비 4,000원 이상 시 100% 방문 포장 또는 주문 포기",
    "무료 배달 구독제 인지도는 높으나 가격 저항선은 월 3,000원 선",
    "단골 매장 자체 배달 서비스에 대한 높은 선호도"
  ],
  "sentiment_score": "neutral", // "positive" | "neutral" | "negative"

  // 💬 상세 Q&A 대화 기록 (타임스탬프 및 번역본 포함)
  "qa_records": [
    {
      "turn_id": 1,
      "question_id": "q1",
      "question_type": "main", // "main" | "follow_up" | "branch" | "observer_injected"
      "question_text": "최근 배달 앱을 이용하면서 배달비 때문에 불편했던 경험이 있으신가요?",
      "answer_ko": "네, 요즘 기본 배달비가 4~5천 원씩 해서 주문 직전에 취소하고 직접 가서 포장해 온 적이 많아요.",
      "answer_en": "Yes, lately basic delivery fees are around 4 to 5 thousand won, so I've often cancelled right before ordering and picked it up myself.",
      "started_at": "2026-08-20T10:01:05Z",
      "ended_at": "2026-08-20T10:01:25Z",
      "ai_rationale": "배달비 부담 체감 여부를 확인하기 위해 1번 메인 질문을 시작함.",
      "observer_instruction_id": null
    },
    {
      "turn_id": 2,
      "question_id": "q1",
      "question_type": "follow_up",
      "question_text": "직접 포장해 오실 때 배달비가 대략 얼마 이상일 때 부담스럽다고 느끼셨나요?",
      "answer_ko": "보통 3,500원 넘어가면 슬슬 망설여지고, 4,000원 넘으면 거의 무조건 포장하러 갑니다.",
      "answer_en": "Usually when it exceeds 3,500 won I hesitate, and over 4,000 won I almost always go pick it up.",
      "started_at": "2026-08-20T10:01:30Z",
      "ended_at": "2026-08-20T10:01:45Z",
      "ai_rationale": "응답자가 포장 전환 경험을 언급하여, 구체적인 가격 저항선 금액을 파악하기 위해 꼬리질문 생성.",
      "observer_instruction_id": null
    }
  ],

  // 🎯 인터뷰 도중 참관자(PM)가 내린 실시간 개입 지시 기록
  "observer_instructions": [
    {
      "id": "ins_001",
      "text": "배달비 저항선 금액을 구체적인 숫자로 물어봐줘",
      "created_at": "2026-08-20T10:01:10Z",
      "applied_at": "2026-08-20T10:01:30Z",
      "applied_turn": 2
    }
  ]
}
```

---

## 4. 🚀 화면별 데이터 조회(Query) 최적화 가이드

| 화면 단계 | 용도 | 쿼리 방식 | 설명 |
| :--- | :--- | :--- | :--- |
| **1단계** | **대시보드 메인 (프로젝트 목록)** | `SELECT id, title, description, created_at, interview_count, completed_count FROM projects` | 무거운 질문 트리나 대화 내용 없이 가볍게 로딩 |
| **2단계** | **프로젝트 상세 (참가자 리스트)** | `SELECT id, interviewee_name, status, started_at, duration_seconds, summary, sentiment_score FROM interviews WHERE project_id = @projectId` | 동일 파티션 내에서 참가자 목록과 요약만 고속 조회 |
| **3단계** | **특정 인터뷰 상세 (Q&A/영상/리포트)** | `SELECT * FROM interviews WHERE id = @session_id` | 해당 인터뷰의 전체 대화 로그 및 영상/리포트 URL 일괄 획득 |
