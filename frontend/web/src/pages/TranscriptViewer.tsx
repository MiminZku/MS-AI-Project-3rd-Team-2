import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, DownloadSimple, FileText, VideoCamera, Warning } from "@phosphor-icons/react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  clientDownloadHeaders,
  clientRecordingDownloadUrl,
  clientTranscriptDownloadUrl,
  fetchClientTranscript,
} from "../lib/clientProjectApi";
import { loadClientProjectGrant } from "../lib/clientProjectGrant";
import {
  adminHeaders,
  downloadFile,
  fetchSessionTranscript,
  recordingDownloadUrl,
  transcriptDownloadUrl,
  type TranscriptTurn,
} from "../lib/researchApi";

function formatTime(value: string): string {
  return new Date(value).toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * 인터뷰 기록을 참관자 대시보드처럼 채팅 형식으로 보여주는 페이지.
 *
 * PM(관리자 헤더)과 클라이언트(Project Access 토큰) 양쪽에서 열 수 있다.
 * 클라이언트 권한이 저장돼 있으면 그 경로를 우선한다.
 */
export default function TranscriptViewer() {
  const { projectId = "", sessionId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const participantLabel = searchParams.get("title") ?? "";

  const grant = loadClientProjectGrant();
  const asClient = Boolean(grant && grant.projectId === projectId);

  const [turns, setTurns] = useState<TranscriptTurn[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyDownload, setBusyDownload] = useState("");
  const [showTranslation, setShowTranslation] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");

    const request =
      asClient && grant
        ? fetchClientTranscript(projectId, sessionId, grant.accessToken)
        : fetchSessionTranscript(sessionId);

    request
      .then((loaded) => {
        if (!cancelled) setTurns(loaded);
      })
      .catch(() => {
        if (!cancelled) setError("인터뷰 기록을 불러오지 못했습니다.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [asClient, grant?.accessToken, projectId, sessionId]);

  const runDownload = useCallback(
    async (key: string, url: string, headers: HeadersInit) => {
      setBusyDownload(key);
      setError("");
      try {
        await downloadFile(url, headers);
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : "다운로드에 실패했습니다.");
      } finally {
        setBusyDownload("");
      }
    },
    [],
  );

  const downloadTargets = useMemo(() => {
    if (asClient && grant) {
      return {
        headers: clientDownloadHeaders(grant.accessToken),
        transcript: clientTranscriptDownloadUrl(projectId, sessionId),
        recording: clientRecordingDownloadUrl(projectId, sessionId),
      };
    }
    return {
      headers: adminHeaders(),
      transcript: transcriptDownloadUrl(sessionId),
      recording: recordingDownloadUrl(sessionId),
    };
  }, [asClient, grant?.accessToken, projectId, sessionId]);

  const hasTranslation = useMemo(
    () => turns.some((turn) => Boolean(turn.text_en)),
    [turns],
  );

  const backLink = asClient ? `/client/project/${projectId}` : "/downloads";

  return (
    <div className="transcript-viewer">
      <header className="transcript-viewer__head">
        <Link to={backLink} className="transcript-viewer__back">
          <ArrowLeft size={16} weight="bold" />
          목록으로
        </Link>
        <div>
          <p className="research-eyebrow">Interview transcript</p>
          <h1>{participantLabel || "인터뷰 기록"}</h1>
          <small>{turns.length}개 발화</small>
        </div>
        <div className="transcript-viewer__actions">
          {hasTranslation && (
            <button
              type="button"
              className="download-center__btn"
              onClick={() => setShowTranslation((value) => !value)}
            >
              {showTranslation ? "번역 숨기기" : "번역 보기"}
            </button>
          )}
          <button
            type="button"
            className="download-center__btn"
            disabled={busyDownload === "transcript"}
            onClick={() =>
              void runDownload("transcript", downloadTargets.transcript, downloadTargets.headers)
            }
          >
            <FileText size={15} weight="bold" />
            {busyDownload === "transcript" ? "받는 중…" : "기록 다운로드"}
          </button>
          <button
            type="button"
            className="download-center__btn download-center__btn--primary"
            disabled={busyDownload === "recording"}
            onClick={() =>
              void runDownload("recording", downloadTargets.recording, downloadTargets.headers)
            }
          >
            <VideoCamera size={15} weight="bold" />
            {busyDownload === "recording" ? "받는 중…" : "영상 다운로드"}
          </button>
        </div>
      </header>

      {error && (
        <p className="download-center__error" role="alert">
          <Warning size={16} weight="fill" />
          {error}
        </p>
      )}

      <main className="transcript-chat">
        {loading ? (
          <p className="download-center__empty">기록을 불러오는 중입니다…</p>
        ) : turns.length === 0 ? (
          <p className="download-center__empty">아직 기록된 대화가 없습니다.</p>
        ) : (
          turns.map((turn) => {
            const isInterviewer = turn.speaker === "assistant";
            return (
              <div
                key={turn.index}
                className={`transcript-bubble-row ${isInterviewer ? "left" : "right"}`}
              >
                <div className="transcript-bubble">
                  <div className="transcript-bubble__meta">
                    <strong>{isInterviewer ? "AI 진행자" : "응답자"}</strong>
                    <time>{formatTime(turn.created_at)}</time>
                  </div>
                  <p className="transcript-bubble__text">{turn.text}</p>
                  {showTranslation && turn.text_en && (
                    <p className="transcript-bubble__translation">{turn.text_en}</p>
                  )}
                </div>
              </div>
            );
          })
        )}
      </main>

      <footer className="transcript-viewer__footer">
        <DownloadSimple size={14} />
        문서(.docx)와 녹화 영상은 위 버튼으로 내려받을 수 있습니다.
      </footer>
    </div>
  );
}
