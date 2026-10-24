"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import WorkflowReviewTrace from "@/components/WorkflowReviewTrace";
import ReleaseReadinessPanel from "@/components/ReleaseReadinessPanel";
import { readReviewHistory, type History } from "@/lib/review-history-response";
import { createReviewSessionGuard } from "@/lib/review-session-guard";

type Artifact = { artifact_id: string; integrity_hash: string; kind: string; payload: unknown };
type PatientOption = { id: number; hn: string; name: string };
type ArtifactOption = { id: string; kind: string; created_at: string };

function object(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}
function display(value: unknown): string {
  return value === null || value === undefined ? "ไม่ได้ระบุ" : typeof value === "string" ? value : JSON.stringify(value);
}
function EvidenceTable({ payload }: { payload: unknown }) {
  const editions = object(object(object(payload).packet).editions);
  const facts = object(editions.PHYSICIAN).facts;
  if (!Array.isArray(facts)) return <p>ฉบับนี้ไม่มีตารางหลักฐาน กรุณาตรวจรายละเอียด JSON ด้านล่าง</p>;
  return <div className="table-responsive"><table className="table table-bordered">
    <caption>หลักฐานตามร่างต้นฉบับ ไม่ใช่การตีความหรือคำแนะนำรักษา</caption>
    <thead><tr><th>ข้อมูล</th><th>ค่า / หน่วย</th><th>แหล่งข้อมูล / เวลา</th><th>การตรวจสอบ</th></tr></thead>
    <tbody>{facts.map((raw, index) => { const fact = object(raw); return <tr key={index}>
      <td>{display(fact.concept_id)}<br /><small>{display(fact.evidence_id)}</small></td>
      <td style={{ whiteSpace: "pre-wrap" }}>{display(fact.value)} / {display(fact.unit)}</td>
      <td>{display(fact.source_id)} · {display(fact.source_type)}<br />{display(fact.source_timestamp)}</td>
      <td>{display(fact.verification)} · v{display(fact.version)}</td>
    </tr>; })}</tbody>
  </table>{facts.length === 0 && <p>ไม่มีหลักฐานในร่างนี้</p>}</div>;
}
const labels: Record<string, string> = {
  REVIEWED_NOT_APPROVED: "ตรวจแล้ว แต่ยังไม่อนุมัติ",
  REQUEST_CHANGES: "ขอแก้ไข",
  REJECT: "ปฏิเสธร่าง",
};

class ReviewAccessError extends Error {}

async function transport(path: string, body?: unknown) {
  const token = localStorage.getItem("doctor_access_token");
  if (!token) throw new Error("กรุณาเข้าสู่ระบบเจ้าหน้าที่ก่อน");
  const configured = process.env.NEXT_PUBLIC_API_URL;
  if (!configured) throw new Error("ยังไม่ได้ตั้งค่า API ของระบบ");
  const base = configured.replace(/\/+$/, "").replace(/\/api$/, "");
  const url = new URL(base);
  if (url.username || url.password || url.search || url.hash ||
      (url.protocol !== "https:" && !(url.protocol === "http:" && ["localhost", "127.0.0.1"].includes(url.hostname)))) {
    throw new Error("การตั้งค่า API ไม่ปลอดภัย");
  }
  const response = await fetch(`${base}/api/${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store", redirect: "error", signal: AbortSignal.timeout(20000),
  });
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) throw new ReviewAccessError("สิทธิ์หมดอายุหรือถูกระงับ กรุณาเข้าสู่ระบบเจ้าหน้าที่และเปิดร่างใหม่");
    const messages: Record<number, string> = {
      401: "บัญชีหมดอายุ กรุณาเข้าสู่ระบบเจ้าหน้าที่ใหม่", 403: "บัญชีนี้ไม่มีสิทธิ์ตรวจร่างหรืออ่านประวัติ",
      404: "ไม่พบร่างนี้สำหรับผู้ป่วยที่ระบุ", 409: "ฉบับร่างไม่ตรงหรือไม่ผ่านการตรวจความสมบูรณ์ กรุณาเปิดใหม่",
      400: "ข้อมูลคำขอไม่ถูกต้อง กรุณาตรวจสอบอีกครั้ง",
    };
    throw new Error(messages[response.status] || "ระบบไม่พร้อมใช้งาน");
  }
  const data = await response.json();
  if (localStorage.getItem("doctor_access_token") !== token) throw new Error("บัญชีเปลี่ยนระหว่างทำรายการ กรุณาเปิดร่างใหม่");
  return data;
}

export default function ArtifactReviewPage() {
  const [patient, setPatient] = useState("");
  const [artifactId, setArtifactId] = useState("");
  const [query, setQuery] = useState("");
  const [patients, setPatients] = useState<PatientOption[]>([]);
  const [artifacts, setArtifacts] = useState<ArtifactOption[]>([]);
  const [artifactCursor, setArtifactCursor] = useState<string | null>(null);
  const [opened, setOpened] = useState<{ path: string; patient: string; artifact: Artifact; session: string | null } | null>(null);
  const [history, setHistory] = useState<History>({ results: [], next_before_id: null });
  const [decision, setDecision] = useState("REQUEST_CHANGES");
  const [reason, setReason] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [mustReload, setMustReload] = useState(false);
  const inFlight = useRef(false);
  const pendingRequest = useRef<{ fingerprint: string; requestId: string } | null>(null);
  const sessionGuard = useRef(createReviewSessionGuard());
  const sessionToken = useRef<string | null>(null);

  function invalidateSession() {
    sessionGuard.current.invalidate();
    sessionToken.current = localStorage.getItem("doctor_access_token");
    pendingRequest.current = null;
    inFlight.current = false;
    setOpened(null); setHistory({ results: [], next_before_id: null });
    setPatients([]); setArtifacts([]); setArtifactCursor(null);
    setPatient(""); setArtifactId(""); setQuery(""); setReason("");
    setConfirmed(false); setDecision("REQUEST_CHANGES"); setMustReload(true); setBusy(false);
    setMessage("บัญชีเปลี่ยนหรือออกจากระบบแล้ว กรุณาค้นหาและเปิดร่างใหม่");
  }

  useEffect(() => {
    const guard = sessionGuard.current;
    sessionToken.current = localStorage.getItem("doctor_access_token");
    const storage = (event: StorageEvent) => {
      if (event.storageArea === localStorage && (event.key === "doctor_access_token" || event.key === null)) invalidateSession();
    };
    const check = () => {
      if (localStorage.getItem("doctor_access_token") !== sessionToken.current) invalidateSession();
    };
    window.addEventListener("storage", storage);
    window.addEventListener("focus", check);
    window.addEventListener("pageshow", check);
    document.addEventListener("visibilitychange", check);
    return () => {
      guard.invalidate();
      window.removeEventListener("storage", storage);
      window.removeEventListener("focus", check);
      window.removeEventListener("pageshow", check);
      document.removeEventListener("visibilitychange", check);
    };
  }, []);

  async function request(path: string, body?: unknown) {
    if (localStorage.getItem("doctor_access_token") !== sessionToken.current) {
      invalidateSession();
      throw new Error("บัญชีเปลี่ยน กรุณาเปิดร่างใหม่");
    }
    const generation = sessionGuard.current.capture();
    try {
      const result = await transport(path, body);
      sessionGuard.current.assertCurrent(generation);
      return result;
    } catch (error) {
      // An old failure must not clear a newer session's data.
      if (error instanceof ReviewAccessError && sessionGuard.current.isCurrent(generation)) {
        invalidateSession();
        setMessage(error.message);
      }
      throw error;
    }
  }

  async function run(work: () => Promise<void>) {
    if (inFlight.current) return;
    inFlight.current = true; setBusy(true); setMessage("");
    const generation = sessionGuard.current.capture();
    try { await work(); }
    catch (error) { if (sessionGuard.current.isCurrent(generation)) setMessage(error instanceof Error ? error.message : "ไม่สามารถทำรายการได้"); }
    finally { if (sessionGuard.current.isCurrent(generation)) { inFlight.current = false; setBusy(false); } }
  }

  async function openArtifact() {
    const session = localStorage.getItem("doctor_access_token");
    setOpened(null); setHistory({ results: [], next_before_id: null }); setConfirmed(false); setReason("");
    if (!/^[1-9]\d*$/.test(patient) || !/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(artifactId)) {
      throw new Error("กรุณาระบุ Patient ID และ Artifact UUID ให้ถูกต้อง");
    }
    const path = `patients/${patient}/agentic-artifacts/${artifactId}/`;
    const artifact: Artifact = await request(path);
    if (artifact.artifact_id.toLowerCase() !== artifactId.toLowerCase() || !/^[0-9a-f]{64}$/.test(artifact.integrity_hash)) {
      throw new Error("ข้อมูลฉบับร่างไม่ครบถ้วน");
    }
    const rows = readReviewHistory(await request(`${path}reviews/`), artifact.integrity_hash);
    if (localStorage.getItem("doctor_access_token") !== session) throw new Error("บัญชีเปลี่ยน กรุณาเปิดร่างใหม่");
    setHistory(rows); setOpened({ path, patient, artifact, session }); setMustReload(false);
  }

  async function saveReview() {
    if (!opened || !confirmed || !reason.trim() || mustReload) return;
    if (localStorage.getItem("doctor_access_token") !== opened.session) {
      setOpened(null);
      throw new Error("บัญชีเปลี่ยน กรุณาเปิดร่างและยืนยันการตรวจใหม่");
    }
    // A response may be lost after the server commits: require a reload before retry.
    setMustReload(true);
    try {
      const fingerprint = JSON.stringify([opened.path, opened.artifact.integrity_hash, decision, reason]);
      if (pendingRequest.current?.fingerprint !== fingerprint) {
        pendingRequest.current = { fingerprint, requestId: crypto.randomUUID() };
      }
      const saved = await request(`${opened.path}reviews/`, {
        expected_artifact_hash: opened.artifact.integrity_hash, decision, reason,
        request_id: pendingRequest.current.requestId,
      });
      if (saved.send_allowed !== false || saved.decision !== decision) throw new Error("ผลตอบกลับไม่ครบถ้วน");
      setReason(""); setConfirmed(false);
      setHistory(readReviewHistory(await request(`${opened.path}reviews/`), opened.artifact.integrity_hash));
      pendingRequest.current = null;
      setMustReload(false);
      setMessage("บันทึกผลตรวจแล้ว ยังไม่ได้อนุมัติหรือส่งรายงาน");
    } catch {
      throw new Error("ยังยืนยันผลบันทึกไม่ได้ กรุณาเปิดร่างและตรวจประวัติก่อนส่งซ้ำ");
    }
  }

  return <main className="container py-4">
    <Link href="/doctor/clinical-review">กลับหน้าตรวจเดิม</Link>
    <h1 className="h3 mt-3">ตรวจร่าง Agentic</h1>
    <p className="alert alert-warning">สำหรับผู้ตรวจที่มีสิทธิ์เท่านั้น — ไม่ใช่ลายเซ็นแพทย์ ไม่อนุมัติการรักษา และไม่ส่งรายงานผู้ป่วย</p>
    <form className="card p-3 mb-3" onSubmit={e => { e.preventDefault(); void run(async () => {
      setPatients([]); setArtifacts([]); setPatient(""); setArtifactId(""); setOpened(null); setArtifactCursor(null);
      const data = await request(`patients/artifact-review-patients/?q=${encodeURIComponent(query.trim())}`);
      setPatients(data.results);
      setMessage(data.truncated ? "พบมากกว่า 50 ราย กรุณาค้นให้เฉพาะเจาะจงขึ้น" : data.results.length ? "เลือกผู้ป่วยด้านล่าง" : "ไม่พบผู้ป่วยที่มีร่างตรงคำค้น");
    }); }}>
      <label>ค้นหาผู้ป่วยที่มีร่างด้วย HN หรือชื่อ<input className="form-control" minLength={2} maxLength={100} required value={query} disabled={busy} onChange={e => setQuery(e.target.value)} /></label>
      <button className="btn btn-outline-primary mt-2" disabled={busy}>ค้นหา</button>
      <label className="mt-2">เลือกผู้ป่วย<select aria-label="เลือกผู้ป่วย" className="form-select" value={patient} disabled={busy} onChange={e => {
        const selected = e.target.value; setPatient(selected); setArtifactId(""); setOpened(null); setArtifacts([]); setArtifactCursor(null);
        if (selected) void run(async () => { const data = await request(`patients/${selected}/artifact-review-list/`); setArtifacts(data.results); setArtifactCursor(data.next_before_id); });
      }}><option value="">เลือกผู้ป่วย</option>{patients.map(row => <option key={row.id} value={String(row.id)}>{row.hn} · {row.name} · ID {row.id}</option>)}</select></label>
      <label className="mt-2">เลือกร่าง (รายการไม่ได้เรียงตามเวลา)<select aria-label="เลือกร่าง (รายการไม่ได้เรียงตามเวลา)" className="form-select" value={artifactId} disabled={busy || !patient} onChange={e => { setArtifactId(e.target.value); setOpened(null); }}>
        <option value="">เลือกร่าง</option>{artifacts.map(row => <option key={row.id} value={row.id}>{row.kind} · {row.created_at} · {row.id}</option>)}
      </select></label>
      {artifactCursor && <button type="button" className="btn btn-link" disabled={busy} onClick={() => void run(async () => {
        const data = await request(`patients/${patient}/artifact-review-list/?before_id=${artifactCursor}`);
        setArtifacts(previous => [...previous, ...data.results]); setArtifactCursor(data.next_before_id);
      })}>โหลดร่างเพิ่มเติม</button>}
    </form>
    <form onSubmit={e => { e.preventDefault(); void run(openArtifact); }} className="row g-3">
      <label className="col-md-4">Patient ID (ระบุเองได้)<input className="form-control" required value={patient} disabled={busy} onChange={e => { setPatient(e.target.value); setOpened(null); setArtifactId(""); setArtifacts([]); setArtifactCursor(null); }} /></label>
      <label className="col-md-8">Artifact UUID<input className="form-control" required value={artifactId} disabled={busy} onChange={e => { setArtifactId(e.target.value); setOpened(null); }} /></label>
      <div><button className="btn btn-primary" disabled={busy}>เปิดร่างและโหลดประวัติ</button></div>
    </form>
    <p role="status" aria-live="polite" className="mt-3">{busy ? "กำลังทำรายการ…" : message}</p>
    {opened && <>
      <ReleaseReadinessPanel key={opened.artifact.artifact_id} artifactId={opened.artifact.artifact_id} inspect={() => request(`${opened.path}release-readiness/`)} />
      <section className="card p-3 my-3">
        <h2 className="h5">ผู้ป่วย ID {opened.patient} · {opened.artifact.kind}</h2>
        <p className="text-break">Artifact: {opened.artifact.artifact_id}<br />Hash: {opened.artifact.integrity_hash}</p>
        <p>ข้อมูลฉบับประวัติ ไม่รับรองว่าเป็นข้อมูลผู้ป่วยล่าสุด</p>
        {opened.artifact.kind === "WORKFLOW" ? <WorkflowReviewTrace payload={opened.artifact.payload} /> : <EvidenceTable payload={opened.artifact.payload} />}
        <details><summary>ดูเนื้อหาร่างและหลักฐาน (JSON)</summary><pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", maxHeight: 500, overflow: "auto" }}>{JSON.stringify(opened.artifact.payload, null, 2)}</pre></details>
      </section>
      <form onSubmit={e => { e.preventDefault(); void run(saveReview); }} className="card p-3">
        <label>ผลตรวจ<select className="form-select" value={decision} disabled={busy} onChange={e => setDecision(e.target.value)}>{Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label className="mt-3">เหตุผล<textarea className="form-control" required maxLength={4000} rows={4} value={reason} disabled={busy} onChange={e => setReason(e.target.value)} /></label>
        <label className="my-3"><input type="checkbox" checked={confirmed} disabled={busy} onChange={e => setConfirmed(e.target.checked)} /> ยืนยันว่าได้ตรวจผู้ป่วยและเนื้อหาร่างฉบับที่แสดงแล้ว</label>
        <button className="btn btn-primary" disabled={busy || !confirmed || !reason.trim() || mustReload}>บันทึกผลตรวจ (ไม่ใช่อนุมัติ)</button>
      </form>
      <section className="mt-4"><h2 className="h5">ประวัติตรวจร่าง</h2>
        {history.results.length === 0 && <p>ยังไม่มีผลตรวจ</p>}
        {history.results.map(row => <article className="card p-3 mb-2" key={row.id}>
          <strong>{labels[row.decision] || row.decision}</strong>
          <span>ผู้ตรวจ ID {row.actor_id} · {row.created_at}</span>
          <p style={{ whiteSpace: "pre-wrap" }}>{row.reason}</p>
        </article>)}
        {history.next_before_id && <button className="btn btn-outline-secondary" disabled={busy} onClick={() => void run(async () => {
          const older = readReviewHistory(await request(`${opened.path}reviews/?before_id=${history.next_before_id}`), opened.artifact.integrity_hash, history.next_before_id ?? undefined);
          setHistory(previous => ({ results: [...previous.results, ...older.results], next_before_id: older.next_before_id }));
        })}>โหลดประวัติเก่าเพิ่ม</button>}
      </section>
    </>}
  </main>;
}
