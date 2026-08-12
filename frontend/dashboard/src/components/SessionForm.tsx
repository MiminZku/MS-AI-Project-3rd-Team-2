import { useState } from "react";
import { createSession, fetchSession } from "../api";
import type { Session } from "../types";

const SAMPLE_SCRIPT = `1. 배달앱을 얼마나 자주 쓰시나요?
2. 최소주문금액에 대해 어떻게 느끼시나요?
   [부담됨] → 그 때문에 주문을 포기한 경험이 있나요?
   [보통]   → 최소주문금액을 맞추려고 더 시킨 적은 있나요?
3. 배달비가 오르면 어떻게 하시나요?`;

interface Props {
  onCreated: (session: Session, intervieweeUrl: string) => void;
}

export default function SessionForm({ onCreated }: Props) {
  const [title, setTitle] = useState("배달앱 사용성 인터뷰");
  const [duration, setDuration] = useState(20);
  const [script, setScript] = useState(SAMPLE_SCRIPT);
  const [joinId, setJoinId] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const run = async (task: () => Promise<void>) => {
    setBusy(true);
    setError("");
    try {
      await task();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="form-page">
      <section className="panel">
        <h2>새 인터뷰 세션</h2>

        <label>
          제목
          <input value={title} onChange={(event) => setTitle(event.target.value)} />
        </label>

        <label>
          예정 시간 (분)
          <input
            type="number"
            min={5}
            max={120}
            value={duration}
            onChange={(event) => setDuration(Number(event.target.value))}
          />
        </label>

        <label>
          질문 리스트
          <textarea
            rows={10}
            value={script}
            onChange={(event) => setScript(event.target.value)}
            spellCheck={false}
          />
          <small className="muted">
            {"번호 = 메인 질문, [조건] → 파생질문 형식으로 분기를 작성합니다."}
          </small>
        </label>

        <button
          disabled={busy}
          onClick={() =>
            run(async () => {
              const result = await createSession({
                title,
                duration_minutes: duration,
                question_script: script,
              });
              onCreated(result.session, result.interviewee_url);
            })
          }
        >
          세션 생성 + 응답자 링크 발급
        </button>
      </section>

      <section className="panel">
        <h2>기존 세션 열기</h2>
        <label>
          세션 ID
          <input
            value={joinId}
            placeholder="ses_..."
            onChange={(event) => setJoinId(event.target.value)}
          />
        </label>
        <button
          className="ghost"
          disabled={busy || !joinId.trim()}
          onClick={() =>
            run(async () => {
              const result = await fetchSession(joinId.trim());
              onCreated(result.session, result.interviewee_url);
            })
          }
        >
          모니터링 시작
        </button>
      </section>

      {error && <p className="error">{error}</p>}
    </main>
  );
}
