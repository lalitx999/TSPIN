"use client";

import { useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { 
  CheckCircle2, 
  Smartphone, 
  AlertCircle, 
  Loader2,
  Lock,
  ArrowRight
} from "lucide-react";

function LinkAccountForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("t");

  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");
  const [patientName, setPatientName] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) {
      setError("ลิงก์นี้ไม่สมบูรณ์ (ไม่พบรหัส Token ยืนยันตัวตน)");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch("/api/line/link", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token,
          phone,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setSuccess(true);
        setPatientName(data.patientName);
      } else {
        setError(data.error || "เกิดข้อผิดพลาดในการเชื่อมบัญชี");
      }
    } catch (err) {
      console.error(err);
      setError("ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาลองใหม่อีกครั้ง");
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="card shadow-lg border-0 rounded-4 overflow-hidden animate-fade-in" style={{ maxWidth: "420px", width: "100%" }}>
        <div className="bg-danger text-white p-4 text-center">
          <AlertCircle size={48} className="mb-2" />
          <h4 className="fw-bold mb-0">ลิงก์ไม่ถูกต้อง</h4>
        </div>
        <div className="p-4 text-center">
          <p className="text-muted mb-4">
            ไม่พบรหัสสิทธิ์การเชื่อมต่อใน URL นี้ กรุณาทักแชท LINE เพื่อให้ระบบออกลิงก์ยืนยันตัวตนอันใหม่ให้ครับ
          </p>
          <a href="line://ti/p/@doctorpatt" className="btn btn-secondary w-100 rounded-pill py-2 fw-bold">
            กลับไปยังแชท LINE
          </a>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div className="card shadow-lg border-0 rounded-4 overflow-hidden animate-fade-in text-center" style={{ maxWidth: "420px", width: "100%" }}>
        <div className="bg-success text-white p-5">
          <div className="d-inline-flex bg-white bg-opacity-20 rounded-circle p-3 mb-3 animate-scale-up">
            <CheckCircle2 size={56} className="text-white" />
          </div>
          <h4 className="fw-bold mb-0">เชื่อมบัญชีสำเร็จแล้ว!</h4>
        </div>
        <div className="p-4">
          <h5 className="fw-bold text-dark mb-2">ยินดีต้อนรับ</h5>
          <h6 className="text-primary fw-bold mb-3" style={{ fontSize: "1.1rem" }}>คุณ {patientName}</h6>
          <p className="small text-muted mb-4">
            ข้อมูลบัญชี LINE ของคุณได้รับการเชื่อมโยงกับฐานข้อมูลคนไข้แล้ว ระบบ AI ได้ส่งข้อความต้อนรับเข้าแชทไลน์ของคุณเรียบร้อยแล้วครับ
          </p>
          <div className="bg-light rounded-3 p-3 mb-4 text-start border border-light">
            <span className="tiny text-success fw-bold d-block mb-1">🏁 สเต็ปต่อไป:</span>
            <p className="tiny text-muted mb-0">
              กรุณาปิดหน้าต่างนี้และกลับไปยังแชท LINE เพื่อเริ่มส่งข้อความซักประวัติสุขภาพของคุณได้ทันที!
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card shadow-lg border-0 rounded-4 overflow-hidden animate-fade-in" style={{ maxWidth: "420px", width: "100%" }}>
      {/* Header with brand gradient */}
      <div className="p-4 text-center text-white" style={{ background: "linear-gradient(135deg, #FF7444 0%, #FF5A26 100%)" }}>
        <div className="bg-white bg-opacity-20 rounded-circle d-inline-flex p-3 mb-3">
          <Lock size={32} />
        </div>
        <h4 className="fw-bold mb-1">เชื่อมต่อบัญชีคนไข้</h4>
        <p className="small mb-0 opacity-75">กรุณายืนยันเบอร์โทรศัพท์เพื่อเชื่อมต่อประวัติการรักษา</p>
      </div>

      <div className="p-4">
        {error && (
          <div className="alert alert-danger d-flex align-items-center gap-2 rounded-3 border-0 small py-3 mb-4 animate-fade-in">
            <AlertCircle size={20} className="flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="form-label small fw-bold text-secondary mb-2">เบอร์โทรศัพท์ที่เคยลงทะเบียนกับคลินิก</label>
            <div className="input-group">
              <span className="input-group-text bg-light border-end-0 border-light rounded-start-pill px-3">
                <Smartphone size={18} className="text-muted" />
              </span>
              <input
                type="tel"
                className="form-control bg-light border-start-0 border-light rounded-end-pill py-2.5 shadow-none"
                placeholder="เช่น 08XXXXXXXX"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                required
                style={{ fontSize: "0.95rem" }}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary w-100 rounded-pill py-3 fw-bold shadow-sm d-flex align-items-center justify-content-center gap-2 border-0"
            style={{ 
              backgroundColor: "#FF7444", 
              backgroundImage: "linear-gradient(135deg, #FF7444 0%, #FF5A26 100%)",
              transition: "transform 0.15s ease-in-out" 
            }}
          >
            {loading ? (
              <>
                <Loader2 className="animate-spin" size={20} />
                กำลังตรวจสอบข้อมูล...
              </>
            ) : (
              <>
                ยืนยันเชื่อมต่อบัญชี
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function LinkAccountPage() {
  return (
    <div className="min-vh-100 d-flex align-items-center justify-content-center p-3" 
         style={{ 
           background: "radial-gradient(circle at 50% 50%, #F8FAFC 0%, #E2E8F0 100%)",
           fontFamily: "'Inter', 'Kanit', sans-serif"
         }}>
      <Suspense fallback={
        <div className="text-center">
          <Loader2 className="animate-spin text-primary-custom mx-auto mb-2" size={40} />
          <p className="small text-muted">กำลังโหลดระบบเชื่อมต่อ...</p>
        </div>
      }>
        <LinkAccountForm />
      </Suspense>

      <style jsx global>{`
        .text-primary-custom { color: #FF7444; }
        .animate-fade-in { animation: fadeIn 0.4s ease-out; }
        .animate-scale-up { animation: scaleUp 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) both; }
        .animate-spin { animation: spin 1s linear infinite; }
        
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes scaleUp {
          from { transform: scale(0.85); opacity: 0; }
          to { transform: scale(1); opacity: 1; }
        }
        @keyframes spin {
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
