"""리포트 배관(트리거→저장→조회) 스모크 테스트.

report/generator.py의 실제 내용(data 안에 뭘 채우는지)은 검증하지 않는다 —
그건 담당자가 설계할 몫이라 여기서 형식을 강제하지 않는다.
"""

import asyncio

SCRIPT = "1. 배달앱을 얼마나 자주 쓰시나요?\n2. 최소주문금액에 대해 어떻게 느끼시나요?"


def _create_session(client) -> str:
    response = client.post(
        "/api/sessions",
        json={"title": "리포트 테스트", "duration_minutes": 20, "question_script": SCRIPT},
    )
    return response.json()["session"]["id"]


def test_세션_종료시_리포트가_비동기로_생성되고_조회된다(client):
    session_id = _create_session(client)

    with client.websocket_connect(f"/ws/interview/{session_id}") as interviewee:
        assert interviewee.receive_json()["type"] == "session.state"
        start_response = client.post(f"/api/sessions/{session_id}/start")
        assert start_response.status_code == 200
        assert interviewee.receive_json()["session"]["status"] == "running"
        interviewee.send_json({"type": "utterance", "text": "일주일에 세 번 정도 씁니다."})
        assert interviewee.receive_json()["type"] == "assistant.question"

    end_response = client.post(f"/api/sessions/{session_id}/end")
    assert end_response.status_code == 200

    # 백그라운드 태스크(fire-and-forget)가 끝날 시간을 준다
    asyncio.run(asyncio.sleep(0.05))

    report_response = client.get(f"/api/sessions/{session_id}/report")
    assert report_response.status_code == 200
    report = report_response.json()
    assert report["session_id"] == session_id
    assert "data" in report
