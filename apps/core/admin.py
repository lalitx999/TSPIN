"""
Admin configuration for Core app and Medical Articles.
"""

from django.contrib import admin
from core.models import MedicalArticle


@admin.register(MedicalArticle)
class MedicalArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author_name', 'read_time_minutes', 'view_count', 'is_published', 'published_at')
    list_filter = ('category', 'is_published', 'published_at')
    search_fields = ('title', 'excerpt', 'content', 'author_name')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('view_count', 'created_at', 'updated_at')
    fieldsets = (
        ('เนื้อหาบทความ (Article Content)', {
            'fields': ('title', 'slug', 'category', 'excerpt', 'content', 'cover_image_url', 'read_time_minutes')
        }),
        ('ผู้เขียน (Author Credentials)', {
            'fields': ('author', 'author_name', 'author_title')
        }),
        ('สถานะและการเผยแพร่ (Publication)', {
            'fields': ('is_published', 'published_at', 'view_count')
        }),
        ('SEO & OpenGraph Meta Tags (Gotcha 1)', {
            'classes': ('collapse',),
            'fields': ('meta_title', 'meta_description')
        }),
    )
