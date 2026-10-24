"use client";

/**
 * ContextInspector.tsx
 * ─────────────────────────────────────────────────────────────
 * แสดงสถานะของ Reasoning Ledger และ Registry Gates
 * เพื่อให้แพทย์เห็นว่า Context ที่ AI ใช้อยู่ตอนนี้
 * มาจากแหล่งข้อมูลอะไร และ Registry ไหนยัง Blocked อยู่
 *
 * Props:
 *   patientId — ID ของคนไข้ที่เลือก (string | null)
 * ─────────────────────────────────────────────────────────────
 */

import React, { useState, useEffect } from "react";
import { getPatient, getLabResults } from "@/utils/api/services";
import { FlaskConical, Pill } from "lucide-react";

interface Props {
  patientId: string | null;
}

interface GateStatus {
  label: string;
  status: "APPROVED" | "UNAVAILABLE" | "PROVISIONAL";
  reason: string;
}

// ── สถานะ Registry Gates ปัจจุบัน ────────────────────────────
// เมื่อ Registry ใดพร้อมใช้งาน ให้เปลี่ยน status เป็น "APPROVED"
const REGISTRY_GATES: GateStatus[] = [
  {
    label: "39-Axis Master Ontology",
    status: "APPROVED",
    reason: "framework_version: 39-axis-master-260715 — ล็อกแล้ว",
  },
  {
    label: "Nine Restoration Steps",
    status: "APPROVED",
    reason: "ชื่อและลำดับล็อกจาก Official TSPI Definition",
  },
  {
    label: "180-Network Registry",
    status: "UNAVAILABLE",
    reason: "PDF ยังไม่ machine-readable — ห้ามสร้าง Network Score",
  },
  {
    label: "Module Registry",
    status: "PROVISIONAL",
    reason: "mapping_status ยังไม่ APPROVED — แสดงได้เฉพาะ PROVISIONAL CANDIDATE",
  },
  {
    label: "Research Database",
    status: "UNAVAILABLE",
    reason: "ยังไม่เชื่อมต่อ Study Registry — ห้ามแสดง Effect Size หรือ p-value",
  },
  {
    label: "Clinical Case Database",
    status: "UNAVAILABLE",
    reason: "ยังไม่มี query log — ห้ามสร้าง Case Number หรือ Match %",
  },
];

// ── สีและ label ตาม status ───────────────────────────────────
const STATUS_CONFIG: Record<GateStatus["status"], { bg: string; text: string; dot: string; badge: string }> = {
  APPROVED:    { bg: "#F0FDF4", text: "#15803D", dot: "#22C55E", badge: "✅ APPROVED" },
  UNAVAILABLE: { bg: "#FFF7ED", text: "#C2410C", dot: "#F97316", badge: "🚫 UNAVAILABLE" },
  PROVISIONAL: { bg: "#FEFCE8", text: "#A16207", dot: "#EAB308", badge: "⚠️ PROVISIONAL" },
};

export default function ContextInspector({ patientId }: Props) {
  const [labs, setLabs] = useState<any[]>([]);
  const [medications, setMedications] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!patientId) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);

    (async () => {
      try {
        const [rawLabs, patient] = await Promise.all([
          getLabResults(patientId),
          getPatient(patientId),
        ]);

        if (cancelled) return;

        const formattedLabs = Array.isArray(rawLabs)
          ? rawLabs.map((l: any) => ({
              test_name: l.test_name || l.name || l.parameter || "Unknown Test",
              result_value: l.result_value ?? l.value ?? l.result ?? "-",
              unit: l.unit || "",
              is_abnormal: l.is_abnormal ?? l.abnormal ?? false,
              test_date: l.test_date || l.date || l.collected_at || "",
            }))
          : [];

        setLabs(formattedLabs);
        setMedications(patient?.current_medications || "");
      } catch (err) {
        console.error("ContextInspector: Failed to load clinical context:", err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [patientId]);

  if (!patientId) {
    return (
      <div style={{ padding: "16px", color: "#9CA3AF", fontSize: "13px", textAlign: "center" }}>
        — เลือกคนไข้เพื่อดู Context Inspector —
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      {/* Clinical Context (live patient data) */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <span style={{ fontSize: "11px", fontWeight: 700, color: "#6B7280", letterSpacing: "0.08em", textTransform: "uppercase" }}>
          Clinical Context
        </span>
        {loading && <span style={{ fontSize: "10px", color: "#9CA3AF" }}>กำลังโหลด...</span>}
      </div>

      <div>
        <p style={{ fontSize: "11px", fontWeight: 700, color: "#6B7280", textTransform: "uppercase", display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
          <FlaskConical size={13} /> Latest Lab Results
        </p>
        {labs.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            {labs.map((lab, i) => (
              <div key={i} style={{ padding: "8px 12px", background: "#F9FAFB", borderRadius: "8px", border: "1px solid #F3F4F6" }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ fontSize: "12px", fontWeight: 600, color: "#111827" }}>{lab.test_name}</span>
                  <span style={{ fontSize: "11px", fontWeight: 700, color: lab.is_abnormal ? "#DC2626" : "#059669" }}>
                    {lab.result_value} {lab.unit}
                  </span>
                </div>
                <p style={{ fontSize: "10px", color: "#9CA3AF", margin: "2px 0 0 0" }}>{lab.test_date || "N/A"}</p>
              </div>
            ))}
          </div>
        ) : (
          !loading && <p style={{ fontSize: "11px", color: "#9CA3AF" }}>ไม่พบข้อมูลผล Lab ล่าสุด</p>
        )}
      </div>

      <div>
        <p style={{ fontSize: "11px", fontWeight: 700, color: "#6B7280", textTransform: "uppercase", display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
          <Pill size={13} /> Current Medications
        </p>
        {medications ? (
          <p style={{ fontSize: "12px", color: "#374151", background: "#F9FAFB", padding: "10px 12px", borderRadius: "8px", border: "1px solid #F3F4F6", whiteSpace: "pre-wrap" }}>
            {medications}
          </p>
        ) : (
          !loading && <p style={{ fontSize: "11px", color: "#9CA3AF" }}>ไม่พบข้อมูลยาที่ใช้ปัจจุบัน</p>
        )}
      </div>

      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
        <span style={{ fontSize: "11px", fontWeight: 700, color: "#6B7280", letterSpacing: "0.08em", textTransform: "uppercase" }}>
          Registry Gate Status
        </span>
        <span style={{ fontSize: "10px", color: "#9CA3AF", fontWeight: 400 }}>
          (Patient ID: {patientId})
        </span>
      </div>

      {/* Gate Cards */}
      {REGISTRY_GATES.map((gate) => {
        const cfg = STATUS_CONFIG[gate.status];
        return (
          <div
            key={gate.label}
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: "10px",
              padding: "10px 14px",
              borderRadius: "8px",
              background: cfg.bg,
              border: `1px solid ${cfg.dot}40`,
            }}
          >
            {/* Dot */}
            <div
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                background: cfg.dot,
                marginTop: "4px",
                flexShrink: 0,
              }}
            />
            {/* Text */}
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                <span style={{ fontSize: "13px", fontWeight: 600, color: "#111827" }}>
                  {gate.label}
                </span>
                <span
                  style={{
                    fontSize: "10px",
                    fontWeight: 700,
                    color: cfg.text,
                    background: `${cfg.dot}20`,
                    padding: "1px 8px",
                    borderRadius: "12px",
                  }}
                >
                  {cfg.badge}
                </span>
              </div>
              <p style={{ fontSize: "11px", color: "#6B7280", margin: "3px 0 0 0", lineHeight: 1.5 }}>
                {gate.reason}
              </p>
            </div>
          </div>
        );
      })}

      {/* Footer Note */}
      <div style={{ fontSize: "11px", color: "#9CA3AF", paddingTop: "4px", borderTop: "1px solid #F3F4F6", lineHeight: 1.6 }}>
        🔒 AI-GENERATED CLINICAL DRAFT — PENDING PHYSICIAN REVIEW — NOT FOR PATIENT RELEASE
        <br />
        Reasoning Ledger version: <strong>39-axis-master-260715</strong> · Safety Gate Engine: keys-v1.0
      </div>
    </div>
  );
}
