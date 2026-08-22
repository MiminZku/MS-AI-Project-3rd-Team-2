import asyncio
from pathlib import Path
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'backend')

from app.services.ai.document_parser import get_document_parser
from app.services.ai.llm import get_question_generator
from app.schemas.session import Session, QuestionNode, Turn, Instruction

async def test_simulation():
    # 1. 가이드라인 파싱
    md_path = Path('backend/dummy_data/question_list_dummy.md')
    parser = get_document_parser()
    text = parser.extract_text_from_bytes(md_path.read_bytes(), 'question_list_dummy.md')
    parsed = await parser.parse_guide(text)
    
    questions = [
        QuestionNode(
            id=f'q{q.order}',
            order=q.order,
            text=q.text,
            branches=q.branches,
        )
        for q in parsed.questions
    ]
    
    session = Session(
        title=parsed.title,
        duration_minutes=10,
        questions=questions,
        current_question_index=0
    )
    
    print('==================================================')
    print(f'🚀 [인터뷰 시작] 주제: {session.title}')
    print(f'총 질문 수: {len(session.questions)}개')
    print('==================================================')
    
    # 1턴: 첫 질문
    print(f'\n🤖 [AI 인터뷰어 - 질문 1]: {session.questions[0].text}')
    
    # 2턴: 사용자 답변 1
    user_ans_1 = '평소에는 VS Code에서 Cursor를 주로 쓰고, 터미널에서는 간단한 작업은 Claude Code를 켜서 씁니다. 복잡한 디버깅할 때는 터미널에서 Claude Code를 켜게 되더라고요.'
    print(f'\n👤 [인터뷰이 답변 1]: {user_ans_1}')
    
    transcript = [
        Turn(index=0, speaker='assistant', text=session.questions[0].text),
        Turn(index=1, speaker='interviewee', text=user_ans_1),
    ]
    
    # 3턴: AI 다음 질문 생성 (꼬리질문 또는 다음 메인)
    llm = get_question_generator()
    gen_q1 = await llm.generate(session, transcript, instruction=None)
    print(f'\n🤖 [AI 인터뷰어 - 후속 질문]: {gen_q1.text}')
    print(f'   🔍 [판단 근거 / Rationale]: {gen_q1.rationale}')
    
    # 4턴: 참관자(PM) 실시간 개입 지시 발생!
    pm_instruction = Instruction(
        session_id=session.id,
        text='복잡한 디버깅할 때 Claude Code가 구체적으로 어떤 점에서 더 편했는지 에러 로그 처리 관점에서 물어봐줘'
    )
    print(f'\n🚨 [참관자(PM) 실시간 지시]: "{pm_instruction.text}"')
    
    user_ans_2 = 'Cursor는 가끔 전체 파일을 덮어써서 망칠 때가 있는데, Claude Code는 diff를 보여주면서 차근차근 고쳐줘서 신뢰가 가요.'
    transcript.extend([
        Turn(index=2, speaker='assistant', text=gen_q1.text),
        Turn(index=3, speaker='interviewee', text=user_ans_2),
    ])
    
    gen_q2 = await llm.generate(session, transcript, instruction=pm_instruction)
    print(f'\n🤖 [AI 인터뷰어 - 지시 반영 꼬리질문]: {gen_q2.text}')
    print(f'   🔍 [판단 근거 / Rationale]: {gen_q2.rationale}')

if __name__ == '__main__':
    asyncio.run(test_simulation())
