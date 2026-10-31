"""
TSPI Botany-Engine Configuration & Environment Management.
Enforces strict environment variable loading (No Hardcoded API Keys or Secrets).
Adheres to Pillar 1 & PDPA Section 26 Institutional Guidelines.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Ensure .env is loaded from workspace root
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / '.env'
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()


class BotanyConfig:
    """Centralized ENV configuration reader for AI & Security Services."""

    # AI Provider Keys
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "").strip()
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip()
    GEMINI_API_KEY: str = (
        os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_AI_API_KEY", "")
    ).strip()

    # LINE OA Credentials
    LINE_CHANNEL_SECRET: str = os.getenv("LINE_CHANNEL_SECRET", "").strip()
    LINE_CHANNEL_ACCESS_TOKEN: str = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip()

    # Internal Service-to-Service Security
    # No default: an unset token makes every internal call fail closed.
    INTERNAL_API_TOKEN: str = os.getenv("INTERNAL_API_TOKEN", "").strip()
    STORAGE_ENCRYPTION_KEY: str = os.getenv("STORAGE_ENCRYPTION_KEY", "").strip()

    # Model Versioning Standards (Configured as requested by user)
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner").strip()
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()
    GEMINI_FLASH_MODEL: str = os.getenv("GEMINI_FLASH_MODEL", "gemini-2.5-flash").strip()
    GEMINI_PRO_MODEL: str = os.getenv("GEMINI_PRO_MODEL", "gemini-2.5-pro").strip()
    # ไม่มีค่าเริ่มต้น: ต้องระบุชื่อโมเดล OpenAI ที่บัญชีใช้ได้เองใน .env
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "").strip()

    # ผู้ให้บริการที่ใช้ร่าง SOAP จากรอบซักประวัติ: groq | openai (Django อ่านค่าเดียวกันเพื่อตรวจงบก่อนเรียก)
    SOAP_PROVIDER: str = os.getenv("AI_SOAP_PROVIDER", "groq").strip().lower()

    # Zero-Retention & Privacy Compliance Headers
    ZERO_RETENTION_ENABLED: bool = os.getenv("ZERO_RETENTION_ENABLED", "True").lower() in ("true", "1", "yes")

    @classmethod
    def is_gemini_available(cls) -> bool:
        return bool(cls.GEMINI_API_KEY)

    @classmethod
    def is_groq_available(cls) -> bool:
        return bool(cls.GROQ_API_KEY)

    @classmethod
    def is_openai_available(cls) -> bool:
        return bool(cls.OPENAI_API_KEY and cls.OPENAI_MODEL)

    @classmethod
    def is_deepseek_available(cls) -> bool:
        return bool(cls.DEEPSEEK_API_KEY)

    @classmethod
    def verify_internal_token(cls, provided_token: Optional[str]) -> bool:
        """Verify internal service authorization token using constant-time comparison."""
        import hmac
        if not provided_token or not cls.INTERNAL_API_TOKEN:
            return False
        return hmac.compare_digest(provided_token.strip(), cls.INTERNAL_API_TOKEN)


config = BotanyConfig()
