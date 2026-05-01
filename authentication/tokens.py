from __future__ import annotations

from rest_framework_simplejwt.tokens import RefreshToken

from tenancy.services import build_auth_claims


class GigsHubRefreshToken(RefreshToken):
    """JWT refresh + access carrying entitlement and tenant claims for API scoping."""

    @classmethod
    def for_user(cls, user, acting_organization_id=None):
        token = super().for_user(user)
        acting = acting_organization_id or ""
        token["acting_org_id"] = str(acting) if acting else ""

        claims = build_auth_claims(user, acting_organization_id=acting_organization_id or None)
        access = token.access_token
        access["entitlements"] = claims["entitlements"]
        access["tenant_kind"] = claims["tenant_kind"]
        access["tenant_id"] = claims["tenant_id"]
        access["org_id"] = claims["org_id"] or ""
        access["org_role"] = claims.get("org_role") or ""
        access["user_id"] = claims["user_id"]
        return token
