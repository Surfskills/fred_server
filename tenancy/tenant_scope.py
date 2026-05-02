"""
Row-level tenant scoping from JWT claims (aligned with uni_services BaseService posting tenant).
"""

from __future__ import annotations

from django.db.models import Q

from authentication.models import User

from tenancy.context import get_request_claims

# Keep in sync with uni_services.models.BaseService.POSTING_TENANT_KIND_CHOICES
TENANT_KIND_CHOICES = (
    ("user", "User"),
    ("native", "Native (partner-selective intake · rare niche skills)"),
    (
        "dynamic",
        "Dynamic (partner certification prerequisite · enterprise / big-tech alum + freelance)",
    ),
    (
        "demer",
        "Demers (partner certification prerequisite · technocrats · elite private practice)",
    ),
    ("organization", "Organization"),
)


def effective_tenant_from_request(request) -> tuple[str, str]:
    claims = get_request_claims(request)
    tenant_kind = (claims.get("tenant_kind") or "user").strip() or "user"
    tenant_id = claims.get("tenant_id")
    if tenant_id is None and getattr(request, "user", None) and request.user.is_authenticated:
        tenant_id = str(request.user.pk)
    else:
        tenant_id = "" if tenant_id is None else str(tenant_id).strip()
    return tenant_kind, tenant_id


def legacy_unscoped_tenant_q(prefix: str = "") -> Q:
    """Rows with NULL tenant fields (created before tenancy)."""
    if prefix:
        return Q(**{f"{prefix}__tenant_kind__isnull": True}) | Q(
            **{f"{prefix}__tenant_id__isnull": True}
        )
    return Q(tenant_kind__isnull=True) | Q(tenant_id__isnull=True)


def scoped_tenant_match_q(tenant_kind: str, tenant_id: str, prefix: str = "") -> Q:
    if prefix:
        return Q(
            **{f"{prefix}__tenant_kind": tenant_kind, f"{prefix}__tenant_id": tenant_id}
        )
    return Q(tenant_kind=tenant_kind, tenant_id=tenant_id)


def tenant_scope_or_legacy_q(request, *, prefix: str = "") -> Q:
    tk, tid = effective_tenant_from_request(request)
    return scoped_tenant_match_q(tk, tid, prefix) | legacy_unscoped_tenant_q(prefix)


def wants_all_tenants(request) -> bool:
    v = (request.query_params.get("all_tenants") or "").lower()
    if v not in ("1", "true", "yes"):
        return False
    user = request.user
    if not user.is_authenticated:
        return False
    return user.is_staff and getattr(user, "user_type", None) == User.Types.ADMIN


def is_platform_admin(user) -> bool:
    return (
        user
        and user.is_authenticated
        and user.is_staff
        and getattr(user, "user_type", None) == User.Types.ADMIN
    )


def row_matches_request_tenant(obj, request) -> bool:
    """Legacy rows (NULL tenant) remain visible; scoped rows must match JWT tenant."""
    if getattr(obj, "tenant_kind", None) is None or getattr(obj, "tenant_id", None) is None:
        return True
    tk, tid = effective_tenant_from_request(request)
    return obj.tenant_kind == tk and str(obj.tenant_id) == str(tid)
