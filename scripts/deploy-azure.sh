#!/usr/bin/env bash
# Copyright (c) Microsoft Corporation. All rights reserved.
# SPDX-License-Identifier: MIT
#
# deploy-azure.sh
# Build and roll out a validated image to selected Azure Container Apps.
#
# Loads .env from the repository root by default. Environment variables win.
# RESOURCE_GROUP or AZURE_RESOURCE_GROUP
# EXPECTED_SUBSCRIPTION_ID or AZURE_SUBSCRIPTION_ID
# ACR_NAME can override tagged ACR discovery. CHAT_APP and MCP_APP can override
# unique Bicep suffix discovery. All three can be set in the environment or .env.
# IMAGE_REPOSITORY defaults to the repository name in infra/main.bicep.
# Set DEPLOYMENT_ENV_FILE to use a different dotenv file.
#
# Usage: scripts/deploy-azure.sh chat|mcp|both

set -euo pipefail

err() {
  printf 'ERROR: %s\n' "$1" >&2
  exit 1
}

require_command() {
  if ! command -v "$1" &>/dev/null; then
    err "Required command not found: $1"
  fi
}

load_env_file() {
  local env_file="${DEPLOYMENT_ENV_FILE:-${REPO_ROOT}/.env}"
  local line
  local key
  local value

  [[ -f "$env_file" ]] || return 0

  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ "$line" =~ ^[[:space:]]*(#|$) ]] && continue
    [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*=[[:space:]]*(.*)$ ]] \
      || continue

    key="${BASH_REMATCH[1]}"
    value="${BASH_REMATCH[2]}"
    if [[ "$value" == \"* ]]; then
      value="${value#\"}"
      value="${value%%\"*}"
    elif [[ "$value" == \'* ]]; then
      value="${value#\'}"
      value="${value%%\'*}"
    else
      value="${value%%#*}"
      value="${value#"${value%%[![:space:]]*}"}"
      value="${value%"${value##*[![:space:]]}"}"
    fi

    case "$key" in
      AZURE_RESOURCE_GROUP)
        [[ -n "${RESOURCE_GROUP+x}" ]] || RESOURCE_GROUP="$value"
        ;;
      RESOURCE_GROUP)
        [[ -n "${RESOURCE_GROUP+x}" ]] || RESOURCE_GROUP="$value"
        ;;
      AZURE_SUBSCRIPTION_ID)
        [[ -n "${EXPECTED_SUBSCRIPTION_ID+x}" ]] \
          || EXPECTED_SUBSCRIPTION_ID="$value"
        ;;
      EXPECTED_SUBSCRIPTION_ID)
        [[ -n "${EXPECTED_SUBSCRIPTION_ID+x}" ]] \
          || EXPECTED_SUBSCRIPTION_ID="$value"
        ;;
      ACR_NAME)
        [[ -n "${ACR_NAME+x}" ]] || ACR_NAME="$value"
        ;;
      IMAGE_REPOSITORY)
        [[ -n "${IMAGE_REPOSITORY+x}" ]] || IMAGE_REPOSITORY="$value"
        ;;
      CHAT_APP)
        [[ -n "${CHAT_APP+x}" ]] || CHAT_APP="$value"
        ;;
      MCP_APP)
        [[ -n "${MCP_APP+x}" ]] || MCP_APP="$value"
        ;;
    esac
  done < "$env_file"
}

discover_deployment_resources() {
  local candidate
  local -a acr_names=()
  local -a app_names=()
  local -a chat_names=()
  local -a mcp_names=()

  if [[ -z "${ACR_NAME:-}" ]]; then
    mapfile -t acr_names < <(az acr list \
      --resource-group "$RESOURCE_GROUP" \
      --query "[?tags.application=='ai-governance-harness' && tags.environment=='hackathon'].name" \
      --output tsv)
    [[ "${#acr_names[@]}" -eq 1 ]] \
      || err "Set ACR_NAME; tagged registry discovery was not unique"
    ACR_NAME="${acr_names[0]}"
  fi

  if [[ -z "${CHAT_APP:-}" || -z "${MCP_APP:-}" ]]; then
    mapfile -t app_names < <(az containerapp list \
      --resource-group "$RESOURCE_GROUP" \
      --query '[].name' \
      --output tsv)
    for candidate in "${app_names[@]}"; do
      if [[ "$candidate" == *-chat-demo ]]; then
        chat_names+=("$candidate")
      elif [[ "$candidate" == *-mcp-demo ]]; then
        mcp_names+=("$candidate")
      fi
    done
  fi

  if [[ -z "${CHAT_APP:-}" ]]; then
    [[ "${#chat_names[@]}" -eq 1 ]] \
      || err "Set CHAT_APP; tagged chat app discovery was not unique"
    CHAT_APP="${chat_names[0]}"
  fi
  if [[ -z "${MCP_APP:-}" ]]; then
    [[ "${#mcp_names[@]}" -eq 1 ]] \
      || err "Set MCP_APP; tagged MCP app discovery was not unique"
    MCP_APP="${mcp_names[0]}"
  fi
}

capture_previous() {
  local app_name="$1"
  local revision_name
  local image

  revision_name=$(az containerapp show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$app_name" \
    --query properties.latestReadyRevisionName \
    --output tsv)
  [[ -n "$revision_name" ]] || return 1

  image=$(az containerapp revision show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$app_name" \
    --revision "$revision_name" \
    --query 'properties.template.containers[0].image' \
    --output tsv)
  [[ -n "$image" ]] || return 1

  case "$app_name" in
    "$CHAT_APP")
      PREVIOUS_CHAT_IMAGE="$image"
      ;;
    "$MCP_APP")
      PREVIOUS_MCP_IMAGE="$image"
      ;;
    *)
      return 1
      ;;
  esac

  printf 'Recorded rollback image for %s (%s).\n' \
    "$app_name" "$revision_name"
}

wait_for_revision() {
  local app_name="$1"
  local revision_name="$2"
  local deadline=$((SECONDS + MAX_WAIT_SECONDS))
  local health
  local active
  local traffic

  while (( SECONDS < deadline )); do
    health=$(az containerapp revision show \
      --resource-group "$RESOURCE_GROUP" \
      --name "$app_name" \
      --revision "$revision_name" \
      --query properties.healthState \
      --output tsv)
    active=$(az containerapp revision show \
      --resource-group "$RESOURCE_GROUP" \
      --name "$app_name" \
      --revision "$revision_name" \
      --query properties.active \
      --output tsv)
    traffic=$(az containerapp revision show \
      --resource-group "$RESOURCE_GROUP" \
      --name "$app_name" \
      --revision "$revision_name" \
      --query properties.trafficWeight \
      --output tsv)

    if [[ "$health" == "Healthy" && "$active" == "true" \
      && "$traffic" == "100" ]]; then
      printf 'Revision is Healthy with 100%% traffic: %s\n' "$revision_name"
      return 0
    fi

    if [[ "$health" == "Failed" ]]; then
      printf 'Revision entered Failed health state: %s\n' "$revision_name" >&2
      return 1
    fi

    sleep "$POLL_INTERVAL_SECONDS"
  done

  printf 'Timed out waiting for revision: %s\n' "$revision_name" >&2
  return 1
}

verify_chat() {
  local chat_fqdn
  local ready_body
  local snapshot_status

  chat_fqdn=$(az containerapp show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CHAT_APP" \
    --query properties.configuration.ingress.fqdn \
    --output tsv)
  [[ -n "$chat_fqdn" ]] || return 1

  curl --fail --silent --show-error --max-time 30 \
    "https://${chat_fqdn}/health/live" >/dev/null || return 1
  ready_body=$(curl --fail --silent --show-error --max-time 30 \
    "https://${chat_fqdn}/health/ready") || return 1
  jq --exit-status \
    '.status == "ready" and .governance.enforcement == "enabled"' \
    <<<"$ready_body" >/dev/null || return 1

  snapshot_status=$(curl --silent --show-error --max-time 30 \
    --output /dev/null --write-out '%{http_code}' \
    "https://${chat_fqdn}/api/governance/snapshot") || return 1
  if [[ "$snapshot_status" != "401" ]]; then
    printf 'Expected unauthenticated snapshot HTTP 401, got %s.\n' \
      "$snapshot_status" >&2
    return 1
  fi

  printf 'Chat liveness, readiness, governance, and auth checks passed.\n'
}

verify_mcp() {
  local mcp_fqdn
  local direct_status

  mcp_fqdn=$(az containerapp show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$MCP_APP" \
    --query properties.configuration.ingress.fqdn \
    --output tsv)
  [[ -n "$mcp_fqdn" ]] || return 1

  direct_status=$(curl --silent --show-error --max-time 30 \
    --output /dev/null --write-out '%{http_code}' \
    "https://${mcp_fqdn}/mcp") || return 1
  if [[ "$direct_status" != "403" ]]; then
    printf 'Expected direct MCP HTTP 403, got %s.\n' \
      "$direct_status" >&2
    return 1
  fi

  printf 'Direct MCP access remains restricted (HTTP 403).\n'
}

verify_app() {
  local app_name="$1"

  case "$app_name" in
    "$CHAT_APP") verify_chat ;;
    "$MCP_APP") verify_mcp ;;
    *) return 1 ;;
  esac
}

rollback_app() {
  local app_name="$1"
  local previous_image="$2"
  local revision_name
  local rollback_suffix="rollback-${SHORT_SHA}-${RUN_TOKEN}"

  printf 'Rolling back %s to its recorded image.\n' "$app_name" >&2
  revision_name=$(az containerapp update \
    --resource-group "$RESOURCE_GROUP" \
    --name "$app_name" \
    --image "$previous_image" \
    --revision-suffix "$rollback_suffix" \
    --query properties.latestRevisionName \
    --output tsv) || return 1
  [[ -n "$revision_name" ]] || return 1
  wait_for_revision "$app_name" "$revision_name" || return 1
  verify_app "$app_name"
}

deploy_app() {
  local app_name="$1"
  local revision_name

  printf 'Deploying %s with image digest %s.\n' "$app_name" "$IMAGE_DIGEST"
  revision_name=$(az containerapp update \
    --resource-group "$RESOURCE_GROUP" \
    --name "$app_name" \
    --image "$IMAGE" \
    --revision-suffix "$REVISION_SUFFIX" \
    --query properties.latestRevisionName \
    --output tsv) || return 1
  [[ -n "$revision_name" ]] || return 1
  wait_for_revision "$app_name" "$revision_name" || return 1
  verify_app "$app_name"
}

rollback_after_failure() {
  local failed_app="$1"
  local target="$2"
  local rollback_failed=false

  case "$failed_app" in
    "$CHAT_APP")
      rollback_app "$CHAT_APP" "$PREVIOUS_CHAT_IMAGE" \
        || rollback_failed=true
      if [[ "$target" == "both" ]]; then
        rollback_app "$MCP_APP" "$PREVIOUS_MCP_IMAGE" \
          || rollback_failed=true
      fi
      ;;
    "$MCP_APP")
      rollback_app "$MCP_APP" "$PREVIOUS_MCP_IMAGE" \
        || rollback_failed=true
      ;;
  esac

  if [[ "$rollback_failed" == "true" ]]; then
    printf 'One or more rollback checks failed; inspect Azure revisions.\n' >&2
  fi
}

main() {
  local target="${1:-}"
  local script_dir
  local current_subscription
  local git_status
  local source_sha
  local run_attempt
  local target_app
  local build_result
  local app
  local deployment_failed=false
  local -a target_apps=()

  script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
  REPO_ROOT="$(cd -- "${script_dir}/.." && pwd)"
  cd "$REPO_ROOT"
  load_env_file
  IMAGE_REPOSITORY="${IMAGE_REPOSITORY:-ai-governance-harness}"

  if [[ "$target" == "--help" || "$target" == "-h" ]]; then
    printf 'Usage: %s chat|mcp|both\n' "$0"
    exit 0
  fi
  [[ "$#" -eq 1 ]] || err "Usage: $0 chat|mcp|both"

  case "$target" in
    chat|mcp|both) ;;
    *) err "Target must be chat, mcp, or both" ;;
  esac

  : "${RESOURCE_GROUP:?Set RESOURCE_GROUP}"
  : "${EXPECTED_SUBSCRIPTION_ID:?Set EXPECTED_SUBSCRIPTION_ID}"
  : "${IMAGE_REPOSITORY:?Set IMAGE_REPOSITORY}"

  require_command az
  require_command curl
  require_command git
  require_command jq

  git_status=$(git status --porcelain --untracked-files=normal)
  [[ -z "$git_status" ]] \
    || err "Commit or remove working-tree changes before deployment"
  source_sha=$(git rev-parse --verify HEAD)
  SHORT_SHA="${source_sha:0:7}"

  current_subscription=$(az account show --query id --output tsv)
  [[ "$current_subscription" == "$EXPECTED_SUBSCRIPTION_ID" ]] \
    || err "Azure CLI is not logged into EXPECTED_SUBSCRIPTION_ID"
  discover_deployment_resources
  : "${ACR_NAME:?Set ACR_NAME}"
  : "${CHAT_APP:?Set CHAT_APP}"
  : "${MCP_APP:?Set MCP_APP}"

  [[ "$CHAT_APP" != "$MCP_APP" ]] \
    || err "CHAT_APP and MCP_APP must be different names"
  case "$target" in
    chat) target_apps=("$CHAT_APP") ;;
    mcp) target_apps=("$MCP_APP") ;;
    both) target_apps=("$MCP_APP" "$CHAT_APP") ;;
  esac

  if [[ -n "${GITHUB_RUN_ID:-}" ]]; then
    run_attempt="${GITHUB_RUN_ATTEMPT:-1}"
    RUN_TOKEN="${GITHUB_RUN_ID}-${run_attempt}"
  else
    RUN_TOKEN="local-$(date -u +%Y%m%d%H%M%S)-$$"
  fi

  IMAGE_TAG="deploy-${SHORT_SHA}-${RUN_TOKEN}"
  REVISION_SUFFIX="deploy-${SHORT_SHA}-${RUN_TOKEN}"
  MAX_WAIT_SECONDS="${DEPLOYMENT_TIMEOUT_SECONDS:-600}"
  POLL_INTERVAL_SECONDS="${DEPLOYMENT_POLL_INTERVAL_SECONDS:-10}"
  [[ "$MAX_WAIT_SECONDS" =~ ^[1-9][0-9]*$ ]] \
    || err "DEPLOYMENT_TIMEOUT_SECONDS must be a positive integer"
  [[ "$POLL_INTERVAL_SECONDS" =~ ^[1-9][0-9]*$ ]] \
    || err "DEPLOYMENT_POLL_INTERVAL_SECONDS must be a positive integer"

  REGISTRY_SERVER=$(az acr show \
    --name "$ACR_NAME" \
    --query loginServer \
    --output tsv)
  [[ -n "$REGISTRY_SERVER" ]] || err "Could not resolve the ACR login server"

  for target_app in "${target_apps[@]}"; do
    capture_previous "$target_app" \
      || err "Could not record the previous ready image for ${target_app}"
  done

  printf 'Building commit %s as %s/%s:%s.\n' \
    "$SHORT_SHA" "$REGISTRY_SERVER" "$IMAGE_REPOSITORY" "$IMAGE_TAG"
  build_result=$(az acr build \
    --registry "$ACR_NAME" \
    --image "${IMAGE_REPOSITORY}:${IMAGE_TAG}" \
    --file Dockerfile . \
    --no-logs \
    --only-show-errors \
    --query 'outputImages[0].digest' \
    --output tsv) || err "ACR image build failed"
  IMAGE_DIGEST="$build_result"
  [[ "$IMAGE_DIGEST" =~ ^sha256:[[:xdigit:]]{64}$ ]] \
    || err "ACR did not return a valid image digest"
  IMAGE="${REGISTRY_SERVER}/${IMAGE_REPOSITORY}@${IMAGE_DIGEST}"

  for app in "${target_apps[@]}"; do
    if ! deploy_app "$app"; then
      printf 'Deployment verification failed for %s.\n' "$app" >&2
      rollback_after_failure "$app" "$target"
      deployment_failed=true
      break
    fi
  done

  [[ "$deployment_failed" == "false" ]] \
    || err "Deployment failed; rollback was attempted"
  printf 'Deployment verified for target=%s, image=%s.\n' "$target" "$IMAGE"
}

main "$@"