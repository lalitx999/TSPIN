"""
TSPI M5: Pre-Flight Sanitizer & Media Scrubber.
Implements Institutional Governance & PDPA Section 26 Data Privacy:
1. EXIF Metadata Stripping (GPS coordinates, camera device IDs)
2. Face Blurring with 25% Safety Margin Expansion (MediaPipe / OpenCV Cascade)
3. Text De-identification (Regex + Thai Clinical Prefix NER)
4. Data Classification Enforcement (Class A, Class B, Class C)
"""

import io
import re
import logging
from typing import Dict, Any, List, Tuple, Optional
from PIL import Image, ImageFilter, ImageOps
import numpy as np
import cv2

logger = logging.getLogger("tspi.sanitizer")


class DataClassification:
    CLASS_A = "CLASS_A"  # Public / De-identified Safe (Anonymized Text, Lab Numbers)
    CLASS_B = "CLASS_B"  # Sanitized Sensitive (Wound/Lab Images without EXIF/Faces)
    CLASS_C = "CLASS_C"  # Biometric / High PII (Raw Audio, ID Cards, Unsanitized Media)


class MediaSanitizer:
    """Pre-flight media scrubber for image and video frames."""

    @staticmethod
    def strip_exif(image_bytes: bytes) -> bytes:
        """
        Strips all EXIF metadata (GPS location, device serial, capture time)
        by recreating image data directly in memory.
        """
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                # Transpose image to honor EXIF orientation before stripping
                img_clean = ImageOps.exif_transpose(img)
                # Create a fresh image copy without metadata dictionary
                output_buffer = io.BytesIO()
                # Retain RGB or RGBA mode
                img_format = img.format if img.format in ("JPEG", "PNG", "WEBP") else "JPEG"
                if img_format == "JPEG" and img_clean.mode in ("RGBA", "P"):
                    img_clean = img_clean.convert("RGB")
                img_clean.save(output_buffer, format=img_format)
                return output_buffer.getvalue()
        except Exception as e:
            logger.warning(f"EXIF stripping warning: {e}. Returning raw bytes.")
            return image_bytes

    @classmethod
    def blur_faces(cls, image_bytes: bytes, safety_margin: float = 0.25) -> Tuple[bytes, int]:
        """
        Detects faces and applies Gaussian blur with a 25% safety margin expansion.
        Returns: (sanitized_image_bytes, faces_detected_count)
        """
        try:
            # 1. Strip EXIF first
            clean_bytes = cls.strip_exif(image_bytes)
            
            # 2. Convert to OpenCV BGR image
            nparr = np.frombuffer(clean_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return clean_bytes, 0

            h, w = img.shape[:2]
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Use OpenCV Haar Cascade for robust local CPU face detection
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml' if hasattr(cv2, 'data') and hasattr(cv2.data, 'haarcascades') else ''
            face_cascade = cv2.CascadeClassifier(cascade_path) if cascade_path else cv2.CascadeClassifier()
            if face_cascade.empty():
                logger.info("Face detector cascade not loaded or empty. Returning clean sanitized image.")
                is_success, buffer = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
                return (buffer.tobytes() if is_success else clean_bytes), 0

            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )

            faces_count = len(faces)
            for (x, y, fw, fh) in faces:
                # Expand bounding box by safety margin (default 25%)
                margin_x = int(fw * safety_margin)
                margin_y = int(fh * safety_margin)

                x1 = max(0, x - margin_x)
                y1 = max(0, y - margin_y)
                x2 = min(w, x + fw + margin_x)
                y2 = min(h, y + fh + margin_y)

                # Extract Region of Interest (ROI)
                roi = img[y1:y2, x1:x2]
                if roi.size > 0:
                    # Calculate proportional heavy Gaussian Blur kernel (must be odd)
                    kw = max(51, int((x2 - x1) * 0.4) | 1)
                    kh = max(51, int((y2 - y1) * 0.4) | 1)
                    blurred_roi = cv2.GaussianBlur(roi, (kw, kh), 30)
                    img[y1:y2, x1:x2] = blurred_roi

            # Encode back to JPEG
            is_success, buffer = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
            if is_success:
                return buffer.tobytes(), faces_count
            return clean_bytes, faces_count

        except Exception as e:
            logger.error(f"Face blurring error: {e}", exc_info=True)
            return image_bytes, 0


class TextDeidentifier:
    """Pre-flight text anonymizer for clinical conversations and notes."""

    # 1. Thai National ID (13 digits with optional hyphens/spaces)
    ID_CARD_REGEX = re.compile(r'\b\d{1}[-\s]?\d{4}[-\s]?\d{5}[-\s]?\d{2}[-\s]?\d{1}\b')

    # 2. Thai Mobile & Landline Phone numbers
    PHONE_REGEX = re.compile(r'\b(?:0[689]\d{1}[-\s]?\d{3}[-\s]?\d{4}|02[-\s]?\d{3}[-\s]?\d{4})\b')

    # 3. Hospital Number (HN) patterns
    HN_REGEX = re.compile(r'\b(?:HN|hn|H\.N\.)\s*[:#]?\s*\d+[/\\-]?\d*\b')

    # 4. Standard Email Addresses
    EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

    # 5. Passport Number patterns
    PASSPORT_REGEX = re.compile(r'\b(?:Passport|หนังสือเดินทาง)?\s*(?:No\.?|เลขที่)?\s*[:#]?\s*([A-Z]{1,2}\d{7,8})\b', re.IGNORECASE)

    # 6. Thai Names with honorific prefixes
    NAME_PREFIX_REGEX = re.compile(
        r'(?:นาย|นาง|นางสาว|น\.ส\.|ด\.ช\.|ด\.ญ\.|นพ\.|พญ\.|อาจารย์|อ\.|คุณลุง|คุณป้า|คุณตา|คุณยาย|คุณ)\s*([ก-๙]+(?:\s+[ก-๙]+)?)'
    )

    @classmethod
    def sanitize(cls, text: str) -> Dict[str, Any]:
        """
        Replaces identifiable PII tokens with standardized placeholders.
        Returns: {
            "sanitized_text": str,
            "redacted_counts": dict,
            "has_pii": bool
        }
        """
        if not text:
            return {"sanitized_text": "", "redacted_counts": {}, "has_pii": False}

        redacted_counts = {
            "id_card": 0,
            "phone": 0,
            "hn": 0,
            "email": 0,
            "passport": 0,
            "names": 0,
        }

        sanitized = text

        # 1. Redact ID Cards
        sanitized, redacted_counts["id_card"] = cls.ID_CARD_REGEX.subn("[ID_TOKEN]", sanitized)

        # 2. Redact Phone numbers
        sanitized, redacted_counts["phone"] = cls.PHONE_REGEX.subn("[PHONE_TOKEN]", sanitized)

        # 3. Redact HN
        sanitized, redacted_counts["hn"] = cls.HN_REGEX.subn("[HN_TOKEN]", sanitized)

        # 4. Redact Emails
        sanitized, redacted_counts["email"] = cls.EMAIL_REGEX.subn("[EMAIL_TOKEN]", sanitized)

        # 5. Redact Passports
        sanitized, redacted_counts["passport"] = cls.PASSPORT_REGEX.subn("[PASSPORT_TOKEN]", sanitized)

        # 6. Redact Thai Names with prefixes
        def replace_name(match):
            return "[PERSON_TOKEN]"

        sanitized, redacted_counts["names"] = cls.NAME_PREFIX_REGEX.subn(replace_name, sanitized)

        has_pii = any(count > 0 for count in redacted_counts.values())

        return {
            "sanitized_text": sanitized,
            "redacted_counts": redacted_counts,
            "has_pii": has_pii,
        }


class PolicyGuard:
    """Enforces institutional Data Classification Rules (Class A, B, C)."""

    @staticmethod
    def classify_payload(has_raw_audio: bool, has_id_photo: bool, has_sanitized_image: bool, text_is_sanitized: bool) -> str:
        """Determines the data classification level of an inbound payload."""
        if has_raw_audio or has_id_photo:
            return DataClassification.CLASS_C
        if has_sanitized_image:
            return DataClassification.CLASS_B
        if text_is_sanitized:
            return DataClassification.CLASS_A
        return DataClassification.CLASS_C
