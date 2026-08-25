import { useState } from "react";
import { ArrowRight, Key, LockKey, ShieldCheck } from "@phosphor-icons/react";
import { ClientProjectApiError, exchangeClientProjectAccess } from "../lib/clientProjectApi";
import { saveClientProjectGrant } from "../lib/clientProjectGrant";

export default function ClientAccess() {
  const [accessId, setAccessId] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedId = accessId.trim().toUpperCase();
    if (!normalizedId) {
      setError("프로젝트 ID를 입력해주세요.");
      return;
    }

    setError("");
    setIsSubmitting(true);
    try {
      const grant = await exchangeClientProjectAccess(normalizedId);
      saveClientProjectGrant({ projectId: grant.project.id, accessToken: grant.access_token });
      window.location.href = `/dashboard/?project=${encodeURIComponent(grant.project.id)}`;
    } catch (cause) {
      setError(
        cause instanceof ClientProjectApiError && cause.status === 404
          ? "존재하지 않는 프로젝트 ID입니다."
          : "프로젝트에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="client-access-page">
      <section className="client-access-shell" aria-labelledby="client-access-title">
        <div className="client-access-brand"><span>Gromit</span> Client delivery</div>
        <div className="client-access-icon" aria-hidden="true"><Key size={28} weight="duotone" /></div>
        <p className="client-access-eyebrow">PROJECT DELIVERY</p>
        <h1 id="client-access-title">프로젝트 접속</h1>
        <p className="client-access-intro">프로젝트 ID를 입력해주세요</p>
        <p className="client-access-description">PM에게 전달받은 Project Access ID로 해당 조사 결과만 안전하게 확인할 수 있습니다.</p>

        <form className="client-access-form" onSubmit={submit} noValidate>
          <label htmlFor="project-access-id">Project Access ID</label>
          <div className="client-access-input">
            <LockKey size={18} aria-hidden="true" />
            <input
              id="project-access-id"
              name="project-access-id"
              value={accessId}
              onChange={(event) => setAccessId(event.target.value.toUpperCase())}
              placeholder="PRJ-A7F3K9..."
              autoCapitalize="characters"
              autoComplete="off"
              spellCheck={false}
            />
          </div>
          {error && <p className="client-access-error" role="alert">{error}</p>}
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "프로젝트 확인 중..." : "프로젝트 접속"} <ArrowRight size={18} weight="bold" />
          </button>
        </form>

        <p className="client-access-note"><ShieldCheck size={17} weight="fill" /> 입력한 ID와 연결된 프로젝트만 조회됩니다.</p>
      </section>
    </main>
  );
}
