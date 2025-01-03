from django.contrib import admin
from django.utils.html import format_html
from .models import SoftwareRequest, ResearchRequest

@admin.register(SoftwareRequest)
class SoftwareRequestAdmin(admin.ModelAdmin):
    list_display = ('project_title', 'user', 'request_type', 'budget_range', 'timeline', 'created_at', 'updated_at')
    list_filter = ('request_type', 'budget_range', 'created_at', 'updated_at')
    search_fields = ('project_title', 'project_description', 'user__email', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'project_title', 'project_description', 'request_type')
        }),
        ('Project Details', {
            'fields': ('budget_range', 'timeline')
        }),
        ('Technical Stack', {
            'fields': (
                ('frontend_languages', 'frontend_frameworks'),
                ('backend_languages', 'backend_frameworks'),
                ('ai_languages', 'ai_frameworks')
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return self.readonly_fields + ('user',)
        return self.readonly_fields

@admin.register(ResearchRequest)
class ResearchRequestAdmin(admin.ModelAdmin):
    list_display = ('project_title', 'user', 'request_type', 'academic_writing_type', 'created_at', 'updated_at')
    list_filter = ('request_type', 'academic_writing_type', 'created_at', 'updated_at')
    search_fields = ('project_title', 'project_description', 'user__email', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'project_title', 'project_description', 'request_type')
        }),
        ('Academic Writing Details', {
            'fields': (
                'academic_writing_type',
                'writing_technique',
                'research_paper_structure',
                'academic_writing_style'
            )
        }),
        ('Research Process', {
            'fields': (
                'research_paper_writing_process',
                'critical_writing_type',
                'critical_thinking_skill',
                'critical_writing_structure'
            ),
            'classes': ('collapse',)
        }),
        ('Discussion and Components', {
            'fields': (
                'discussion_type',
                'discussion_component',
                'academic_discussion_type'
            ),
            'classes': ('collapse',)
        }),
        ('Tools and Resources', {
            'fields': (
                'academic_writing_tool',
                'research_paper_database',
                'plagiarism_checker',
                'reference_management_tool',
                'citation_style'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return self.readonly_fields + ('user',)
        return self.readonly_fields
