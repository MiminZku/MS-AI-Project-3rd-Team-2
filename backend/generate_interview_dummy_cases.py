"""3명의 가상 인터뷰이 대상 실시간 통역(한국어 원문 + 영어 번역본) 및 
실제 타임스탬프, PM 실시간 지시, AI 판단근거를 완벽하게 반영한 
인터뷰 결과 더미 데이터 생성 스크립트.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
import sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.schemas.session import QuestionNode, Session, Turn, Instruction
from app.services.ai.document_parser import get_document_parser

# 3인 페르소나 (한국어 답변 + 실시간 영문 번역본 answer_en 완벽 포함)
PERSONAS = [
    {
        "id": "ses_dev_kim_01",
        "name": "김민수 (백엔드 시니어 개발자 / 8년차)",
        "email": "minsu.kim@techcorp.io",
        "trait": "대규모 분산 시스템 및 마이크로서비스 아키텍처 담당. 터미널 환경을 극도로 선호하며 멀티레포 컨텍스트 파악과 Git 충돌 방지를 중요하게 여김.",
        "pm_instruction": {
            "text": "대규모 코드베이스에서 Claude Code가 여러 파일 간의 종속성을 어떻게 파악했는지 구체적인 사례를 물어봐줘"
        },
        "answers": {
            "q1": {
                "ko": "저는 터미널에서 Neovim이랑 tmux를 주로 쓰고, 복잡한 작업이나 전체 프로젝트 컨텍스트를 다룰 때는 Claude Code CLI를 메인으로 씁니다. 가끔 빠른 단일 함수 작성을 할 때만 Cursor나 Copilot을 씁니다.",
                "en": "I mainly use Neovim and tmux in the terminal, and when dealing with complex tasks or overall project context, I use Claude Code CLI as my primary tool. I only use Cursor or Copilot occasionally for quickly writing single functions."
            },
            "q1_follow": {
                "ko": "네, 맞습니다. 일반적인 CRUD 작업은 단축키로 Cursor에서 바로 치는데, 여러 패키지에 걸친 DB 마이그레이션이나 리팩토링은 무조건 Claude Code로 작업합니다.",
                "en": "Yes, that's right. For routine CRUD tasks, I just type them out in Cursor with shortcuts, but for DB migrations or refactorings spanning multiple packages, I definitely work with Claude Code."
            },
            "q2": {
                "ko": "완전 공감합니다. OpenAI o3-mini나 gpt-4o가 코딩 벤치마크 점수는 높을지 몰라도, 실제 터미널에서 대화형으로 작업할 때는 Claude Code가 압도적입니다. 일단 파일 검색(Glob)과 diff 검토 인터페이스가 터미널 워크플로우에 최적화되어 있어요.",
                "en": "I completely agree. Even though OpenAI's o3-mini or gpt-4o might score higher on coding benchmarks, when working interactively in the actual terminal, Claude Code is overwhelming. First of all, its file search (Glob) and diff review interface are optimized for the terminal workflow."
            },
            "q2_follow_pm": {
                "ko": "최근 15개 마이크로서비스 간의 gRPC proto 정의를 바꾸는 작업이 있었는데, Claude Code는 제가 일일이 경로를 안 알려줘도 grep이랑 ripgrep으로 연관된 모듈을 스스로 찾아서 순서대로 패치해주더라고요. OpenAI CLI 툴들은 컨텍스트 윈도우가 터지거나 엉뚱한 파일을 수정해서 망친 적이 많았습니다.",
                "en": "Recently, I had to change gRPC proto definitions across 15 microservices. Claude Code automatically found related modules using grep and ripgrep without me specifying paths, and patched them in sequence. OpenAI CLI tools often blew up context windows or edited the wrong files, messing things up."
            },
            "q3": {
                "ko": "OpenAI 도구들은 에이전트의 '자율성' 제어가 너무 투박합니다. 한 번에 너무 많은 코드를 한꺼번에 덮어쓰려고 하거나, 파일 수정 승인 단계가 터미널 친화적이지 않아서 작업 흐름이 뚝뚝 끊깁니다.",
                "en": "OpenAI tools have very clunky controls for agent 'autonomy'. They try to overwrite too much code at once, and the file edit approval steps aren't terminal-friendly, which constantly interrupts my workflow."
            },
            "q3_follow": {
                "ko": "네, 수동으로 롤백하거나 git diff를 따로 터미널 탭 열어서 확인해야 하는 번거로움이 제일 컸습니다. 속도보다는 이 '신뢰성과 제어감'의 차이가 결정적입니다.",
                "en": "Yes, the biggest hassle was having to manually roll back or open a separate terminal tab to check git diff. Rather than speed, this difference in 'reliability and sense of control' is crucial."
            },
            "q4": {
                "ko": "OpenAI도 터미널 내에서 git diff와 실시간 파일 트리를 완벽하게 인식하고, 단계별 승인(Interactive Diff Accept/Reject)이 가능한 CLI 전용 에이전트 인터페이스를 제공해야 합니다.",
                "en": "OpenAI must also provide a dedicated CLI agent interface that perfectly recognizes git diff and real-time file trees in the terminal, allowing interactive step-by-step diff accept/reject."
            }
        },
        "summary": "8년차 백엔드 시니어 개발자로서 멀티 모듈 리팩토링 및 대규모 코드베이스 파악 시 Claude Code의 자율적 파일 탐색(Grep/Glob)과 정교한 diff 제어력을 높게 평가함. OpenAI는 모델 성능은 뛰어나나 터미널 UX 및 에이전트 작업 승인 절차가 불완전하여 실무 이탈이 발생함을 확인.",
        "key_insights": [
            "대규모 모듈 수정 시 Claude Code의 파일 간 종속성 자동 추적 및 순차 패치 능력 선호",
            "OpenAI 도구의 가장 큰 병목은 '과도한 일괄 덮어쓰기'와 '불편한 승인 UI로 인한 흐름 단절'",
            "터미널 인터랙티브 Diff 승인/거부 인터페이스 도입이 최우선 해결 과제"
        ],
        "sentiment": "neutral"
    },
    {
        "id": "ses_dev_park_02",
        "name": "박지은 (풀스택 주니어 개발자 / 2년차)",
        "email": "jieun.park@startup.kr",
        "trait": "Next.js 및 React 기반 프론트엔드/BFF 개발. 빠른 UI 개발 속도와 디버깅 피드백 루프를 중시하며, 에러 메시지 해석 능력을 중요시함.",
        "pm_instruction": {
            "text": "타입스크립트 컴파일 에러나 빌드 실패 시 두 툴의 해결 방식 차이를 물어봐줘"
        },
        "answers": {
            "q1": {
                "ko": "저는 VS Code 에디터 안에서 Cursor를 주로 쓰고 있었는데, 동료 추천으로 2주 전부터 Claude Code 터미널 버전을 병행하고 있습니다.",
                "en": "I was mainly using Cursor inside the VS Code editor, but starting two weeks ago upon a coworker's recommendation, I've been using the Claude Code terminal version alongside it."
            },
            "q1_follow": {
                "ko": "네, 평소 컴포넌트 짤 때는 Cursor 단축키가 편한데, Next.js 15 버전 마이그레이션이나 복잡한 타입 에러 잡을 때는 Claude Code를 터미널에서 켜게 돼요.",
                "en": "Yes, Cursor shortcuts are convenient for normal component coding, but for Next.js 15 migration or tracking down complex type errors, I end up opening Claude Code in the terminal."
            },
            "q2": {
                "ko": "네, 100% 공감해요! 모델 성능이 아무리 좋아도 터미널에서 작업할 때 에러 로그를 읽고 스스로 `npm run build`를 돌려보면서 테스트를 통과할 때까지 루프를 도는 경험은 Claude Code가 훨씬 매끄러워요.",
                "en": "Yes, I 100% agree! No matter how good the raw model is, Claude Code provides a much smoother experience when reading terminal error logs and automatically running `npm run build` in a loop until tests pass."
            },
            "q2_follow_pm": {
                "ko": "Next.js 빌드 시 복잡한 Zod 스키마랑 Server Actions 타입 불일치 에러가 났을 때, OpenAI 툴은 에러 텍스트만 복붙하라고 하거나 엉뚱한 타입 단언(as any)을 남발했는데, Claude는 tsconfig와 전체 타입을 추적해서 근본적인 제네릭 문제를 고쳐줬어요.",
                "en": "When I had Next.js build errors with complex Zod schemas and Server Actions type mismatches, OpenAI tools told me to paste error logs or spammed `as any`, whereas Claude tracked tsconfig and overall types to fix the fundamental generic issues."
            },
            "q3": {
                "ko": "OpenAI ChatGPT나 API 기반 툴은 제가 에러 로그를 일일이 복사해서 프롬프트에 붙여넣어야 하는 게 너무 귀찮았어요. 프롬프트 창 왔다 갔다 하다가 집중력이 깨집니다.",
                "en": "With OpenAI ChatGPT or API tools, having to copy each error log and paste it into the prompt was so tedious. Switching back and forth between prompt windows broke my focus."
            },
            "q3_follow": {
                "ko": "네, 맞아요. 복붙하는 번거로움과 이전 대화 맥락이 길어지면 앞서 말한 프로젝트 구조를 까먹는 컨텍스트 소실 문제가 제일 답답했어요.",
                "en": "Yes, exactly. The hassle of copying and pasting, plus the context loss where it forgets earlier project structures as conversation grows long, were the most frustrating aspects."
            },
            "q4": {
                "ko": "터미널에서 에러가 발생했을 때 백그라운드에서 즉시 에러 원인을 진단하고 원클릭으로 가이드해주는 자동 디버깅 에이전트가 나오면 좋겠어요.",
                "en": "I'd love to see an automated debugging agent that diagnoses terminal errors in the background immediately and guides fixes with one click."
            }
        },
        "summary": "2년차 풀스택 개발자로 빌드/타입 에러 발생 시 Claude Code의 '스스로 명령어를 실행하고 검증하는 자율 피드백 루프'를 극찬함. OpenAI 툴은 에러 로그 복사/붙여넣기 번거로움과 임시방편(as any) 코드 제안으로 신뢰도가 낮아짐.",
        "key_insights": [
            "빌드 실패 시 스스로 테스트/빌드 명령어를 실행하며 자가 교정(Self-healing)하는 능력 차이",
            "웹 UI/프롬프트 창과 터미널 간의 반복적인 복사/붙여넣기가 주요 마찰 지점",
            "근본적인 타입 추론보다 임시방편 코드를 제시하는 경향에 대한 피로감"
        ],
        "sentiment": "positive"
    },
    {
        "id": "ses_dev_lee_03",
        "name": "이성호 (AI/ML 엔지니어 / 5년차)",
        "email": "sh.lee@dataworks.ai",
        "trait": "Python 기반 데이터 파이프라인 및 LLM 서빙 엔지니어. GPU 서버 SSH 원격 접속 환경이 주 작업장이며 속도와 API 토큰 비용에 민감함.",
        "pm_instruction": {
            "text": "원격 GPU 서버(SSH) 환경에서 CLI 툴 사용 시 토큰 비용과 속도 체감을 구체적으로 비교해줘"
        },
        "answers": {
            "q1": {
                "ko": "저는 로컬 GUI를 거의 안 쓰고 리모트 리눅스 서버에 SSH로 붙어서 작업합니다. CLI 기반 OpenAI 툴들과 Claude Code를 둘 다 설치해 두고 쓰고 있습니다.",
                "en": "I rarely use local GUIs and mostly SSH into remote Linux servers. I have both CLI-based OpenAI tools and Claude Code installed and use both."
            },
            "q1_follow": {
                "ko": "스크립트 하나 짤 때는 OpenAI CLI를 쓰고, 프로젝트 전체 파이프라인 구조를 짤 때는 Claude Code를 씁니다.",
                "en": "I use OpenAI CLI when writing single scripts, and Claude Code when structuring overall project pipelines."
            },
            "q2": {
                "ko": "공감 반, 불만 반입니다. Claude Code가 컨텍스트 파악과 멀티스텝 실행은 훨씬 뛰어난데, 비용(토큰) 소모가 너무 크고 속도가 느릴 때가 많아요. 반면 OpenAI는 응답 속도와 가격은 좋은데 터미널 CLI의 UX 완결성이 떨어집니다.",
                "en": "I half agree and half disagree. Claude Code is much better at context comprehension and multi-step execution, but it consumes too many tokens and is often slow. On the other hand, OpenAI has great speed and pricing, but lacks complete terminal CLI UX."
            },
            "q2_follow_pm": {
                "ko": "SSH 터미널에서 Claude Code는 매 턴마다 수만 토큰의 파일 트리를 다시 읽다 보니 API 비용이 순식간에 몇 달러씩 나가요. 반면 OpenAI는 가볍고 빠른데, 에이전트가 명령어를 실행할 때 위험 명령어 방지나 환경 변수 처리가 불안정합니다.",
                "en": "In SSH terminals, Claude Code re-reads tens of thousands of tokens of file trees every turn, draining several dollars in API fees quickly. OpenAI is lightweight and fast, but lacks stability in dangerous command prevention or environment variable handling during execution."
            },
            "q3": {
                "ko": "OpenAI의 가장 큰 문제는 공식 CLI 툴의 완성도 부족입니다. 서드파티 오픈소스 CLI에 의존하다 보니 버전 호환성이 깨지거나 토큰 스트리밍이 불안정합니다.",
                "en": "OpenAI's biggest problem is the lack of a mature official CLI tool. Relying on third-party open-source CLIs leads to broken version compatibility and unstable token streaming."
            },
            "q3_follow": {
                "ko": "네, 비용보다는 CLI 도구 자체의 안정성과 공식 지원 부족이 가장 아쉬웠습니다.",
                "en": "Yes, rather than cost, the lack of tool stability and official support was the most disappointing factor."
            },
            "q4": {
                "ko": "SSH 원격 환경에서도 초경량으로 동작하면서, 로컬/원격 토큰 캐싱을 완벽 지원하는 공식 고성능 OpenAI CLI를 만들어주면 바로 스위칭하겠습니다.",
                "en": "If OpenAI creates an official, high-performance CLI that operates ultra-lightweight in SSH environments and fully supports local/remote token caching, I'd switch immediately."
            }
        },
        "summary": "5년차 AI/ML 엔지니어로 SSH 원격 환경에서의 CLI 안정성과 토큰 캐싱 효율을 중시함. Claude Code의 깊은 컨텍스트 관리력은 인정하나 토큰 비용과 속도에 부담을 느낌. OpenAI가 고성능 공식 CLI와 비용 최적화 캐싱을 제공한다면 스위칭 의향이 높음.",
        "key_insights": [
            "원격 SSH 환경에서 Claude Code의 과도한 토큰 소모(파일 트리 전체 재전송)에 대한 비용 부담",
            "OpenAI의 빠른 추론 속도와 저렴한 가격은 강력한 경쟁 우위이나 공식 CLI 도구의 부재가 치명적",
            "프롬프트/컨텍스트 캐싱을 극대화한 경량 터미널 에이전트 출시 시 높은 스위칭 잠재력"
        ],
        "sentiment": "negative"
    }
]


async def run_simulation_with_translations():
    md_path = Path("backend/dummy_data/question_list_dummy.md")
    parser = get_document_parser()
    text = parser.extract_text_from_bytes(md_path.read_bytes(), "question_list_dummy.md")
    parsed = await parser.parse_guide(text)

    project_id = "proj_claude_vs_openai_2026"
    results = []

    for idx, p in enumerate(PERSONAS, start=1):
        qa_records = []
        turn_id = 1
        base_minute = idx * 15

        # Helper to format timestamps
        def ts(m_offset, s_offset):
            return f"2026-08-20T10:{base_minute + m_offset:02d}:{s_offset:02d}Z"

        # Turn 1: Main Q1
        q1_text = parsed.questions[0].text
        qa_records.append({
            "turn_id": turn_id,
            "question_id": "q1",
            "question_type": "main",
            "question_text": q1_text,
            "answer_ko": p["answers"]["q1"]["ko"],
            "answer_en": p["answers"]["q1"]["en"],
            "started_at": ts(1, 5),
            "ended_at": ts(1, 30),
            "ai_rationale": "인터뷰 도입부로써 참가자의 현재 주력 개발 툴체인을 파악하기 위해 1번 메인 질문 진행.",
            "observer_instruction_id": None
        })
        turn_id += 1

        # Turn 2: Follow-up Q1
        q1_follow = list(parsed.questions[0].branches.values())[0] if parsed.questions[0].branches else "상황에 따라 사용하는 툴이 어떻게 달라지나요?"
        qa_records.append({
            "turn_id": turn_id,
            "question_id": "q1",
            "question_type": "follow_up",
            "question_text": q1_follow,
            "answer_ko": p["answers"]["q1_follow"]["ko"],
            "answer_en": p["answers"]["q1_follow"]["en"],
            "started_at": ts(1, 35),
            "ended_at": ts(2, 5),
            "ai_rationale": "응답자가 도구를 혼용한다고 답변하여, 작업 복잡도별 툴 분기 기준을 심층 탐색.",
            "observer_instruction_id": None
        })
        turn_id += 1

        # Turn 3: Main Q2
        q2_text = parsed.questions[1].text
        qa_records.append({
            "turn_id": turn_id,
            "question_id": "q2",
            "question_type": "main",
            "question_text": q2_text,
            "answer_ko": p["answers"]["q2"]["ko"],
            "answer_en": p["answers"]["q2"]["en"],
            "started_at": ts(2, 10),
            "ended_at": ts(2, 45),
            "ai_rationale": "핵심 조사 질문으로 진입하여 모델 스펙과 터미널 실사용 체감 간의 괴리 원인을 질문함.",
            "observer_instruction_id": None
        })
        turn_id += 1

        # Turn 4: PM Intervention Injected Follow-up!
        pm_ins = p["pm_instruction"]
        q2_pm_text = f"방금 말씀하신 맥락에서, {pm_ins['text']} 관련해서 조금 더 구체적인 경험을 들려주실 수 있을까요?"
        qa_records.append({
            "turn_id": turn_id,
            "question_id": "q2",
            "question_type": "observer_injected",
            "question_text": q2_pm_text,
            "answer_ko": p["answers"]["q2_follow_pm"]["ko"],
            "answer_en": p["answers"]["q2_follow_pm"]["en"],
            "started_at": ts(2, 50),
            "ended_at": ts(3, 40),
            "ai_rationale": f"참관자(PM)의 긴급 지시('{pm_ins['text']}')를 수신하여 자연스러운 후속 탐색 질문으로 즉시 변환 주입함.",
            "observer_instruction_id": f"ins_{idx}_01"
        })
        turn_id += 1

        # Turn 5: Main Q3 (Pain Points)
        q3_text = parsed.questions[2].text
        qa_records.append({
            "turn_id": turn_id,
            "question_id": "q3",
            "question_type": "main",
            "question_text": q3_text,
            "answer_ko": p["answers"]["q3"]["ko"],
            "answer_en": p["answers"]["q3"]["en"],
            "started_at": ts(3, 45),
            "ended_at": ts(4, 20),
            "ai_rationale": "OpenAI 툴 사용 시 흐름이 끊기거나 답답했던 구체적인 병목 지점을 정조준 질문.",
            "observer_instruction_id": None
        })
        turn_id += 1

        # Turn 6: Follow-up Q3
        q3_follow = "프롬프트 입력 및 결과물 검토 과정에서 불필요하게 수동 개입해야 했던 번거로움이 구체적으로 어떠셨나요?"
        qa_records.append({
            "turn_id": turn_id,
            "question_id": "q3",
            "question_type": "follow_up",
            "question_text": q3_follow,
            "answer_ko": p["answers"]["q3_follow"]["ko"],
            "answer_en": p["answers"]["q3_follow"]["en"],
            "started_at": ts(4, 25),
            "ended_at": ts(4, 55),
            "ai_rationale": "수동 개입 및 컨텍스트 단절 문제에 대한 실제 작업 충격도를 심층 확인.",
            "observer_instruction_id": None
        })
        turn_id += 1

        # Turn 7: Closing Q4
        q4_text = parsed.questions[3].text
        qa_records.append({
            "turn_id": turn_id,
            "question_id": "q4",
            "question_type": "main",
            "question_text": q4_text,
            "answer_ko": p["answers"]["q4"]["ko"],
            "answer_en": p["answers"]["q4"]["en"],
            "started_at": ts(5, 0),
            "ended_at": ts(5, 30),
            "ai_rationale": "인터뷰 마무리 질문으로 향후 OpenAI 터미널 툴에 가장 바라는 핵심 기능 요구사항 수집.",
            "observer_instruction_id": None
        })

        interview_doc = {
            "id": p["id"],
            "type": "interview",
            "project_id": project_id,
            "interviewee_name": p["name"].split(" (")[0],
            "interviewee_email": p["email"],
            "status": "completed",
            "started_at": ts(1, 0),
            "ended_at": ts(5, 35),
            "duration_seconds": 275,
            "video_recording_url": f"https://staiitvteam2.blob.core.windows.net/recordings/{p['id']}/full_video.mp4",
            "individual_report_url": f"https://staiitvteam2.blob.core.windows.net/reports/{p['id']}/interview_summary.pdf",
            "summary": p["summary"],
            "key_insights": p["key_insights"],
            "sentiment_score": p["sentiment"],
            "qa_records": qa_records,
            "observer_instructions": [
                {
                    "id": f"ins_{idx}_01",
                    "text": p["pm_instruction"]["text"],
                    "created_at": ts(2, 46),
                    "applied_at": ts(2, 50),
                    "applied_turn": 4
                }
            ]
        }
        results.append(interview_doc)

    output_file = Path("backend/dummy_data/interview_results_dummy_3cases.json")
    output_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"🎉 영문 실시간 번역본(answer_en) 및 타임스탬프가 완벽 포함된 더미 데이터 생성 완료!")
    print(f"📁 저장 경로: {output_file}")

if __name__ == "__main__":
    asyncio.run(run_simulation_with_translations())
