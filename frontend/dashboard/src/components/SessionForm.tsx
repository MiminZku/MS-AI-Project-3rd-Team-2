import { useEffect, useState } from "react";
import { createSession, fetchSession, listSessions } from "../api";
import type { Session } from "../types";

const SAMPLE_SCRIPT = `1. 배달앱을 얼마나 자주 쓰시나요?
2. 최소주문금액에 대해 어떻게 느끼시나요?
   [부담됨] → 그 때문에 주문을 포기한 경험이 있나요?
   [보통]   → 최소주문금액을 맞추려고 더 시킨 적은 있나요?
3. 배달비가 오르면 어떻게 하시나요?`;

const MOCK_PROJECTS = [
  { id: "proj_delivery_ux", label: "배달앱 UX 사용성 조사" },
  { id: "proj_subscription", label: "무료배달 구독제 만족도 조사" },
] as const;

const STATUS_LABEL: Record<Session["status"], string> = {
  created: "대기",
  running: "진행중",
  ended: "종료",
};

interface Props {
  onCreated: (session: Session, intervieweeUrl: string) => void;
}

export default function SessionForm({ onCreated }: Props) {
  const [projectId, setProjectId] = useState("");
  const [duration, setDuration] = useState(60);
  const [language, setLanguage] = useState("ko");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<{ session: Session; intervieweeUrl: string } | null>(null);
  const [copied, setCopied] = useState(false);
  const [sessions, setSessions] = useState<Session[]>([]);

  useEffect(() => {
    listSessions()
      .then(setSessions)
      .catch((cause: unknown) => console.error("세션 목록 조회 실패", cause));
  }, []);

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
            <h2>새 인터뷰 세션</h2>
            <div className="sub">PM만 접근 · 생성 후 링크가 발급됩니다</div>
          </div>
        </header>
        <div className="p-body">
        {!created ? (
          <>
            <label>
              프로젝트
              <p className="desc">실제 프로젝트 연동은 백엔드 준비 중 — 지금은 목업 목록입니다.</p>
              <select value={projectId} onChange={(event) => setProjectId(event.target.value)}>
                <option value="" disabled>
                  프로젝트를 선택하세요
                </option>
                {MOCK_PROJECTS.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.label}
                  </option>
                ))}
              </select>
            </label>

            <div className="two">
              <label>
                인터뷰 시간
                <p className="desc">종료 예정 시각 계산에 사용됩니다</p>
                <select value={duration} onChange={(event) => setDuration(Number(event.target.value))}>
                  <option value={10}>10분</option>
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
              <button
                disabled={busy || !projectId}
                onClick={() =>
                  run(async () => {
                    const project = MOCK_PROJECTS.find((p) => p.id === projectId);
                    const result = await createSession({
                      title: project?.label ?? "제목 없는 인터뷰",
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
            <h2>세션 목록</h2>
            <div className="sub">이미 만든 세션에 다시 들어가기</div>
          </div>
        </header>
        <div className="p-body">
          {sessions.length === 0 ? (
            <p className="muted small">아직 생성된 세션이 없습니다.</p>
          ) : (
            sessions.map((session) => (
              <button
                key={session.id}
                type="button"
                className="link-row"
                style={{ width: "100%", cursor: "pointer", textAlign: "left" }}
                disabled={busy}
                onClick={() =>
                  run(async () => {
                    const result = await fetchSession(session.id);
                    onCreated(result.session, result.interviewee_url);
                  })
                }
              >
                <span className={`badge ${session.status === "running" ? "connected" : ""}`}>
                  {STATUS_LABEL[session.status]}
                </span>
                <code>{session.title}</code>
                <span className="desc" style={{ width: "100%", margin: "4px 0 0" }}>
                  {new Date(session.created_at).toLocaleString("ko-KR")}
                </span>
              </button>
            ))
          )}
        </div>
      </section>

      {error && <p className="error">{error}</p>}
    </main>
  );
}
