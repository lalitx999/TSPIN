"""
Custom Template Tags and Filters for TSPI Clinical EMR (Pillars 2, 8, PDPA Compliance).
Provides:
- Thai Buddhist Era Date Formatting (พ.ศ. 2569)
- Thai Phone Number Masking and Formatting (081-xxx-5678)
- Thai National ID Card PDPA Masking (1-xxxx-xxxxx-45-6)
"""

from datetime import datetime, date
from django import template

register = template.Library()

THAI_MONTHS_FULL = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
]

THAI_MONTHS_SHORT = [
    "", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
    "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."
]


@register.filter(name='thai_buddhist_date')
def thai_buddhist_date(value, format_type='short'):
    """
    แปลงวันที่ ค.ศ. เป็น พ.ศ. ภาษาไทย
    format_type: 'short' (26 ต.ค. 2569) หรือ 'full' (26 ตุลาคม 2569)
    """
    if not value:
        return "-"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except Exception:
            return value

    day = value.day
    month_idx = value.month
    be_year = value.year + 543

    if format_type == 'full':
        month_name = THAI_MONTHS_FULL[month_idx]
        return f"{day} {month_name} {be_year}"
    else:
        month_name = THAI_MONTHS_SHORT[month_idx]
        return f"{day} {month_name} {be_year}"


@register.filter(name='thai_phone')
def thai_phone(value):
    """
    จัดรูปแบบเบอร์โทรศัพท์มือถือไทยให้เป็น 081-234-5678 หรือ 02-123-4567
    """
    if not value:
        return "-"
    cleaned = ''.join(c for c in str(value) if c.isdigit())
    if len(cleaned) == 10:
        return f"{cleaned[:3]}-{cleaned[3:6]}-{cleaned[6:]}"
    elif len(cleaned) == 9:
        return f"{cleaned[:2]}-{cleaned[2:5]}-{cleaned[5:]}"
    return value


@register.filter(name='mask_id_card')
def mask_id_card(value):
    """
    ปิดบังเลขประจำตัวประชาชน 13 หลักตามมาตรฐาน PDPA เช่น 1-xxxx-xxxxx-45-6
    """
    if not value:
        return "-"
    cleaned = ''.join(c for c in str(value) if c.isdigit())
    if len(cleaned) == 13:
        return f"{cleaned[0]}-xxxx-xxxxx-{cleaned[10:12]}-{cleaned[12]}"
    return "x-xxxx-xxxxx-xx-x"
