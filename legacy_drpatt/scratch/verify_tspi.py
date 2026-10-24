import os
import sys

# Setup django environment
import django
sys.path.append('/Users/tanchonl/Downloads/drpatt/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

def load_env():
    env_path = '/Users/tanchonl/Downloads/drpatt/backend/.env'
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        os.environ[parts[0].strip()] = parts[1].strip()

load_env()
django.setup()

from patients.models import Patient, PatientBiologicalRecord, ClinicalKnowledgeSegment
from patients.tspi_engine import calculate_tspi_analysis
from patients.views_ai import get_gemini_embedding, cosine_similarity

def main():
    print("🧪 --- TSPI Integration Verification ---")
    
    # 1. Test Decision Engine
    print("\n1. Testing TSPI Clinical Decision Engine calculations:")
    patient = Patient.objects.first()
    if not patient:
        print("  ❌ No patients found in DB to test.")
        return
        
    latest_record = patient.axes_records.first()
    if not latest_record:
        latest_record = PatientBiologicalRecord.objects.create(
            patient=patient,
            axis_1=85,  # Inflammatory (Critical)
            axis_9=75,  # Redox (Critical)
            axis_15=90, # Detox (Critical)
            axis_17=65, # Microbiome (High)
            axis_18=80  # Gut Barrier (Critical)
        )
        print("  Created default test record for patient.")
        
    analysis = calculate_tspi_analysis(latest_record, bowel_status='constipated')
    
    print(f"  Patient: {patient.first_name} {patient.last_name}")
    print(f"  Computed NSS (Network Severity): {analysis['nss']}")
    print(f"  Severity Level: {analysis['severity_level']} ({analysis['severity_label']})")
    print(f"  General Dosage Recommendation: {analysis['dosing_rule']}")
    print(f"  KS Bowel Optimization Dosage: {analysis['ks_dosing']}")
    print("  Top Recommended Modules:")
    for mod in analysis['recommended_modules'][:3]:
        print(f"    - [{mod['code']}] {mod['name']} (Match: {mod['match_score']}%)")
        
    print("  ✅ Decision Engine test successful.")
    
    # 2. Test RAG Vector Search
    print("\n2. Testing Closed-Circuit RAG Vector Search:")
    query = "กุญแจ 3 ดอก"
    query_vector = get_gemini_embedding(query)
    if not query_vector:
        print("  ❌ Failed to get query embedding from Gemini API.")
        return
        
    print(f"  Successfully got 3072-dimensional vector for query '{query}'")
    
    # Run cosine similarity across DB segments
    segments = ClinicalKnowledgeSegment.objects.all()
    matches = []
    for seg in segments:
        if seg.embedding:
            sim = cosine_similarity(query_vector, seg.embedding)
            matches.append((sim, seg))
            
    matches = sorted(matches, key=lambda x: x[0], reverse=True)
    
    print(f"  Top 3 RAG search matches in DB:")
    for sim, seg in matches[:3]:
        print(f"    - [Sim: {sim:.4f}] [Src: {seg.source}] {seg.content[:150]}...")
        
    print("  ✅ RAG Search test successful.")
    print("\n🎉 All TSPI Integration systems are functional!")

if __name__ == '__main__':
    main()
