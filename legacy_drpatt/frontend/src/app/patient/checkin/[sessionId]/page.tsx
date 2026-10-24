"use client";

import { useEffect, useState, use } from "react";
import QuestionnaireFlow from "@/components/clinical/QuestionnaireFlow";
import { QuestionnaireSession } from "@/types/clinical";
import { getPatient } from "@/utils/api/services";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function CheckinPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const unwrappedParams = use(params);
  const [session, setSession] = useState<QuestionnaireSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const fetchSession = async () => {
      try {
        if (!unwrappedParams.sessionId) return;
        
        // Fetch patient profile via auth token to get extra_data sessions
        const token = localStorage.getItem("patient_access_token");
        if (!token) {
          setError(true);
          setLoading(false);
          return;
        }

        const res = await fetch(`${API_BASE}/api/auth/me/`, {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (!res.ok) {
          setError(true);
          setLoading(false);
          return;
        }

        const patientProfile = await res.json();
        const questionnaireSessions = patientProfile.extra_data?.questionnaire_sessions || [];
        const matched = questionnaireSessions.find((s: any) => s.id === unwrappedParams.sessionId);

        if (matched) {
          setSession({
            id: matched.id,
            patientId: matched.patientId,
            createdAt: matched.createdAt ? new Date(matched.createdAt) : new Date(),
            status: matched.status || "pending",
            questions: matched.questions || [],
          });
        } else {
          setError(true);
        }
      } catch (err) {
        console.error("Error fetching session:", err);
        setError(true);
      } finally {
        setLoading(false);
      }
    };

    fetchSession();
  }, [unwrappedParams.sessionId]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-pulse text-blue-600 font-semibold text-lg">กำลังโหลดแบบสอบถาม...</div>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
        <div className="text-center p-8 bg-white rounded-3xl shadow-lg max-w-sm w-full border border-gray-100">
          <h1 className="text-2xl font-bold text-gray-800 mb-3">ไม่พบแบบสอบถาม</h1>
          <p className="text-gray-500">เซสชันหมายเลข: <span className="font-mono text-xs">{unwrappedParams.sessionId}</span><br/>ไม่ได้อยู่ในระบบ (ไม่มี Mock Data)</p>
        </div>
      </div>
    );
  }

  return <QuestionnaireFlow session={session} />;
}
