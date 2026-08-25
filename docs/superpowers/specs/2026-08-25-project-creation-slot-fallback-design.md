# Local project creation slot fallback

## Goal

Allow PMs to create a project and interview session in the local workspace when the Azure OpenAI Information Slot request is unavailable or fails.

## Existing behavior

`POST /api/projects` parses the question script and then awaits `SlotGenerator.generate`. A failed or stalled Azure OpenAI request prevents the project from being saved, so PMs cannot create a session or open the Respondent flow.

The guide-upload endpoint already treats Information Slot generation as an enhancement: it logs the error, uses an empty slot list, and still persists the project.

## Approved design

Apply that same resilience boundary to the normal project creation endpoint only.

1. Parse and validate the question script as today. Invalid or empty scripts still return HTTP 400.
2. Attempt Information Slot generation.
3. If generation raises an exception, log a warning and continue with `information_slots=[]`.
4. Generate the Project Access ID, save the project, and return HTTP 201 as today.

No Project, Session, access-ID, question, AI interview, or report schema changes are needed. Azure-generated slots are retained whenever Azure responds successfully.

## Verification

Add a regression test where the slot generator raises an exception and assert that `POST /api/projects` returns 201 with an empty `information_slots` list. Run the focused test suite, full backend tests, production builds, and create a local project/session against the local API before opening its Respondent URL.
