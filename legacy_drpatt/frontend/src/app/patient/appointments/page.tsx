"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { 
  Calendar as CalendarIcon, 
  Clock, 
  ChevronRight, 
  Loader2,
  ArrowLeft,
  Plus,
  MapPin
} from "lucide-react";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
// Removed Firebase imports. Converted to Django + PostgreSQL.

export default function AppointmentsPage() {
  const router = useRouter();
  const [appointments, setAppointments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"upcoming" | "past">("upcoming");

  useEffect(() => {
    const checkAuthAndFetch = async () => {
      if (typeof window === "undefined") return;
      const token = localStorage.getItem("patient_access_token");
      if (!token) {
        router.push("/");
        return;
      }

      try {
        const meRes = await fetch(`${API_BASE}/api/auth/me/`, {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (!meRes.ok) {
          localStorage.removeItem("patient_access_token");
          router.push("/");
          return;
        }
        const profile = await meRes.json();
        
        const appRes = await fetch(`${API_BASE}/api/appointments/?user=${profile.id_card}`);
        if (appRes.ok) {
          const rawApps = await appRes.json();
          const mappedApps = rawApps.map((a: any) => ({
            id: String(a.id),
            date: a.date_meet,
            time: a.time_meet,
            doctor: a.doctorid || "แพทย์ผู้เชี่ยวชาญ",
            doctorName: a.doctorid || "แพทย์ผู้เชี่ยวชาญ",
            status: a.status || "รอยืนยัน",
            symptom: a.symptom || "ตรวจรักษาทั่วไป",
            symptoms: a.symptom || "ตรวจรักษาทั่วไป"
          }));
          mappedApps.sort((x: any, y: any) => new Date(x.date).getTime() - new Date(y.date).getTime());
          setAppointments(mappedApps);
        }
      } catch (err) {
        console.error("Error loading appointments from Django:", err);
      } finally {
        setLoading(false);
      }
    };

    checkAuthAndFetch();
  }, [router]);

  const today = new Date().toISOString().split('T')[0];
  const upcomingAppointments = appointments.filter(a => a.date >= today);
  const pastAppointments = appointments.filter(a => a.date < today);

  const displayList = activeTab === "upcoming" ? upcomingAppointments : pastAppointments;

  const formatDate = (dateString: string) => {
    if (!dateString) return "ไม่ระบุวันที่";
    const date = new Date(dateString);
    return date.toLocaleDateString("th-TH", {
      year: "numeric",
      month: "short",
      day: "numeric",
      weekday: "short"
    });
  };

  return (
    <div className="bg-light min-vh-100 font-kanit pb-5">
      {/* Header */}
      <div className="bg-white px-3 py-3 d-flex align-items-center justify-content-between shadow-sm sticky-top border-bottom border-light">
        <div className="d-flex align-items-center gap-3">
           <Link href="/patient/dashboard" className="text-dark"><ArrowLeft size={24} /></Link>
           <div>
             <h5 className="fw-bold mb-0 text-dark">การนัดหมาย</h5>
             <p className="tiny text-muted mb-0">ตารางพบแพทย์ของคุณ</p>
           </div>
        </div>
      </div>

      <div className="container-fluid p-3">
        {/* Apple Health Style Segmented Control */}
        <div className="bg-secondary bg-opacity-10 rounded-3 p-1 d-flex mb-4">
           <button 
              onClick={() => setActiveTab("upcoming")}
              className={`flex-grow-1 py-2 rounded-2 border-0 small fw-bold transition-all ${activeTab === 'upcoming' ? 'bg-white text-dark shadow-sm' : 'bg-transparent text-muted'}`}
           >
              กำลังมาถึง
           </button>
           <button 
              onClick={() => setActiveTab("past")}
              className={`flex-grow-1 py-2 rounded-2 border-0 small fw-bold transition-all ${activeTab === 'past' ? 'bg-white text-dark shadow-sm' : 'bg-transparent text-muted'}`}
           >
              ที่ผ่านมาแล้ว
           </button>
        </div>

        {loading ? (
          <div className="py-5 text-center">
            <Loader2 className="animate-spin text-primary-custom mx-auto mb-3" size={32} />
            <p className="small text-muted">กำลังโหลดข้อมูลนัดหมาย...</p>
          </div>
        ) : (
          <div className="animate-fade-in">
            {displayList.length === 0 ? (
              <div className="text-center py-5">
                <div className="bg-white rounded-circle d-inline-flex align-items-center justify-content-center mb-3 shadow-sm" style={{width: '64px', height: '64px'}}>
                  <CalendarIcon size={32} className="text-muted opacity-50" />
                </div>
                <h6 className="fw-bold text-dark mb-1">ไม่มีนัดหมาย{activeTab === 'upcoming' ? 'เร็วๆ นี้' : 'ที่ผ่านมา'}</h6>
                <p className="small text-muted mb-0">เมื่อแพทย์ทำการนัดหมาย จะแสดงที่นี่</p>
              </div>
            ) : (
              <div className="d-grid gap-3">
                {displayList.map((apt) => (
                  <div key={apt.id} className="bg-white rounded-4 p-4 shadow-sm border border-light position-relative overflow-hidden transition hover-shadow cursor-pointer">
                    {/* Status indicator line */}
                    <div className={`position-absolute top-0 bottom-0 start-0 ${activeTab === 'upcoming' ? 'bg-primary-custom' : 'bg-secondary'} opacity-75`} style={{ width: '4px' }}></div>
                    
                    <div className="d-flex justify-content-between align-items-start mb-3">
                       <div>
                          <p className="tiny fw-bold text-primary-custom uppercase tracking-widest mb-1 d-flex align-items-center gap-1">
                             <CalendarIcon size={12} /> {formatDate(apt.date)}
                          </p>
                          <h5 className="fw-bold text-dark mb-0">{apt.time || "รอระบุเวลา"} น.</h5>
                       </div>
                       <div className="bg-light rounded-pill px-3 py-1">
                          <span className="tiny fw-bold text-dark">{apt.status === "confirmed" ? "ยืนยันแล้ว" : "รอการยืนยัน"}</span>
                       </div>
                    </div>

                    <div className="bg-light rounded-3 p-3 mb-0">
                       <div className="d-flex align-items-center gap-2 mb-2">
                          <span className="fs-5">👨‍⚕️</span>
                          <span className="small fw-bold text-dark">แพทย์: {apt.doctorName || "ไม่ระบุแพทย์"}</span>
                       </div>
                       {apt.symptoms && (
                          <div className="d-flex align-items-start gap-2">
                             <span className="fs-5">📝</span>
                             <span className="small text-muted line-clamp-2">อาการ: {apt.symptoms}</span>
                          </div>
                       )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <style jsx>{`
        .bg-primary-custom { background-color: var(--drpat-primary, #FF7444); }
        .text-primary-custom { color: var(--drpat-primary, #FF7444); }
        .hover-shadow:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important; }
        .transition { transition: all 0.2s ease; }
        .animate-fade-in { animation: fadeIn 0.3s ease-out; }
        .line-clamp-2 {
           display: -webkit-box;
           -webkit-line-clamp: 2;
           -webkit-box-orient: vertical;  
           overflow: hidden;
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(5px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}

