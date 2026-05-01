from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from tenancy.models import Organization, OrganizationMembership, OrganizationRole, UserEntitlement


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_user_entitlement(sender, instance, created, **kwargs):
    if kwargs.get("raw"):
        return
    UserEntitlement.objects.get_or_create(
        user=instance,
        defaults={"flags": {"base": True}},
    )


@receiver(post_save, sender=Organization)
def sync_organization_owner_membership(sender, instance, **kwargs):
    """Keep a canonical OrganizationMembership row for the org owner (OWNER role)."""

    if kwargs.get("raw"):
        return
    OrganizationMembership.objects.update_or_create(
        organization=instance,
        user_id=instance.owner_id,
        defaults={"role": OrganizationRole.OWNER.value},
    )
