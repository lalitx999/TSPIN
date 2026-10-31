"""
Test runner that keeps the suite offline.

The AI gateway calls paid LLM providers whenever an API key is present, and
`.env` holds real keys. Blanking them here makes every gateway call take its
"key missing" fallback, so running tests never spends money or ships data out.
"""

import os

from django.test.runner import DiscoverRunner

AI_PROVIDER_KEYS = (
    'OPENAI_API_KEY',
    'DEEPSEEK_API_KEY',
    'GROQ_API_KEY',
    'GEMINI_API_KEY',
    'GOOGLE_AI_API_KEY',
)

TEST_INTERNAL_API_TOKEN = 'test-internal-token-for-unit-tests-only-0123456789'


class OfflineAITestRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        for key in AI_PROVIDER_KEYS:
            os.environ[key] = ''
        os.environ['INTERNAL_API_TOKEN'] = TEST_INTERNAL_API_TOKEN

        from ai_service.config import BotanyConfig
        BotanyConfig.DEEPSEEK_API_KEY = ''
        BotanyConfig.GROQ_API_KEY = ''
        BotanyConfig.GEMINI_API_KEY = ''
        BotanyConfig.INTERNAL_API_TOKEN = TEST_INTERNAL_API_TOKEN

        from django.conf import settings
        settings.INTERNAL_API_TOKEN = TEST_INTERNAL_API_TOKEN
