"""
Resolve JWT claims on the request for row-level scoping (no extra DB hit if decode fails).
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import UntypedToken


def get_request_claims(request) -> dict[str, Any]:
    auth = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth.startswith("Bearer "):
        return {}
    raw = auth[7:].strip()
    if not raw:
        return {}
    try:
        t = UntypedToken(raw)
        return {k: v for k, v in t.items() if k not in ("exp", "iat", "jti")}
    except InvalidToken:
        return {}
    except Exception:
        return {}
