"""
Development Settings for Dr. Patt Clinical EMR.
"""

from .base import *

DEBUG = True

SECRET_KEY = os.getenv(
    'DJANGO_SECRET_KEY', 
    'django-insecure-dev-key-never-use-this-in-production-min-50-characters-long'
)

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', 'testserver']

# ทดสอบ LINE กับมือถือจริงผ่าน tunnel: DEV_TUNNEL_HOSTS=.trycloudflare.com
# host เหล่านี้เข้าได้เฉพาะ LINE webhook / LIFF (ดู DevTunnelGuardMiddleware)
DEV_TUNNEL_HOSTS = tuple(h.strip().lower() for h in os.getenv('DEV_TUNNEL_HOSTS', '').split(',') if h.strip())
ALLOWED_HOSTS += list(DEV_TUNNEL_HOSTS)
if DEV_TUNNEL_HOSTS:
    MIDDLEWARE = ['accounts.middleware.DevTunnelGuardMiddleware'] + MIDDLEWARE
    # LIFF เปิดผ่าน https ของ tunnel และส่ง X-Forwarded-Proto มา
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Database: PostgreSQL with SQLite fallback for offline development
DB_NAME = os.getenv('DB_NAME', 'drpatrcl_sys')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = os.getenv('DB_PORT', '5432')

if os.getenv('USE_SQLITE', 'False').lower() in ('true', '1'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': DB_NAME,
            'USER': DB_USER,
            'PASSWORD': DB_PASSWORD,
            'HOST': DB_HOST,
            'PORT': DB_PORT,
            'CONN_MAX_AGE': 60,
        }
    }

# ใน dev เราปิด session cookie secure เพื่อให้เทสผ่าน http://localhost ได้
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
