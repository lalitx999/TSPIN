from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
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


# ==============================================================================
# ผู้ช่วย AI บนหน้าแรก สำหรับผู้ใช้ที่ยังไม่ลงทะเบียน
# - ไม่เก็บบทสนทนาบนเซิร์ฟเวอร์ (ประวัติอยู่ในเบราว์เซอร์ของผู้ใช้) เพราะไม่รู้ตัวตนและไม่มีความยินยอม
# - จำกัดจำนวนต่อ IP ต่อวัน และเพดานรวมทั้งระบบต่อวัน เพื่อกันงบ AI หมด
# ==============================================================================
GUEST_DAILY_LIMIT_PER_IP = 15
GUEST_DAILY_LIMIT_TOTAL = 1000


@require_POST
def guest_assistant_api(request):
    import json as _json
    import httpx
    from django.conf import settings as dj_settings
    from django.core.cache import cache
    from django.utils import timezone
    from accounts.views import get_client_ip
    from intelligence import ai_budget

    try:
        body = _json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'error': 'รูปแบบข้อมูลไม่ถูกต้อง'}, status=400)

    raw = body.get('messages') if isinstance(body.get('messages'), list) else []
    history = [
        {'role': m.get('role'), 'content': str(m.get('content', ''))[:1500]}
        for m in raw[-8:]
        if isinstance(m, dict) and m.get('role') in ('user', 'assistant') and str(m.get('content', '')).strip()
    ]
    if not history or history[-1]['role'] != 'user':
        return JsonResponse({'error': 'กรุณาพิมพ์คำถาม'}, status=400)

    today = timezone.localdate().strftime('%Y%m%d')
    ip_key = f"guest_asst_{get_client_ip(request)}_{today}"
    total_key = f"guest_asst_total_{today}"
    if cache.get(ip_key, 0) >= GUEST_DAILY_LIMIT_PER_IP or cache.get(total_key, 0) >= GUEST_DAILY_LIMIT_TOTAL:
        return JsonResponse({'error': 'วันนี้ถามครบจำนวนแล้ว ลงทะเบียนเพื่อคุยต่อ หรือทักเจ้าหน้าที่ทาง LINE ได้เลยค่ะ',
                             'limited': True}, status=429)
    cache.set(ip_key, cache.get(ip_key, 0) + 1, timeout=60 * 60 * 24)
    cache.set(total_key, cache.get(total_key, 0) + 1, timeout=60 * 60 * 24)

    provider = dj_settings.AI_SOAP_PROVIDER
    allowed, budget_msg = ai_budget.check_budget(provider)
    if not allowed:
        return JsonResponse({'answer': budget_msg, 'kind': 'unavailable', 'sources': []})
    try:
        resp = httpx.post(
            f"{dj_settings.AI_SERVICE_URL}/api/ai/assistant/chat",
            json={'messages': history},
            headers={'X-Internal-Token': dj_settings.INTERNAL_API_TOKEN},
            timeout=45.0,
        )
        data = resp.json() if resp.status_code == 200 else {}
    except (httpx.HTTPError, ValueError):
        data = {}
    if any((data.get('usage') or {}).values()):
        ai_budget.record_usage(data.get('provider') or provider, data.get('model', ''), data['usage'], 'guest_assistant')
    return JsonResponse({
        'answer': data.get('answer') or 'ขออภัยค่ะ ระบบผู้ช่วยไม่พร้อมใช้งานชั่วคราว กรุณาลองใหม่ภายหลัง',
        'kind': data.get('kind', 'unavailable'),
        'sources': data.get('sources', []),
    })
