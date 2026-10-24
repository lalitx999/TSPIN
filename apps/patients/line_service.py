"""
LINE Official Account Integration Service for TSPI Clinic (Pillars 8, 14).
Provides Cryptographic Signature Verification, Rich Flex Message Builders,
and Secure Message Delivery Pipeline.
"""

import hmac
import hashlib
import base64
import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


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
    รองรับภาษาไทย Sarabun-styled, Modern Medical Theme (Cyan / Slate / White)
    """

    @staticmethod
    def build_welcome_card(binding_url: Optional[str] = None) -> Dict[str, Any]:
        """การ์ดต้อนรับและปุ่มเชื่อมต่อเวชระเบียนคลินิก TSPI"""
        body_contents = [
            {
                "type": "text",
                "text": "TSPI CLINIC PRECISION MEDICINE",
                "weight": "bold",
                "color": "#0ea5e9",
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
                "color": "#0284c7",
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
                    "backgroundColor": "#0284c7",
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
