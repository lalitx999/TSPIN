"""Fixed-window staff login limits; use a shared atomic cache in multi-worker deployments."""
import time
from django.conf import settings
from django.core.cache import caches
from django.utils.crypto import salted_hmac
from rest_framework.throttling import BaseThrottle


class StaffLoginThrottle(BaseThrottle):
    scope = 'staff-login-ip'
    setting = 'STAFF_LOGIN_IP_LIMIT_PER_MINUTE'
    default_limit = 60

    def identity(self, request):
        # Untrusted X-Forwarded-For must not let clients rotate the throttle key.
        return request.META.get('REMOTE_ADDR') or 'unknown-peer'

    def allow_request(self, request, view):
        identity = self.identity(request)
        if identity is None:
            return True
        now = time.time()
        self.retry_after = max(1, 60 - int(now % 60))
        limit = getattr(settings, self.setting, self.default_limit)
        if type(limit) is not int or limit < 1:
            return False
        digest = salted_hmac(self.scope, identity).hexdigest()
        key = f'{self.scope}:{int(now // 60)}:{digest}'
        try:
            cache = caches[getattr(settings, 'STAFF_LOGIN_CACHE_ALIAS', 'default')]
            count = 1 if cache.add(key, 1, timeout=120) else cache.incr(key)
        except Exception:
            # A cache outage must not silently disable a public authentication limit.
            return False
        return count <= limit

    def wait(self):
        return self.retry_after


class StaffLoginAccountThrottle(StaffLoginThrottle):
    scope = 'staff-login-account'
    setting = 'STAFF_LOGIN_ACCOUNT_LIMIT_PER_MINUTE'
    default_limit = 10

    def identity(self, request):
        if not isinstance(request.data, dict):
            return None
        email = request.data.get('email')
        if not isinstance(email, str) or not email.strip() or len(email) > 254:
            return None
        return email.strip().lower()
