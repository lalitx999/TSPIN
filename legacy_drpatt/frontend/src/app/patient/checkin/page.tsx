"use client";

import { useState, useEffect } from "react";
import { Loader2, ClipboardList, ArrowLeft, Brain, Activity, Plus } from "lucide-react";
import { getPatient, updatePatient } from "@/utils/api/services";
import Link from "next/link";
import QuestionnaireFlow from "@/components/clinical/QuestionnaireFlow";
import { QuestionItem } from "@/types/clinical";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const CORE_QUESTIONS: QuestionItem[] = [
  { id: "core_sleep_01", text: "ในช่วงสัปดาห์ที่ผ่านมา คุณภาพการนอนหลับของคุณเป็นอย่างไร?", type: "slider_0_10", linkedAxes: ["Sleep/Circadian Biology"], isAiGenerated: false },
  { id: "core_energy_01", text: "คุณมีอาการเหนื่อยล้าแม้จะพักผ่อนเพียงพอหรือไม่?", type: "boolean", linkedAxes: ["Mitochondrial Function", "Cognitive Reserve"], isAiGenerated: false },
  { id: "core_gut_01", text: "ลักษณะการขับถ่ายของคุณในช่วง 3 วันที่ผ่านมาเป็นอย่างไร?", type: "multiple_choice", options: ["ปกติ / เป็นก้อน", "ท้องผูก / แข็ง", "เหลว / ท้องเสีย", "ไม่ถ่ายเลย"], linkedAxes: ["Gut Barrier Integrity"], isAiGenerated: false },
  { id: "core_stress_01", text: "ช่วยอธิบายความรู้สึกเครียด หรือความกังวลที่คุณเผชิญอยู่ในสัปดาห์นี้สั้นๆ (อัตนัย)", type: "text", linkedAxes: ["Autonomic Nervous System", "Hormonal Balance"], isAiGenerated: false },
  { id: "core_immunity_01", text: "สภาพภูมิคุ้มกันของคุณโดยรวม (0 = ป่วยบ่อยมาก, 10 = แข็งแรงมาก)", type: "slider_0_10", linkedAxes: ["Immune Resilience", "Inflammatory Load"], isAiGenerated: false }
];

export default function CheckinPage() {
  const [session, setSession] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [userUid, setUserUid] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    const checkAuthAndLoad = async () => {
      if (typeof window === "undefined") return;
      const token = localStorage.getItem("patient_access_token");
      if (!token) {
        window.location.href = "/patient/login";
        return;
      }

      try {
        const res = await fetch(`${API_BASE}/api/auth/me/`, {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          const uid = String(data.id);
          setUserUid(uid);
          await fetchLatestSession(data);
        } else {
          window.location.href = "/patient/login";
        }
      } catch (err) {
        console.error("Auth check error:", err);
        window.location.href = "/patient/login";
      }
    };
    checkAuthAndLoad();
  }, []);

  const fetchLatestSession = async (patientProfile: any) => {
    try {
      const questionnaireSessions = patientProfile.extra_data?.questionnaire_sessions || [];
      const pendingSessions = questionnaireSessions.filter((s: any) => s.status === "pending");

      if (pendingSessions.length > 0) {
        // Sort by createdAt desc
        pendingSessions.sort((a: any, b: any) => {
          const dateA = a.createdAt ? new Date(a.createdAt).getTime() : 0;
          const dateB = b.createdAt ? new Date(b.createdAt).getTime() : 0;
          return dateB - dateA;
        });
        setSession(pendingSessions[0]);
      }
    } catch (err) {
      console.error("Fetch sessions error:", err);
    } finally {
      setLoading(false);
    }
  };

  const startNewAssessment = async () => {
    if (!userUid) return;
    setIsCreating(true);
    try {
      const patient = await getPatient(userUid);
      if (patient) {
        const newSessionId = `sess_${Date.now()}`;
        const newSessionPayload = {
          id: newSessionId,
          patientId: userUid,
          createdAt: new Date().toISOString(),
          status: "pending",
          questions: CORE_QUESTIONS
        };

        const currentSessions = patient.extra_data?.questionnaire_sessions || [];
        const updatedSessions = [newSessionPayload, ...currentSessions];

        await updatePatient(userUid, {
          extra_data: {
            ...(patient.extra_data || {}),
            questionnaire_sessions: updatedSessions
          }
        });

        setSession(newSessionPayload);
      }
    } catch (error) {
      console.error("Error creating new assessment session:", error);
      alert("ไม่สามารถสร้างแบบประเมินได้ กรุณาลองใหม่อีกครั้ง");
    } finally {
      setIsCreating(false);
    }
  };

  if (loading) {
    return (
      <div className="min-vh-100 d-flex flex-column align-items-center justify-content-center bg-light">
        <Loader2 className="animate-spin text-warning mb-3" size={40} />
        <p className="fw-bold text-muted font-kanit">กำลังโหลดแบบประเมิน...</p>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="bg-light min-vh-100 font-kanit pb-5">
        <div className="bg-white px-3 py-3 d-flex align-items-center gap-3 shadow-sm sticky-top border-bottom border-light">
          <Link href="/patient/dashboard" className="text-dark"><ArrowLeft size={24} /></Link>
          <div>
            <h5 className="fw-bold mb-0 text-dark">แบบประเมินสุขภาพ</h5>
            <p className="tiny text-muted mb-0">ระบบการเรียนรู้ทางคลินิก (Clinical Learning)</p>
          </div>
        </div>

        <div className="container-fluid p-4 d-flex flex-column align-items-center text-center mt-4">
          <div className="bg-white rounded-circle d-flex align-items-center justify-content-center mb-4 shadow-sm border border-light p-4">
            <Brain size={48} className="text-primary-custom" />
          </div>
          <h4 className="fw-bold text-dark mb-2">เริ่มต้นแบบประเมินอัจฉริยะ</h4>
          <p className="small text-muted mb-4 px-2">
            ข้อมูลของคุณจะถูกนำไปใช้วิเคราะห์ 39 แกนสรีรวิทยา (Systems Biology Axes) เพื่อให้ AI และแพทย์วางแผนการรักษาได้อย่างแม่นยำ
          </p>

          <div className="bg-white rounded-4 p-4 shadow-sm border border-light w-100 text-start mb-4">
            <h6 className="fw-bold text-dark mb-3 d-flex align-items-center gap-2"><Activity size={18} className="text-success" /> สิ่งที่คุณจะได้ประเมิน</h6>
            <ul className="small text-muted mb-0 ps-3 space-y-2" style={{ lineHeight: '1.8' }}>
              <li>การนอนหลับและนาฬิกาชีวภาพ (Sleep/Circadian)</li>
              <li>ความสมดุลของระบบภูมิคุ้มกัน (Immune Resilience)</li>
              <li>ระบบย่อยอาหารและการดูดซึม (Gut Barrier Integrity)</li>
              <li>ระดับความเครียดและระบบประสาทอัตโนมัติ</li>
            </ul>
          </div>

          <button
            onClick={startNewAssessment}
            disabled={isCreating}
            className="btn btn-dark rounded-pill px-4 py-3 fw-bold shadow w-100 d-flex align-items-center justify-content-center gap-2"
          >
            {isCreating ? <Loader2 className="animate-spin" size={20} /> : <Plus size={20} />}
            {isCreating ? "กำลังสร้างแบบสอบถาม..." : "สร้างแบบประเมินชุดใหม่"}
          </button>
        </div>
      </div>
    );
  }

  // Render the QuestionnaireFlow if a pending session is found
  return (
    <div className="bg-light min-vh-100 font-kanit pb-5">
      <div className="bg-white px-3 py-3 d-flex align-items-center gap-3 shadow-sm sticky-top border-bottom border-light">
        <Link href="/patient/dashboard" className="text-dark"><ArrowLeft size={24} /></Link>
        <div>
          <h5 className="fw-bold mb-0 text-dark">แบบประเมินสุขภาพ 39 แกน</h5>
        </div>
      </div>
      <QuestionnaireFlow session={session} />
    </div>
  );
}
