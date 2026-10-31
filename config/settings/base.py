"""
Django Base Settings for Dr. Patt Clinical EMR.
Enforces the 15 Security Pillars (The Iron Rules).
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project: BASE_DIR is /Users/tanchonl/Documents/tspiN
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables
load_dotenv(BASE_DIR / '.env')

# Add apps folder to Python path
sys.path.insert(0, str(BASE_DIR / 'apps'))

# ==============================================================================
# 1. AUTHENTICATION & PASSWORD HASHING (Pillar 1)
# ==============================================================================
# ใช้ Custom User Model เพื่อรองรับ Role-Based Access Control (RBAC) ทางการแพทย์
AUTH_USER_MODEL = 'accounts.User'

# ⚠️ ปลอดภัยสูงสุด: บังคับใช้ Argon2 hasher แทน PBKDF2 ตาม Pillar 1
# ทำไมปลอดภัย: Argon2 เป็นผู้ชนะเลิศ Password Hashing Competition (PHC)
# มีการป้องกันการโจมตีแบบ GPU/ASIC Cracking ด้วยการใช้ Memory-hard computational cost
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 12},  # ⚠️ บังคับความยาวขั้นต่ำ 12 ตัวอักษร
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ==============================================================================
# 2. SESSION COOKIE SECURITY (Pillar 1)
# ==============================================================================
# ทำไมปลอดภัย: HttpOnly ป้องกัน JavaScript (XSS) ขโมย Session ID
# SameSite='Lax' ป้องกันการโจมตีข้ามไซต์ (CSRF)
# อายุ Session: 30 นาทีเมื่อไม่มีการใช้งาน (Idle) / 12 ชั่วโมง Absolute
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 1800  # 30 นาที (1800 วินาที)
SESSION_SAVE_EVERY_REQUEST = True  # รีเซ็ตตัวนับเวลา idle ทุกครั้งที่มี request
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# ==============================================================================
# 3. CSRF & XSS PROTECTION (Pillar 4)
# ==============================================================================
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
X_FRAME_OPTIONS = 'DENY'  # ป้องกัน Clickjacking 100%
SECURE_CONTENT_TYPE_NOSNIFF = True  # ป้องกัน MIME-type confusion attacks
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# ==============================================================================
# 4. CONTENT SECURITY POLICY (django-csp - Pillar 4)
# ==============================================================================
# ทำไมปลอดภัย: บล็อกการรันสคริปต์แปลกปลอมจากภายนอก
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "https://fonts.googleapis.com",)
CSP_FONT_SRC = ("'self'", "https://fonts.gstatic.com", "data:",)
CSP_IMG_SRC = ("'self'", "data:", "https:",)
CSP_CONNECT_SRC = ("'self'",)

# ==============================================================================
# 5. LOGIN THROTTLING (django-axes - Pillar 1 & 7)
# ==============================================================================
# ล็อกอินผิด 5 ครั้งภายใน 15 นาที → Lockout ทันที
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 0.25  # 15 นาที (0.25 ชั่วโมง)
AXES_RESET_ON_SUCCESS = True
# ล็อกตามคู่ (username, IP): ถ้าล็อกตาม IP อย่างเดียว หลัง nginx ทุกคนจะเป็น IP เดียวกันและโดนล็อกพร้อมกัน
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_LOCKOUT_TEMPLATE = 'accounts/lockout.html'
AXES_ENABLE_ACCESS_FAILURE_LOG = True

# ==============================================================================
# 6. APPLICATION DEFINITION
# ==============================================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Security & Protection Packages
    'axes',

    # Local Domain Apps
    'accounts.apps.AccountsConfig',
    'patients.apps.PatientsConfig',
    'clinical.apps.ClinicalConfig',
    'intelligence.apps.IntelligenceConfig',
    'portal_patient.apps.PortalPatientConfig',
    'core.apps.CoreConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'csp.middleware.CSPMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # ⚠️ Session Timeout Enforcement (30 นาที idle / 12 ชั่วโมง absolute)
    'accounts.middleware.IdleSessionTimeoutMiddleware',
    'accounts.middleware.ForcePasswordChangeMiddleware',
    # ⚠️ AxesMiddleware ต้องอยู่หลัง AuthenticationMiddleware เสมอ
    'axes.middleware.AxesMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

# ==============================================================================
# 7. TEMPLATES CONFIGURATION
# ==============================================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            # ⚠️ ห้ามปิด autoescape เด็ดขาด ป้องกัน Stored/Reflected XSS
            'autoescape': True,
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ==============================================================================
# 8. INTERNATIONALIZATION & LOCALIZATION
# ==============================================================================
LANGUAGE_CODE = 'th'
TIME_ZONE = 'Asia/Bangkok'
USE_I18N = True
USE_TZ = True

# ==============================================================================
# 9. STATIC & MEDIA FILES
# ==============================================================================
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
# ไฟล์ทางคลินิก (เข้ารหัส) อยู่นอก MEDIA_ROOT เพื่อไม่ให้ nginx serve ตรง ๆ
PRIVATE_MEDIA_ROOT = Path(os.environ.get('PRIVATE_MEDIA_ROOT', BASE_DIR / 'private_media'))

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication Backends
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# ==============================================================================
# 10. LINE OFFICIAL ACCOUNT (Pillars 8, 14)
# ==============================================================================
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET', '')
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '')
# LIFF app id ("{channelId}-{suffix}"): ใช้ตรวจ ID token ของผู้ใช้ LINE ในฟอร์มยืนยันตัวตน
LINE_LIFF_ID = os.environ.get('LINE_LIFF_ID', '')
# อีเมล (OTP ยืนยันตัวตนผ่าน LINE) ใช้ SMTP ของ Hostinger: ตั้งค่าใน .env
# ถ้าไม่ตั้ง EMAIL_HOST จะพิมพ์อีเมลออก console (ใช้ตอนพัฒนา)
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '465'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'True' if EMAIL_PORT == 465 else 'False').lower() in ('true', '1')
EMAIL_USE_TLS = not EMAIL_USE_SSL and EMAIL_PORT == 587
EMAIL_TIMEOUT = 15
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'no-reply@localhost')
EMAIL_BACKEND = (
    'django.core.mail.backends.smtp.EmailBackend' if EMAIL_HOST
    else 'django.core.mail.backends.console.EmailBackend'
)

# คีย์เข้ารหัสข้อมูลทางคลินิก (เลขบัตร ปชช., ไฟล์ LINE) แยกจาก SECRET_KEY เพื่อหมุน SECRET_KEY ได้โดยข้อมูลไม่เสีย
# FERNET_OLD_KEYS: คีย์เก่าคั่นด้วย , ใช้ถอดข้อมูลที่ยังไม่ได้หมุน (manage.py rotate_encryption_key)
FERNET_KEY = os.environ.get('FERNET_KEY', '').strip()
FERNET_OLD_KEYS = tuple(k.strip() for k in os.environ.get('FERNET_OLD_KEYS', '').split(',') if k.strip())

# Cache: Redis เมื่อมี REDIS_HOST (ต้องใช้ร่วมกันทุก gunicorn worker ไม่งั้น rate limit/OTP/กันเดารหัส
# จะแยกกันคนละ process) ไม่มี Redis (ตอนพัฒนา/เทสต์) ใช้ locmem
REDIS_HOST = os.environ.get('REDIS_HOST', '')
if REDIS_HOST:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': f"redis://{REDIS_HOST}:{os.environ.get('REDIS_PORT', '6379')}/1",
        }
    }
else:
    CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}

# Shared secret for Django <-> FastAPI calls. No default: unset means internal calls fail closed.
INTERNAL_API_TOKEN = os.environ.get('INTERNAL_API_TOKEN', '')
AI_SERVICE_URL = os.environ.get('AI_SERVICE_URL', 'http://127.0.0.1:8088')
# ผู้ให้บริการที่ใช้ร่าง SOAP (ต้องตรงกับ AI service) ใช้ตรวจงบก่อนเรียก
AI_SOAP_PROVIDER = os.environ.get('AI_SOAP_PROVIDER', 'groq').strip().lower()
# ให้บอท LINE ถามต่อด้วย AI (ใช้งบ) ปิดไว้เป็นค่าเริ่มต้น
AI_INTAKE_BOT_ENABLED = os.environ.get('AI_INTAKE_BOT_ENABLED', 'False').lower() in ('true', '1')

# Blanks LLM provider keys during tests so the suite never calls paid APIs
TEST_RUNNER = 'config.test_runner.OfflineAITestRunner'

# ==============================================================================
# 11. ENTERPRISE LOGGING (Rotating File Handlers)
# ==============================================================================
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} [{name}:{lineno}] {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{asctime}] {levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'django_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'django.log',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'clinical_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'clinical.log',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'security_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'security.log',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'django_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'tspi.clinical': {
            'handlers': ['console', 'clinical_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'tspi.security': {
            'handlers': ['console', 'security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

