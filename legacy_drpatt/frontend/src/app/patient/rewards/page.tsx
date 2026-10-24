"use client";

import { useState, useEffect } from "react";
import { 
  Award, 
  Gift, 
  Sparkles, 
  TrendingUp, 
  CheckCircle2, 
  ArrowLeft,
  Loader2,
  Clock,
  Heart,
  ChevronRight
} from "lucide-react";
import Link from "next/link";
import Swal from "sweetalert2";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function PatientRewardsPage() {
  const [loading, setLoading] = useState(true);
  const [patientName, setPatientName] = useState("");
  const [points, setPoints] = useState(180);

  useEffect(() => {
    const loadPatient = async () => {
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
          const profile = await res.json();
          setPatientName(`${profile.first_name || ""} ${profile.last_name || ""}`.trim() || "คนไข้");
          // Calculate mock points based on profile features to make it dynamic
          const calculatedPoints = 120 + ((profile.first_name?.length || 0) * 10);
          setPoints(calculatedPoints);
        }
      } catch (err) {
        console.error("Failed to load patient for rewards:", err);
      } finally {
        setLoading(false);
      }
    };
    loadPatient();
  }, []);

  const handleRedeem = (rewardName: string, cost: number) => {
    if (points < cost) {
      Swal.fire({
        title: "คะแนนสะสมไม่เพียงพอ",
        text: `คุณต้องการอีก ${cost - points} คะแนน เพื่อแลกรับรางวัลนี้`,
        icon: "warning",
        confirmButtonColor: "#D4AF37",
        confirmButtonText: "รับทราบ"
      });
      return;
    }

    Swal.fire({
      title: "ยืนยันการแลกรางวัล?",
      text: `คุณต้องการใช้คะแนนสะสมจำนวน ${cost} คะแนน เพื่อแลกรับ "${rewardName}" ใช่หรือไม่?`,
      icon: "question",
      showCancelButton: true,
      confirmButtonColor: "#1a1a2e",
      cancelButtonColor: "#9ca3af",
      confirmButtonText: "ยืนยันการแลก",
      cancelButtonText: "ยกเลิก"
    }).then((result) => {
      if (result.isConfirmed) {
        setPoints(prev => prev - cost);
        Swal.fire({
          title: "แลกรางวัลสำเร็จ! 🎉",
          text: `รหัสคูปองการแลกรางวัลของคุณถูกส่งไปยัง SMS / ประวัติการรักษาเรียบร้อยแล้ว`,
          icon: "success",
          confirmButtonColor: "#D4AF37"
        });
      }
    });
  };

  if (loading) {
    return (
      <div className="d-flex align-items-center justify-content-center min-vh-100 bg-light">
        <div className="text-center">
          <div className="spinner-border text-primary-custom mb-3" role="status" style={{ width: '40px', height: '40px', color: '#D4AF37' }}>
            <span className="visually-hidden">กำลังโหลด...</span>
          </div>
          <h5 className="fw-bold text-dark">กำลังโหลดข้อมูลคะแนนสะสมสุขภาพ...</h5>
        </div>
      </div>
    );
  }

  const rewardItems = [
    { id: 1, name: "ส่วนลดค่ายาคลินิก 10%", cost: 100, desc: "ใช้เป็นส่วนลดสำหรับค่ายาที่ได้รับการจัดจากแพทย์คลินิก TSPI", category: "คลินิก" },
    { id: 2, name: "บริการให้คำปรึกษา AI Premium 1 เดือน", cost: 50, desc: "ขยายขีดความสามารถการถามตอบ AI คัดกรองขั้นลึก 24 ชั่วโมง", category: "บริการ AI" },
    { id: 3, name: "บริการเจาะเลือดตรวจแล็บถึงบ้านฟรี 1 ครั้ง", cost: 350, desc: "พยาบาลเดินทางไปให้บริการเจาะเลือดและรับตัวอย่างวิเคราะห์ถึงที่พักของคุณ", category: "บริการแพทย์" },
    { id: 4, name: "ฟรี PhytoCore Supplement 1 กระปุก", cost: 500, desc: "ผลิตภัณฑ์อาหารเสริมบำรุงกลไกเซลล์ย่อยระดับโมเลกุลที่แพทย์แนะนำ", category: "อาหารเสริม" },
  ];

  return (
    <div className="container py-4" style={{ maxWidth: '800px', paddingBottom: '80px' }}>
      
      {/* ===== HEADER ===== */}
      <div className="d-flex align-items-center gap-3 mb-4">
        <Link href="/patient/dashboard" className="text-dark p-2 rounded-circle hover-bg-glass d-flex align-items-center justify-content-center" style={{ backgroundColor: 'rgba(0,0,0,0.03)' }}>
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h1 className="fs-4 fw-bold text-dark mb-1" style={{ letterSpacing: '-0.3px' }}>
            รางวัลสุขภาพและสิทธิประโยชน์
          </h1>
          <p className="text-muted mb-0 small">
            ร่วมกิจกรรมและรักษาสุขภาพอย่างมีวินัยเพื่อสะสมแต้มแลกของรางวัลพิเศษ
          </p>
        </div>
      </div>

      {/* ===== SCORE BANNER CARD ===== */}
      <div 
        className="card border-0 rounded-4 shadow-sm p-4 mb-4 text-white text-center" 
        style={{ 
          background: "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)",
          boxShadow: '0 10px 30px rgba(15,23,42,0.12)'
        }}
      >
        <div className="d-flex align-items-center justify-content-center gap-2 mb-2">
          <Award size={20} className="text-warning" />
          <span className="text-uppercase tracking-wider opacity-60 fw-bold" style={{ fontSize: '11px' }}>
            คะแนนสะสมปัจจุบันของคุณ
          </span>
        </div>
        <h2 className="fw-bold mb-1" style={{ fontSize: '48px', color: '#D4AF37' }}>
          {points} <span style={{ fontSize: '18px', fontWeight: 500, color: 'white', opacity: 0.7 }}>คะแนน</span>
        </h2>
        <p className="opacity-80 small mb-0">
          ยินดีด้วยคุณ {patientName}! คุณติดท็อป 15% ของคนไข้ที่รักษาสุขภาพยอดเยี่ยมในสัปดาห์นี้
        </p>
      </div>

      {/* ===== ACTIVITIES SECTION ===== */}
      <h3 className="fw-bold text-dark mb-3" style={{ fontSize: '15px' }}>
        กิจกรรมสะสมคะแนนเพิ่ม ⚡
      </h3>
      <div className="card border-0 rounded-4 shadow-sm p-3 mb-4 bg-white">
        <div className="d-grid gap-3">
          <div className="d-flex align-items-center justify-content-between border-bottom pb-2.5">
            <div className="d-flex align-items-center gap-3">
              <div className="bg-success bg-opacity-10 text-success p-2.5 rounded-3 d-flex align-items-center justify-content-center" style={{ width: '38px', height: '38px' }}>
                <TrendingUp size={16} />
              </div>
              <div>
                <h4 className="fw-bold text-dark mb-0.5" style={{ fontSize: '13px' }}>บันทึกค่าวัดระดับ FBS/HbA1c ประจำวัน</h4>
                <p className="text-muted mb-0" style={{ fontSize: '11px' }}>อัปเดตสถิติน้ำตาลในแผงความควบคุม</p>
              </div>
            </div>
            <span className="badge rounded-pill bg-success bg-opacity-10 text-success px-2.5 py-1" style={{ fontSize: '11px', fontWeight: 700 }}>+10 แต้ม</span>
          </div>

          <div className="d-flex align-items-center justify-content-between border-bottom pb-2.5">
            <div className="d-flex align-items-center gap-3">
              <div className="bg-primary bg-opacity-10 text-primary p-2.5 rounded-3 d-flex align-items-center justify-content-center" style={{ width: '38px', height: '38px', color: 'var(--drpat-primary)' }}>
                <Sparkles size={16} />
              </div>
              <div>
                <h4 className="fw-bold text-dark mb-0.5" style={{ fontSize: '13px' }}>ประเมินและคัดกรองอาการด้วย AI ครบถ้วน</h4>
                <p className="text-muted mb-0" style={{ fontSize: '11px' }}>พูดคุยบันทึกประวัติก่อนพบแพทย์</p>
              </div>
            </div>
            <span className="badge rounded-pill bg-primary bg-opacity-10 text-primary px-2.5 py-1" style={{ fontSize: '11px', fontWeight: 700, color: '#0d6efd !important' }}>+20 แต้ม</span>
          </div>

          <div className="d-flex align-items-center justify-content-between">
            <div className="d-flex align-items-center gap-3">
              <div className="bg-warning bg-opacity-10 text-warning p-2.5 rounded-3 d-flex align-items-center justify-content-center" style={{ width: '38px', height: '38px' }}>
                <CheckCircle2 size={16} />
              </div>
              <div>
                <h4 className="fw-bold text-dark mb-0.5" style={{ fontSize: '13px' }}>ปฏิบัติตามแผนคำแนะนำของแพทย์ครบ 7 วัน</h4>
                <p className="text-muted mb-0" style={{ fontSize: '11px' }}>ปรับปรุงพฤติกรรม อาหาร และการนอนสำเร็จ</p>
              </div>
            </div>
            <span className="badge rounded-pill bg-warning bg-opacity-10 text-warning px-2.5 py-1" style={{ fontSize: '11px', fontWeight: 700, color: '#d97706 !important' }}>+50 แต้ม</span>
          </div>
        </div>
      </div>

      {/* ===== REDEEMABLE LIST ===== */}
      <h3 className="fw-bold text-dark mb-3" style={{ fontSize: '15px' }}>
        รางวัลสุขภาพที่สามารถแลกรับได้ 🎁
      </h3>
      <div className="row g-3">
        {rewardItems.map((item) => {
          const isAffordable = points >= item.cost;
          return (
            <div key={item.id} className="col-12 col-md-6">
              <div className="card border-0 rounded-4 shadow-sm p-4 h-100 bg-white d-flex flex-column justify-content-between hover-lift">
                <div>
                  <div className="d-flex justify-content-between align-items-start mb-2">
                    <span className="badge bg-light text-dark border px-2 py-1" style={{ fontSize: '9.5px', fontWeight: 600 }}>
                      {item.category}
                    </span>
                    <span className="fw-bold text-dark" style={{ fontSize: '12px', color: '#D4AF37' }}>
                      {item.cost} คะแนน
                    </span>
                  </div>
                  <h4 className="fw-bold text-dark mb-1" style={{ fontSize: '13.5px' }}>{item.name}</h4>
                  <p className="text-muted small mb-3" style={{ fontSize: '11px', lineHeight: 1.5 }}>
                    {item.desc}
                  </p>
                </div>

                <button
                  onClick={() => handleRedeem(item.name, item.cost)}
                  className={`btn w-100 rounded-3 py-2 fw-bold d-flex align-items-center justify-content-center gap-1.5 border-0 ${
                    isAffordable 
                      ? 'btn-dark text-white' 
                      : 'btn-light text-muted cursor-not-allowed'
                  }`}
                  style={{ fontSize: '11.5px', transition: 'all 0.2s', cursor: isAffordable ? 'pointer' : 'not-allowed' }}
                >
                  <Gift size={13} />
                  แลกสิทธิประโยชน์
                </button>
              </div>
            </div>
          );
        })}
      </div>

      <style jsx global>{`
        .hover-lift {
          transition: transform 0.2s, box-shadow 0.2s;
        }
        .hover-lift:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.06);
        }
      `}</style>

    </div>
  );
}
