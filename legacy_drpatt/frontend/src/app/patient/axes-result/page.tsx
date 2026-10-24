"use client";

import { useState, useEffect, useMemo } from "react";
import {
  Search,
  Activity,
  Info,
  X,
  ChevronDown,
  ChevronUp,
  Beaker,
  ShieldCheck,
  Heart,
  TrendingUp,
  AlertTriangle,
  HelpCircle
} from "lucide-react";
import Link from "next/link";
import { getAxes } from "@/utils/api/services";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface AxisData {
  id: string;
  axis_id: string;
  name: string;
  domain_title: string;
  description?: string;
  sub_axes?: Record<string, { name: string; description: string }>;
}

export default function PatientAxesResultPage() {
  const [axes, setAxes] = useState<AxisData[]>([]);
  const [patientAxes, setPatientAxes] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [patientName, setPatientName] = useState("");
  const [hn, setHn] = useState("");

  useEffect(() => {
    const loadData = async () => {
      if (typeof window === "undefined") return;
      const token = localStorage.getItem("patient_access_token");
      if (!token) {
        window.location.href = "/patient/login";
        return;
      }

      try {
        // 1. Fetch patient profile with axes records from Django
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

        // 2. Fetch axes dictionary
        const axesData = await getAxes();
        const sorted = axesData.sort((a: any, b: any) => {
          const idA = parseInt(String(a.axis_id).replace(/\D/g, '')) || 0;
          const idB = parseInt(String(b.axis_id).replace(/\D/g, '')) || 0;
          return idA - idB;
        });
        setAxes(sorted);

      } catch (error) {
        console.error("Error loading patient axes scores:", error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  const getScoreStatus = (score: number) => {
    if (score >= 40 && score <= 60) {
      return { label: "สมดุล (Optimal)", color: "#10b981", bg: "#ecfdf5", border: "rgba(16,185,129,0.15)", type: "optimal" };
    } else if ((score >= 25 && score < 40) || (score > 60 && score <= 75)) {
      return { label: "ไม่สมดุลเล็กน้อย (Borderline)", color: "#f59e0b", bg: "#fffbeb", border: "rgba(245,158,11,0.15)", type: "warning" };
    } else {
      return { label: "ไม่สมดุลรุนแรง (Dysfunction)", color: "#ef4444", bg: "#fef2f2", border: "rgba(239,68,68,0.15)", type: "danger" };
    }
  };

  const filteredAxes = axes.filter(axis =>
    (axis.name || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
    (axis.domain_title || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
    String(axis.axis_id).toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Group axes by domain_title
  const groupedAxes = useMemo(() => {
    const groups: Record<string, AxisData[]> = {};
    filteredAxes.forEach(axis => {
      const domain = axis.domain_title || "ระบบทั่วไป (General Biology)";
      if (!groups[domain]) groups[domain] = [];
      groups[domain].push(axis);
    });
    // Sort domains alphabetically
    const sortedGroups: Record<string, AxisData[]> = {};
    Object.keys(groups).sort().forEach(key => {
      sortedGroups[key] = groups[key];
    });
    return sortedGroups;
  }, [filteredAxes]);

  // Compute overall health metrics
  const stats = useMemo(() => {
    const scores = Object.values(patientAxes);
    if (scores.length === 0) return { optimal: 0, warning: 0, danger: 0, average: 50 };

    let optimal = 0;
    let warning = 0;
    let danger = 0;
    let sum = 0;

    scores.forEach(score => {
      sum += score;
      const status = getScoreStatus(score);
      if (status.type === "optimal") optimal++;
      else if (status.type === "warning") warning++;
      else danger++;
    });

    return {
      optimal,
      warning,
      danger,
      average: Math.round(sum / scores.length)
    };
  }, [patientAxes]);

  const toggleExpand = (id: string) => {
    setExpandedId(prev => prev === id ? null : id);
  };

  if (loading) {
    return (
      <div className="d-flex align-items-center justify-content-center min-vh-100 bg-light">
        <div className="text-center">
          <div className="spinner-border text-primary-custom mb-3" role="status" style={{ width: '40px', height: '40px', color: '#D4AF37' }}>
            <span className="visually-hidden">กำลังโหลด...</span>
          </div>
          <h5 className="fw-bold text-dark">กำลังประมวลผลข้อมูล 39 แกนสุขภาพ...</h5>
          <p className="text-muted small">ระบบรักษาความปลอดภัยกำลังถอดรหัสและดึงข้อมูลผลแล็บ</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container py-4" style={{ maxWidth: '1000px', paddingBottom: '80px' }}>
      
      {/* ===== HEADER ===== */}
      <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
        <div>
          <h1 className="fs-4 fw-bold text-dark mb-1" style={{ letterSpacing: '-0.3px' }}>
            ผลวิเคราะห์ระบบชีววิทยา 39 แกน
          </h1>
          <p className="text-muted mb-0 small">
            ถอดรหัสกลไกเชิงลึกของร่างกายตามหลักการแพทย์แบบเจาะจงบุคคล (TSPI Core Pathways)
          </p>
        </div>

        {/* Search input */}
        <div className="position-relative" style={{ minWidth: '280px' }}>
          <Search size={14} className="position-absolute top-50 start-0 translate-middle-y ms-3 text-muted" />
          <input
            type="text"
            placeholder="ค้นหาแกน, ระบบ หรือรหัส..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="form-control ps-5 py-2 rounded-pill border-0 shadow-sm"
            style={{ fontSize: '13px', backgroundColor: '#fff', color: '#0f172a' }}
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm("")}
              className="btn border-0 position-absolute top-50 end-0 translate-middle-y me-2 p-1 text-muted"
            >
              <X size={12} />
            </button>
          )}
        </div>
      </div>

      {/* ===== PATIENT BRIEF CARD ===== */}
      <div 
        className="card border-0 rounded-4 shadow-sm p-4 mb-4" 
        style={{ 
          background: "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)",
          color: "white"
        }}
      >
        <div className="row g-4 align-items-center">
          <div className="col-md-6">
            <div className="d-flex align-items-center gap-3">
              <div 
                className="rounded-circle d-flex align-items-center justify-content-center fw-bold"
                style={{ 
                  width: '56px', 
                  height: '56px', 
                  background: 'linear-gradient(135deg, #D4AF37 0%, #B8962E 100%)',
                  fontSize: '22px'
                }}
              >
                {patientName.charAt(0).toUpperCase()}
              </div>
              <div>
                <h5 className="fw-bold mb-0 text-white">{patientName}</h5>
                <p className="text-white opacity-60 mb-0 small" style={{ letterSpacing: '0.5px' }}>
                  หมายเลขประจำตัวคนไข้: {hn}
                </p>
              </div>
            </div>
          </div>
          <div className="col-md-6 border-start border-white border-opacity-10">
            <div className="d-flex justify-content-around text-center">
              <div>
                <p className="text-white opacity-60 small mb-1">สมดุลสมบูรณ์</p>
                <h4 className="fw-bold text-success mb-0" style={{ color: '#10b981 !important' }}>{stats.optimal} <span className="small text-white opacity-40">แกน</span></h4>
              </div>
              <div>
                <p className="text-white opacity-60 small mb-1">เฝ้าระวัง</p>
                <h4 className="fw-bold text-warning mb-0" style={{ color: '#f59e0b !important' }}>{stats.warning} <span className="small text-white opacity-40">แกน</span></h4>
              </div>
              <div>
                <p className="text-white opacity-60 small mb-1">ไม่สมดุล</p>
                <h4 className="fw-bold text-danger mb-0" style={{ color: '#ef4444 !important' }}>{stats.danger} <span className="small text-white opacity-40">แกน</span></h4>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ===== OVERVIEW INFORMATION ===== */}
      <div 
        className="card border-0 rounded-4 shadow-sm p-3 mb-4" 
        style={{ backgroundColor: '#eff6ff', border: '1px solid #dbeafe' }}
      >
        <div className="d-flex align-items-start gap-2.5">
          <Info size={18} className="text-primary flex-shrink-0 mt-0.5" />
          <div style={{ fontSize: '12px', lineHeight: 1.5, color: '#1e3a8a' }}>
            <strong>คำชี้แจงสำหรับคนไข้:</strong> คะแนนของแต่ละแกนสุขภาพอยู่ระหว่าง 0 ถึง 100 โดยจุดศูนย์กลางสมดุล (Homeostasis) ของร่างกายจะอยู่ที่ค่าประมาณ <strong>50 คะแนน</strong> หากมีคะแนนสูงหรือต่ำเกินไปจะส่งผลให้ระบบทำงานผิดปกติ (Dysfunction) คุณสามารถอ่านรายละเอียดย่อยได้โดยคลิกเปิดทีละแกนครับ
          </div>
        </div>
      </div>

      {/* ===== DYNAMIC CATEGORIES ===== */}
      {Object.keys(groupedAxes).length === 0 ? (
        <div className="card border-0 rounded-4 shadow-sm text-center py-5">
          <Beaker size={48} className="text-muted mb-3 opacity-30" />
          <h6 className="text-muted fw-bold">ไม่พบแกนสุขภาพที่ตรงตามการค้นหา</h6>
          <p className="text-muted small">กรุณาลองเปลี่ยนคำค้นหาใหม่อีกครั้งครับ</p>
        </div>
      ) : (
        <div className="d-flex flex-column gap-4">
          {Object.entries(groupedAxes).map(([domain, domainAxes]) => (
            <div key={domain} className="card border-0 rounded-4 shadow-sm overflow-hidden">
              
              {/* Category Domain Header */}
              <div 
                className="px-4 py-3 bg-light border-bottom d-flex align-items-center justify-content-between"
                style={{ backgroundColor: '#f8fafc' }}
              >
                <div className="d-flex align-items-center gap-2">
                  <div style={{ width: '6px', height: '18px', backgroundColor: '#D4AF37', borderRadius: '3px' }} />
                  <h3 className="fw-bold text-dark mb-0" style={{ fontSize: '15px' }}>
                    {domain}
                  </h3>
                </div>
                <span className="badge rounded-pill bg-white text-dark border px-3 py-1" style={{ fontSize: '11px', fontWeight: 600 }}>
                  {domainAxes.length} แกนหลัก
                </span>
              </div>

              {/* Axes Lists within Domain */}
              <div className="list-group list-group-flush">
                {domainAxes.map((axis) => {
                  const isExpanded = expandedId === axis.id;
                  const score = patientAxes[`axis_${axis.axis_id}`] ?? 50;
                  const status = getScoreStatus(score);

                  return (
                    <div 
                      key={axis.id}
                      className="list-group-item p-0 border-bottom border-light"
                      style={{ transition: 'all 0.2s' }}
                    >
                      {/* Row Clickable Area */}
                      <div 
                        onClick={() => toggleExpand(axis.id)}
                        className="p-3.5 d-flex flex-column flex-sm-row justify-content-between align-items-sm-center gap-3 cursor-pointer hover-bg"
                        style={{ cursor: 'pointer' }}
                      >
                        <div className="d-flex align-items-center gap-3 flex-grow-1">
                          {/* Axis Badge */}
                          <div 
                            className="fw-bold rounded-3 d-flex align-items-center justify-content-center"
                            style={{
                              width: '38px',
                              height: '38px',
                              backgroundColor: isExpanded ? '#0f172a' : '#f1f5f9',
                              color: isExpanded ? '#fff' : '#475569',
                              fontSize: '12px',
                              transition: 'all 0.2s'
                            }}
                          >
                            A{axis.axis_id}
                          </div>
                          <div>
                            <h4 
                              className="fw-bold mb-0 text-dark" 
                              style={{ 
                                fontSize: '14.5px',
                                color: isExpanded ? '#D4AF37' : '#1f2937'
                              }}
                            >
                              {axis.name}
                            </h4>
                            <p className="text-muted mb-0" style={{ fontSize: '10.5px' }}>
                              {axis.sub_axes ? `${Object.keys(axis.sub_axes).length} องค์ประกอบย่อย` : 'กลไกหลักเชิงเดี่ยว'}
                            </p>
                          </div>
                        </div>

                        {/* Triage Rating and Score Bar */}
                        <div className="d-flex align-items-center gap-3" style={{ minWidth: '220px' }}>
                          <div className="flex-grow-1">
                            <div className="d-flex justify-content-between mb-1" style={{ fontSize: '10px', fontWeight: 600 }}>
                              <span style={{ color: status.color }}>{status.label}</span>
                              <span className="text-dark">{score} / 100</span>
                            </div>
                            <div style={{ height: '5px', backgroundColor: '#e2e8f0', borderRadius: '3px', overflow: 'hidden' }}>
                              <div 
                                style={{ 
                                  height: '100%', 
                                  width: `${score}%`, 
                                  backgroundColor: status.color,
                                  borderRadius: '3px',
                                  transition: 'width 0.3s ease'
                                }}
                              />
                            </div>
                          </div>
                          
                          {/* Toggle Arrow */}
                          <div className="text-muted flex-shrink-0">
                            {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                          </div>
                        </div>
                      </div>

                      {/* Expandable Description Area */}
                      {isExpanded && (
                        <div className="px-4 py-4 bg-light bg-opacity-50 border-top border-light animate-fade-in" style={{ backgroundColor: '#fafafa' }}>
                          
                          {axis.sub_axes && Object.keys(axis.sub_axes).length > 0 ? (
                            <div className="d-flex flex-column gap-3.5">
                              <h5 className="fw-bold text-dark" style={{ fontSize: '12px', letterSpacing: '0.5px' }}>
                                รายละเอียดและองค์ประกอบย่อยของแกนหลัก:
                              </h5>
                              {Object.entries(axis.sub_axes).sort().map(([subKey, subAxis]: any) => (
                                <div key={subKey} className="d-flex align-items-start gap-2.5">
                                  <div 
                                    className="fw-bold text-muted rounded d-flex align-items-center justify-content-center flex-shrink-0"
                                    style={{
                                      width: '24px',
                                      height: '24px',
                                      backgroundColor: '#e2e8f0',
                                      fontSize: '11px'
                                    }}
                                  >
                                    {subKey}
                                  </div>
                                  <div>
                                    <h6 className="fw-bold text-dark mb-0.5" style={{ fontSize: '13px' }}>
                                      {subAxis.name}
                                    </h6>
                                    <p className="text-muted mb-0" style={{ fontSize: '12px', lineHeight: 1.6 }}>
                                      {subAxis.description}
                                    </p>
                                  </div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="d-flex align-items-start gap-3">
                              <Beaker size={18} className="text-muted flex-shrink-0 mt-0.5" />
                              <div>
                                <h5 className="fw-bold text-dark" style={{ fontSize: '12px', letterSpacing: '0.5px', marginBottom: '6px' }}>
                                  คำอธิบายกลไกทางเคมีของแกน:
                                </h5>
                                <p className="text-muted mb-0" style={{ fontSize: '13px', lineHeight: 1.6 }}>
                                  {axis.description || "กำลังดำเนินการจัดเตรียมข้อมูลอ้างอิงทางวิชาการและแนวทางแพทย์จากระบบฐานความรู้หลัก..."}
                                </p>
                              </div>
                            </div>
                          )}

                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

            </div>
          ))}
        </div>
      )}

      {/* ===== SUPPORT WARNING FOOTER ===== */}
      <div 
        className="card border-0 rounded-4 shadow-sm p-4 mt-5" 
        style={{ backgroundColor: '#fff', border: '1px solid #e2e8f0' }}
      >
        <div className="d-flex gap-3 align-items-start">
          <div 
            className="p-2 rounded-3 text-primary bg-primary bg-opacity-10 d-flex align-items-center justify-content-center"
            style={{ width: '40px', height: '40px', backgroundColor: 'rgba(212,175,55,0.06)' }}
          >
            <ShieldCheck size={20} style={{ color: '#D4AF37' }} />
          </div>
          <div>
            <h6 className="fw-bold text-dark mb-1" style={{ fontSize: '13px' }}>การวิเคราะห์ตามหลักการแพทย์เฉพาะบุคคล</h6>
            <p className="text-muted mb-0" style={{ fontSize: '12px', lineHeight: 1.6 }}>
              ข้อมูล 39 แกนชีววิทยานี้ประมวลผลขึ้นมาจากการจับคู่ผลตรวจเลือด ปัสสาวะ หรือผลตรวจแล็บอื่น ๆ ของคนไข้ ร่วมกับอัลกอริทึมการคำนวณของ TSPI Core Framework เพื่อใช้ร่วมกับการวินิจฉัยและออกแบบสูตรการดูแลสุขภาพโดยแพทย์ผู้เชี่ยวชาญ กรุณาปรึกษาแพทย์เจ้าของไข้เพื่อรับคำแนะนำการรักษาอย่างถูกต้อง
            </p>
          </div>
        </div>
      </div>

      <style jsx global>{`
        .hover-bg {
          transition: background-color 0.2s;
        }
        .hover-bg:hover {
          background-color: #f8fafc;
        }
        .animate-fade-in {
          animation: fadeIn 0.25s ease-out both;
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>

    </div>
  );
}
