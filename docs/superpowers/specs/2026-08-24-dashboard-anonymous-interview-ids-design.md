# Dashboard Anonymous Interview IDs

## Goal

Prevent participant real names from being entered or displayed in the observer dashboard while preserving the existing session API contract.

## Scope

- Change the PM new-session field from a session name to a required participant ID.
- Accept only 3–40 uppercase letters, digits, and hyphens (for example, `INT-001`).
- Send that ID through the existing `title` field required by `POST /api/sessions`.
- Display a safe value derived from the immutable server session ID in the existing-session list, rather than `session.title`.
- Keep project titles unchanged: they describe research topics, not interview participants.

## Design

The creation form stores `participantId` in component state. The submit path validates its normalized value before making an API call. It sends the ID as `title`, avoiding an API schema change and ensuring that all newly created sessions have an anonymous identifier.

A small pure formatter returns `인터뷰 · <session-id>` for any existing session. The session list always uses that formatter, so historical `title` values cannot reveal a participant name. The full ID is used rather than a truncated value because it is the unique server lookup identifier.

## Errors and Accessibility

Invalid or empty IDs are blocked before the request, with an inline Korean error that explains the permitted format. The field's label, help text, placeholder, and validation message do not contain name-like examples.

## Tests

Add focused component tests that assert the form uses the participant-ID label and anonymous placeholder, and that the old real-name example and raw session title are absent from static markup. Add pure formatter tests for stable ID-based labels.

## Non-goals

- Changing the backend request schema.
- Migrating historical database records.
- Changing project-title display.
