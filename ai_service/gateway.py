"""
TSPI Cloud AI Gateway Client.
Integrates Multimodal Foundation Models (Gemini, Groq, DeepSeek)
with strict Environment Variable loading and Zero-Retention compliance.
"""

import json
import logging
from typing import Dict, Any, List, Optional
import httpx

from .config import config

logger = logging.getLogger("tspi.gateway")


class ExternalAIGateway:
    """Enterprise Gateway for Gemini, Groq, and DeepSeek Cloud AI services."""

    def __init__(self):
        self.timeout = httpx.Timeout(45.0, connect=10.0)

    # =========================================================================
    # 1. GROQ CLIENT (SOAP Structuring & Real-time Chat)
    # =========================================================================
    async def call_groq_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Calls Groq API using Llama-3.3-70B for high-speed clinical inference."""
        if not config.is_groq_available():
            logger.warning("GROQ_API_KEY not configured in environment. Returning fallback simulation.")
            return {
                "success": False,
                "error": "GROQ_API_KEY_MISSING",
                "content": "ขออภัยครับ ไม่พบการตั้งค่า GROQ_API_KEY ในระบบ"
            }

        headers = {
            "Authorization": f"Bearer {config.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload: Dict[str, Any] = {
            "model": config.GROQ_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return {"success": True, "content": content, "raw": data}
                else:
                    logger.error(f"Groq API Error [{resp.status_code}]: {resp.text}")
                    return {"success": False, "error": f"HTTP_{resp.status_code}", "detail": resp.text}
        except Exception as e:
            logger.error(f"Groq Request Exception: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # =========================================================================
    # 2. DEEPSEEK CLIENT (Deep Biological Reasoning & 39 Axes Calculation)
    # =========================================================================
    async def call_deepseek_reasoner(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        """Calls DeepSeek-R1 API for multi-factorial health balance analysis."""
        if not config.is_deepseek_available():
            logger.warning("DEEPSEEK_API_KEY not configured in environment. Returning fallback simulation.")
            return {
                "success": False,
                "error": "DEEPSEEK_API_KEY_MISSING",
                "content": "ขออภัยครับ ไม่พบการตั้งค่า DEEPSEEK_API_KEY ในระบบ"
            }

        headers = {
            "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": config.DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature
        }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
                resp = await client.post(
                    "https://api.deepseek.com/chat/completions",
                    headers=headers,
                    json=payload
                )
                if resp.status_code == 200:
                    data = resp.json()
                    message = data["choices"][0]["message"]
                    content = message.get("content", "")
                    reasoning_content = message.get("reasoning_content", "")
                    return {
                        "success": True,
                        "content": content,
                        "reasoning_content": reasoning_content,
                        "raw": data
                    }
                else:
                    logger.error(f"DeepSeek API Error [{resp.status_code}]: {resp.text}")
                    return {"success": False, "error": f"HTTP_{resp.status_code}", "detail": resp.text}
        except Exception as e:
            logger.error(f"DeepSeek Request Exception: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # =========================================================================
    # 3. GEMINI MULTIMODAL CLIENT (Voice, Lab Vision, Video Scan)
    # =========================================================================
    async def call_gemini_vision(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sends sanitized lab image to Gemini 1.5 Flash Vision for numerical extraction."""
        if not config.is_gemini_available():
            logger.warning("GEMINI_API_KEY not configured in environment. Returning fallback simulation.")
            return {
                "success": False,
                "error": "GEMINI_API_KEY_MISSING",
                "content": "ขออภัยครับ ไม่พบการตั้งค่า GEMINI_API_KEY ในระบบ"
            }

        import base64
        chosen_model = model or config.GEMINI_FLASH_MODEL
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{chosen_model}:generateContent?key={config.GEMINI_API_KEY}"
        
        base64_data = base64.b64encode(image_bytes).decode("utf-8")
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64_data
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 2048,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        text = "".join(part.get("text", "") for part in parts)
                        return {"success": True, "content": text, "raw": data}
                    return {"success": False, "error": "EMPTY_GEMINI_CANDIDATES"}
                else:
                    logger.error(f"Gemini API Error [{resp.status_code}]: {resp.text}")
                    return {"success": False, "error": f"HTTP_{resp.status_code}", "detail": resp.text}
        except Exception as e:
            logger.error(f"Gemini Request Exception: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def call_gemini_audio(
        self,
        prompt: str,
        audio_bytes: bytes,
        mime_type: str = "audio/mp3",
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transcribes Thai audio clinical complaint via Gemini 1.5 Flash Audio."""
        if not config.is_gemini_available():
            logger.warning("GEMINI_API_KEY not configured in environment. Returning fallback transcript.")
            return {
                "success": False,
                "error": "GEMINI_API_KEY_MISSING",
                "content": "คนไข้แจ้งว่ามีอาการปวดกล้ามเนื้อเรื้อรัง นอนไม่ค่อยหลับ และรู้สึกอ่อนเพลียช่วงบ่าย (Simulated Fallback)"
            }

        import base64
        chosen_model = model or config.GEMINI_FLASH_MODEL
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{chosen_model}:generateContent?key={config.GEMINI_API_KEY}"
        
        base64_data = base64.b64encode(audio_bytes).decode("utf-8")
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64_data
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 2048,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        text = "".join(part.get("text", "") for part in parts)
                        return {"success": True, "content": text, "raw": data}
                    return {"success": False, "error": "EMPTY_GEMINI_CANDIDATES"}
                else:
                    logger.error(f"Gemini Audio Error [{resp.status_code}]: {resp.text}")
                    return {"success": False, "error": f"HTTP_{resp.status_code}", "detail": resp.text}
        except Exception as e:
            logger.error(f"Gemini Audio Exception: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def call_gemini_video(
        self,
        prompt: str,
        video_bytes: bytes,
        mime_type: str = "video/mp4",
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Scans clinical video clips (wounds, tremor, gait) with temporal timestamping."""
        if not config.is_gemini_available():
            logger.warning("GEMINI_API_KEY not configured in environment. Returning fallback video summary.")
            return {
                "success": False,
                "error": "GEMINI_API_KEY_MISSING",
                "content": (
                    "บันทึกการสังเกตการณ์คลิปวิดีโอ (Simulated Fallback):\n"
                    "- [00:05] พบรอยผื่นแดงขอบเขตไม่ชัดเจนบริเวณท่อนแขนด้านใน\n"
                    "- [00:18] มีอาการเกาอย่างต่อเนื่อง ไม่พบบาดแผลเปิดหรือมีหนอง\n"
                    "- ข้อเสนอแนะ: ส่งต่อภาพขยายให้แพทย์ผู้เชี่ยวชาญวินิจฉัย"
                )
            }

        import base64
        chosen_model = model or config.GEMINI_PRO_MODEL
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{chosen_model}:generateContent?key={config.GEMINI_API_KEY}"
        
        base64_data = base64.b64encode(video_bytes).decode("utf-8")
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64_data
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 2048,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=15.0)) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        text = "".join(part.get("text", "") for part in parts)
                        return {"success": True, "content": text, "raw": data}
                    return {"success": False, "error": "EMPTY_GEMINI_CANDIDATES"}
                else:
                    logger.error(f"Gemini Video Error [{resp.status_code}]: {resp.text}")
                    return {"success": False, "error": f"HTTP_{resp.status_code}", "detail": resp.text}
        except Exception as e:
            logger.error(f"Gemini Video Exception: {e}", exc_info=True)
            return {"success": False, "error": str(e)}


gateway = ExternalAIGateway()
