# Observer-controlled interview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the PM explicitly start and end an interview, record the interviewee's remote ACS stream, and upload the recording to the requested endpoint.

**Architecture:** Move the session start transition out of the interviewee WebSocket handler into a protected session route. Let `VideoSubscriber` expose the ACS raw `MediaStream` to `Monitor`, where a small recorder hook owns chunk collection and multipart upload. Keep the recording persistence boundary in the backend route so Azure Blob and local fallback details remain server-side.

**Tech Stack:** React 18, TypeScript, MediaRecorder, Azure Communication Calling SDK, FastAPI, Azure Blob Storage SDK (optional), pytest.

## Global Constraints

- Do not add a frontend recording dependency; use the browser `MediaRecorder` API.
- Upload field name is `file`; endpoint is `POST /api/sessions/{session_id}/recording`.
- Azure path is `recordings/{session_id}/recording.webm`; local fallback must work without Azure credentials.
- Keep the interviewee waiting until the PM starts the session.
- Do not overlay partial transcripts on the video.

---

### Task 1: Explicit session lifecycle route

**Files:**
- Modify: `backend/app/api/routes/sessions.py`
- Modify: `backend/app/api/ws/interview.py`
- Modify: `backend/app/services/orchestrator.py`
- Test: `backend/tests/test_interview_flow.py`

**Interfaces:**
- Produces `POST /api/sessions/{session_id}/start -> Session`.
- Produces a `session.started` observer message and `session.state` message to the interviewee.

- [ ] **Step 1: Write failing lifecycle tests**

```python
def test_interviewee_join_waits_for_pm_start(client):
    session_id = _create_session(client)
    with client.websocket_connect(f"/ws/interview/{session_id}") as interviewee:
        assert interviewee.receive_json()["session"]["status"] == "created"
        response = client.post(f"/api/sessions/{session_id}/start")
        assert response.status_code == 200
        assert response.json()["status"] == "running"
        assert interviewee.receive_json()["session"]["status"] == "running"
```

- [ ] **Step 2: Run the lifecycle test**

Run: `pytest backend/tests/test_interview_flow.py -q`

Expected: FAIL because the WebSocket currently starts the session and no start route exists.

- [ ] **Step 3: Implement the route and notifications**

```python
@router.post("/{session_id}/start", response_model=Session)
async def start_session(session: Session = Depends(load_session)) -> Session:
    started = await orchestrator.start_session_if_needed(session)
    await manager.broadcast_to_observers(
        started.id, server_message("session.started", session=started.model_dump(mode="json"))
    )
    await manager.send_to_interviewee(
        started.id, server_message("session.state", session={"id": started.id, "title": started.title, "status": started.status})
    )
    return started
```

Remove `start_session_if_needed` from `interview_ws`; it only connects and reports the current status. Make `start_session_if_needed` return an ended session unchanged and start the timekeeper only on the created-to-running transition.

- [ ] **Step 4: Run backend lifecycle tests**

Run: `pytest backend/tests/test_interview_flow.py -q`

Expected: PASS.

### Task 2: Recording upload endpoint and persistence

**Files:**
- Modify: `backend/app/api/routes/sessions.py`
- Modify: `backend/app/core/config.py`
- Create: `backend/app/services/recordings.py`
- Test: `backend/tests/test_recordings.py`

**Interfaces:**
- Consumes multipart field `file`.
- Produces `RecordingUploadResponse(session_id, video_recording_url, size_bytes, status)`.

- [ ] **Step 1: Write failing upload tests**

```python
def test_recording_upload_uses_local_fallback(client):
    session_id = _create_session(client)
    response = client.post(
        f"/api/sessions/{session_id}/recording",
        files={"file": ("recording.webm", b"webm-data", "video/webm")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == session_id
    assert body["size_bytes"] == len(b"webm-data")
    assert body["status"] == "uploaded"
```

- [ ] **Step 2: Run recording tests**

Run: `pytest backend/tests/test_recordings.py -q`

Expected: FAIL because no route exists.

- [ ] **Step 3: Implement storage service and route**

Use `UploadFile`/`File`, reject an empty body and a non-`video/` content type with HTTP 422, and save the exact byte payload. Read `AZURE_STORAGE_CONNECTION_STRING` and `AZURE_STORAGE_RECORDINGS_CONTAINER` from settings; when configured upload through `BlobServiceClient` with overwrite enabled, otherwise write under `backend/data/recordings/<session_id>/recording.webm` and return a local recording URL.

- [ ] **Step 4: Run recording tests**

Run: `pytest backend/tests/test_recordings.py -q`

Expected: PASS.

### Task 3: Recorder integration and controlled controls

**Files:**
- Modify: `frontend/dashboard/src/api.ts`
- Modify: `frontend/dashboard/src/App.tsx`
- Modify: `frontend/dashboard/src/components/Monitor.tsx`
- Modify: `frontend/dashboard/src/components/VideoSubscriber.tsx`
- Create: `frontend/dashboard/src/hooks/useRemoteRecording.ts`

**Interfaces:**
- `VideoSubscriber` accepts `onStreamReady?: (stream: MediaStream | null) => void`.
- `useRemoteRecording()` returns `start(stream)`, `stopAndUpload(sessionId)`, `isRecording`, and `error`.
- API functions are `startSession(sessionId)` and `uploadRecording(sessionId, blob)`.

- [ ] **Step 1: Implement API and hook interfaces**

```ts
export async function uploadRecording(sessionId: string, blob: Blob) {
  const body = new FormData();
  body.append("file", blob, `session_${sessionId}.webm`);
  const response = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}/recording`, {
    method: "POST", headers: adminHeadersWithoutContentType(), body,
  });
  if (!response.ok) throw new Error(`녹화 업로드 실패 (${response.status})`);
  return response.json();
}
```

Record in one-second chunks, resolve `stopAndUpload` only from `onstop`, clear the recorder after success or failure, and never issue an upload without chunks.

- [ ] **Step 2: Wire stream, start, and end state**

Call `await remoteVideoStream.getMediaStream()` in `VideoSubscriber` once availability is true; pass the result upward and clear it on disposal. On a successful PM start request start recording if the stream is available. When ending, await recording upload before `endSession`; always call `endSession` if the recorder never started. Remove the separate 녹화 시작 top-bar button.

- [ ] **Step 3: Verify the dashboard build**

Run: `npm run build`

Working directory: `frontend/dashboard`

Expected: TypeScript type-check and Vite production build succeed.

### Task 4: Menu dismissal and transcript layout

**Files:**
- Modify: `frontend/dashboard/src/components/Monitor.tsx`
- Modify: `frontend/dashboard/src/styles.css`

**Interfaces:**
- The drawer state belongs to `Monitor` and is closed by outside pointer press and Escape.

- [ ] **Step 1: Make the kebab drawer click-controlled**

Attach a ref to the wrapper and document listeners while open:

```ts
if (event.key === "Escape") setDrawerPinned(false);
if (!drawerRef.current?.contains(event.target as Node)) setDrawerPinned(false);
```

Remove hover/focus CSS selectors so the three-dot button is the sole opener and toggler.

- [ ] **Step 2: Move live transcript out of video**

Render Korean/English partials immediately after `.rs-figure` in a semantic `aria-live="polite"` transcript element. Remove its absolute positioning and style it as a compact card beneath the frame.

- [ ] **Step 3: Rebuild the dashboard**

Run: `npm run build`

Working directory: `frontend/dashboard`

Expected: PASS.

### Task 5: Full verification

**Files:**
- Verify only.

- [ ] **Step 1: Run all backend tests**

Run: `pytest backend/tests -q`

Expected: PASS.

- [ ] **Step 2: Run the dashboard build**

Run: `npm run build`

Working directory: `frontend/dashboard`

Expected: PASS.

- [ ] **Step 3: Review the diff**

Run: `git diff --check && git diff -- backend frontend/dashboard`

Expected: no whitespace errors and only lifecycle, recording, drawer, and transcript changes.

## Plan self-review

- Spec coverage: Tasks 1-3 cover controlled lifecycle, automatic recording, endpoint upload, Azure/local storage, and error handling. Task 4 covers the menu and transcript layout.
- Placeholder scan: no deferred requirements are left in the plan.
- Type consistency: `startSession`, `uploadRecording`, `onStreamReady`, and the recording hook signatures are used consistently by their producing and consuming tasks.
