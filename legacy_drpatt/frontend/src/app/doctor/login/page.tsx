"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { readPatientTokens } from "@/lib/patient-auth-response";
// Firebase Auth connection removed. Converted to Django + PostgreSQL.
import { Shield, Lock, Mail, ArrowLeft, LogIn, Loader2, ShieldAlert } from "lucide-react";

export default function DoctorLogin() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";
      const base = apiBase.replace(/\/+$/, "").replace(/\/api$/, "");
      const res = await fetch(`${base}/api/auth/doctor/login/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      
      if (!res.ok) {
        if (res.status === 429) throw new Error("พยายามเข้าสู่ระบบถี่เกินไป กรุณารอสักครู่แล้วลองใหม่");
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || "อีเมลหรือรหัสผ่านไม่ถูกต้อง หรือบัญชีของคุณไม่มีสิทธิ์การใช้งานของแพทย์");
      }
      
      const data = await res.json();
      const tokens = readPatientTokens(data);
      localStorage.setItem("doctor_access_token", tokens.access);
      localStorage.setItem("doctor_refresh_token", tokens.refresh);
      router.push("/doctor/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "การเชื่อมต่อหลังบ้านขัดข้อง กรุณาลองใหม่อีกครั้ง");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-vh-100 d-flex align-items-center justify-content-center bg-secondary-custom p-3 font-kanit">
      <div className="bg-white rounded-5 shadow-lg p-4 p-md-5 w-100 animate-fade-in" style={{ maxWidth: '450px' }}>
        <div className="text-center mb-5">
          <div className="d-flex justify-content-start mb-4">
            <Link href="/" className="btn btn-light rounded-circle p-2 shadow-sm">
              <ArrowLeft size={20} />
            </Link>
          </div>
          <div className="overflow-hidden rounded-circle shadow-sm mx-auto mb-3" style={{ width: '80px', height: '80px', border: '3px solid var(--drpat-card)' }}>
            <img src="/logo_tspi.jpg" alt="TSPI Logo" className="w-100 h-100 object-fit-cover" />
          </div>
          <h3 className="fw-bold text-dark">Doctor Portal</h3>
          <p className="text-muted small">Clinical Intelligence Dashboard</p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-danger bg-opacity-10 border border-danger border-opacity-20 rounded-4 text-danger tiny fw-bold d-flex align-items-center gap-2 justify-content-center">
            <ShieldAlert size={16} /> {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="d-grid gap-4">
          <div className="form-group text-start">
            <label className="tiny fw-bold text-muted mb-2 text-uppercase tracking-wider">Staff Email</label>
            <div className="input-group">
              <span className="input-group-text bg-light border-0 px-3"><Mail size={18} className="text-muted" /></span>
              <input
                type="email"
                className="form-control bg-light border-0 py-3 small"
                placeholder="doctor@tspi-clinic.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="form-group text-start">
            <label className="tiny fw-bold text-muted mb-2 text-uppercase tracking-wider">Password</label>
            <div className="input-group">
              <span className="input-group-text bg-light border-0 px-3"><Lock size={18} className="text-muted" /></span>
              <input
                type="password"
                className="form-control bg-light border-0 py-3 small"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
          </div>

          <button type="submit" className="btn btn-drpat-primary btn-lg w-100 py-3 shadow-sm d-flex align-items-center justify-content-center gap-2 mt-2 rounded-4" disabled={loading}>
            {loading ? <Loader2 size={20} className="animate-spin" /> : <><LogIn size={20} /> เข้าสู่ระบบ</>}
          </button>
        </form>

        <div className="mt-4 text-center">
          <p className="small text-muted">
            ยังไม่มีบัญชีเจ้าหน้าที่? <Link href="/doctor/register" className="text-drpat-primary fw-bold text-decoration-none">ดูวิธีขอบัญชีจากคลินิก</Link>
          </p>
        </div>

        <div className="mt-5 pt-4 border-top text-center text-muted">
          <p className="tiny mb-0">Security Level: Grade-A Medical Data Encryption</p>
        </div>
      </div>
    </div>
  );
}
