"""
ภาษาของหน้าบ้าน (TH/EN)

ใช้ภาษาที่ผู้ใช้เลือก (คุกกี้ LANGUAGE_COOKIE_NAME จากปุ่มสลับภาษา) เฉพาะ URL หน้าบ้าน:
หน้าเว็บสาธารณะ, เข้าสู่ระบบ/ลงทะเบียนคนไข้, ลงทะเบียน LINE และ portal คนไข้
ทุก URL อื่น (EMR, staff, clinical, admin, API) บังคับภาษาไทยเสมอ — EMR ห้ามเปลี่ยนตาม
ไม่อ่าน Accept-Language ของเบราว์เซอร์ ค่าเริ่มต้นคือไทยจนกว่าผู้ใช้จะกดเลือก EN เอง
"""
from django.conf import settings
from django.utils import translation

FRONT_EXACT = {
    '/', '/about/', '/guide/', '/install/', '/platform/', '/protocol/', '/research/',
    '/articles/', '/news/', '/privacy/', '/terms/', '/legal/privacy/', '/legal/terms/', '/ai/',
}
FRONT_PREFIXES = (
    '/articles/',
    '/accounts/patient/',
    '/patient/',
    '/line/register/',
    '/liff/bind/',
)
# ข้อยกเว้นใต้ /patient/ ที่เป็น API ภายใน (ตอบเป็นข้อมูล ไม่ใช่หน้าเว็บ) ยังใช้ภาษาที่เลือกได้ ไม่มีผลกับ EMR


def is_front_path(path: str) -> bool:
    return path in FRONT_EXACT or path.startswith(FRONT_PREFIXES)


def front_language(request) -> str:
    lang = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME, '')
    allowed = {code for code, _ in settings.LANGUAGES}
    return lang if lang in allowed else settings.LANGUAGE_CODE


class FrontLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lang = front_language(request) if is_front_path(request.path_info) else settings.LANGUAGE_CODE
        translation.activate(lang)
        request.LANGUAGE_CODE = lang
        try:
            response = self.get_response(request)
        finally:
            translation.deactivate()
        response.headers.setdefault('Content-Language', lang)
        return response
