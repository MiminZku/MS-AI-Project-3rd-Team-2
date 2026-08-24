# Client Project Access Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate PM and Client entry flows so a Client can access exactly one research project by a high-entropy Project Access ID, while the backend enforces that project boundary.

**Architecture:** Extend the existing `ResearchStudy` rather than create a new project model. PM creation routes issue and persist a unique `access_id`; a public access exchange validates it and returns a short-lived HMAC-signed project-scoped token. Client-only API routes validate that token against the requested project ID. The web app gets independent `/client/access` and `/client/project/:projectId` pages outside the PM layout, while the dashboard continues to own PM project creation and displays the access ID.

**Tech Stack:** FastAPI, Pydantic, Python standard-library HMAC, React 19, React Router, TypeScript, Vitest, pytest.

## Global Constraints

- Use only localhost for this task; do not run Azure deployment commands.
- Do not run `git commit`, `git push`, create a Pull Request, or change GitHub Actions.
- Keep only PM and Client roles; do not introduce Admin as an application role.
- Preserve existing PM endpoints protected by `X-Admin-Token`.
- Client API responses must not include question scripts, PM settings, full project lists, transcripts, recordings, or observer controls.
- Client project routes must verify both a scoped token and its path project ID.

---

### Task 1: Persist a unique Project Access ID

**Files:**

- Create: `backend/app/services/project_access.py`
- Modify: `backend/app/schemas/study.py`
- Modify: `backend/app/services/store.py`
- Modify: `backend/app/services/cosmos_store.py`
- Modify: `backend/app/api/routes/studies.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_client_project_access.py`

**Interfaces:**

- Produces: `generate_project_access_id() -> str`, formatted `PRJ-` plus 12 uppercase alphanumeric characters.
- Produces: `issue_unique_project_access_id(store: Store) -> str`.
- Produces: `Store.get_study_by_access_id(access_id: str) -> ResearchStudy | None`.

- [ ] **Step 1: Write a failing backend test**

```py
def test_pm_project_creation_returns_a_unique_access_id(client):
    response = client.post(
        "/api/projects",
        json={"title": "Laptop study", "research_purpose": "Compare", "question_script": "1. Why?"},
    )
    study = response.json()["study"]
    assert response.status_code == 201
    assert re.fullmatch(r"PRJ-[A-Z0-9]{12}", study["access_id"])
```

- [ ] **Step 2: Run the test and confirm the expected failure**

Run: `pytest tests/test_client_project_access.py::test_pm_project_creation_returns_a_unique_access_id -q`

Expected: FAIL because `access_id` is not in the study response.

- [ ] **Step 3: Implement the minimal persistence path**

```py
def generate_project_access_id() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "PRJ-" + "".join(secrets.choice(alphabet) for _ in range(12))

async def issue_unique_project_access_id(store: Store) -> str:
    for _ in range(10):
        candidate = generate_project_access_id()
        if await store.get_study_by_access_id(candidate) is None:
            return candidate
    raise RuntimeError("Unable to issue a unique project access ID")
```

Set `ResearchStudy.access_id` to `str | None`, issue an ID in both manual and guide-upload project creation paths, add the lookup method to InMemory, Redis, and Cosmos stores, and backfill missing IDs during application startup.

- [ ] **Step 4: Run the focused test and confirm it passes**

Run: `pytest tests/test_client_project_access.py::test_pm_project_creation_returns_a_unique_access_id -q`

Expected: PASS.

### Task 2: Add project-scoped Client API access

**Files:**

- Create: `backend/app/api/routes/client_projects.py`
- Modify: `backend/app/api/deps.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_client_project_access.py`

**Interfaces:**

- Consumes: `Store.get_study_by_access_id` and `ResearchStudy.access_id` from Task 1.
- Produces: `POST /api/client/projects/access`, `GET /api/client/projects/{study_id}`, and `GET /api/client/projects/{study_id}/sessions`.
- Produces: `X-Project-Access-Token`, an HMAC-signed, expiring token bound to one `study_id`.

- [ ] **Step 1: Write failing API tests**

```py
def test_client_access_id_grants_only_its_project(client):
    first = _create_study(client, "First")
    second = _create_study(client, "Second")
    grant = client.post("/api/client/projects/access", json={"access_id": first["access_id"]})
    token = grant.json()["access_token"]
    headers = {"X-Project-Access-Token": token}
    assert client.get(f"/api/client/projects/{first['id']}", headers=headers).status_code == 200
    assert client.get(f"/api/client/projects/{second['id']}", headers=headers).status_code == 403

def test_unknown_access_id_has_a_client_safe_error(client):
    response = client.post("/api/client/projects/access", json={"access_id": "PRJ-DOESNOTEXIST"})
    assert response.status_code == 404
    assert response.json()["detail"] == "존재하지 않는 프로젝트 ID입니다."
```

- [ ] **Step 2: Run tests and confirm expected failure**

Run: `pytest tests/test_client_project_access.py -q`

Expected: FAIL because `/api/client/projects/access` is not registered.

- [ ] **Step 3: Implement client-safe schemas and scope validation**

```py
@router.post("/projects/access")
async def exchange_access_id(payload: ClientAccessRequest) -> ClientAccessResponse:
    study = await get_store().get_study_by_access_id(payload.access_id.upper().strip())
    if study is None:
        raise HTTPException(404, "존재하지 않는 프로젝트 ID입니다.")
    return ClientAccessResponse(project=to_client_project(study), access_token=issue_client_access_token(study.id))
```

Expose only project ID, title, research purpose, creation time, and read-only session status/timestamps. Add a dependency that rejects missing, invalid, expired, or mismatched project tokens before any lookup.

- [ ] **Step 4: Run focused API tests and confirm they pass**

Run: `pytest tests/test_client_project_access.py -q`

Expected: PASS, including wrong-ID and URL-tampering coverage.

### Task 3: Create the Client-only web entry and project page

**Files:**

- Create: `frontend/web/src/lib/clientProjectApi.ts`
- Create: `frontend/web/src/lib/clientProjectAccess.ts`
- Create: `frontend/web/src/pages/ClientAccess.tsx`
- Create: `frontend/web/src/pages/ClientProject.tsx`
- Create: `frontend/web/src/pages/ClientAccess.test.tsx`
- Modify: `frontend/web/src/App.tsx`
- Modify: `frontend/web/src/pages/Login.tsx`
- Modify: `frontend/web/src/auth/RequirePmRole.tsx`
- Modify: `frontend/web/.env.example`
- Modify: `frontend/web/src/styles/global.css`

**Interfaces:**

- Consumes: Client project access endpoint and `X-Project-Access-Token` API contract from Task 2.
- Produces: `/client/access` and `/client/project/:projectId` routes outside the PM `Layout`.
- Produces: session-scoped browser storage containing only `{ projectId, accessToken }`.

- [ ] **Step 1: Write a failing component test**

```tsx
it("renders only the Project Access ID entry controls for clients", () => {
  const markup = renderToStaticMarkup(<MemoryRouter><ClientAccess /></MemoryRouter>);
  expect(markup).toContain("프로젝트 접속");
  expect(markup).toContain("Project Access ID 입력");
  expect(markup).not.toContain("새 조사 만들기");
  expect(markup).not.toContain("프로젝트 목록");
});
```

- [ ] **Step 2: Run test and confirm expected failure**

Run: `npm test -- src/pages/ClientAccess.test.tsx`

Expected: FAIL because `ClientAccess` does not exist.

- [ ] **Step 3: Implement Client-only routing and state**

```tsx
const grant = await exchangeClientAccessId(accessId);
saveClientProjectAccess({ projectId: grant.project.id, accessToken: grant.access_token });
navigate(`/client/project/${grant.project.id}`);
```

The client project page redirects to `/client/access` if browser storage lacks a grant or the path ID differs from its stored project ID. Every backend request sends the scoped token; no route renders the PM layout, project list, creation actions, downloads, or settings.

- [ ] **Step 4: Run focused test and confirm it passes**

Run: `npm test -- src/pages/ClientAccess.test.tsx`

Expected: PASS.

### Task 4: Display and copy Access IDs in PM project creation

**Files:**

- Modify: `frontend/dashboard/src/types.ts`
- Modify: `frontend/dashboard/src/components/SessionForm.tsx`
- Modify: `frontend/dashboard/src/components/SessionForm.privacy.test.tsx`

**Interfaces:**

- Consumes: `Project.access_id` returned by existing PM project creation routes.
- Produces: a PM-only `Client Access ID` section with a copy action after project creation.

- [ ] **Step 1: Write a failing static-render test**

```tsx
expect(projectSuccessMarkup).toContain("Client Access ID");
expect(projectSuccessMarkup).toContain("ID 복사");
```

- [ ] **Step 2: Run test and confirm expected failure**

Run: `npm test -- src/components/SessionForm.privacy.test.tsx`

Expected: FAIL because the PM success view does not render an access ID.

- [ ] **Step 3: Implement the PM access-ID presentation**

Add an optional `access_id` to the existing `Project` type and render it only in the successful PM project creation panel. The copy action writes the ID, never the full project object, to the clipboard.

- [ ] **Step 4: Run focused test and confirm it passes**

Run: `npm test -- src/components/SessionForm.privacy.test.tsx`

Expected: PASS.

### Task 5: Verify the local integration without Git operations

**Files:**

- Test only; do not create a commit.

- [ ] **Step 1: Run complete backend suite**

Run: `pytest -q`

Expected: all backend tests pass.

- [ ] **Step 2: Run complete frontend suites and production builds**

Run: `npm test && npm run build` in `frontend/web`, then `npm test && npm run build` in `frontend/dashboard`.

Expected: all tests and both TypeScript/Vite builds pass.

- [ ] **Step 3: Start localhost processes for manual verification**

Run: `uvicorn app.main:app --reload --port 8000` in `backend`, `npm run dev` in `frontend/web`, and `npm run dev` in `frontend/dashboard`.

Verify: PM creates a project and sees/copies `PRJ-...`; Client enters that value at `http://localhost:5175/client/access`; a wrong value shows the required error; manually replacing the client project URL redirects before data is shown.
