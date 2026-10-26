from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db import connection
from django.utils.safestring import mark_safe
import markdown
import nh3

from core.models import MedicalArticle

def home(request):
    """
    Public Landing Page:
    - Hero Section with CTA 'เริ่มต้นใช้งาน'
    - 3-Phase 9-Step Recovery Protocol Overview
    - 39 Biological Axes Living Network
    - Clinical Validation & Stats
    - Latest Medical Articles & Clinical Insights (Phase 1)
    - Doctor & Clinic Credentials
    """
    latest_articles = MedicalArticle.objects.alive().filter(
        is_published=True
    ).order_by('-published_at')[:4]

    context = {
        'latest_articles': latest_articles,
    }
    return render(request, 'core/home.html', context)

def article_list_view(request):
    """
    รายการบทความทางการแพทย์และสาระสุขภาพ (Clinical Articles & Insights)
    รองรับการกรองตามหมวดหมู่
    """
    category = request.GET.get('category', '').strip()
    articles_qs = MedicalArticle.objects.alive().filter(is_published=True)
    if category:
        articles_qs = articles_qs.filter(category=category)

    articles = articles_qs.order_by('-published_at')
    categories = MedicalArticle.CATEGORY_CHOICES

    context = {
        'articles': articles,
        'selected_category': category,
        'categories': categories,
    }
    return render(request, 'core/article_list.html', context)

def article_detail_view(request, slug):
    """
    หน้ารายละเอียดบทความทางการแพทย์ฉบับเต็ม:
    - เพิ่มยอดวิว (view_count)
    - เรนเดอร์ Markdown อย่างปลอดภัยด้วย nh3 Sanitization (Gotcha 1)
    - ส่งค่า OpenGraph Meta Tags สำหรับ Facebook/LINE Share
    - แนะนำบทความที่เกี่ยวข้อง
    """
    article = get_object_or_404(
        MedicalArticle.objects.alive().filter(is_published=True),
        slug=slug
    )
    article.increment_view_count()

    # Markdown conversion + strict HTML sanitization via nh3 (Prevent XSS)
    raw_html = markdown.markdown(
        article.content,
        extensions=['extra', 'nl2br']
    )
    clean_html = nh3.clean(
        raw_html,
        tags={'p', 'br', 'strong', 'em', 'h1', 'h2', 'h3', 'h4', 'ul', 'ol', 'li', 'blockquote', 'code', 'pre', 'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'a'},
        attributes={'a': {'href', 'target'}},
        link_rel='noopener noreferrer'
    )


    related_articles = MedicalArticle.objects.alive().filter(
        is_published=True
    ).exclude(pk=article.pk).order_by('-published_at')[:3]

    context = {
        'article': article,
        'rendered_content': mark_safe(clean_html),
        'related_articles': related_articles,
        'meta_title': article.meta_title or f"{article.title} | TSPI Clinic",
        'meta_description': article.meta_description or article.excerpt,
        'og_image': article.cover_image_url or '/static/img/og_default.jpg',
    }
    return render(request, 'core/article_detail.html', context)


def platform_view(request):
    """
    Platform Deep Dive:
    - 38 Mechanistic Biological Axes (Immune, Metabolic, Cellular, Endocrine, Digestive, etc.)
    - AI Diagnostic Engine & Scoring Logic
    - Digital Twin Physiological Framework
    """
    return render(request, 'core/platform.html')

def protocol_view(request):
    """
    9-Step Clinical Recovery Protocol:
    - Phase 1: Deep Assessment, Detoxification, Gut Restoration
    - Phase 2: Metabolic Reset, Hormonal Balance, Immune Modulation
    - Phase 3: Cellular Repair, Neuroplasticity, Longevity Protocol
    """
    return render(request, 'core/protocol.html')

def research_view(request):
    """
    Research & Clinical Evidence:
    - 200 Botanical & Nutritional Modules
    - Biomarker Correlation Matrix
    - Clinical Outcome Case Studies (e.g. Case Nikom Psoriasis Recovery)
    """
    return render(request, 'core/research.html')

def about(request):
    """About TSPI Clinic & Dr. Patt Systems Biology Precision Medicine"""
    return render(request, 'core/about.html')

def guide_view(request):
    """Patient & User Onboarding Guide (Step 01 - Step 06)"""
    return render(request, 'core/guide.html')

def install_view(request):
    """PWA Mobile & Desktop Web App Installation Guide (iOS, Android, Desktop)"""
    return render(request, 'core/install.html')

def privacy_policy(request):
    """PDPA Privacy Policy & Patient Consent Governance"""
    return render(request, 'core/privacy.html')

def terms_of_service(request):
    """Terms of Service"""
    return render(request, 'core/terms.html')

def health_check_view(request):
    """
    Production Healthcheck Endpoint (/health/ and /healthz/)
    Used by Docker, Kubernetes, and Cloud Load Balancers to verify container health.
    """
    health_status = {
        'status': 'healthy',
        'database': 'unknown',
        'service': 'tspi-clinical-emr',
        'version': '1.0.0',
    }

    try:
        connection.ensure_connection()
        health_status['database'] = 'connected'
    except Exception as e:
        health_status['database'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
        return JsonResponse(health_status, status=503)

    return JsonResponse(health_status, status=200)
