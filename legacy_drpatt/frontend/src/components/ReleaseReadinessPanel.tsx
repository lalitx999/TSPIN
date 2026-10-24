"use client";

import { useRef, useState } from "react";
import { releaseReadinessView } from "@/lib/release-readiness-view";

export default function ReleaseReadinessPanel({ artifactId, inspect }: {
  artifactId: string; inspect: () => Promise<unknown>;
}) {
  const [result, setResult] = useState<ReturnType<typeof releaseReadinessView> | null>(null);
  const [checkedAt, setCheckedAt] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const inFlight = useRef(false);
  async function check() {
    if (inFlight.current) return;
    inFlight.current = true; setBusy(true); setResult(null); setError(""); setCheckedAt("");
    try {
      setResult(releaseReadinessView(await inspect(), artifactId));
      setCheckedAt(new Date().toLocaleString("th-TH", { timeZone: "Asia/Bangkok" }));
    } catch {
      setError("ยังยืนยันผลตรวจไม่ได้ อาจไม่มีสิทธิ์หรือบริการไม่พร้อม กรุณาลองตรวจใหม่ ไม่มีการอนุมัติให้ส่ง");
    } finally { inFlight.current = false; setBusy(false); }
  }
  return <section className="card p-3 my-3" aria-label="เงื่อนไขก่อนส่งรายงาน">
    <h2 className="h5">เงื่อนไขก่อนส่งรายงาน</h2>
    <p>ตรวจสถานะเท่านั้น ไม่ใช่อนุมัติหรือส่งรายงาน ผลนี้เป็นข้อมูล ณ เวลาที่ตรวจ ไม่แทนการตรวจซ้ำก่อนส่งจริง</p>
    <button type="button" className="btn btn-outline-primary" disabled={busy} onClick={() => void check()}>{busy ? "กำลังตรวจ…" : "ตรวจเงื่อนไขกับข้อมูลปัจจุบัน"}</button>
    {error && <p role="alert" className="text-danger mt-2">{error}</p>}
    {result && <div className="mt-3" aria-live="polite">
      <strong>ยังไม่อนุญาตให้ส่งรายงาน</strong>
      <p>เวลารับผลตรวจ (กรุงเทพฯ): {checkedAt}<br />{result.current ? "ข้อมูลต้นทางตรงกับฉบับนี้ ณ เวลาตรวจ — ไม่ใช่การอนุมัติ" : "ยังยืนยันไม่ได้ว่าข้อมูลต้นทางตรงกับฉบับปัจจุบัน"}</p>
      <ul>{result.issues.map((issue, index) => <li key={index}>{issue.message} <code>{issue.code}</code></li>)}</ul>
      <details><summary>Manifest hashes</summary><p className="text-break">ฉบับร่าง: {result.artifactHash}<br />ปัจจุบัน: {result.currentHash || "ตรวจสอบไม่ได้"}</p></details>
    </div>}
  </section>;
}
