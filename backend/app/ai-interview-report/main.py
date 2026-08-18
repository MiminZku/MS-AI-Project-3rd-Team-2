import json


# 1. 원본 인터뷰 JSON 읽기
with open("dummy_interview.json", "r", encoding="utf-8") as file:
    data = json.load(file)


# 2. 기본 정보 가져오기
session = data["session"]
transcript = data["transcript"]
instructions = data["instructions"]


# 3. 응답자 발언만 따로 추출
interviewee_answers = []

for turn in transcript:

    if turn["speaker"] == "interviewee":

        interviewee_answers.append({
            "turn_index": turn["index"],
            "text": turn["text"],
            "created_at": turn["created_at"]
        })


# 4. AI 분석용 데이터 만들기
analysis_input = {

    "session_id": session["id"],

    "research_title": session["title"],

    "duration_minutes": session["duration_minutes"],

    "questions": session["questions"],

    "observer_instructions": instructions,

    "interviewee_answers": interviewee_answers,

    "full_transcript": transcript
}


# 5. 새로운 JSON 파일로 저장
with open(
    "analysis_input.json",
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        analysis_input,
        file,
        ensure_ascii=False,
        indent=2
    )


print("✅ analysis_input.json 생성 완료!")
print()
print("응답자 답변 개수:", len(interviewee_answers))