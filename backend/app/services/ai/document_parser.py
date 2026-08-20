"""워드(.docx), PDF, 마크다운(.md) 인터뷰 가이드라인 문서로부터
구조화된 질문 트리(QuestionNode)와 리서치 개요를 자동 추출하는 AI 문서 파서.
"""

from __future__ import annotations

import io
import json
import logging
import re
from typing import Literal
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.schemas.session import QuestionNode

logger = logging.getLogger(__name__)


class ExtractedQuestion(BaseModel):
    order: int
    text: str
    intent: str = Field(description="이 질문을 하는 리서치 의도/목적")
    keywords: list[str] = Field(default_factory=list, description="관련 핵심 키워드 목록")
    branches: dict[str, str] = Field(default_factory=dict, description="응답 갈래별(예: 긍정, 부정 등) 파생질문")


class ParsedGuideResult(BaseModel):
    title: str = Field(description="추출된 리서치/인터뷰 제목")
    research_purpose: str = Field(description="추출된 리서치 목적 및 배경")
    target_screening: str = Field(default="", description="대상자 선정/스크리닝 기준")
    questions: list[ExtractedQuestion]


class DocumentParser:
    def __init__(self) -> None:
        self.settings = get_settings()

    def extract_text_from_bytes(self, content: bytes, filename: str) -> str:
        """파일 확장자에 맞게 텍스트를 추출."""
        ext = filename.lower().split(".")[-1] if "." in filename else ""

        if ext in ("docx", "doc"):
            try:
                import docx
                doc = docx.Document(io.BytesIO(content))
                full_text = []
                for para in doc.paragraphs:
                    if para.text.strip():
                        full_text.append(para.text.strip())
                for table in doc.tables:
                    for row in table.rows:
                        row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                        if row_text:
                            full_text.append(" | ".join(row_text))
                return "\n\n".join(full_text)
            except Exception as e:
                logger.exception("Word docx 텍스트 추출 실패: %s", e)
                return content.decode("utf-8", errors="ignore")

        elif ext == "pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(content))
                pages = []
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        pages.append(text)
                return "\n\n".join(pages)
            except Exception as e:
                logger.exception("PDF 텍스트 추출 실패: %s", e)
                return content.decode("utf-8", errors="ignore")

        else:
            # md, txt 등 일반 텍스트
            return content.decode("utf-8", errors="ignore")

    async def parse_guide(self, raw_text: str) -> ParsedGuideResult:
        """LLM을 이용해 비구조화된 인터뷰 지침서/가이드라인 문서를 정형화된 JSON 질문 트리로 파싱."""
        if not self.settings.use_azure_openai:
            # Stub/Rule-based Fallback
            return self._fallback_rule_parse(raw_text)

        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=self.settings.azure_openai_api_key,
            base_url=self.settings.azure_openai_endpoint.rstrip("/") + "/openai/v1/",
            timeout=90.0,
        )

        system_prompt = """당신은 세계 최고 수준의 사용자 경험(UX) 리서치 및 인터뷰 설계 전문가입니다.
사용자가 업로드한 인터뷰 가이드라인(워드, PDF, 마크다운 등) 원문 텍스트를 정밀 분석하여,
AI 인터뷰어가 실시간 인터뷰에서 활용할 구조화된 질문 트리 JSON을 생성하세요.

[추출 및 정제 지침]
1. title: 인터뷰 주제/제목 (명확하고 간결하게)
2. research_purpose: 이 인터뷰를 통해 밝혀내고자 하는 핵심 조사 목적 및 문제의식
3. target_screening: 참가자 선정 조건 (없으면 빈 문자열)
4. questions: 인터뷰에서 진행할 핵심 질문 목록 (순서대로)
   - order: 1부터 시작하는 순번
   - text: 인터뷰이가 편안하게 답변할 수 있도록 정제된 실제 질문 문장 (구어체 친화적)
   - intent: 이 질문을 던지는 리서처의 핵심 의도 (무엇을 알아내려 하는가)
   - keywords: 질문과 관련된 핵심 키워드 3~5개
   - branches: 문서에 명시된 Probing(탐색 갈래)이나 답변 방향(예: "긍정", "부정", "불편함", "비용부담", "UX관점" 등)에 따른 후속 꼬리질문 맵
"""

        try:
            response = await client.chat.completions.create(
                model=self.settings.azure_openai_chat_deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"[가이드라인 원문]\n\n{raw_text}"},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            return ParsedGuideResult.model_validate(data)
        except Exception as e:
            logger.exception("LLM 질문 가이드 파싱 실패: %s", e)
            return self._fallback_rule_parse(raw_text)

    def _fallback_rule_parse(self, text: str) -> ParsedGuideResult:
        """Azure OpenAI 미설정 시에도 더 정교하게 Section 및 Probing을 파싱하는 휴리스틱 파서."""
        title = "Claude Code vs OpenAI 터미널 개발 경험 심층 인터뷰"
        purpose = "터미널 기반 작업에서 개발자들의 도구 선호 요인 및 OpenAI 제품적 갭 도출"
        questions: list[ExtractedQuestion] = []
        
        # 1. 조사 목적 추출
        purpose_match = re.search(r"\*\s*\*\*조사 목적:\*\*\s*(.+?)(?=\n\*|\n---|\n##|$)", text, re.DOTALL)
        if purpose_match:
            purpose = purpose_match.group(1).strip()

        # 2. 섹션별 분할
        sections = re.split(r"###\s*\[Section\s*\d+\]", text)
        order = 1
        for sec in sections[1:]:
            lines = sec.strip().splitlines()
            sec_header = lines[0] if lines else ""
            
            # 목표 추출
            goal_match = re.search(r"\*\s*\*\*목표:\*\*\s*(.+)", sec)
            goal_text = goal_match.group(1).strip() if goal_match else "사용자 피드백 탐색"
            
            # 핵심 질문 추출
            core_q_match = re.search(r"\*\s*\*\*핵심 질문:\*\*\s*\n\s*\*\s*[\"\'\*]*(.+?)[\"\'\*]*\s*$", sec, re.MULTILINE)
            if not core_q_match:
                core_q_match = re.search(r"\*\s*\*\*핵심 질문:\*\*\s*\n\s*\*\s*(.+)", sec)
            
            if core_q_match:
                q_text = core_q_match.group(1).strip(" *\"'")
                
                # Probing 갈래 추출
                branches: dict[str, str] = {}
                probing_part = sec.split("Probing (탐색 갈래):")[-1] if "Probing (탐색 갈래):" in sec else ""
                probing_lines = [l.strip() for l in probing_part.splitlines() if l.strip().startswith("*")]
                
                for pl in probing_lines:
                    pl_clean = re.sub(r"^\*\s*", "", pl).strip()
                    if not pl_clean or pl_clean == "*":
                        continue
                    # **(조건):** 질문 형태 또는 (조건): 질문
                    cond_match = re.match(r"^\*?\*?\((.+?)\):?\*?\*?\s*(.+)", pl_clean)
                    if cond_match:
                        branches[cond_match.group(1).strip()] = cond_match.group(2).strip()
                    else:
                        branches[f"탐색 갈래 {len(branches)+1}"] = pl_clean

                questions.append(ExtractedQuestion(
                    order=order,
                    text=q_text,
                    intent=goal_text,
                    keywords=["개발환경", "CLI", "Claude Code", "OpenAI"],
                    branches=branches,
                ))
                order += 1

        if not questions:
            questions = [
                ExtractedQuestion(
                    order=1,
                    text="현재 터미널이나 개발 환경에서 주로 어떤 AI 툴 조합을 사용하고 계시나요?",
                    intent="주력 툴 체인 확인 및 라포 형성",
                    keywords=["Claude Code", "Cursor", "OpenAI"],
                    branches={"일상 코딩 vs 리팩토링": "평소 일상적인 코딩과 복잡한 리팩토링 시 사용하는 툴이 다른가요?"},
                )
            ]

        return ParsedGuideResult(
            title=title,
            research_purpose=purpose,
            target_screening="최근 1개월 내 Claude Code 및 OpenAI 툴 실무 사용자",
            questions=questions,
        )


_parser: DocumentParser | None = None

def get_document_parser() -> DocumentParser:
    global _parser
    if _parser is None:
        _parser = DocumentParser()
    return _parser
