"""
คุมงบ LLM รายเดือนต่อผู้ให้บริการ (groq / openai / deepseek / gemini)

ตั้งค่าใน .env (หน่วยบาท):
  AI_BUDGET_THB_<PROVIDER>=500                 งบต่อเดือน
  AI_PRICE_THB_PER_1M_INPUT_<PROVIDER>=...     ราคา token ขาเข้าต่อ 1 ล้าน token
  AI_PRICE_THB_PER_1M_OUTPUT_<PROVIDER>=...    ราคา token ขาออกต่อ 1 ล้าน token

ไม่ใส่ราคาตายตัวในโค้ด เพราะราคาของผู้ให้บริการเปลี่ยนบ่อย ถ้ายังไม่ตั้งราคา ระบบยังบันทึก token
แต่คำนวณเงินไม่ได้ จึงไม่บล็อก (และแสดงว่า "ยังไม่ตั้งราคา" ในหน้าตั้งค่า)
"""

import os
from decimal import Decimal
from typing import Dict, Optional, Tuple

from django.db.models import Sum
from django.utils import timezone

from intelligence.models import AIUsageLog

PROVIDERS = ('groq', 'openai', 'deepseek', 'gemini')


def _env_decimal(name: str) -> Optional[Decimal]:
    raw = os.environ.get(name, '').strip()
    try:
        return Decimal(raw) if raw else None
    except ArithmeticError:
        return None


def budget_thb(provider: str) -> Optional[Decimal]:
    return _env_decimal(f'AI_BUDGET_THB_{provider.upper()}')


def estimate_cost_thb(provider: str, prompt_tokens: int, completion_tokens: int) -> Optional[Decimal]:
    price_in = _env_decimal(f'AI_PRICE_THB_PER_1M_INPUT_{provider.upper()}')
    price_out = _env_decimal(f'AI_PRICE_THB_PER_1M_OUTPUT_{provider.upper()}')
    if price_in is None or price_out is None:
        return None
    return (price_in * prompt_tokens + price_out * completion_tokens) / Decimal(1_000_000)


def month_spend_thb(provider: str) -> Decimal:
    start = timezone.localtime().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total = AIUsageLog.objects.filter(provider=provider, created_at__gte=start).aggregate(s=Sum('estimated_cost_thb'))['s']
    return total or Decimal('0')


def check_budget(provider: str) -> Tuple[bool, str]:
    """เรียกก่อนใช้ LLM: งบเดือนนี้หมดแล้วหรือยัง"""
    cap = budget_thb(provider)
    if cap is None:
        return True, ''
    if month_spend_thb(provider) >= cap:
        return False, f'งบ AI ของ {provider} เดือนนี้ครบ {cap} บาทแล้ว กรุณาติดต่อผู้ดูแลระบบ'
    return True, ''


def record_usage(provider: str, model_name: str, usage: Dict[str, int], purpose: str, user=None) -> AIUsageLog:
    prompt_tokens = int((usage or {}).get('prompt_tokens') or 0)
    completion_tokens = int((usage or {}).get('completion_tokens') or 0)
    return AIUsageLog.objects.create(
        provider=provider or 'unknown',
        model_name=model_name or '',
        purpose=purpose,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        estimated_cost_thb=estimate_cost_thb(provider, prompt_tokens, completion_tokens),
        user=user if getattr(user, 'is_authenticated', False) else None,
    )


def monthly_summary():
    """สรุปการใช้เดือนนี้ต่อผู้ให้บริการ สำหรับแสดงในหน้าตั้งค่า"""
    start = timezone.localtime().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    rows = []
    for provider in PROVIDERS:
        agg = AIUsageLog.objects.filter(provider=provider, created_at__gte=start).aggregate(
            tokens_in=Sum('prompt_tokens'), tokens_out=Sum('completion_tokens'), cost=Sum('estimated_cost_thb'))
        priced = estimate_cost_thb(provider, 0, 0) is not None
        rows.append({
            'provider': provider,
            'tokens_in': agg['tokens_in'] or 0,
            'tokens_out': agg['tokens_out'] or 0,
            'cost': agg['cost'] or Decimal('0'),
            'budget': budget_thb(provider),
            'priced': priced,
        })
    return rows
