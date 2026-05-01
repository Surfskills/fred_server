from django.contrib import admin

from tenancy.models import Organization, OrganizationMembership, RecruitedFreelancer, UserEntitlement


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ("organization", "user", "role", "created_at")
    list_filter = ("role",)
    search_fields = ("organization__name", "organization__slug", "user__email")
    raw_id_fields = ("organization", "user")


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "owner", "created_at")
    search_fields = ("name", "slug", "owner__email")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(UserEntitlement)
class UserEntitlementAdmin(admin.ModelAdmin):
    list_display = ("user", "primary_organization", "updated_at")
    search_fields = ("user__email",)
    raw_id_fields = ("user", "primary_organization")


@admin.register(RecruitedFreelancer)
class RecruitedFreelancerAdmin(admin.ModelAdmin):
    list_display = ("recruiter", "freelancer", "created_at")
    raw_id_fields = ("recruiter", "freelancer")
