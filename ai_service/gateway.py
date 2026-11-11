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



def _usage(data: Dict[str, Any]) -> Dict[str, int]:
    """จำนวน token จาก response แบบ OpenAI-compatible (ใช้คำนวณงบต่อผู้ให้บริการ)"""
    usage = data.get("usage") or {}
    return {
        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
        "completion_tokens": int(usage.get("completion_tokens") or 0),
    }

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
                    return {"success": True, "content": content, "raw": data,
                            "provider": "groq", "model": config.GROQ_MODEL, "usage": _usage(data)}
                else:
                    logger.error(f"Groq API Error [{resp.status_code}]: {resp.text}")
                    return {"success": False, "error": f"HTTP_{resp.status_code}", "detail": resp.text}
        except Exception as e:
            logger.error(f"Groq Request Exception: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # =========================================================================
    # 1b. OPENAI (ChatGPT) CLIENT
    # =========================================================================
    async def call_openai_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Calls OpenAI Chat Completions. ไม่ส่ง temperature เพราะโมเดลตระกูล reasoning รับเฉพาะค่าเริ่มต้น"""
        if not config.is_openai_available():
            return {"success": False, "error": "OPENAI_NOT_CONFIGURED",
                    "content": "ขออภัยครับ ไม่พบการตั้งค่า OPENAI_API_KEY / OPENAI_MODEL ในระบบ"}

        payload: Dict[str, Any] = {
            "model": config.OPENAI_MODEL,
            "messages": messages,
            "max_completion_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}", "Content-Type": "application/json"},
                    json=payload,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return {"success": True, "content": data["choices"][0]["message"]["content"], "raw": data,
                            "provider": "openai", "model": config.OPENAI_MODEL, "usage": _usage(data)}
                logger.error(f"OpenAI API Error [{resp.status_code}]")
                return {"success": False, "error": f"HTTP_{resp.status_code}"}
        except Exception as e:
            logger.error(f"OpenAI Request Exception: {e}", exc_info=True)
            return {"success": False, "error": type(e).__name__}

    async def call_chat(
        self,
        provider: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> Dict[str, Any]:
        """เรียกผู้ให้บริการแชทตามที่ตั้งค่าไว้ (groq | openai)"""
        fmt = {"type": "json_object"} if json_mode else None
        if provider == "openai":
            return await self.call_openai_chat(messages, max_tokens=max_tokens,
                                               response_format=fmt if config.is_openai_available() else None)
        return await self.call_groq_chat(messages, temperature=temperature, max_tokens=max_tokens,
                                         response_format=fmt if config.is_groq_available() else None)

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
    async def _post_gemini_generate(
        self,
        system_prompt: str,
        contents: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        response_mime_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """ตัวช่วยกลางเรียก Gemini generateContent (ส่งคีย์ทาง header และคัดกรอง thought)"""
        chosen_model = model or config.GEMINI_FLASH_MODEL
        meta = {"provider": "gemini", "model": chosen_model, "usage": {"prompt_tokens": 0, "completion_tokens": 0}}
        if not config.is_gemini_available():
            return {"success": False, "error": "GEMINI_API_KEY_MISSING", **meta}

        gen_cfg: Dict[str, Any] = {
            "temperature": temperature,
            "maxOutputTokens": max(max_tokens, 8192),
            "thinkingConfig": {"thinkingBudget": 512},
        }
        if response_mime_type:
            gen_cfg["responseMimeType"] = response_mime_type

        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": contents,
            "generationConfig": gen_cfg,
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{chosen_model}:generateContent"
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=10.0)) as client:
                resp = await client.post(url, json=payload, headers={"x-goog-api-key": config.GEMINI_API_KEY})
            if resp.status_code != 200:
                logger.error(f"Gemini error [{resp.status_code}]: {resp.text[:500]}")
                return {"success": False, "error": f"HTTP_{resp.status_code}", **meta}
            data = resp.json()
            usage = data.get("usageMetadata") or {}
            meta["usage"] = {
                "prompt_tokens": int(usage.get("promptTokenCount") or 0),
                "completion_tokens": int(usage.get("candidatesTokenCount") or 0) + int(usage.get("thoughtsTokenCount") or 0),
            }
            candidates = data.get("candidates") or []
            if not candidates:
                return {"success": False, "error": "EMPTY_GEMINI_CANDIDATES", **meta}
            candidate_parts = (candidates[0].get("content") or {}).get("parts") or []
            # แยก thought ออกจากเนื้อหาหลัก (ใน Gemini 2.5 parts อาจมี thought: true)
            text = "".join(p.get("text", "") for p in candidate_parts if not p.get("thought"))
            if not text:
                text = "".join(p.get("text", "") for p in candidate_parts)
            if not text:
                return {"success": False, "error": "EMPTY_GEMINI_CANDIDATES", **meta}
            return {"success": True, "content": text, **meta}
        except Exception as e:
            logger.error(f"Gemini request exception: {type(e).__name__}", exc_info=True)
            return {"success": False, "error": type(e).__name__, **meta}

    async def call_gemini_json(
        self,
        system_prompt: str,
        user_text: str,
        images: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> Dict[str, Any]:
        """
        ข้อความ + รูปหลายรูป -> คำตอบ JSON จาก Gemini
        images: [{"data": bytes, "mime_type": "image/jpeg"}] ต้องผ่าน MediaSanitizer มาก่อน
        """
        import base64
        parts: List[Dict[str, Any]] = [{"text": user_text}]
        for img in images or []:
            parts.append({"inline_data": {"mime_type": img.get("mime_type") or "image/jpeg",
                                          "data": base64.b64encode(img["data"]).decode("ascii")}})
        return await self._post_gemini_generate(
            system_prompt=system_prompt,
            contents=[{"role": "user", "parts": parts}],
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_mime_type="application/json",
        )

    async def call_gemini_chat(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        images: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> Dict[str, Any]:
        """แชทหลายรอบ + รูปภาพ (แนบรูปเข้ากับข้อความล่าสุดของผู้ใช้)"""
        import base64
        contents: List[Dict[str, Any]] = []
        for idx, msg in enumerate(messages):
            role = "model" if msg.get("role") == "assistant" else "user"
            parts: List[Dict[str, Any]] = [{"text": str(msg.get("content") or "")}]
            if idx == len(messages) - 1 and role == "user" and images:
                for img in images:
                    parts.append({"inline_data": {
                        "mime_type": img.get("mime_type") or "image/jpeg",
                        "data": base64.b64encode(img["data"]).decode("ascii"),
                    }})
            contents.append({"role": role, "parts": parts})
        return await self._post_gemini_generate(
            system_prompt=system_prompt,
            contents=contents,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

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
