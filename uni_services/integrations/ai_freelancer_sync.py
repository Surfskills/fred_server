"""
Push Freelancer profiles to gigs-hub-ai-engine-api so matching uses a full snapshot.

Called after Freelancer saves (see uni_services.signals). Requires the same env vars as
ai_engine: GIGSHUB_AI_ENGINE_URL, GIGSHUB_AI_API_KEY.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

import requests

from uni_services.integrations.ai_engine import (
    ai_engine_configured,
    post_freelancer_sync_to_engine,
)

logger = logging.getLogger(__name__)


def build_freelancer_sync_item(freelancer) -> dict[str, Any]:
    """One FreelancerSyncItem dict — keep in sync with gigs-hub-ai-engine-api FreelancerSyncItem."""
    from django.db.models import Avg

    from uni_services.models import FreelancerReview

    user = freelancer.user
    email = getattr(user, "email", "") or ""

    reviews = FreelancerReview.objects.filter(freelancer=freelancer)
    comm_avg = 0.0
    qual_avg = 0.0
    if reviews.exists():
        agg = reviews.aggregate(
            comm=Avg("communication_rating"),
            qual=Avg("quality_rating"),
        )
        comm_avg = float(agg.get("comm") or 0)
        qual_avg = float(agg.get("qual") or 0)

    public_first = ""
    if getattr(user, "first_name", None):
        public_first = (user.first_name or "").strip()
    name = (freelancer.display_name or "").strip()
    if not public_first and name:
        public_first = name.split()[0]

    portfolio_titles = list(
        freelancer.portfolio_items.order_by("-is_featured", "-created_at").values_list(
            "title", flat=True
        )[:20]
    )

    last_active = getattr(freelancer, "last_active", None)
    last_active_iso = last_active.isoformat() if last_active else None

    return {
        "gigshub_freelancer_id": str(freelancer.id),
        "gigshub_user_id": freelancer.user_id,
        "display_name": freelancer.display_name or user.get_full_name() or email,
        "email": email,
        "title": freelancer.title or "",
        "bio": freelancer.bio or "",
        "freelancer_type": freelancer.freelancer_type,
        "experience_level": freelancer.experience_level,
        "marketplace_tier": freelancer.marketplace_tier,
        "marketplace_tier_display": freelancer.get_marketplace_tier_display(),
        "public_first_name": public_first or None,
        "portfolio_item_titles": portfolio_titles,
        "skills": freelancer.skills or [],
        "specializations": freelancer.specializations or [],
        "languages": freelancer.languages or [],
        "hourly_rate": float(freelancer.hourly_rate) if freelancer.hourly_rate else None,
        "minimum_project_budget": (
            float(freelancer.minimum_project_budget)
            if freelancer.minimum_project_budget
            else None
        ),
        "availability_status": freelancer.availability_status,
        "is_available": freelancer.is_available,
        "preferred_project_duration": freelancer.preferred_project_duration,
        "max_concurrent_projects": freelancer.max_concurrent_projects,
        "total_projects_completed": freelancer.total_projects_completed,
        "average_rating": float(freelancer.average_rating),
        "communication_rating": comm_avg,
        "quality_rating": qual_avg,
        "total_earnings": float(freelancer.total_earnings),
        "profile_completion_score": freelancer.profile_completion_score,
        "is_profile_verified": freelancer.is_profile_verified,
        "is_featured": freelancer.is_featured,
        "location": freelancer.location or "",
        "timezone": freelancer.timezone or "",
        "willing_to_travel": getattr(freelancer, "willing_to_travel", False),
        "portfolio_url": freelancer.portfolio_url or "",
        "last_active": last_active_iso,
    }


def schedule_freelancer_pool_sync(freelancer) -> None:
    """Non-blocking POST of one freelancer to the AI engine pool."""
    if not ai_engine_configured():
        logger.debug("AI engine not configured; skipping freelancer pool sync.")
        return

    item = build_freelancer_sync_item(freelancer)

    def _run() -> None:
        try:
            r = post_freelancer_sync_to_engine([item])
            if not r.ok:
                logger.warning(
                    "Freelancer pool sync failed: %s %s",
                    r.status_code,
                    r.text[:500],
                )
            else:
                logger.info("Freelancer pool sync OK for %s", item["gigshub_freelancer_id"])
        except requests.RequestException:
            logger.exception("Freelancer pool sync request error for %s", freelancer.pk)

    threading.Thread(target=_run, daemon=True).start()
