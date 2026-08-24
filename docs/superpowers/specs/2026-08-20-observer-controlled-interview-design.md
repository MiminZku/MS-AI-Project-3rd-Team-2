# Observer-controlled interview and recording design

## Scope

The observer dashboard controls the interview lifecycle. An interviewee may join the WebSocket and ACS call while the session remains `created`; only the PM's **인터뷰 시작** action moves it to `running`. The active session exposes **인터뷰 종료** and uploads the observer-recorded remote stream before ending the session.

## Lifecycle

1. The interviewee connection announces presence but does not call `start_session_if_needed`.
2. `POST /api/sessions/{session_id}/start` starts a created session, records `started_at`, starts the timekeeper, notifies observers, and tells the connected interviewee that the session is now running.
3. The dashboard starts a `MediaRecorder` after the remote ACS `MediaStream` is supplied by `VideoSubscriber`.
4. On end, the dashboard stops the recorder, waits for its final Blob, POSTs it as `file` to `/api/sessions/{session_id}/recording`, and then ends the session. A failed upload is shown to the PM and does not silently discard the recording.
5. The recording API writes to Azure Blob Storage at `recordings/{session_id}/recording.webm` when configured; otherwise it writes to `backend/data/recordings/{session_id}/recording.webm` for local development and returns a URL/path plus byte count.

## Dashboard UX

- The disabled start and recording controls are replaced by one enabled **인터뷰 시작** control for a joined PM session. There is no separate 녹화 시작 button.
- Start is disabled while its request is pending or no interviewee is connected. End is disabled while recording upload/session end is pending.
- The status preview controls remain a developer preview only and cannot alter server state.
- The three-dot drawer opens only on click and closes on the next click, Escape, or a pointer press outside it. Hover/focus no longer opens or keeps it open.
- Partial Korean and English transcript text is rendered below the video frame in a dedicated transcript card, never as an overlay.

## Recording compatibility

`VideoSubscriber` obtains the ACS `RemoteVideoStream.getMediaStream()` value and passes it to `Monitor`. `MediaRecorder` prefers `video/webm;codecs=vp9,opus`, then `video/webm`, then the browser default MIME type. If the ACS stream has no audio track, the created recording is video-only; no stream is fabricated or failed upload hidden.

## Errors and verification

The API rejects non-video/empty uploads and recording uploads for unknown sessions. The frontend reports start/end/upload failures, clears a failed recorder cleanly, and always permits retrying a start/end action. Backend tests cover explicit start, an interviewee connection that remains created, and local recording upload. The dashboard TypeScript build validates the UI and recorder interfaces.
