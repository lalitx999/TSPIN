"""
LINE Official Account Integration Service for TSPI Clinic (Pillars 8, 14).
Provides Cryptographic Signature Verification, Rich Flex Message Builders,
and Secure Message Delivery Pipeline.
"""

import hmac
import re
import hashlib
import base64
import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import quote
from django.conf import settings
from django.core import signing

logger = logging.getLogger(__name__)

BOT_ON_WORD = 'เปิดบอท'
BOT_OFF_WORD = 'ปิดบอท'
# พิมพ์แบบไหนก็เปิดหรือปิดได้ แต่ต้องเป็นคำสั่งทั้งข้อความ ประโยคที่แค่มีคำนี้อยู่ (เช่น "เปิดบอทยังไง") ไม่นับ
BOT_ON_WORDS = frozenset({'เปิดบอท', 'เปิดใช้งานบอท', 'เปิดใช้บอท', 'เปิดการใช้งานบอท', 'คุยกับai', 'คุยกับเอไอ',
                          'คุยกับบอท', 'เปิดai'})
BOT_OFF_WORDS = frozenset({'ปิดบอท', 'ปิดใช้งานบอท', 'ปิดใช้บอท', 'ปิดการใช้งานบอท', 'ปิดai', 'หยุดบอท'})
_POLITE_ENDING = re.compile(r'(?:นะ)?(?:ครับผม|ครับ|คับ|ค่ะ|คะ|ค่า|จ้า|จ้ะ)$')
LINE_REGISTER_SALT = 'patients.line_register'
LINE_REGISTER_MAX_AGE_SECONDS = 24 * 60 * 60


def _command_form(text: str) -> str:
    """ตัดช่องว่าง ตัวพิมพ์ และคำลงท้ายสุภาพ เพื่อเทียบกับคำสั่ง"""
    return _POLITE_ENDING.sub('', ''.join((text or '').split()).lower().rstrip('!.'))


def is_bot_on_word(text: str) -> bool:
    return _command_form(text) in BOT_ON_WORDS


def is_bot_off_word(text: str) -> bool:
    return _command_form(text) in BOT_OFF_WORDS


def text_message(text: str) -> Dict[str, Any]:
    """ข้อความแชทธรรมดา (LINE จำกัด 5,000 ตัวอักษร)"""
    return {"type": "text", "text": text[:5000]}


def make_line_register_token(line_user_id: str) -> str:
    return signing.dumps(line_user_id, salt=LINE_REGISTER_SALT)


def read_line_register_token(token: str) -> str:
    """คืน LINE user id จากลิงก์เชื่อมบัญชี (ว่างถ้าลิงก์ปลอมหรือหมดอายุ)"""
    try:
        return signing.loads(token, salt=LINE_REGISTER_SALT, max_age=LINE_REGISTER_MAX_AGE_SECONDS)
    except signing.BadSignature:
        return ''


def line_bot_link() -> str:
    """ลิงก์เปิดแชท OA พร้อมพิมพ์คำเปิดบอทไว้ให้ ลูกค้ากดส่งอย่างเดียว"""
    return f"https://line.me/R/oaMessage/{quote(settings.LINE_OA_ID, safe='@')}/?{quote(BOT_ON_WORD)}"


def line_bot_url() -> str:
    """ลิงก์สำหรับเว็บสาธารณะ (ว่างถ้ายังไม่เปิดใช้)"""
    return line_bot_link() if settings.LINE_BOT_LINK_ENABLED else ''


class LineSecurity:
    """
    ระบบรักษาความปลอดภัยสำหรับ LINE Webhook (Pillar 14: Zero-Trust External APIs)
    ตรวจสอบลายเซ็น HMAC-SHA256 แบบ Exact-byte และ Constant-time Comparison
    """

    @staticmethod
    def verify_signature(raw_body: bytes, signature: str, secret: Optional[str] = None) -> bool:
        """
        ตรวจสอบความถูกต้องของ X-Line-Signature
        :param raw_body: ไบนารีแท้จริงของคำขอ (Raw Request Bytes) ห้าม decode ก่อน
        :param signature: ค่าที่ส่งมาใน Header X-Line-Signature
        :param secret: LINE Channel Secret
        :return: True หากลายเซ็นถูกต้องสมบูรณ์, False หากไม่ถูกต้อง
        """
        channel_secret = secret or getattr(settings, 'LINE_CHANNEL_SECRET', '')
        if not channel_secret or not signature or not raw_body:
            return False

        try:
            # คำนวณ HMAC-SHA256 ด้วย Channel Secret
            mac = hmac.new(
                channel_secret.encode('utf-8'),
                raw_body,
                hashlib.sha256
            ).digest()
            expected_signature = base64.b64encode(mac).decode('utf-8')

            # เปรียบเทียบแบบ Constant-time เพื่อป้องกัน Timing Attacks
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error(f"[LINE Security] Signature verification error: {e}")
            return False


class LineFlexMessageBuilder:
    """
    ตัวสร้างโครงสร้างข้อความ Rich Flex Message สำหรับส่งให้ผู้ป่วยบน LINE OA
    โทนเขียวเดียวกับหน้าเว็บ TSPI Clinic
    """

    GREEN = "#2E7D32"
    RED = "#B91C1C"
    BOT_OFF_POSTBACK = "action=bot_off"

    @staticmethod
    def button_message(label: str, text: str, style: str = "primary") -> Dict[str, Any]:
        return LineFlexMessageBuilder._button(label, {"type": "message", "label": label, "text": text}, style)

    @staticmethod
    def button_postback(label: str, data: str, style: str = "secondary") -> Dict[str, Any]:
        return LineFlexMessageBuilder._button(label, {"type": "postback", "label": label, "data": data, "displayText": label}, style)

    @staticmethod
    def button_uri(label: str, uri: str, style: str = "primary") -> Dict[str, Any]:
        return LineFlexMessageBuilder._button(label, {"type": "uri", "label": label, "uri": uri}, style)

    @staticmethod
    def _button(label: str, action: Dict[str, Any], style: str) -> Dict[str, Any]:
        button = {"type": "button", "style": style, "height": "sm", "action": action}
        if style == "primary":
            button["color"] = LineFlexMessageBuilder.GREEN
        return button

    @classmethod
    def close_button(cls) -> Dict[str, Any]:
        return {"type": "button", "style": "link", "height": "sm", "color": "#64748B",
                "action": {"type": "postback", "label": "ปิดบอท", "data": cls.BOT_OFF_POSTBACK, "displayText": "ปิดบอท"}}

    @classmethod
    def with_close_button(cls, message: Dict[str, Any]) -> Dict[str, Any]:
        """เติมปุ่มปิดบอทลงการ์ดที่มีอยู่แล้ว (ใบนัด, รายงาน) โดยไม่แก้การ์ดต้นฉบับ"""
        bubble = dict(message["contents"])
        footer = dict(bubble.get("footer") or {"type": "box", "layout": "vertical", "spacing": "sm", "contents": []})
        footer["contents"] = [*footer["contents"], cls.close_button()]
        bubble["footer"] = footer
        return {**message, "contents": bubble}

    @classmethod
    def build_bot_card(cls, title: str, body: str, buttons: Optional[List[Dict[str, Any]]] = None,
                       danger: bool = False, closable: bool = True) -> Dict[str, Any]:
        """การ์ดข้อความของบอท ทุกข้อความใช้แบบเดียวกัน และมีปุ่มปิดบอทเสมอ (ยกเว้นการ์ดยืนยันว่าปิดแล้ว)"""
        footer = list(buttons or [])
        if closable:
            footer.append(cls.close_button())
        bubble: Dict[str, Any] = {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "lg",
                "backgroundColor": cls.RED if danger else cls.GREEN,
                "contents": [
                    {"type": "text", "text": "TSPI Clinic", "color": "#FFFFFFCC", "size": "xs"},
                    {"type": "text", "text": title, "color": "#FFFFFF", "size": "lg", "weight": "bold", "wrap": True, "margin": "xs"},
                ],
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "lg",
                "contents": [{"type": "text", "text": body, "size": "md", "color": "#0F172A", "wrap": True, "lineSpacing": "6px"}],
            },
        }
        if footer:
            bubble["footer"] = {"type": "box", "layout": "vertical", "spacing": "sm", "contents": footer}
        return {"type": "flex", "altText": f"{title}: {body}"[:400], "contents": bubble}

    @classmethod
    def default_quick_replies(cls) -> List[Dict[str, Any]]:
        """ปุ่มลัดสไตล์ Gemini ด้านล่างห้องแชท LINE"""
        return [
            {"type": "action", "action": {"type": "message", "label": "อธิบายง่ายขึ้น", "text": "อธิบายให้เข้าใจง่ายกว่านี้หน่อยครับ"}},
            {"type": "action", "action": {"type": "message", "label": "ซักประวัติเพิ่ม", "text": "ช่วยซักประวัติอาการต่อเลยครับ"}},
            {"type": "action", "action": {"type": "message", "label": "ดูใบนัดหมาย", "text": "นัดหมาย"}},
            {"type": "action", "action": {"type": "postback", "label": "ปิดบอท (คุยเจ้าหน้าที่)", "data": cls.BOT_OFF_POSTBACK, "displayText": "ปิดบอท"}},
        ]

    @classmethod
    def build_bot_welcome_card(cls, patient_name: str, idle_text: str, off_word: str = "ปิดบอท") -> Dict[str, Any]:
        """การ์ดต้อนรับเมื่อเปิดบอทใน LINE โทน Gemini Clean พร้อม Quick Reply"""
        greeting = f"สวัสดีครับคุณ{patient_name}"
        desc = (
            f"ผมเป็นผู้ช่วย AI ของคลินิก TSPI เล่าอาการ ส่งรูปภาพ หรือสอบถามข้อมูลสุขภาพได้เลยครับ "
            f"ทีมแพทย์สามารถเปิดอ่านบทสนทนานี้ได้\n\n"
            f"หากเงียบเกิน {idle_text} ระบบจะปิดบอทให้อัตโนมัติ หรือพิมพ์ \"{off_word}\" เพื่อคุยกับเจ้าหน้าที่ได้ตลอดครับ"
        )
        bubble = {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "horizontal",
                "backgroundColor": "#F0F6FF",
                "paddingAll": "lg",
                "alignItems": "center",
                "contents": [
                    {
                        "type": "box",
                        "layout": "vertical",
                        "width": "10px",
                        "height": "10px",
                        "cornerRadius": "5px",
                        "backgroundColor": "#1A73E8",
                        "contents": [],
                    },
                    {
                        "type": "text",
                        "text": "TSPI AI · พร้อมดูแลคุณ",
                        "weight": "bold",
                        "size": "sm",
                        "color": "#174EA6",
                        "margin": "sm",
                        "flex": 1,
                    },
                ],
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "lg",
                "spacing": "sm",
                "contents": [
                    {"type": "text", "text": greeting, "weight": "bold", "size": "lg", "color": "#111827", "wrap": True},
                    {"type": "text", "text": desc, "size": "sm", "color": "#374151", "wrap": True, "lineSpacing": "6px"},
                ],
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "paddingTop": "none",
                "contents": [cls.close_button()],
            },
        }
        return {
            "type": "flex",
            "altText": f"{greeting} พร้อมคุยกับผู้ช่วย AI ของคลินิกแล้วครับ"[:400],
            "contents": bubble,
            "quickReply": {"items": cls.default_quick_replies()},
        }

    @classmethod
    def build_assistant_reply(
        cls,
        answer: str,
        kind: str = "answer",
        sources: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        การ์ดคำตอบ AI บน LINE โทน Gemini Clean:
        - แยกส่วนข้อมูลคลินิก vs กล่องความรู้ทั่วไปเพิ่มเติม
        - แสดงแหล่งอ้างอิงแบบกะทัดรัด (ถ้ามี)
        - แนบ Quick Reply ลัดด้านล่างสำหรับกดถามต่อทันที
        """
        raw = (answer or "").strip()
        heading = "ข้อมูลทั่วไปเพิ่มเติม"
        idx = raw.find(heading)
        if kind == "general" and idx < 0:
            clinic_part, general_part = "", raw
        elif idx >= 0:
            clinic_part = raw[:idx].strip()
            general_part = raw[idx:].split(":", 1)[-1].strip() if ":" in raw[idx:].splitlines()[0] else raw[idx + len(heading):].strip()
        else:
            clinic_part, general_part = raw, ""

        body_contents: List[Dict[str, Any]] = []
        if clinic_part:
            body_contents.append({
                "type": "text",
                "text": clinic_part[:1800],
                "size": "sm",
                "color": "#1F2937",
                "wrap": True,
                "lineSpacing": "6px",
            })

        if general_part:
            body_contents.append({
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#F8FAFC",
                "borderColor": "#CBD5E1",
                "borderWidth": "1px",
                "cornerRadius": "12px",
                "paddingAll": "md",
                "margin": "md" if clinic_part else "none",
                "spacing": "xs",
                "contents": [
                    {
                        "type": "text",
                        "text": "ความรู้ทั่วไปเพิ่มเติม · ไม่ใช่เอกสารคลินิก",
                        "size": "xxs",
                        "weight": "bold",
                        "color": "#475569",
                        "wrap": True,
                    },
                    {
                        "type": "text",
                        "text": general_part[:1400],
                        "size": "sm",
                        "color": "#334155",
                        "wrap": True,
                        "lineSpacing": "5px",
                    },
                ],
            })

        if not body_contents:
            body_contents.append({"type": "text", "text": raw[:1800] or "-", "size": "sm", "color": "#1F2937", "wrap": True})

        clean_sources = [str(s).strip() for s in (sources or []) if str(s).strip()][:3]
        if clean_sources:
            body_contents.append({"type": "separator", "margin": "md", "color": "#EEF2F7"})
            body_contents.append({
                "type": "text",
                "text": "อ้างอิง TSPI: " + " · ".join(clean_sources),
                "size": "xxs",
                "color": "#64748B",
                "wrap": True,
                "margin": "sm",
            })

        badge_text = "ข้อมูลคลินิก TSPI" if clean_sources else "คำแนะนำสุขภาพเบื้องต้น"
        bubble: Dict[str, Any] = {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "horizontal",
                "backgroundColor": "#F0F6FF",
                "paddingAll": "md",
                "alignItems": "center",
                "contents": [
                    {
                        "type": "box",
                        "layout": "vertical",
                        "width": "8px",
                        "height": "8px",
                        "cornerRadius": "4px",
                        "backgroundColor": "#1A73E8",
                        "contents": [],
                    },
                    {
                        "type": "text",
                        "text": f"TSPI AI · {badge_text}",
                        "size": "xs",
                        "weight": "bold",
                        "color": "#174EA6",
                        "margin": "sm",
                        "flex": 1,
                    },
                ],
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "lg",
                "contents": body_contents,
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "paddingTop": "none",
                "contents": [cls.close_button()],
            },
        }
        return {
            "type": "flex",
            "altText": (raw or "คำตอบจาก TSPI AI")[:400],
            "contents": bubble,
            "quickReply": {"items": cls.default_quick_replies()},
        }

    @staticmethod
    def build_welcome_card(binding_url: Optional[str] = None) -> Dict[str, Any]:
        """การ์ดต้อนรับและปุ่มเชื่อมต่อเวชระเบียนคลินิก TSPI"""
        body_contents = [
            {
                "type": "text",
                "text": "TSPI CLINIC PRECISION MEDICINE",
                "weight": "bold",
                "color": "#2E7D32",
                "size": "xs"
            },
            {
                "type": "text",
                "text": "ยินดีต้อนรับสู่ระบบดูแลสุขภาพเฉพาะบุคคล",
                "weight": "bold",
                "size": "md",
                "margin": "md",
                "wrap": True
            },
            {
                "type": "text",
                "text": "ท่านสามารถตรวจสอบผลตรวจ 39 แกนชีวภาพ รายงานการแพทย์แม่นยำ และตารางนัดหมายแพทย์ได้โดยตรง",
                "size": "xs",
                "color": "#64748b",
                "margin": "sm",
                "wrap": True
            }
        ]

        footer_contents = []
        if binding_url:
            footer_contents.append({
                "type": "button",
                "style": "primary",
                "color": "#2E7D32",
                "height": "sm",
                "action": {
                    "type": "uri",
                    "label": "เชื่อมต่อประวัติการรักษา (HN)",
                    "uri": binding_url
                }
            })
        else:
            footer_contents.append({
                "type": "button",
                "style": "secondary",
                "height": "sm",
                "action": {
                    "type": "message",
                    "label": "สอบถามเจ้าหน้าที่",
                    "text": "ติดต่อเจ้าหน้าที่คลินิก"
                }
            })

        return {
            "type": "flex",
            "altText": "ยินดีต้อนรับสู่ TSPI Precision Medicine Clinic",
            "contents": {
                "type": "bubble",
                "size": "mega",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": body_contents
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": footer_contents
                }
            }
        }

    @staticmethod
    def build_appointment_card(patient_name: str, appt_date: str, appt_time: str, doctor_name: Optional[str] = None) -> Dict[str, Any]:
        """การ์ดแจ้งเตือนและยืนยันตารางนัดหมายแพทย์"""
        return {
            "type": "flex",
            "altText": f"แจ้งเตือนนัดหมายแพทย์สำหรับคุณ {patient_name}",
            "contents": {
                "type": "bubble",
                "size": "mega",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": "#2E7D32",
                    "contents": [
                        {
                            "type": "text",
                            "text": "ใบนัดหมายแพทย์ / APPOINTMENT",
                            "color": "#ffffff",
                            "size": "xs",
                            "weight": "bold"
                        }
                    ]
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"คุณ {patient_name}",
                            "weight": "bold",
                            "size": "lg"
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "margin": "lg",
                            "spacing": "sm",
                            "contents": [
                                {
                                    "type": "box",
                                    "layout": "baseline",
                                    "contents": [
                                        {"type": "text", "text": "วันที่นัด:", "color": "#64748b", "size": "xs", "flex": 2},
                                        {"type": "text", "text": str(appt_date), "weight": "bold", "color": "#0f172a", "size": "xs", "flex": 4}
                                    ]
                                },
                                {
                                    "type": "box",
                                    "layout": "baseline",
                                    "contents": [
                                        {"type": "text", "text": "เวลานัด:", "color": "#64748b", "size": "xs", "flex": 2},
                                        {"type": "text", "text": str(appt_time), "weight": "bold", "color": "#0f172a", "size": "xs", "flex": 4}
                                    ]
                                },
                                {
                                    "type": "box",
                                    "layout": "baseline",
                                    "contents": [
                                        {"type": "text", "text": "แพทย์ผู้ตรวจ:", "color": "#64748b", "size": "xs", "flex": 2},
                                        {"type": "text", "text": doctor_name or "แพทย์ประจำคลินิก TSPI", "color": "#0f172a", "size": "xs", "flex": 4}
                                    ]
                                }
                            ]
                        }
                    ]
                }
            }
        }

    @staticmethod
    def build_report_released_card(patient_name: str, report_title: str, portal_url: str) -> Dict[str, Any]:
        """การ์ดแจ้งเตือนเมื่อแพทย์ลงนามอนุมัติรายงานการแพทย์แม่นยำ (Approved Precision Report)"""
        return {
            "type": "flex",
            "altText": f"รายงานการแพทย์แม่นยำของคุณ {patient_name} พร้อมให้เข้าดูแล้ว",
            "contents": {
                "type": "bubble",
                "size": "mega",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": "#059669",
                    "contents": [
                        {
                            "type": "text",
                            "text": "PRECISION MEDICINE REPORT READY",
                            "color": "#ffffff",
                            "size": "xs",
                            "weight": "bold"
                        }
                    ]
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"เรียนคุณ {patient_name}",
                            "weight": "bold",
                            "size": "md"
                        },
                        {
                            "type": "text",
                            "text": "แพทย์ผู้เชี่ยวชาญได้ทำการวิเคราะห์ 39 แกนชีววิทยาและลงนามอนุมัติรายงานของท่านเรียบร้อยแล้ว",
                            "size": "xs",
                            "color": "#475569",
                            "margin": "sm",
                            "wrap": True
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "margin": "md",
                            "paddingAll": "md",
                            "backgroundColor": "#f0fdf4",
                            "borderColor": "#bbf7d0",
                            "borderWidth": "1px",
                            "cornerRadius": "8px",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": report_title,
                                    "weight": "bold",
                                    "size": "xs",
                                    "color": "#166534"
                                }
                            ]
                        }
                    ]
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#059669",
                            "height": "sm",
                            "action": {
                                "type": "uri",
                                "label": "เปิดดูรายงานสุขภาพฉบับคนไข้",
                                "uri": portal_url
                            }
                        }
                    ]
                }
            }
        }


class LineMessagingService:
    """
    บริการส่งข้อความผ่าน LINE Messaging API
    """

    @classmethod
    def push_message(cls, to_line_id: str, messages: List[Dict[str, Any]]) -> bool:
        """
        ส่งข้อความ Push Message ไปยังผู้ใช้รายบุคคล
        """
        token = getattr(settings, 'LINE_CHANNEL_ACCESS_TOKEN', '')
        if not token:
            logger.info(f"[LINE MOCK PUSH] To: {to_line_id} | Payload: {len(messages)} messages")
            return True

        url = "https://api.line.me/v2/bot/message/push"
        payload = {
            "to": to_line_id,
            "messages": messages
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status in (200, 202)
        except Exception as e:
            logger.error(f"[LINE Push Error] Failed to push message: {e}")
            return False

    @classmethod
    def reply_message(cls, reply_token: str, messages: List[Dict[str, Any]]) -> bool:
        """
        ส่งข้อความตอบกลับ Reply Message โดยใช้ replyToken
        """
        token = getattr(settings, 'LINE_CHANNEL_ACCESS_TOKEN', '')
        if not token:
            logger.info(f"[LINE MOCK REPLY] Token: {reply_token} | Messages: {len(messages)}")
            return True

        url = "https://api.line.me/v2/bot/message/reply"
        payload = {
            "replyToken": reply_token,
            "messages": messages
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status in (200, 202)
        except Exception as e:
            logger.error(f"[LINE Reply Error] Failed to reply message: {e}")
            return False

    @classmethod
    def show_loading(cls, chat_id: str, seconds: int = 30) -> None:
        """แสดงจุดกำลังพิมพ์ในแชทระหว่างรอ AI (ไม่สำเร็จก็ไม่กระทบคำตอบ)"""
        token = getattr(settings, 'LINE_CHANNEL_ACCESS_TOKEN', '')
        if not token:
            return
        try:
            req = urllib.request.Request(
                "https://api.line.me/v2/bot/chat/loading/start",
                data=json.dumps({"chatId": chat_id, "loadingSeconds": seconds}).encode('utf-8'),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=3):
                pass
        except Exception as e:
            logger.info(f"[LINE Loading] Could not show loading: {e}")

    @classmethod
    def get_message_content(cls, message_id: str, max_bytes: int = 25 * 1024 * 1024) -> Optional[Tuple[bytes, str]]:
        """
        ดาวน์โหลดไฟล์ (รูป/เสียง/วิดีโอ/ไฟล์) ที่ผู้ใช้ส่งมา
        LINE เก็บไฟล์ไว้ให้ดึงได้ระยะสั้นเท่านั้น ต้องเรียกทันทีที่ webhook เข้ามา
        คืนค่า (bytes, content_type) หรือ None ถ้าดึงไม่สำเร็จ
        """
        token = getattr(settings, 'LINE_CHANNEL_ACCESS_TOKEN', '')
        if not token:
            logger.info(f"[LINE MOCK CONTENT] message_id={message_id} (no access token configured)")
            return None

        url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"}, method='GET')
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                data = response.read(max_bytes + 1)
                if len(data) > max_bytes:
                    logger.warning(f"[LINE Content] message_id={message_id} exceeds {max_bytes} bytes, skipped")
                    return None
                return data, response.headers.get('Content-Type', 'application/octet-stream')
        except Exception as e:
            logger.error(f"[LINE Content Error] Failed to fetch content for {message_id}: {e}")
            return None
