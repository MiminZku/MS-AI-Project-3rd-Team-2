# Azure 데모 프로젝트 생성 + CI/CD 연결 가이드

목표: **Azure 리소스를 만들고 GitHub Actions로 자동 배포되는 상태까지** 도달하는 것.
AI 기능(STT/TTS/GPT)은 아직 안 붙어도 된다. 백엔드는 Azure OpenAI 키가 없으면 스텁 생성기로 동작하므로,
파이프라인(참관자 지시 → 다음 질문 주입)은 **리소스 없이도 끝까지 확인된다.**

---

## 0. 준비물

| 항목 | 확인 방법 |
|---|---|
| Azure 구독 (기여자 권한) | `az account show` |
| Azure CLI | `az version` — 없으면 [Azure Cloud Shell](https://shell.azure.com) 사용 (설치 불필요, 권장) |
| GitHub 리포지토리 (이 코드가 push된 상태) | — |
| gh CLI (선택) | `gh auth status` |

> **Cloud Shell 권장.** 브라우저에서 열고 `git clone <리포지토리 URL>` 후 스크립트를 돌리면
> 로컬 az 설치/로그인 문제가 전부 사라진다.

---

## 1. 만들 리소스 (데모 최소 구성)

| 리소스 | 이름 예시 | SKU | 왜 지금 필요한가 |
|---|---|---|---|
| Resource Group | `rg-aiitv` | — | 한 번에 지우기 위해 |
| Container Registry | `acraiitv1234` | Basic | 백엔드 이미지 저장소 |
| Container Apps 환경 + 앱 | `ca-aiitv-backend` | Consumption | FastAPI WebSocket 서버 |
| Static Web Apps × 2 | `swa-aiitv-interviewee`, `swa-aiitv-dashboard` | **Free** | 인터뷰이 웹 / 참관자 대시보드 (D10) |
| Azure Cache for Redis | `redis-aiitv-1234` | Basic C0 | **나중에.** 생성에 15~20분 걸리고, 없으면 백엔드가 인메모리로 폴백 |

Azure OpenAI / Speech는 이 단계에서 만들지 않는다. 배포 파이프라인이 도는 걸 먼저 확인하고,
모델 배포는 별도로 붙인 뒤 Container Apps 환경변수만 추가하면 된다.

---

## 2. 방법 A — 스크립트 한 번에 (권장)

```bash
# Cloud Shell 또는 로컬 Git Bash, 리포지토리 루트에서
export PREFIX=aiitv                      # 팀 이름 등으로 변경 (소문자/숫자)
export GITHUB_REPO=<owner>/<repo>        # 예) my-team/MS-AI-Project-3rd-Team-2
export LOCATION=koreacentral
export SWA_LOCATION=eastasia

bash infra/azure-setup.sh
```

스크립트가 하는 일:

1. 리소스 그룹 + ACR 생성 후 **`backend/Dockerfile`을 ACR에서 바로 빌드** (로컬 Docker 불필요)
2. Container Apps 환경 + 앱 생성 (포트 8000, external ingress, `min-replicas 1`, sticky sessions)
3. Static Web Apps 2개 생성 + 배포 토큰 발급
4. 프론트 도메인을 백엔드 `CORS_ORIGINS` / `INTERVIEWEE_BASE_URL`에 주입
5. GitHub Actions용 Entra ID 앱 등록 + **OIDC 페더레이션 자격증명** (비밀번호 없는 인증)
6. GitHub에 넣을 Secrets/Variables 목록 출력

끝나면 `https://<백엔드FQDN>/health`가 열리는지 확인:

```json
{ "status": "ok", "environment": "demo", "store": "memory", "llm": "stub" }
```

**옵션**

```bash
CREATE_REDIS=true bash infra/azure-setup.sh   # Redis까지 (15~20분 추가)
CREATE_OIDC=false bash infra/azure-setup.sh   # Entra ID 앱 등록 권한이 없을 때
```

---

## 3. 방법 B — 포털에서 클릭으로

스크립트가 막히면(권한/정책 이슈) 포털에서 같은 것을 만든다.

1. **리소스 그룹**: 포털 → *리소스 그룹* → 만들기 → 지역 `Korea Central`
2. **Container Registry**: *컨테이너 레지스트리* → 만들기 → SKU `Basic` → 생성 후 *액세스 키*에서 **관리 사용자 사용** 켜기
3. **Container App**:
   - *Container Apps* → 만들기 → 새 환경 만들기
   - 컨테이너 탭: 처음엔 *빠른 시작 이미지*로 만들고, 첫 CI 배포가 진짜 이미지로 교체한다
   - 수신(Ingress) 탭: **사용** → 트래픽 `모든 위치에서 수락` → **대상 포트 8000**
   - 만든 뒤 *스케일*에서 **최소 복제본 1** (C1), *수신 → 세션 선호도*에서 **고정(sticky)**
4. **Static Web Apps** (2번 반복, 각각 인터뷰이/대시보드):
   - *Static Web Apps* → 만들기 → 플랜 **Free**
   - 배포 원본은 **기타(Other)** 를 선택한다. GitHub을 고르면 Azure가 워크플로 파일을 제멋대로 커밋하기 때문
   - 생성 후 *개요 → 배포 토큰 관리*에서 토큰 복사
5. **환경변수** (Container App → *컨테이너 → 편집 및 배포 → 환경 변수*):

   | 이름 | 값 |
   |---|---|
   | `CORS_ORIGINS` | `https://<인터뷰이SWA>,https://<대시보드SWA>` |
   | `INTERVIEWEE_BASE_URL` | `https://<인터뷰이SWA>` |
   | `ADMIN_TOKEN` | 임의 문자열 (대시보드와 동일하게) |

6. **GitHub 인증용 서비스 주체** (OIDC 대신 간단히):

   ```bash
   az ad sp create-for-rbac --name gh-aiitv \
     --role contributor \
     --scopes /subscriptions/<구독ID>/resourceGroups/rg-aiitv \
     --json-auth
   ```

   출력 JSON 전체를 `AZURE_CREDENTIALS` 시크릿으로 넣고,
   `deploy-backend.yml`의 `azure/login` 스텝을 아래로 바꾼다.

   ```yaml
   - uses: azure/login@v2
     with:
       creds: ${{ secrets.AZURE_CREDENTIALS }}
   ```

---

## 4. GitHub에 넣을 값

**Settings → Secrets and variables → Actions**

### Secrets

| 이름 | 값 | 쓰는 곳 |
|---|---|---|
| `AZURE_CLIENT_ID` | Entra 앱 등록의 appId | deploy-backend |
| `AZURE_TENANT_ID` | 테넌트 ID | deploy-backend |
| `AZURE_SUBSCRIPTION_ID` | 구독 ID | deploy-backend |
| `AZURE_SWA_TOKEN_INTERVIEWEE` | 인터뷰이 SWA 배포 토큰 | deploy-frontend-interviewee |
| `AZURE_SWA_TOKEN_DASHBOARD` | 대시보드 SWA 배포 토큰 | deploy-frontend-dashboard |
| `DEMO_ADMIN_TOKEN` | 백엔드 `ADMIN_TOKEN`과 동일한 값 | deploy-frontend-dashboard |

### Variables

| 이름 | 값 예시 |
|---|---|
| `AZURE_RESOURCE_GROUP` | `rg-aiitv` |
| `ACR_NAME` | `acraiitv1234` |
| `CONTAINER_APP_NAME` | `ca-aiitv-backend` |
| `VITE_API_BASE_URL` | `https://ca-aiitv-backend.xxx.koreacentral.azurecontainerapps.io` |
| `VITE_WS_BASE_URL` | `wss://ca-aiitv-backend.xxx.koreacentral.azurecontainerapps.io` |

> `VITE_*` 는 빌드 시점에 번들에 그대로 박힌다. **비밀값을 넣지 말 것.**
> `DEMO_ADMIN_TOKEN`도 결국 대시보드 번들에 들어가므로 데모용 임시 값으로만 쓰고,
> 실제 보호는 Static Web Apps의 Entra ID 인증으로 대체해야 한다.

---

## 5. 첫 배포 돌려보기

```bash
git add .
git commit -m "chore: 초기 구조 + CI/CD"
git push origin main
```

- `backend/**`가 바뀌면 → `deploy-backend` (테스트 → ACR 빌드 → Container Apps 업데이트 → `/health` 스모크)
- `frontend/interviewee/**`가 바뀌면 → `deploy-frontend-interviewee`만
- `frontend/dashboard/**`가 바뀌면 → `deploy-frontend-dashboard`만

`paths` 필터 때문에 **처음 push에서는 세 워크플로가 모두** 돈다. 이후에는 건드린 쪽만 돈다.
수동 실행은 Actions 탭 → 워크플로 선택 → *Run workflow* (`workflow_dispatch`).

---

## 6. 배포 후 동작 확인 (데모 시나리오)

1. 대시보드 URL 접속 → 질문 리스트 입력 → **세션 생성** → 응답자 링크 복사
2. 다른 브라우저(또는 시크릿 창)에서 응답자 링크 접속 → 답변 입력
3. 대시보드에 응답자 발화가 실시간으로 뜨는지 확인
4. 대시보드에서 지시 입력: `경쟁사 대비 장점을 물어봐` → 상태 `queued`
5. 응답자가 다음 답변을 보내면 → AI 질문에 지시가 반영되고 상태가 `applied`로 전환
6. 응답자 화면에는 **판단 근거가 보이지 않는지** 확인 (C5)

이게 되면 CI/CD + 핵심 차별점 파이프라인이 살아 있는 것이다.

---

## 7. 자주 막히는 곳

| 증상 | 원인 / 해결 |
|---|---|
| WebSocket이 붙지 않음 (`wss` 실패) | `VITE_WS_BASE_URL`이 `wss://`인지 확인. HTTPS 페이지에서 `ws://`는 브라우저가 차단한다 |
| CORS 오류 | Container Apps `CORS_ORIGINS`에 SWA 도메인 2개가 들어갔는지. 값 변경 후 새 리비전이 활성인지 확인 |
| 세션이 가끔 사라짐 | 인메모리 폴백 상태. `REDIS_URL`을 넣으면 해결 (D4) |
| `az containerapp` 명령을 못 찾음 | `az extension add --name containerapp --upgrade` |
| OIDC 로그인 실패 (`AADSTS70021`) | 페더레이션 자격증명의 `subject`가 `repo:<owner>/<repo>:ref:refs/heads/main`과 정확히 일치해야 함 |
| SWA 배포가 `deployment token` 오류 | 토큰 재발급 후 시크릿 갱신 (*배포 토큰 관리 → 재설정*) |
| Container Apps 배포는 됐는데 502 | 컨테이너가 8000 포트로 뜨는지, `ingress --target-port 8000`인지 확인. 로그: `az containerapp logs show -n <앱> -g <RG> --follow` |
| 첫 push에서 `npm ci` 실패 | `package-lock.json`이 커밋되어 있어야 한다 |

---

## 8. 비용과 정리

- Static Web Apps **Free**, Container Apps는 요청 없을 때 사실상 무료지만 `min-replicas 1`이라 **상시 소량 과금**된다.
- Redis Basic C0가 이 구성에서 제일 비싸다. 데모 직전에 만들어도 늦지 않다.
- 발표가 끝나면 통째로 지우기:

  ```bash
  az group delete --name rg-aiitv --yes --no-wait
  ```

---

## 9. 다음 단계 (AI 붙이기)

1. Azure AI Foundry에서 `gpt-4o`, `gpt-4o-mini` 배포 → Container Apps에 시크릿으로 주입

   ```bash
   az containerapp secret set -n <앱> -g <RG> --secrets openai-key=<키>
   az containerapp update -n <앱> -g <RG> --set-env-vars \
     AZURE_OPENAI_ENDPOINT=https://<리소스>.openai.azure.com \
     AZURE_OPENAI_API_KEY=secretref:openai-key \
     AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o \
     AZURE_OPENAI_TIMEKEEPER_DEPLOYMENT=gpt-4o-mini
   ```

   `/health`의 `"llm"`이 `stub` → `azure-openai`로 바뀌면 성공.
2. STT 모델(`gpt-transcribe` / `gpt-live-transcribe`) 리전 확인 후 `backend/app/services/ai/stt.py` 구현 (D8, C7)
3. Azure Speech 리소스 생성 후 `backend/app/services/ai/tts.py` 구현 → 아바타, 실패 시 오브 폴백 (D7, C6)
4. Redis 생성 후 `REDIS_URL` 주입 → `max-replicas`를 2 이상으로 올려 스케일아웃 시연 (D4)
