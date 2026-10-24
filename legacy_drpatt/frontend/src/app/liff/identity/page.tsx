"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { useLiff } from "@/components/providers/LiffProvider";
import "./identity.css";

const messages: Record<string, string> = {
  CLINIC_LOGIN_REQUIRED: "กรุณาเข้าสู่ระบบคลินิก แล้วกลับมาหน้านี้เพื่อเชื่อมบัญชี",
  PASSWORD_CONFIRMATION_FAILED: "ยืนยันรหัสผ่านไม่สำเร็จ กรุณาตรวจสอบรหัสผ่านบัญชีคลินิก",
  LINE_LINK_CONFLICT: "บัญชีมีการเชื่อมต่ออื่นอยู่แล้ว กรุณาติดต่อคลินิก ไม่สามารถย้ายบัญชีอัตโนมัติได้",
  LINE_TOKEN_INVALID: "สิทธิ์ LINE หมดอายุหรือไม่ตรงกับแอป กรุณาปิดแล้วเปิดหน้านี้จาก LINE ใหม่",
  LINE_PROFILE_INVALID: "ไม่สามารถยืนยันบัญชี LINE ได้ กรุณาเปิดหน้านี้จาก LINE ใหม่",
  CLINIC_PATIENT_IDENTITY_AMBIGUOUS: "ข้อมูลบัญชีคลินิกไม่ชัดเจน กรุณาติดต่อคลินิกเพื่อตรวจสอบ",
};

export default function LiffIdentity() {
  const { liff, liffError, isLoggedIn } = useLiff();
  const [password, setPassword] = useState("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");
  const inFlight = useRef(false);

  async function handleLink(event: React.FormEvent) {
    event.preventDefault();
    if (inFlight.current || !consent || !liff || !isLoggedIn) return;
    inFlight.current = true;
    setBusy(true);
    setError("");
    try {
      const clinicToken = localStorage.getItem("patient_access_token");
      if (!clinicToken) { setError(messages.CLINIC_LOGIN_REQUIRED); return; }
      const lineToken = liff.getAccessToken();
      if (!lineToken) { setError(messages.LINE_TOKEN_INVALID); return; }
      const response = await fetch("/api/liff/identity", {
        method: "POST", cache: "no-store", signal: AbortSignal.timeout(25000),
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${clinicToken}` },
        body: JSON.stringify({ password, access_token: lineToken }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok || data?.success !== true) {
        setError(messages[data?.error] || "ยังเชื่อมบัญชีไม่สำเร็จ กรุณาลองใหม่ภายหลัง หากยังพบปัญหาให้ติดต่อคลินิก");
        return;
      }
      setSuccess(true);
    } catch {
      setError("ยังยืนยันผลไม่ได้ กรุณาลองใหม่ได้อย่างปลอดภัย ระบบจะไม่สร้างการเชื่อมซ้ำ");
    } finally {
      setPassword("");
      setBusy(false);
      inFlight.current = false;
    }
  }

  return <main className="liff-container">
    <section className="premium-card">
      <div className="card-header-gradient">
        <h1 className="h4 mb-2">เชื่อมบัญชี LINE กับคลินิก</h1>
        <p className="mb-0">ยืนยันทั้งบัญชีคลินิกและ LINE โดยไม่ใช้เบอร์โทรแทนการยืนยันตัวตน</p>
      </div>
      <div className="p-4">
        {success ? <div role="status">
          <h2 className="h5">เชื่อมบัญชีสำเร็จแล้ว</h2>
          <p>บัญชีนี้พร้อมใช้การเชื่อมต่อ LINE การอนุมัติรายงานทางการแพทย์เป็นขั้นตอนแยกต่างหาก</p>
          {liff?.isInClient() && <button className="btn btn-primary w-100 mb-3" onClick={() => liff.closeWindow()}>ปิดหน้านี้กลับ LINE</button>}
          <Link href="/patient/dashboard">กลับหน้าผู้ป่วย</Link>
        </div> : <>
          <p>เข้าสู่ระบบคลินิกด้วยบัญชีของคุณก่อน แล้วกลับมายืนยันการเชื่อมต่อที่หน้านี้</p>
          <Link href="/patient/login?returnTo=line-link">เข้าสู่ระบบ / เปลี่ยนบัญชีคลินิก</Link>
          {liffError && <p role="alert" className="text-danger mt-3">ยังเริ่ม LINE ไม่สำเร็จ กรุณาเปิดใหม่ภายหลังหรือติดต่อคลินิก</p>}
          {!liff && !liffError && <p role="status" className="mt-3">กำลังเตรียมการเชื่อมต่อ LINE… หากไม่พร้อม กรุณาติดต่อคลินิก</p>}
          {liff && !isLoggedIn && <button type="button" className="btn btn-outline-primary mt-3" onClick={() => liff.login({ redirectUri: window.location.origin + "/liff/identity" })}>เข้าสู่ระบบ LINE</button>}
          <form onSubmit={handleLink} className="mt-4">
            <label htmlFor="clinic-password" className="form-label">รหัสผ่านบัญชีคลินิก (ไม่ใช่รหัสผ่าน LINE)</label>
            <input id="clinic-password" type="password" autoComplete="current-password" className="form-control" required maxLength={1024}
              value={password} onChange={e => setPassword(e.target.value)} disabled={busy} />
            <label className="d-flex gap-2 my-3">
              <input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} disabled={busy} />
              <span>ฉันต้องการเชื่อมบัญชี LINE นี้กับบัญชีคลินิกของฉัน</span>
            </label>
            {error && <p role="alert" className="text-danger">{error}</p>}
            <button className="btn btn-primary w-100" disabled={busy || !consent || !liff || !isLoggedIn || !password}>
              {busy ? "กำลังยืนยันและเชื่อมบัญชี…" : "ยืนยันและเชื่อมบัญชี"}
            </button>
          </form>
          <p className="mt-3"><Link href="/patient/register">ยังไม่มีบัญชี? ลงทะเบียนผู้ป่วย</Link></p>
        </>}
      </div>
    </section>
  </main>;
}
