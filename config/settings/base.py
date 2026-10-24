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

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication Backends
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]
