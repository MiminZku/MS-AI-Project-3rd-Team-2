#!/usr/bin/env bash
# =============================================================================
# 데모용 Azure 리소스 일괄 생성 + GitHub Actions OIDC 연결 준비
#
# 실행 위치: 리포지토리 루트 (backend/Dockerfile 이 보이는 곳)
# 실행 환경: Azure Cloud Shell(Bash) 권장. 로컬은 Git Bash + az CLI 로그인 상태.
#
#   bash infra/azure-setup.sh
#
# 만드는 것:
#   1) 리소스 그룹
#   2) Azure Container Registry (+ 백엔드 이미지 첫 빌드)
#   3) Container Apps 환경 + 백엔드 앱 (WebSocket, min replica 1, sticky sessions)
#   4) Static Web Apps 2개 (인터뷰이 / 대시보드)
#   5) (선택) Azure Cache for Redis
#   6) (선택) GitHub Actions용 앱 등록 + OIDC 페더레이션 자격증명
#
# 마지막에 GitHub에 넣을 Secrets/Variables 목록을 출력한다.
# =============================================================================
set -euo pipefail

# ---------------------------- 여기만 수정 ------------------------------------
PREFIX="${PREFIX:-aiitv}"                    # 리소스 이름 접두사 (소문자/숫자)
LOCATION="${LOCATION:-koreacentral}"         # Container Apps / Redis 리전
SWA_LOCATION="${SWA_LOCATION:-eastasia}"     # Static Web Apps 지원 리전
GITHUB_REPO="${GITHUB_REPO:-<owner>/<repo>}" # 예) my-team/MS-AI-Project-3rd-Team-2

CREATE_REDIS="${CREATE_REDIS:-false}"        # true면 Redis도 생성 (15~20분 소요)
CREATE_OIDC="${CREATE_OIDC:-true}"           # Entra ID 앱 등록 권한이 없으면 false
DEMO_ADMIN_TOKEN="${DEMO_ADMIN_TOKEN:-demo-$(openssl rand -hex 8)}"
# -----------------------------------------------------------------------------

SUFFIX="${SUFFIX:-$(printf '%04d' $((RANDOM % 10000)))}"
RG="rg-${PREFIX}"
ACR="acr${PREFIX}${SUFFIX}"                  # ACR 이름은 전역 유일 + 소문자/숫자만
ACA_ENV="cae-${PREFIX}"
ACA_APP="ca-${PREFIX}-backend"
REDIS_NAME="redis-${PREFIX}-${SUFFIX}"
SWA_INTERVIEWEE="swa-${PREFIX}-interviewee"
SWA_DASHBOARD="swa-${PREFIX}-dashboard"
IMAGE_NAME="interview-backend"

if [[ ! -f backend/Dockerfile ]]; then
  echo "리포지토리 루트에서 실행하세요 (backend/Dockerfile 을 찾을 수 없음)" >&2
  exit 1
fi

SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
TENANT_ID="$(az account show --query tenantId -o tsv)"
echo "구독: ${SUBSCRIPTION_ID}"

echo "==> 1/6 리소스 그룹 ${RG}"
az group create --name "$RG" --location "$LOCATION" --output none

echo "==> 2/6 ACR ${ACR} + 백엔드 이미지 빌드"
az acr create --name "$ACR" --resource-group "$RG" --sku Basic --admin-enabled true --output none
# 데모 편의를 위해 admin 계정을 켠다. 운영에서는 관리 ID + AcrPull 로 바꿀 것.
az acr build --registry "$ACR" --image "${IMAGE_NAME}:bootstrap" --file backend/Dockerfile backend --output none
ACR_PASSWORD="$(az acr credential show --name "$ACR" --query 'passwords[0].value' -o tsv)"

echo "==> 3/6 Container Apps 환경 + 백엔드 앱"
az extension add --name containerapp --upgrade --only-show-errors --output none
az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.OperationalInsights --wait

az containerapp env create \
  --name "$ACA_ENV" --resource-group "$RG" --location "$LOCATION" --output none

az containerapp create \
  --name "$ACA_APP" --resource-group "$RG" --environment "$ACA_ENV" \
  --image "${ACR}.azurecr.io/${IMAGE_NAME}:bootstrap" \
  --registry-server "${ACR}.azurecr.io" \
  --registry-username "$ACR" --registry-password "$ACR_PASSWORD" \
  --target-port 8000 --ingress external --transport auto \
  --min-replicas 1 --max-replicas 1 \
  --secrets "admin-token=${DEMO_ADMIN_TOKEN}" \
  --env-vars "ENVIRONMENT=demo" "ADMIN_TOKEN=secretref:admin-token" \
  --output none
# min-replicas 1: WebSocket 세션이 스케일 인으로 끊기지 않도록 (C1)
# max-replicas 1: Redis 붙이기 전까지는 세션이 인스턴스 간에 갈라지지 않게 잠가둔다

az containerapp ingress sticky-sessions set \
  --name "$ACA_APP" --resource-group "$RG" --affinity sticky --output none

BACKEND_FQDN="$(az containerapp show --name "$ACA_APP" --resource-group "$RG" \
  --query properties.configuration.ingress.fqdn -o tsv)"
echo "백엔드: https://${BACKEND_FQDN}/health"

echo "==> 4/6 Static Web Apps 2개"
az staticwebapp create --name "$SWA_INTERVIEWEE" --resource-group "$RG" \
  --location "$SWA_LOCATION" --sku Free --output none
az staticwebapp create --name "$SWA_DASHBOARD" --resource-group "$RG" \
  --location "$SWA_LOCATION" --sku Free --output none

SWA_TOKEN_INTERVIEWEE="$(az staticwebapp secrets list --name "$SWA_INTERVIEWEE" \
  --resource-group "$RG" --query properties.apiKey -o tsv)"
SWA_TOKEN_DASHBOARD="$(az staticwebapp secrets list --name "$SWA_DASHBOARD" \
  --resource-group "$RG" --query properties.apiKey -o tsv)"
SWA_HOST_INTERVIEWEE="$(az staticwebapp show --name "$SWA_INTERVIEWEE" \
  --resource-group "$RG" --query defaultHostname -o tsv)"
SWA_HOST_DASHBOARD="$(az staticwebapp show --name "$SWA_DASHBOARD" \
  --resource-group "$RG" --query defaultHostname -o tsv)"

echo "==> 5/6 Redis (CREATE_REDIS=${CREATE_REDIS})"
REDIS_URL=""
if [[ "$CREATE_REDIS" == "true" ]]; then
  az redis create --name "$REDIS_NAME" --resource-group "$RG" --location "$LOCATION" \
    --sku Basic --vm-size c0 --minimum-tls-version 1.2 --output none
  REDIS_HOST="$(az redis show --name "$REDIS_NAME" --resource-group "$RG" --query hostName -o tsv)"
  REDIS_KEY="$(az redis list-keys --name "$REDIS_NAME" --resource-group "$RG" --query primaryKey -o tsv)"
  # 키에 +, / 가 들어갈 수 있으므로 URL 인코딩
  REDIS_KEY_ENC="$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1],safe=""))' "$REDIS_KEY")"
  REDIS_URL="rediss://:${REDIS_KEY_ENC}@${REDIS_HOST}:6380/0"
  az containerapp secret set --name "$ACA_APP" --resource-group "$RG" \
    --secrets "redis-url=${REDIS_URL}" --output none
  az containerapp update --name "$ACA_APP" --resource-group "$RG" \
    --set-env-vars "REDIS_URL=secretref:redis-url" --output none
fi

echo "==> 백엔드 환경변수 (프론트 도메인 CORS 허용)"
az containerapp update --name "$ACA_APP" --resource-group "$RG" \
  --set-env-vars \
    "CORS_ORIGINS=https://${SWA_HOST_INTERVIEWEE},https://${SWA_HOST_DASHBOARD}" \
    "INTERVIEWEE_BASE_URL=https://${SWA_HOST_INTERVIEWEE}" \
  --output none

echo "==> 6/6 GitHub Actions OIDC (CREATE_OIDC=${CREATE_OIDC})"
CLIENT_ID=""
if [[ "$CREATE_OIDC" == "true" ]]; then
  APP_DISPLAY_NAME="gh-actions-${PREFIX}"
  CLIENT_ID="$(az ad app create --display-name "$APP_DISPLAY_NAME" --query appId -o tsv)"
  az ad sp create --id "$CLIENT_ID" --output none 2>/dev/null || true
  sleep 15  # 디렉터리 전파 대기

  az role assignment create --assignee "$CLIENT_ID" --role Contributor \
    --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RG}" --output none
  az role assignment create --assignee "$CLIENT_ID" --role AcrPush \
    --scope "$(az acr show --name "$ACR" --query id -o tsv)" --output none

  az ad app federated-credential create --id "$CLIENT_ID" --parameters "$(cat <<JSON
{
  "name": "github-main",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:${GITHUB_REPO}:ref:refs/heads/main",
  "audiences": ["api://AzureADTokenExchange"]
}
JSON
)" --output none
fi

cat <<SUMMARY

=============================================================================
 완료. GitHub 리포지토리에 아래 값을 넣으세요.
 (Settings > Secrets and variables > Actions)
=============================================================================

[Secrets]
  AZURE_CLIENT_ID                = ${CLIENT_ID:-<OIDC 미생성>}
  AZURE_TENANT_ID                = ${TENANT_ID}
  AZURE_SUBSCRIPTION_ID          = ${SUBSCRIPTION_ID}
  AZURE_SWA_TOKEN_INTERVIEWEE    = ${SWA_TOKEN_INTERVIEWEE}
  AZURE_SWA_TOKEN_DASHBOARD      = ${SWA_TOKEN_DASHBOARD}
  DEMO_ADMIN_TOKEN               = ${DEMO_ADMIN_TOKEN}

[Variables]
  AZURE_RESOURCE_GROUP  = ${RG}
  ACR_NAME              = ${ACR}
  CONTAINER_APP_NAME    = ${ACA_APP}
  VITE_API_BASE_URL     = https://${BACKEND_FQDN}
  VITE_WS_BASE_URL      = wss://${BACKEND_FQDN}

[URL]
  백엔드          https://${BACKEND_FQDN}/health
  인터뷰이 웹      https://${SWA_HOST_INTERVIEWEE}
  참관자 대시보드   https://${SWA_HOST_DASHBOARD}
  Redis           ${REDIS_URL:-<미생성 — 백엔드는 인메모리 폴백으로 동작>}

 gh CLI가 있다면 한 번에 등록:
   gh secret set AZURE_CLIENT_ID --body "${CLIENT_ID:-}"
   gh secret set AZURE_TENANT_ID --body "${TENANT_ID}"
   gh secret set AZURE_SUBSCRIPTION_ID --body "${SUBSCRIPTION_ID}"
   gh secret set AZURE_SWA_TOKEN_INTERVIEWEE --body "${SWA_TOKEN_INTERVIEWEE}"
   gh secret set AZURE_SWA_TOKEN_DASHBOARD --body "${SWA_TOKEN_DASHBOARD}"
   gh secret set DEMO_ADMIN_TOKEN --body "${DEMO_ADMIN_TOKEN}"
   gh variable set AZURE_RESOURCE_GROUP --body "${RG}"
   gh variable set ACR_NAME --body "${ACR}"
   gh variable set CONTAINER_APP_NAME --body "${ACA_APP}"
   gh variable set VITE_API_BASE_URL --body "https://${BACKEND_FQDN}"
   gh variable set VITE_WS_BASE_URL --body "wss://${BACKEND_FQDN}"

 정리(과금 중단):  az group delete --name ${RG} --yes --no-wait
=============================================================================
SUMMARY
