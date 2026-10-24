"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { 
  ShieldCheck, 
  Lock, 
  CheckCircle2, 
  ArrowLeft, 
  Loader2,
  FileCheck
} from "lucide-react";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function PDPAConsentPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [policy, setPolicy] = useState<any>(null);
  const [choices, setChoices] = useState<Record<string, boolean>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const fetchPolicy = async () => {
      try {
        // Use standard default policy locally (no Firebase dependency)
        const defaultPolicy = {
          version: "1.0",
          policies: [
            { id: "medical_records", label: "ยินยอมให้เข้าถึงประวัติการรักษา", description: "เพื่อให้แพทย์และ AI สามารถวิเคราะห์อาการจากประวัติเดิมได้", required: true },
            { id: "ai_analysis", label: "ยินยอมให้ AI ประมวลผลข้อมูล", description: "ข้อมูลของคุณจะถูกใช้โดยโมเดล AI ในการจัดกลุ่มอาการ (Triage) เบื้องต้น", required: true },
            { id: "marketing", label: "รับข่าวสารและโปรโมชัน", description: "รับการแจ้งเตือนสิทธิประโยชน์และข่าวสารด้านสุขภาพ", required: false },
            { id: "research", label: "ยินยอมให้นำข้อมูลไปใช้ในงานวิจัย (ไม่ระบุตัวตน)", description: "เพื่อสนับสนุนการพัฒนาวิจัยวิทยาศาสตร์และเวชศาสตร์ระดับโมเลกุล", required: false }
          ]
        };
        setPolicy(defaultPolicy);
        const initialChoices: Record<string, boolean> = {};
        defaultPolicy.policies.forEach((p: any) => {
          initialChoices[p.id] = p.required;
        });
        setChoices(initialChoices);
      } catch (err) {
        console.error("Policy fetch error:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchPolicy();
  }, []);

  const handleSubmit = async () => {
    if (typeof window === "undefined") return;
    const token = localStorage.getItem("patient_access_token");
    if (!token) {
      alert("กรุณาเข้าสู่ระบบก่อนทำรายการ");
      router.push("/patient/login");
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        terms_version: policy?.version || "v1.0",
        consent_treatment: (choices["medical_records"] || false) && (choices["ai_analysis"] || false),
        consent_marketing: choices["marketing"] || false,
        consent_research: choices["research"] || false
      };

      const res = await fetch(`${API_BASE}/api/pdpa-consent/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        throw new Error("Failed to post consent to EMR");
      }

      router.push("/patient/dashboard");
    } catch (err) {
      console.error("PDPA submission error:", err);
      alert("เกิดข้อผิดพลาดในการบันทึกข้อมูล");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-vh-100 d-flex align-items-center justify-content-center" style={{ backgroundColor: '#F2F2F7' }}>
        <Loader2 className="animate-spin text-primary-custom" size={48} />
      </div>
    );
  }

  return (
    <div className="min-vh-100 font-kanit pb-5 mb-5" style={{ backgroundColor: '#F2F2F7' }}>
      
      {/* Header */}
      <div className="bg-white px-3 py-3 d-flex align-items-center justify-content-between shadow-sm position-sticky top-0" style={{ zIndex: 10 }}>
        <div className="d-flex align-items-center gap-3">
          <button onClick={() => router.back()} className="btn btn-link text-muted text-decoration-none p-1 border-0">
            <ArrowLeft size={22} />
          </button>
          <div>
            <h5 className="fw-bold text-dark mb-0 lh-1">ความยินยอม</h5>
            <p className="small text-muted mb-0" style={{ fontSize: '0.8rem' }}>PDPA & Medical Consent</p>
          </div>
        </div>
        <div className="bg-light rounded-circle p-2 shadow-sm border border-white">
          <ShieldCheck size={20} className="text-success" />
        </div>
      </div>

      <div className="container-fluid p-3 max-w-md mx-auto mt-3">
        
        {/* Banner */}
        <div className="bg-white rounded-4 p-4 shadow-sm border-light mb-4 text-center animate-fade-in">
          <div className="bg-success bg-opacity-10 rounded-circle d-inline-flex align-items-center justify-content-center mb-3" style={{ width: '64px', height: '64px' }}>
            <Lock size={32} className="text-success" />
          </div>
          <h5 className="fw-bold text-dark mb-2">นโยบายความเป็นส่วนตัว</h5>
          <p className="small text-muted mb-0 px-2" style={{ fontSize: '0.85rem' }}>
            เพื่อให้การรักษาด้วยระบบ AI และ 39 Biological Axes เป็นไปอย่างแม่นยำ โปรดตรวจสอบและให้ความยินยอมในหัวข้อดังต่อไปนี้
          </p>
          {policy?.version && (
             <div className="mt-3">
               <span className="badge bg-light text-secondary border px-3 py-2 rounded-pill shadow-sm">
                 เวอร์ชัน: {policy.version}
               </span>
             </div>
          )}
        </div>

        {/* Policy List */}
        <div className="d-grid gap-3 pb-5 mb-5">
          {policy?.policies?.map((p: any, idx: number) => (
            <div 
              key={p.id} 
              className={`bg-white rounded-4 p-3 shadow-sm border transition-all animate-fade-in ${choices[p.id] ? 'border-primary' : 'border-light'}`}
              style={{ animationDelay: `${idx * 0.1}s` }}
            >
              <div className="d-flex align-items-start gap-3">
                <div className="flex-grow-1">
                  <div className="d-flex align-items-center justify-content-between mb-1">
                    <h6 className="fw-bold text-dark mb-0" style={{ fontSize: '0.95rem' }}>{p.label}</h6>
                    <div className="form-check form-switch m-0 p-0 d-flex align-items-center">
                      <input 
                        className="form-check-input custom-switch m-0" 
                        type="checkbox" 
                        role="switch" 
                        id={`switch-${p.id}`}
                        checked={choices[p.id] || false}
                        disabled={p.required}
                        onChange={(e) => setChoices({...choices, [p.id]: e.target.checked})}
                        style={{ cursor: p.required ? 'not-allowed' : 'pointer', width: '40px', height: '20px' }}
                      />
                    </div>
                  </div>
                  {p.description && (
                    <p className="text-muted small mb-0 mt-2" style={{ fontSize: '0.8rem', lineHeight: '1.4' }}>
                      {p.description}
                    </p>
                  )}
                  {p.required && (
                    <div className="mt-2">
                      <span className="badge bg-danger bg-opacity-10 text-danger border border-danger border-opacity-25 py-1 px-2" style={{ fontSize: '0.7rem' }}>
                        * จำเป็นต้องยินยอมเพื่อรับการรักษา
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

      </div>

      {/* Action Button - Fixed at bottom */}
      <div className="position-fixed bottom-0 start-0 w-100 p-3 bg-white border-top shadow-lg" style={{ zIndex: 100 }}>
        <div className="max-w-md mx-auto">
          <button 
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="btn btn-primary-custom w-100 rounded-pill py-3 fw-bold shadow d-flex align-items-center justify-content-center gap-2 transition"
          >
            {isSubmitting ? <Loader2 className="animate-spin" size={20} /> : <CheckCircle2 size={20} />}
            ยืนยันการให้ความยินยอม
          </button>
        </div>
      </div>

      <style jsx global>{`
        .bg-primary-custom { background-color: var(--drpat-primary, #0d6efd); }
        .text-primary-custom { color: var(--drpat-primary, #0d6efd); }
        .btn-primary-custom { background-color: var(--drpat-primary, #0d6efd); color: white; border: none; }
        .btn-primary-custom:hover { filter: brightness(0.9); color: white; }
        
        .custom-switch:checked {
          background-color: var(--drpat-primary, #0d6efd);
          border-color: var(--drpat-primary, #0d6efd);
        }

        .animate-fade-in { animation: fadeIn 0.4s ease-out both; }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-spin { animation: spin 1s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
