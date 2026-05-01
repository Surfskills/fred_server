"""
Tenancy & entitlements (ERD summary)

User (AUTH_USER_MODEL)
  1──1 UserEntitlement (flags JSON: base, native, dynamic, demer — additive)
  1──* Organization (owner_id → User)   # org = upgraded Native extension
  1──* RecruitedFreelancer (recruiter_id → User, freelancer_id → Freelancer)

Organization
  *──1 User (owner)

RecruitedFreelancer
  *──1 User (recruiter)
  *──1 Freelancer

BaseService (uni_services) — posting context
  posting_tenant_kind, posting_tenant_id  # snapshot of JWT tenant at create time

JWT access claims (mirrored in login `auth_context`):
  entitlements[], tenant_kind, tenant_id, org_id?, user_id
"""
import uuid

from django.conf import settings
from django.db import models


class TenantKind(models.TextChoices):
    """Active tenancy context for JWT + row-level scoping."""

    USER = "user", "User"
    NATIVE = "native", "Native (partner-selective intake · rare niche skills)"
    DYNAMIC = "dynamic", "Dynamic (implementing-partner certification · enterprise / big-tech alum + freelance)"
    DEMER = "demer", "Demers (partner certification prerequisite · technocrats · private practice)"
    ORGANIZATION = "organization", "Organization"


class Organization(models.Model):
    """
    Organization is an upgraded Native (extension), not a separate auth principal.
    Owner remains a User; org rows scope team/project features.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_organizations",
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class OrganizationRole(models.TextChoices):
    """Role within one organization (distinct from global platform User.Types)."""

    OWNER = "owner", "Owner"
    ADMIN = "admin", "Administrator"
    SUPPORT = "support", "Support"
    MEMBER = "member", "Member"


class OrganizationMembership(models.Model):
    """Membership in an organization — owner is stored here too for uniform permission checks."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
    )
    role = models.CharField(
        max_length=20,
        choices=OrganizationRole.choices,
        default=OrganizationRole.MEMBER,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "user"),
                name="uniq_organization_membership_user",
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.organization_id}:{self.user_id}:{self.role}"


class UserEntitlement(models.Model):
    """
    Additive capability flags. Base signup implies `base` in flags; upgrades add keys
    without removing prior data (see product rules).
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="entitlement",
    )
    flags = models.JSONField(
        default=dict,
        help_text=(
            'Additive capability keys, e.g. {"base": true, "native": true, "dynamic": false, "demer": false}. '
            'native = partner-coordinated scarce intake signalling niche craft on GigsHub; '
            'dynamic = implementing-partner certifications (policy cites WeDemo Africa) before claiming tier; '
            'then enterprise / big-tech alum + freelance; '
            'demer = same partner prerequisites as policy requires; technocrats practising privately.'
        ),
    )
    primary_organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_for_users",
        help_text="Optional default org context for SaaS views.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User entitlement"

    def __str__(self):
        return f"Entitlement<{self.user.email}>"


class RecruitedFreelancer(models.Model):
    """Native recruits freelancers under their profile (visibility / AI scope)."""

    recruiter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recruited_freelancer_links",
    )
    freelancer = models.ForeignKey(
        "uni_services.Freelancer",
        on_delete=models.CASCADE,
        related_name="recruiter_links",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("recruiter", "freelancer")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.recruiter_id} → {self.freelancer_id}"
