"use client";

import { useState, useEffect, useMemo } from "react";
import {
  Activity,
  ShieldCheck,
  Zap,
  Dna,
  Droplet,
  Heart,
  Bone,
  Brain,
  Star,
  ShieldAlert,
  Sliders,
  Sparkles,
  Info,
  ArrowRight,
  MessageSquare,
  FileText
} from "lucide-react";
import Link from "next/link";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip as RechartsTooltip
} from "recharts";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Domain visual mapping config ──────────────────────────────────
const DOMAINS_CONFIG: Record<number, { name: string; color: string; icon: any; desc: string; axes: number[] }> = {
  1: { name: "Immune–Infection Governance", color: "#ef4444", icon: ShieldCheck, desc: "ความแข็งแกร่งของระบบภูมิคุ้มกัน การอักเสบ และกลไกป้องกันการติดเชื้อ", axes: [1, 2, 3, 4] },
  2: { name: "Metabolic–Energy Core", color: "#10b981", icon: Zap, desc: "การเผาผลาญระดับเซลล์ ความไวต่ออินซูลิน และสุขภาพไมโตคอนเดรีย", axes: [5, 6, 7, 8, 9, 10] },
  3: { name: "Genomic–Longevity Programming", color: "#3b82f6", icon: Dna, desc: "กลไกการซ่อมแซม DNA และการทำงานของยีนควบคุมความชรา", axes: [11, 12, 13, 14] },
  4: { name: "Detox–Digestive–Gut Ecosystem", color: "#f59e0b", icon: Droplet, desc: "การทำงานของระบบขับสารพิษ ตับ ลำไส้ใหญ่ และระบบย่อยอาหาร", axes: [15, 16, 17, 18, 19] },
  5: { name: "Vascular–Circulation–Stroke", color: "#ec4899", icon: Heart, desc: "ความยืดหยุ่นของหลอดเลือด อัตราการไหลเวียน และความเสี่ยงต่อหัวใจ", axes: [20, 21, 22, 23] },
  6: { name: "Repair–Fibrosis–Regeneration", color: "#8b5cf6", icon: Bone, desc: "การซ่อมแซมเนื้อเยื่อ สเต็มเซลล์ และการป้องกันพังผืดส่วนเกิน", axes: [24, 25, 26, 27] },
  7: { name: "Musculoskeletal & Structural", color: "#f43f5e", icon: Activity, desc: "ความหนาแน่นมวลกระดูก และความแข็งแรงของระบบกล้ามเนื้อและข้อต่อ", axes: [28, 29, 30] },
  8: { name: "Endocrine Network", color: "#fb923c", icon: Star, desc: "การทำงานของต่อมไร้ท่อ วงจรฮอร์โมน และการรับมือความเครียดต่อมหมวกไต", axes: [31, 32, 33] },
  9: { name: "Neuro–Sleep–Stress", color: "#6366f1", icon: Brain, desc: "การตอบสนองของระบบประสาท การนอนหลับ และความสมดุลของสารเคมีสมอง", axes: [34, 35, 36] },
  10: { name: "Organ Axis + Oncology", color: "#06b6d4", icon: ShieldAlert, desc: "การปกป้องอวัยวะสำคัญ (ไต, ปอด) และระบบป้องกันเนื้องอกมะเร็ง", axes: [37, 38, 39] }
};

export default function PatientDigitalTwinPage() {
  const [patientName, setPatientName] = useState("");
  const [hn, setHn] = useState("");
  const [patientAxes, setPatientAxes] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadPatientData = async () => {
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
          setHn(profile.hn || "N/A");

          if (profile.axes_records && profile.axes_records.length > 0) {
            const latestRecord = profile.axes_records[0];
            const axesScores: Record<string, number> = {};
            for (let i = 1; i <= 39; i++) {
              axesScores[`axis_${i}`] = latestRecord[`axis_${i}`] ?? 50;
            }
            setPatientAxes(axesScores);
          }
        }
      } catch (error) {
        console.error("Error loading patient data for digital twin:", error);
      } finally {
        setLoading(false);
      }
    };

    loadPatientData();
  }, []);

  // Compute average score for each of the 10 domains
  const domainScores = useMemo(() => {
    return Object.entries(DOMAINS_CONFIG).map(([id, config]) => {
      const axesScores = config.axes.map(axisId => patientAxes[`axis_${axisId}`] ?? 50);
      const average = axesScores.reduce((sum, val) => sum + val, 0) / axesScores.length;
      const rounded = Math.round(average);

      let status = "สมดุล";
      let statusColor = "#10b981";
      let statusBg = "rgba(16,185,129,0.08)";

      // Homeostasis target is 50. Deviation calculates warning
      if (rounded < 35 || rounded > 65) {
        status = "ไม่สมดุล";
        statusColor = "#ef4444";
        statusBg = "rgba(239,68,68,0.08)";
      } else if (rounded < 43 || rounded > 57) {
        status = "เฝ้าระวัง";
        statusColor = "#f59e0b";
        statusBg = "rgba(245,158,11,0.08)";
      }

      return {
        id: parseInt(id),
        name: config.name,
        shortName: config.name.split("–")[0].split("&")[0].split("+")[0].trim(),
        score: rounded,
        color: config.color,
        icon: config.icon,
        desc: config.desc,
        status,
        statusColor,
        statusBg,
        axesCount: config.axes.length
      };
    });
  }, [patientAxes]);

  // Format data specifically for Recharts Radar Chart
  const radarChartData = useMemo(() => {
    return domainScores.map(d => ({
      subject: d.shortName,
      score: d.score,
      fullMark: 100
    }));
  }, [domainScores]);

  const getSystemStatusLabel = (score: number) => {
    if (score >= 43 && score <= 57) {
      return { text: "สมดุลดี (Optimal)", color: "#10b981", bg: "#ecfdf5" };
    } else if ((score >= 35 && score < 43) || (score > 57 && score <= 65)) {
      return { text: "เฝ้าระวัง (Borderline)", color: "#f59e0b", bg: "#fffbeb" };
    } else {
      return { text: "ไม่สมดุล (Imbalance)", color: "#ef4444", bg: "#fef2f2" };
    }
  };

  if (loading) {
    return (
      <div className="d-flex align-items-center justify-content-center min-vh-100 bg-light">
        <div className="text-center">
          <div className="spinner-border text-primary-custom mb-3" role="status" style={{ width: '40px', height: '40px', color: '#D4AF37' }}>
            <span className="visually-hidden">กำลังประมวลผล...</span>
          </div>
          <h5 className="fw-bold text-dark">กำลังจำลองแบบจำลองสุขภาพ Digital Twin...</h5>
          <p className="text-muted small">เชื่อมต่อเวกเตอร์ชีววิทยา 39 แกนหลัก</p>
        </div>
      </div>
    );
  }

  // Count domain severities
  const optimalCount = domainScores.filter(d => d.status === "สมดุล").length;
  const warningCount = domainScores.filter(d => d.status === "เฝ้าระวัง").length;
  const dangerCount = domainScores.filter(d => d.status === "ไม่สมดุล").length;

  return (
    <div className="container py-4" style={{ maxWidth: '1000px', paddingBottom: '80px' }}>

      {/* ===== HEADER ===== */}
      <div className="mb-4">
        <h1 className="fs-4 fw-bold text-dark mb-1" style={{ letterSpacing: '-0.3px' }}>
          ข้อมูลจำลองสุขภาพ Digital Twin
        </h1>
        <p className="text-muted mb-0 small">
          แบบจำลองชีววิทยาระบบแสดงกลไกการสืบย้อนความชราและสมดุลเซลล์เสมือนจริงรายบุคคล
        </p>
      </div>

      <div className="row g-4 mb-4">

        {/* RADAR CHART PANEL */}
        <div className="col-12 col-lg-6 order-2 order-lg-2">
          <div className="card border-0 rounded-4 shadow-sm p-4 h-100 bg-white">
            <h2 className="fw-bold text-dark mb-3" style={{ fontSize: '15px' }}>
              แผนผังระบบชีววิทยาร่างกาย (Systems Biology Radar)
            </h2>

            <div style={{ width: '100%', height: '340px', position: 'relative' }}>
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarChartData}>
                  <PolarGrid stroke="#e2e8f0" />
                  <PolarAngleAxis
                    dataKey="subject"
                    tick={{ fill: '#475569', fontSize: 10, fontWeight: 600 }}
                  />
                  <PolarRadiusAxis
                    angle={30}
                    domain={[0, 100]}
                    tick={{ fill: '#94a3b8', fontSize: 9 }}
                  />
                  <Radar
                    name={patientName}
                    dataKey="score"
                    stroke="#D4AF37"
                    fill="#D4AF37"
                    fillOpacity={0.2}
                  />
                  <RechartsTooltip />
                </RadarChart>
              </ResponsiveContainer>
            </div>

            <div className="d-flex justify-content-center gap-3 mt-3 flex-wrap">
              <span className="badge rounded-pill px-3 py-1.5" style={{ backgroundColor: '#ecfdf5', color: '#065f46', fontSize: '10px', fontWeight: 600 }}>
                🟢 สมบูรณ์: {optimalCount} ระบบ
              </span>
              <span className="badge rounded-pill px-3 py-1.5" style={{ backgroundColor: '#fffbeb', color: '#92400e', fontSize: '10px', fontWeight: 600 }}>
                🟡 เฝ้าระวัง: {warningCount} ระบบ
              </span>
              <span className="badge rounded-pill px-3 py-1.5" style={{ backgroundColor: '#fef2f2', color: '#991b1b', fontSize: '10px', fontWeight: 600 }}>
                🔴 ไม่สมดุล: {dangerCount} ระบบ
              </span>
            </div>
          </div>
        </div>

        {/* CLINICAL INSIGHT & DIGITAL TWIN BANNER */}
        <div className="col-12 col-lg-6 d-flex flex-column gap-3 order-1 order-lg-1">

          {/* Status summary */}
          <div
            className="card border-0 rounded-4 shadow-sm p-4 text-white flex-grow-1 d-flex flex-column justify-content-between"
            style={{ background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)' }}
          >
            <div>
              <div className="d-flex align-items-center gap-2 mb-2">
                <Sparkles size={16} className="text-warning animate-pulse" />
                <span className="text-uppercase tracking-wider opacity-60" style={{ fontSize: '10px', fontWeight: 700 }}>
                  HEALTH TWIN HUD
                </span>
              </div>
              <h3 className="fw-bold text-white mb-3" style={{ fontSize: '18px' }}>
                สวัสดีคุณ {patientName}
              </h3>
              <p className="opacity-80 small mb-4" style={{ lineHeight: '1.6' }}>
                นี่คือแผนภาพดิจิทัลทวินของคุณที่สร้างขึ้นโดยนำผลตรวจแล็บล่าสุดมาประมวลผลผ่าน 39 แกนกลไกหลักของเซลล์ คะแนนเป้าหมายสมดุลสูงสุดคือการควบคุมให้ทุกระบบอยู่ในเกณฑ์ **40 - 60 คะแนน** ซึ่งหมายถึงระบบชีววิทยามีสมดุลไม่ตึงหรือหย่อนเกินไป
              </p>
            </div>

            <div className="d-grid gap-2">
              <Link
                href="/patient/ai-intake"
                className="btn btn-warning py-2.5 px-4 rounded-3 border-0 fw-bold d-flex align-items-center justify-content-center gap-2 text-dark text-decoration-none hover-scale"
                style={{ fontSize: '12.5px' }}
              >
                <MessageSquare size={16} />
                ปรึกษาอาการกับ AI TSPI
                <ArrowRight size={14} />
              </Link>
              <Link
                href="/patient/axes-result"
                className="btn py-2.5 px-4 rounded-3 fw-bold d-flex align-items-center justify-content-center gap-2 text-white text-decoration-none hover-bg-glass border"
                style={{ fontSize: '12.5px', borderColor: 'rgba(255,255,255,0.15)', backgroundColor: 'rgba(255,255,255,0.05)' }}
              >
                <FileText size={16} />
                เจาะลึกคะแนน 39 แกนหลัก
              </Link>
            </div>
          </div>

          {/* Security details */}
          <div className="card border-0 rounded-4 shadow-sm p-4 bg-white">
            <div className="d-flex gap-3 align-items-start">
              <div
                className="p-2 rounded-3 text-primary d-flex align-items-center justify-content-center"
                style={{ backgroundColor: 'rgba(212,175,55,0.06)' }}
              >
                <ShieldCheck size={20} style={{ color: '#D4AF37' }} />
              </div>
              <div>
                <h4 className="fw-bold text-dark mb-1" style={{ fontSize: '13px' }}>
                  ระบบความปลอดภัยขั้นสูง (HIPAA Compliance)
                </h4>
                <p className="text-muted mb-0" style={{ fontSize: '11.5px', lineHeight: 1.5 }}>
                  แบบจำลองชีววิทยาเสมือนจริงนี้เก็บข้อมูลภายใต้การเข้ารหัสแบบ AES-256 เพื่อปกป้องเวกเตอร์ชีววิทยาของคนไข้ไม่ให้รั่วไหล และจำกัดสิทธิ์การเข้าอ่านเฉพาะคุณและแพทย์เจ้าของไข้เท่านั้น
                </p>
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* ===== SYSTEMS LIST ===== */}
      <h3 className="fw-bold text-dark mb-3" style={{ fontSize: '16px' }}>
        รายละเอียดระบบชีววิทยา 10 ด้านหลัก
      </h3>

      <div className="row g-3">
        {domainScores.map((domain) => {
          const statusDetail = getSystemStatusLabel(domain.score);
          const DomainIcon = domain.icon;

          return (
            <div key={domain.id} className="col-12 col-md-6 col-lg-6">
              <div
                className="card border-0 rounded-4 shadow-sm h-100 bg-white overflow-hidden hover-lift"
                style={{
                  transition: 'all 0.2s',
                  borderLeft: `4px solid ${domain.color}`
                }}
              >
                <div className="card-body p-4">
                  <div className="d-flex align-items-center justify-content-between mb-2">
                    <div className="d-flex align-items-center gap-2">
                      <div
                        className="rounded-3 d-flex align-items-center justify-content-center text-white"
                        style={{ width: '32px', height: '32px', backgroundColor: domain.color }}
                      >
                        <DomainIcon size={16} />
                      </div>
                      <h4 className="fw-bold text-dark mb-0" style={{ fontSize: '13.5px' }}>
                        {domain.name.split("–")[0]}
                      </h4>
                    </div>
                    <span
                      className="badge rounded-pill px-2.5 py-1"
                      style={{
                        fontSize: '9.5px',
                        backgroundColor: statusDetail.bg,
                        color: statusDetail.color,
                        fontWeight: 700
                      }}
                    >
                      {statusDetail.text}
                    </span>
                  </div>

                  <p className="text-muted mb-3" style={{ fontSize: '11px', lineHeight: 1.5 }}>
                    {domain.desc}
                  </p>

                  <div className="d-flex justify-content-between align-items-center bg-light p-2.5 rounded-3" style={{ backgroundColor: '#f8fafc' }}>
                    <span className="text-muted" style={{ fontSize: '11px' }}>คะแนนเฉลี่ยระบบ</span>
                    <span className="fw-bold text-dark" style={{ fontSize: '13px' }}>{domain.score} <span className="text-muted small" style={{ fontWeight: 400 }}>/ 100</span></span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {styleTag}
    </div>
  );
}

// Inline CSS details
const styleTag = (
  <style jsx global>{`
    .hover-lift {
      transition: transform 0.2s, box-shadow 0.2s;
    }
    .hover-lift:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.06);
    }
    .hover-scale {
      transition: transform 0.2s ease;
    }
    .hover-scale:hover {
      transform: scale(1.025);
    }
    .hover-bg-glass:hover {
      background-color: rgba(255,255,255,0.15) !important;
    }
    .animate-pulse {
      animation: pulse 2s infinite;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.6; }
    }
  `}</style>
);
