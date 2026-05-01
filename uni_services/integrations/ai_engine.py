"""
Optional call-out to gigs-hub-ai-engine-api after a BaseService is created.
Configure: GIGSHUB_AI_ENGINE_URL (e.g. http://127.0.0.1:8001), GIGSHUB_AI_API_KEY.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import requests

from tenancy.context import get_request_claims
from tenancy.services import get_recruited_freelancer_ids

logger = logging.getLogger(__name__)


def ai_engine_configured() -> bool:
    base = (os.environ.get("GIGSHUB_AI_ENGINE_URL") or "").strip()
    key = (os.environ.get("GIGSHUB_AI_API_KEY") or "").strip()
    return bool(base and key)


def _engine_base_and_key() -> tuple[str, str] | None:
    base = (os.environ.get("GIGSHUB_AI_ENGINE_URL") or "").rstrip("/")
    key = os.environ.get("GIGSHUB_AI_API_KEY", "")
    if not base or not key:
        return None
    return base, key


def resolve_match_scope(user, claims: dict[str, Any]) -> tuple[str, list[str] | None]:
    entitlements = claims.get("entitlements") or []
    tenant_kind = claims.get("tenant_kind") or "user"
    recruited = get_recruited_freelancer_ids(user)

    if tenant_kind == "organization":
        if recruited:
            return "organization", recruited
        return "marketplace", None

    if "native" in entitlements and recruited:
        return "recruiter_network", recruited

    return "marketplace", None


def build_project_analyze_payload(request, order) -> dict[str, Any]:
    claims = get_request_claims(request)
    user = request.user
    scope, allowed = resolve_match_scope(user, claims)
    if scope in ("organization", "recruiter_network") and not allowed:
        scope, allowed = "marketplace", None

    return {
        "project_id": order.id,
        "title": order.title,
        "description": order.description,
        "project_type": order.category,
        "budget": float(order.cost) if order.cost is not None else None,
        "priority": order.priority,
        "tenant_kind": claims.get("tenant_kind"),
        "tenant_id": claims.get("tenant_id"),
        "requesting_user_id": user.pk,
        "match_scope": scope,
        "allowed_freelancer_ids": allowed,
    }


def post_project_analyze_to_engine(payload: dict[str, Any]) -> requests.Response:
    cfg = _engine_base_and_key()
    if not cfg:
        raise RuntimeError("AI engine not configured")
    base, key = cfg
    url = f"{base}/api/v1/projects/analyze"
    return requests.post(
        url,
        json=payload,
        headers={"X-Api-Key": key, "Content-Type": "application/json"},
        timeout=120,
    )


def get_project_analysis_from_engine(project_id: str) -> requests.Response:
    cfg = _engine_base_and_key()
    if not cfg:
        raise RuntimeError("AI engine not configured")
    base, key = cfg
    url = f"{base}/api/v1/projects/{project_id}/analysis"
    return requests.get(
        url,
        headers={"X-Api-Key": key, "Accept": "application/json"},
        timeout=60,
    )


def trigger_project_analysis(request, order) -> None:
    if not ai_engine_configured():
        logger.debug("GIGSHUB_AI_ENGINE_URL or GIGSHUB_AI_API_KEY unset; skipping AI analyze.")
        return

    payload = build_project_analyze_payload(request, order)
    try:
        r = post_project_analyze_to_engine(payload)
        if not r.ok:
            logger.warning("AI analyze failed: %s %s", r.status_code, r.text[:500])
        else:
            logger.info("AI analyze OK for project %s", order.id)
    except requests.RequestException:
        logger.exception("AI analyze request error for project %s", order.id)
