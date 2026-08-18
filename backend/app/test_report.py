import asyncio
import json

from app.schemas.session import Instruction, Session, Turn
from app.services.report.generator import generate


async def main():

    # 더미 인터뷰 JSON 읽기
    with open(
        "app/ai-interview-report/dummy_interview.json",
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    # JSON → 우리 백엔드 모델로 변환
    session = Session.model_validate(data["session"])

    transcript = [
        Turn.model_validate(turn)
        for turn in data["transcript"]
    ]

    instructions = [
        Instruction.model_validate(instruction)
        for instruction in data.get("instructions", [])
    ]

    # 실제 generator.py 실행
    report = await generate(
        session=session,
        transcript=transcript,
        instructions=instructions,
    )

    # 결과 저장
    with open(
        "app/ai-interview-report/participant_report.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report.model_dump(mode="json"),
            file,
            ensure_ascii=False,
            indent=2,
        )

    print("✅ participant_report.json 생성 완료!")
    print("세션 ID:", report.session_id)


asyncio.run(main())