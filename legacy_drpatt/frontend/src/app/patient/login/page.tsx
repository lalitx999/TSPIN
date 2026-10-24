"use client";

import { useState } from "react";
import Link from "next/link";
import { patientAuthEndpoint, readPatientTokens } from "@/lib/patient-auth-response";
import { useRouter } from "next/navigation";
// Firebase Auth and client imports removed. Converted to Django + PostgreSQL.
import {
  ArrowLeft,
  ChevronRight,
  Sparkles,
  Mail,
  Lock,
  Loader2,
  ShieldAlert,
  CreditCard,
  User
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";

export default function PatientLogin() {
  const router = useRouter();
  
  // Tab states: "idcard" | "email"
  const [authMethod, setAuthMethod] = useState<"idcard" | "email">("idcard");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [citizenId, setCitizenId] = useState("");

  // Common UI states
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await fetch(patientAuthEndpoint(API_BASE, "login"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          auth_method: authMethod,
          citizenId: citizenId,
          email: email,
          password: password
        })
      });
      
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || "การเข้าสู่ระบบไม่สำเร็จ");
      }
      
      const data = await res.json();
      const tokens = readPatientTokens(data);
      localStorage.setItem("patient_access_token", tokens.access);
      localStorage.setItem("patient_refresh_token", tokens.refresh);
      // Fixed allowlisted destination; never redirect to arbitrary query URLs.
      const returnTo = new URLSearchParams(window.location.search).get("returnTo");
      router.push(returnTo === "line-link" ? "/liff/identity" : "/patient/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "การเข้าสู่ระบบไม่สำเร็จ กรุณาติดต่อคลินิก");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-vh-100 d-flex align-items-center justify-content-center bg-secondary-custom p-3 font-kanit">
      <div className="bg-white rounded-5 shadow-lg p-4 p-md-5 w-100 animate-fade-in text-center" style={{ maxWidth: '460px' }}>

        <div className="d-flex justify-content-start mb-4">
          <Link href="/" className="btn btn-light rounded-circle p-2 shadow-sm">
            <ArrowLeft size={20} />
          </Link>
        </div>

        <div className="overflow-hidden rounded-circle shadow-sm mx-auto mb-4" style={{ width: '80px', height: '80px', border: '4px solid var(--drpat-card)' }}>
          <img src="/logo_tspi.jpg" alt="TSPI Logo" className="w-100 h-100 object-fit-cover" />
        </div>

        <h3 className="fw-bold text-dark mb-2">
          เข้าสู่ระบบคนไข้
        </h3>
        <p className="text-muted small mb-4 px-3">TSPI Clinical Intelligence System</p>

        {error && (
          <div className="mb-4 p-3 bg-danger bg-opacity-10 border border-danger border-opacity-20 rounded-4 text-danger tiny fw-bold d-flex align-items-center gap-2 justify-content-center">
            <ShieldAlert size={16} className="flex-shrink-0" />
            <span style={{ fontSize: '12px', textAlign: 'left' }}>{error}</span>
          </div>
        )}

            {/* Tab Selection */}
            <div className="p-1 rounded-4 bg-light d-flex mb-4 gap-1" style={{ border: '1px solid #E5E7EB' }}>
              <button
                type="button"
                onClick={() => {
                  setAuthMethod("idcard");
                  setError(null);
                }}
                className={`flex-grow-1 py-2.5 rounded-3 small fw-bold border-0 transition-all ${
                  authMethod === "idcard"
                    ? "bg-white text-primary-custom shadow-xs"
                    : "bg-transparent text-muted"
                }`}
              >
                เลขบัตรประจำตัวประชาชน
              </button>
              <button
                type="button"
                onClick={() => {
                  setAuthMethod("email");
                  setError(null);
                }}
                className={`flex-grow-1 py-2.5 rounded-3 small fw-bold border-0 transition-all ${
                  authMethod === "email"
                    ? "bg-white text-primary-custom shadow-xs"
                    : "bg-transparent text-muted"
                }`}
              >
                อีเมล
              </button>
            </div>

            <form onSubmit={handleLogin} className="text-start mb-4">
              {authMethod === "idcard" ? (
                /* Citizen ID Login */
                <div className="mb-4">
                  <label className="tiny fw-bold text-muted text-uppercase mb-2 d-block tracking-wider">
                    เลขบัตรประจำตัวประชาชน (13 หลัก)
                  </label>
                  <div className="input-group">
                    <span className="input-group-text bg-light border-0 px-3">
                      <CreditCard size={18} className="text-muted" />
                    </span>
                    <input
                      type="text"
                      maxLength={13}
                      className="form-control bg-light border-0 py-3 small"
                      placeholder="กรอกเลขบัตรประชาชน 13 หลัก"
                      required
                      value={citizenId}
                      onChange={(e) => setCitizenId(e.target.value.replace(/\D/g, ""))}
                    />
                  </div>
                </div>
              ) : (
                /* Email Login */
                <div className="mb-4">
                  <label className="tiny fw-bold text-muted text-uppercase mb-2 d-block tracking-wider">อีเมล</label>
                  <div className="input-group">
                    <span className="input-group-text bg-light border-0 px-3">
                      <Mail size={18} className="text-muted" />
                    </span>
                    <input
                      type="email"
                      className="form-control bg-light border-0 py-3 small"
                      placeholder="email@example.com"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                    />
                  </div>
                </div>
              )}

              <div className="mb-4">
                <label className="tiny fw-bold text-muted text-uppercase mb-2 d-block tracking-wider">รหัสผ่าน</label>
                <div className="input-group">
                  <span className="input-group-text bg-light border-0 px-3">
                    <Lock size={18} className="text-muted" />
                  </span>
                  <input
                    type="password"
                    className="form-control bg-light border-0 py-3 small"
                    placeholder="••••••••"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </div>
              </div>

              <button
                type="submit"
                className="btn btn-drpat-primary btn-lg w-100 py-3 shadow-sm d-flex align-items-center justify-content-center gap-2 rounded-4"
                disabled={loading}
              >
                {loading ? <Loader2 size={20} className="animate-spin" /> : "เข้าสู่ระบบ"}
              </button>
            </form>

            <div className="mt-4 d-grid gap-3">
              <button
                type="button"
                onClick={() => {
                  sessionStorage.removeItem("activationPatient");
                  setError("ผู้ป่วยเดิมที่ยังไม่มีบัญชีออนไลน์ กรุณาติดต่อคลินิกเพื่อยืนยันเจ้าของเวชระเบียน ไม่สามารถเปิดบัญชีด้วยชื่อและเบอร์โทรเพียงอย่างเดียวได้");
                }}
                className="d-flex align-items-center justify-content-between p-3 border rounded-4 text-decoration-none text-dark hover-bg-light transition-all text-start shadow-xs w-100 bg-white"
              >
                <div className="d-flex align-items-center gap-3">
                  <div className="bg-primary-custom bg-opacity-10 p-2 rounded-3">
                    <Sparkles size={20} className="text-primary-custom" />
                  </div>
                  <div>
                    <p className="fw-bold mb-0 small">คนไข้เดิมยังไม่มีบัญชีออนไลน์?</p>
                    <p className="tiny text-muted mb-0">ติดต่อคลินิกเพื่อยืนยันตัวตนก่อนเปิดบัญชี</p>
                  </div>
                </div>
                <ChevronRight size={18} className="text-muted" />
              </button>

              <Link
                href="/patient/register"
                onClick={() => {
                  if (typeof window !== "undefined") {
                    sessionStorage.removeItem("activationPatient");
                  }
                }}
                className="d-flex align-items-center justify-content-between p-3 border rounded-4 text-decoration-none text-dark hover-bg-light transition-all text-start shadow-xs w-100 bg-white"
              >
                <div className="d-flex align-items-center gap-3">
                  <div className="bg-success bg-opacity-10 p-2 rounded-3">
                    <User size={20} className="text-success" />
                  </div>
                  <div>
                    <p className="fw-bold mb-0 small">ลงทะเบียนคนไข้ใหม่</p>
                    <p className="tiny text-muted mb-0">สำหรับผู้ที่ไม่เคยเข้ารับการรักษาที่คลินิก</p>
                  </div>
                </div>
                <ChevronRight size={18} className="text-muted" />
              </Link>
            </div>

        <div className="mt-5 pt-4 border-top">
          <p className="tiny text-muted mb-0">การเข้าใช้งานเป็นไปตามนโยบาย PDPA ของ TSPI Clinic</p>
        </div>
      </div>

      <style jsx>{`
        .hover-bg-light:hover { background-color: #f8f9fa; transform: translateY(-2px); }
        .shadow-xs { box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
      `}</style>
    </div>
  );
}
