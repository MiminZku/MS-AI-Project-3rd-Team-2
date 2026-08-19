import { useState } from "react";
import { createSession, fetchSession } from "../api";
import { DEMO_SESSION } from "../demoData";
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
  const [duration, setDuration] = useState(60);
  const [language, setLanguage] = useState("ko");
  const [joinId, setJoinId] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<{ session: Session; intervieweeUrl: string } | null>(null);
  const [copied, setCopied] = useState(false);

  const copyLink = async (url: string) => {
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

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
        <header className="p-head">
          <div>
            <h2>목데이터 미리보기</h2>
            <div className="sub">백엔드 연결 없이 화면만 확인</div>
          </div>
        </header>
        <div className="p-body">
          <p className="muted small" style={{ margin: "0 0 12px" }}>
            백엔드가 아직 준비되지 않았을 때, 목데이터로 관리자 대시보드 화면만 확인합니다.
          </p>
          <button className="ghost" onClick={() => onCreated(DEMO_SESSION, "")}>
            데모로 미리보기
          </button>
        </div>
      </section>

      <section className="panel">
        <header className="p-head">
          <div>
            <h2>새 인터뷰 세션</h2>
            <div className="sub">PM만 접근 · 생성 후 링크가 발급됩니다</div>
          </div>
        </header>
        <div className="p-body">
        {!created ? (
          <>
            <label>
              세션 이름
              <input value={title} onChange={(event) => setTitle(event.target.value)} />
            </label>

            <div className="two">
              <label>
                인터뷰 시간
                <p className="desc">종료 예정 시각 계산에 사용됩니다</p>
                <select value={duration} onChange={(event) => setDuration(Number(event.target.value))}>
                  <option value={30}>30분</option>
                  <option value={60}>60분</option>
                  <option value={90}>90분</option>
                </select>
              </label>

              <label>
                통역 언어
                <p className="desc">응답자 발화를 이 언어로 통역해 백룸에 전달합니다 (준비 중)</p>
                <select value={language} onChange={(event) => setLanguage(event.target.value)}>
                  <option value="ko">한국어</option>
                  <option value="en">English</option>
                  <option value="ja">日本語</option>
                </select>
              </label>
            </div>

            <label>
              질문 리스트
              <p className="desc">
                질문은 세션 생성 후 백룸 콘솔의 [＋ 질문 편집]에서 입력합니다. 인터뷰 진행 중에도 수정할 수
                있습니다.
              </p>
            </label>

            <div className="form-actions">
              <button className="ghost" disabled title="곧 지원 예정">
                임시 저장
              </button>
              <button
                disabled={busy}
                onClick={() =>
                  run(async () => {
                    const result = await createSession({
                      title,
                      duration_minutes: duration,
                      question_script: SAMPLE_SCRIPT,
                    });
                    setCreated({ session: result.session, intervieweeUrl: result.interviewee_url });
                  })
                }
              >
                세션 생성
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="linkrow">
              <span className="lk-tag">인터뷰이</span>
              <code>{created.intervieweeUrl}</code>
              <button type="button" className="btn-sm" onClick={() => copyLink(created.intervieweeUrl)}>
                {copied ? "복사됨" : "복사"}
              </button>
              <span className="desc" style={{ width: "100%", margin: "4px 0 0" }}>
                일회용 · 1회 입장 후 만료
              </span>
            </div>
            <div className="linkrow">
              <span className="lk-tag">클라이언트</span>
              <code>준비 중</code>
              <button type="button" className="btn-sm" disabled title="곧 지원 예정">
                복사
              </button>
              <span className="desc" style={{ width: "100%", margin: "4px 0 0" }}>
                관찰 전용 · 세션 종료 시 만료 (곧 지원 예정)
              </span>
            </div>
            <div className="form-actions">
              <button onClick={() => onCreated(created.session, created.intervieweeUrl)}>백룸 열기 →</button>
            </div>
          </>
        )}
        </div>
      </section>

      <section className="panel">
        <header className="p-head">
          <div>
            <h2>기존 세션 열기</h2>
            <div className="sub">세션 ID로 다시 접속</div>
          </div>
        </header>
        <div className="p-body">
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
        </div>
      </section>

      {error && <p className="error">{error}</p>}
    </main>
  );
}
