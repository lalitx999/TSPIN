from django.conf import settings
from django.core.checks import Error, Tags, Warning, register


@register(Tags.security, deploy=True)
def staff_login_deployment_checks(app_configs, **kwargs):
    issues = []
    alias = getattr(settings, 'STAFF_LOGIN_CACHE_ALIAS', 'default')
    configured = settings.CACHES.get(alias)
    if not configured:
        issues.append(Error('Staff login cache alias is not configured.', id='accounts.E001'))
    elif configured.get('BACKEND') not in {
        'django.core.cache.backends.redis.RedisCache',
        'django.core.cache.backends.memcached.PyMemcacheCache',
        'django.core.cache.backends.memcached.PyLibMCCache',
    }:
        issues.append(Warning('Staff login throttling needs a shared cache with atomic add/incr '
                              'for multiple workers. Current backend has not been verified.', id='accounts.W001'))
    for key, default in [('STAFF_LOGIN_IP_LIMIT_PER_MINUTE', 60), ('STAFF_LOGIN_ACCOUNT_LIMIT_PER_MINUTE', 10)]:
        value = getattr(settings, key, default)
        if type(value) is not int or value < 1:
            issues.append(Error(f'{key} must be a positive integer.', id='accounts.E002'))
    return issues
