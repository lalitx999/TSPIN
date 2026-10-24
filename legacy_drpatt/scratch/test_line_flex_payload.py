"""
Verification test script for LINE Flex Builder & Multimodal Services
"""
import sys
import os
import json

# Add backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from patients.line_flex_builder import (
    build_lab_result_flex,
    build_voice_intake_flex,
    build_axes_dashboard_flex
)
from patients.multimodal_service import analyze_lab_image, transcribe_audio_video

def test_flex_builders():
    print("🧪 Testing LINE Flex Builders...")
    
    # 1. Test Lab Result Flex Builder
    sample_lab = {
        "summary": "พบระดับน้ำตาลและไขมันในเลือดสูงกว่าเกณฑ์มาตรฐาน",
        "lab_items": [
            {"name": "Fasting Blood Sugar (FBS)", "value": 126, "unit": "mg/dL", "status": "สูง"},
            {"name": "HbA1c", "value": 6.8, "unit": "%", "status": "เสี่ยง"},
            {"name": "Triglycerides", "value": 195, "unit": "mg/dL", "status": "สูง"}
        ],
        "affected_axes": [
            {"id": "AXIS_9", "name": "Glucose & Lipid Dynamics"},
            {"id": "AXIS_15", "name": "Metabolic Energy Production"}
        ]
    }
    lab_flex = build_lab_result_flex(sample_lab, patient_hn="HN-2026-0089")
    assert lab_flex["type"] == "flex"
    assert "altText" in lab_flex
    print("✅ build_lab_result_flex passed successfully!")

    # 2. Test Voice Intake Flex Builder
    voice_flex = build_voice_intake_flex(
        transcript="ปวดหัวตึงๆ ตอนตื่นนอน เหนื่อยง่าย ท้องอืดแน่นท้องหลังทานอาหาร",
        symptoms=["ปวดศีรษะท้ายทอย", "เหนื่อยง่าย", "ท้องอืดแน่นท้อง"],
        patient_hn="HN-2026-0089"
    )
    assert voice_flex["type"] == "flex"
    print("✅ build_voice_intake_flex passed successfully!")

    # 3. Test Axes Dashboard Carousel Flex Builder
    dashboard_flex = build_axes_dashboard_flex(
        domain_scores={
            "Energy & Metabolism": 8.5,
            "Vascular & Microcirculation": 7.0,
            "Detoxification & Clearance": 9.0
        },
        patient_hn="HN-2026-0089"
    )
    assert dashboard_flex["type"] == "flex"
    assert dashboard_flex["contents"]["type"] == "carousel"
    print("✅ build_axes_dashboard_flex passed successfully!")

    # 4. Test Multimodal Services
    print("\n📸 Testing Multimodal Service Fallbacks...")
    lab_analysis = analyze_lab_image(None)
    assert "lab_items" in lab_analysis
    print("✅ analyze_lab_image fallback passed!")

    audio_analysis = transcribe_audio_video(b"dummy_bytes", mime_type="audio/m4a")
    assert "transcript" in audio_analysis
    print("✅ transcribe_audio_video fallback passed!")

    print("\n🎉 ALL LINE OA FLEX BOT TESTS PASSED CLEANLY!")

if __name__ == "__main__":
    test_flex_builders()
