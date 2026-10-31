"""
Production Settings for Dr. Patt Clinical EMR.
Enforces strict Production Security (Pillar 6, 8, 14).
"""

from .base import *

# ⚠️ กฎเหล็ก Pillar 6: บังคับ DEBUG = False บน Production เด็ดขาด
DEBUG = False

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY or len(SECRET_KEY) < 50:
    raise ValueError("CRITICAL: DJANGO_SECRET_KEY must be set in environment and be at least 50 chars long!")

# Django <-> FastAPI shared secret ต้องตั้งค่าเสมอบน Production
if len(INTERNAL_API_TOKEN) < 32:
    raise ValueError("CRITICAL: INTERNAL_API_TOKEN must be set in environment and be at least 32 chars long!")

# ระบุ Domain ชัดเจน ห้ามใช้ '*'
raw_hosts = os.environ.get('ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [h.strip() for h in raw_hosts.split(',') if h.strip()]
if not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS:
    raise ValueError("CRITICAL: ALLOWED_HOSTS must explicitly list production domain names without '*'!")

# Database: PostgreSQL Only in Production
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ['DB_HOST'],
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 600,  # Connection pooling 10 นาที
        'OPTIONS': {
            'sslmode': 'require',
        }
    }
}

# ==============================================================================
# HTTPS, SSL & COOKIE HARDENING (Pillar 6 & 14)
# ==============================================================================
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# อยู่หลัง nginx ที่ตั้ง X-Real-IP = $remote_addr เสมอ จึงเชื่อ header นี้ได้
# (ถ้าไม่ตั้ง rate limit แบบ key='ip' จะเห็นทุกคนเป็น IP ของ nginx และนับรวมกัน)
TRUST_X_REAL_IP = True
RATELIMIT_IP_META_KEY = 'HTTP_X_REAL_IP'
AXES_IPWARE_META_PRECEDENCE_ORDER = ('HTTP_X_REAL_IP', 'REMOTE_ADDR')

# HSTS: 1 ปี (31,536,000 วินาที) + includeSubDomains + preload
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Production Logging (Pillar 8)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json_verbose': {
            'format': '%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json_verbose',
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'axes': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
