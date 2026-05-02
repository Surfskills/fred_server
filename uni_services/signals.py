"""Side effects on uni_services models (e.g. AI engine freelancer pool)."""

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from uni_services.models import Freelancer


@receiver(post_save, sender=Freelancer)
def push_freelancer_profile_to_ai_engine(sender, instance, **kwargs):
    """After commit: upsert this freelancer into gigs-hub-ai-engine-api."""
    pk = instance.pk

    def _after_commit() -> None:
        from uni_services.integrations.ai_freelancer_sync import schedule_freelancer_pool_sync

        try:
            fl = Freelancer.objects.select_related("user").prefetch_related(
                "portfolio_items"
            ).get(pk=pk)
        except Freelancer.DoesNotExist:
            return
        schedule_freelancer_pool_sync(fl)

    transaction.on_commit(_after_commit)
