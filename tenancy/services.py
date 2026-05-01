from __future__ import annotations

import uuid
from typing import Any

from django.apps import apps
from rest_framework.exceptions import PermissionDenied

from tenancy.models import Organization, OrganizationMembership, OrganizationRole


def _UserEntitlement():
    return apps.get_model("tenancy", "UserEntitlement")


def get_or_create_entitlement(user):
    UserEntitlement = _UserEntitlement()
    ent, _ = UserEntitlement.objects.get_or_create(
        user=user,
        defaults={"flags": {"base": True}},
    )
    if not ent.flags.get("base"):
        flags = dict(ent.flags)
        flags["base"] = True
        ent.flags = flags
        ent.save(update_fields=["flags", "updated_at"])
    return ent


def merge_entitlement_flags(user, updates: dict[str, bool]):
    """
    Additive entitlement updater. Only boolean keys are applied.
    Existing keys remain unless explicitly set in `updates`.
    """
    ent = get_or_create_entitlement(user)
    flags = dict(ent.flags or {})
    for key, value in updates.items():
        if isinstance(value, bool):
            flags[key] = value
    ent.flags = flags
    ent.save(update_fields=["flags", "updated_at"])
    return ent


def set_exclusive_freelancer_tier_flag(user, tier: str):
    """
    Enforce single active freelancer tier across native/dynamic/demer flags.
    """
    if tier not in ("native", "dynamic", "demer"):
        raise ValueError("tier must be one of: native, dynamic, demer")
    flags = {"native": False, "dynamic": False, "demer": False, tier: True, "freelancer": True}
    return merge_entitlement_flags(user, flags)


def _personal_claims(user, entitlements: list[str]) -> dict[str, Any]:
    return {
        "entitlements": sorted(set(entitlements)),
        "tenant_kind": "user",
        "tenant_id": str(user.id),
        "org_id": None,
        "org_role": "",
        "user_id": user.pk,
    }


def resolve_organization_role(user, org: Organization) -> OrganizationRole | None:
    """Effective org role for this user (`None` = not part of organization)."""

    if org.owner_id == user.id:
        return OrganizationRole.OWNER

    membership = OrganizationMembership.objects.filter(organization_id=org.id, user_id=user.id).first()
    if not membership:
        return None
    return OrganizationRole(membership.role)


def resolve_organization_org_and_role(user, org_uuid: uuid.UUID) -> tuple[Organization | None, OrganizationRole | None]:
    try:
        org = Organization.objects.get(pk=org_uuid)
    except Organization.DoesNotExist:
        return None, None

    role = resolve_organization_role(user, org)
    if role is None:
        return org, None
    return org, role


def org_role_can_manage_members(role: OrganizationRole) -> bool:
    """List / invite teammates (not platform-wide admin)."""

    return role in (OrganizationRole.OWNER, OrganizationRole.ADMIN)


def org_role_can_change_roles(actor: OrganizationRole) -> bool:
    """Promote/demote members — owner and admin (admin with scoped limits in view logic)."""

    return actor in (OrganizationRole.OWNER, OrganizationRole.ADMIN)


def user_can_manage_organization_dashboard(user: OrganizationRole) -> bool:
    """Scoped org admin UX (similar to tenant admin — not Django staff ADMIN)."""

    return user in (OrganizationRole.OWNER, OrganizationRole.ADMIN)


def build_auth_claims(user, acting_organization_id: str | uuid.UUID | None = None, *, strict_org: bool = False) -> dict[str, Any]:
    """
    Canonical session claims mirrored into JWT access + login response body.

    If `acting_organization_id` is set but the user cannot access that org,
    raises `PermissionDenied` when strict_org=True; otherwise falls back to the personal tenant (legacy soft ignore).
    """
    ent = get_or_create_entitlement(user)
    flags = ent.flags or {}

    entitlements: list[str] = []
    if flags.get("base", True):
        entitlements.append("base")
    # Backward-compatible baseline workspace entitlement from legacy single-role account type.
    if getattr(user, "is_freelancer", False):
        entitlements.append("freelancer")
    if getattr(user, "is_client", False):
        entitlements.append("client")
    if getattr(user, "is_support_agent", False):
        entitlements.append("support")
    if getattr(user, "is_admin", False):
        entitlements.append("admin")
    # Additive capability flags.
    if flags.get("freelancer"):
        entitlements.append("freelancer")
    if flags.get("client"):
        entitlements.append("client")
    if flags.get("support"):
        entitlements.append("support")
    if flags.get("admin"):
        entitlements.append("admin")
    if flags.get("native"):
        entitlements.append("native")
    if flags.get("dynamic"):
        entitlements.append("dynamic")
    if flags.get("demer"):
        entitlements.append("demer")

    if not acting_organization_id:
        return _personal_claims(user, entitlements)

    oid = acting_organization_id
    if isinstance(oid, str):
        oid = oid.strip()
        try:
            org_uuid = uuid.UUID(oid)
        except ValueError:
            if strict_org:
                raise PermissionDenied(detail="Invalid organization id.")
            return _personal_claims(user, entitlements)
    elif isinstance(oid, uuid.UUID):
        org_uuid = oid
    else:
        return _personal_claims(user, entitlements)

    org, role = resolve_organization_org_and_role(user, org_uuid)
    if org is None:
        if strict_org:
            raise PermissionDenied(detail="Organization not found.")
        return _personal_claims(user, entitlements)
    if role is None:
        if strict_org:
            raise PermissionDenied(detail="You do not belong to this organization.")
        return _personal_claims(user, entitlements)

    if "organization" not in entitlements:
        entitlements.append("organization")

    return {
        "entitlements": sorted(set(entitlements)),
        "tenant_kind": "organization",
        "tenant_id": str(org.id),
        "org_id": str(org.id),
        "org_role": role.value,
        "user_id": user.pk,
    }


def get_recruited_freelancer_ids(recruiter_user) -> list[str]:
    """UUID strings for Freelancer PKs recruited by this user (AI `allowed_freelancer_ids`)."""

    RecruitedFreelancer = apps.get_model("tenancy", "RecruitedFreelancer")
    return [
        str(x)
        for x in RecruitedFreelancer.objects.filter(recruiter=recruiter_user).values_list(
            "freelancer_id",
            flat=True,
        )
    ]
