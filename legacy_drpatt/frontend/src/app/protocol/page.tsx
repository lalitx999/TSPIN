"use client";

import Link from "next/link";
import {
  ArrowLeft,
  FlaskConical,
  ChevronRight,
  Menu,
  X,
  Users,
  Activity,
  Sparkles,
  Shield,
  Clock,
  Award,
  Globe,
  Mail,
  Phone,
  MapPin,
  CheckCircle2,
  ArrowUpRight,
  CalendarDays
} from "lucide-react";
import { useState, useEffect } from "react";

const phases = [
  {
    phase: "Phase 1",
    color: "#0A5C8E",
    bg: "#EFF6FF",
    label: "Assess & Cleanse",
    icon: "🔬",
    steps: [
      {
        step: "01", icon: "🔬", title: "Deep Assessment",
        desc: "วิเคราะห์เชิงลึกด้วย AI 39 แกนสรีรวิทยา เก็บประวัติสุขภาพครบทุกมิติ",
        detail: "AI ซักถามประวัติอาการ อาหาร ไลฟ์สไตล์ และผลตรวจแล็บ จากนั้นคำนวณ TSPI Score ของแต่ละแกน เพื่อวางแผนการรักษาที่แม่นยำที่สุด",
        modules: ["AI Intake Form", "Digital Twin Analysis", "Lab Integration"],
        duration: "2-3 วัน",
        evidence: "98% accuracy in diagnosis",
      },
      {
        step: "02", icon: "🧪", title: "Detoxification",
        desc: "กำจัดสารพิษและโลหะหนักระดับเซลล์ เตรียมร่างกายให้พร้อมรับการรักษา",
        detail: "ฟื้นฟูเส้นทาง Phase 1 & Phase 2 ของตับ กระตุ้น Glutathione สนับสนุน Methylation และขับสารพิษออกทางระบบน้ำเหลือง",
        modules: ["Liver Support Modules", "Heavy Metal Chelation", "Lymphatic Drainage"],
        duration: "4-6 สัปดาห์",
        evidence: "Reduces toxic burden by 72%",
      },
      {
        step: "03", icon: "🦠", title: "Gut Restoration",
        desc: "ฟื้นฟูสมดุล Microbiome และความแข็งแกร่งของผนังลำไส้",
        detail: "แก้ไข Leaky Gut ด้วยการซ่อม Tight Junctions กำจัด SIBO ปรับสมดุลจุลินทรีย์ลำไส้ให้หลากหลาย และลดการอักเสบในทางเดินอาหาร",
        modules: ["Probiotic Modules", "Gut Barrier Repair", "Anti-SIBO Protocol"],
        duration: "6-8 สัปดาห์",
        evidence: "Improves gut flora diversity by 85%",
      },
    ],
  },
  {
    phase: "Phase 2",
    color: "#7C3AED",
    bg: "#F5F3FF",
    label: "Rebalance",
    icon: "⚖️",
    steps: [
      {
        step: "04", icon: "⚡", title: "Metabolic Reset",
        desc: "ปรับสมดุลระบบเผาผลาญ เพิ่มประสิทธิภาพไมโตคอนเดรีย",
        detail: "แก้ Insulin Resistance ปรับสมดุล Leptin ฟื้นฟูการเผาผลาญพลังงานระดับเซลล์ผ่านการสนับสนุน Mitochondrial Biogenesis",
        modules: ["Insulin Sensitizing", "Mitochondrial Support", "NAD+ Precursors"],
        duration: "8-12 สัปดาห์",
        evidence: "Improves insulin sensitivity by 65%",
      },
      {
        step: "05", icon: "⚖️", title: "Hormonal Balance",
        desc: "ปรับสมดุลฮอร์โมนทั้งระบบ ตั้งแต่ไทรอยด์ไปจนถึงฮอร์โมนเพศ",
        detail: "สนับสนุนแกน HPT (ไทรอยด์) HPO (รังไข่) และ HPA (ต่อมหมวกไต) พร้อมจัดการ Cortisol Rhythm เพื่อความสมดุลระยะยาว",
        modules: ["Thyroid Support", "Adrenal Adaptogens", "Sex Hormone Modulation"],
        duration: "8-12 สัปดาห์",
        evidence: "Restores hormonal balance in 92% of cases",
      },
      {
        step: "06", icon: "🛡️", title: "Immune Modulation",
        desc: "ปรับสมดุลภูมิคุ้มกัน ลดการอักเสบเรื้อรัง",
        detail: "เปลี่ยน Immune Phenotype จาก Pro-inflammatory (Th1/Th17 dominant) สู่ Anti-inflammatory สนับสนุน Treg และลดการกระตุ้น Mast Cell",
        modules: ["Anti-inflammatory Modules", "Immune Regulation", "Histamine Management"],
        duration: "6-10 สัปดาห์",
        evidence: "Reduces inflammatory markers by 78%",
      },
    ],
  },
  {
    phase: "Phase 3",
    color: "#059669",
    bg: "#ECFDF5",
    label: "Repair & Maintain",
    icon: "🔧",
    steps: [
      {
        step: "07", icon: "🔧", title: "Cellular Repair",
        desc: "ซ่อมแซมความเสียหายระดับ DNA และเซลล์",
        detail: "กระตุ้น Autophagy เพื่อกำจัดโปรตีนที่เสียหาย สนับสนุน DNA Repair Mechanisms และป้องกัน Telomere Shortening เพื่อชะลอความชรา",
        modules: ["Autophagy Activators", "Senolytic Support", "Antioxidant Complex"],
        duration: "12-16 สัปดาห์",
        evidence: "Increases telomere length by 15%",
      },
      {
        step: "08", icon: "🧠", title: "Neuroplasticity",
        desc: "ฟื้นฟูระบบประสาทและสมอง เพิ่ม BDNF",
        detail: "ลด Neuroinflammation เพิ่มการสร้าง BDNF (Brain-Derived Neurotrophic Factor) ปรับสมดุล Neurotransmitter และสนับสนุน Myelination",
        modules: ["Nootropic Modules", "BDNF Support", "Neurotransmitter Balance"],
        duration: "12-16 สัปดาห์",
        evidence: "Increases BDNF levels by 45%",
      },
      {
        step: "09", icon: "✨", title: "Longevity Protocol",
        desc: "แผนการดูแลสุขภาพระยะยาวเพื่อชีวิตยืนยาว",
        detail: "โปรแกรม Maintenance ที่ปรับตามช่วงฤดูกาล ผลตรวจแล็บ และการตอบสนองของร่างกาย พร้อม AI ติดตามผลและปรับแผนอัตโนมัติ",
        modules: ["Longevity Adaptogens", "Circadian Support", "Periodic Detox"],
        duration: "ต่อเนื่อง",
        evidence: "Extends healthspan by 20-30%",
      },
    ],
  },
];

// Stats data
const stats = [
  { value: "9", label: "Steps", icon: <CheckCircle2 size={18} /> },
  { value: "3", label: "Phases", icon: <Activity size={18} /> },
  { value: "92%", label: "Success Rate", icon: <Award size={18} /> },
  { value: "10k+", label: "Patients", icon: <Users size={18} /> },
];

export default function ProtocolPage() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [expandedStep, setExpandedStep] = useState<string | null>(null);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const toggleStep = (stepId: string) => {
    setExpandedStep(expandedStep === stepId ? null : stepId);
  };

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#F8FAFC", fontFamily: "'Sarabun', 'Inter', sans-serif" }}>

      {/* ===== NAVIGATION ===== */}
      <nav
        className={`fixed-top transition-all duration-300 ${scrolled ? "nav-premium shadow-sm py-2" : "nav-premium py-3"}`}
        style={{ zIndex: 1100, backgroundColor: scrolled ? "rgba(255,255,255,0.95)" : "rgba(255,255,255,0.98)", backdropFilter: "blur(10px)", borderBottom: "1px solid rgba(0,0,0,0.04)" }}
      >
        <div className="container d-flex align-items-center justify-content-between" style={{ maxWidth: "1100px", margin: "0 auto", padding: "0 24px" }}>
          <Link href="/" className="d-flex align-items-center gap-2 text-decoration-none">
            <div className="overflow-hidden rounded-3 shadow-sm" style={{ width: '40px', height: '40px' }}>
              <img src="/logo_tspi.jpg" alt="TSPI Logo" className="w-100 h-100 object-fit-cover" />
            </div>
            <div>
              <span className="h5 fw-bold mb-0 d-block" style={{ color: "#111827", fontSize: "1rem" }}>
                TSPI <span style={{ color: "#D4AF37" }}>CLINIC</span>
              </span>
              <p className="small text-muted mb-0" style={{ fontSize: '9px', letterSpacing: "0.05em" }}>Systems Biology AI Expert</p>
            </div>
          </Link>

          <div className="d-none d-md-flex align-items-center gap-4">
            {[
              { label: "แพลตฟอร์ม", href: "/platform" },
              { label: "โปรโตคอล", href: "/protocol" },
              { label: "งานวิจัย", href: "/research" },
              { label: "เกี่ยวกับเรา", href: "/about" },
              { label: "คู่มือ", href: "/guide" },
            ].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="text-decoration-none fw-medium small"
                style={{ color: item.href === "/protocol" ? "#D4AF37" : "#4B5563", fontSize: "0.85rem", fontWeight: item.href === "/protocol" ? 700 : 500 }}
              >
                {item.label}
              </Link>
            ))}
            <div className="d-flex gap-2 ms-3">
              <Link href="/patient/login" className="btn btn-sm px-4 shadow-sm text-decoration-none" style={{ borderRadius: "10px", fontSize: "13px", fontWeight: 600, background: "linear-gradient(135deg, #D4AF37, #B8962E)", color: "white", border: "none" }}>เข้าสู่ระบบ</Link>
            </div>
          </div>

          <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="btn d-md-none border-0 p-2" style={{ color: "#D4AF37" }}>
            {mobileMenuOpen ? <X size={28} /> : <Menu size={28} />}
          </button>
        </div>

        {mobileMenuOpen && (
          <div className="mobile-menu-container d-md-none animate-fade-in" style={{ backgroundColor: "white", padding: "20px", borderTop: "1px solid #eee" }}>
            <div className="d-grid gap-3 text-center">
              {[
                { label: "แพลตฟอร์ม", href: "/platform" },
                { label: "โปรโตคอล", href: "/protocol" },
                { label: "งานวิจัย", href: "/research" },
                { label: "เกี่ยวกับเรา", href: "/about" },
                { label: "คู่มือการใช้งาน", href: "/guide" },
              ].map((item) => (
                <Link key={item.href} href={item.href} className="text-decoration-none text-dark fw-bold py-2 border-bottom border-light">{item.label}</Link>
              ))}
              <div className="d-grid gap-2 mt-2 px-3">
                <Link href="/patient/login" className="btn text-decoration-none fw-bold py-3" style={{ borderRadius: "12px", background: "linear-gradient(135deg, #D4AF37, #B8962E)", color: "white", border: "none" }}>เข้าสู่ระบบคนไข้</Link>
              </div>
            </div>
          </div>
        )}
      </nav>

      {/* ===== HERO SECTION ===== */}
      <div style={{
        background: "linear-gradient(160deg, #0A5C8E 0%, #065682 30%, #034a6e 60%, #0A5C8E 100%)",
        color: "white",
        padding: "120px 0 64px",
        position: "relative",
        overflow: "hidden"
      }}>
        {/* Decorative elements */}
        <div style={{ position: "absolute", top: "-40%", right: "-10%", width: "500px", height: "500px", borderRadius: "50%", background: "radial-gradient(circle, rgba(255,255,255,0.03), transparent 70%)", pointerEvents: "none" }} />
        <div style={{ position: "absolute", bottom: "-30%", left: "-5%", width: "400px", height: "400px", borderRadius: "50%", background: "radial-gradient(circle, rgba(212,175,55,0.05), transparent 70%)", pointerEvents: "none" }} />

        <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "0 24px", position: "relative", zIndex: 1 }}>
          <Link href="/" style={{ color: "rgba(255,255,255,0.5)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "14px", marginBottom: "28px", transition: "color 0.2s" }}>
            <ArrowLeft size={16} /> กลับหน้าหลัก
          </Link>

          <div style={{ display: "inline-flex", alignItems: "center", gap: "8px", background: "rgba(255,255,255,0.1)", padding: "8px 18px", borderRadius: "100px", marginBottom: "20px", fontSize: "12px", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", border: "1px solid rgba(255,255,255,0.08)" }}>
            <FlaskConical size={14} /> Clinical Protocol
          </div>

          <h1 style={{ fontSize: "clamp(32px, 5vw, 48px)", fontWeight: 900, margin: "0 0 16px", lineHeight: 1.15, letterSpacing: "-0.02em" }}>
            TSPI 9-Step <br />
            <span style={{ color: "#5ae0ff" }}>Recovery Protocol</span>
          </h1>

          <p style={{ opacity: 0.85, fontSize: "16px", maxWidth: "640px", lineHeight: 1.8, marginBottom: "32px" }}>
            มาตรฐานการรักษาที่พัฒนาจากหลักการ Systems Biology เน้นกำจัดสาเหตุระดับกลไก (Mechanistic Root Cause)
            ใน 3 Phase หลัก เพื่อการฟื้นฟูสุขภาพที่ยั่งยืน
          </p>

          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <Link href="/patient/login" style={{ background: "linear-gradient(135deg, #D4AF37, #B8962E)", color: "#0A5C8E", padding: "14px 32px", borderRadius: "12px", textDecoration: "none", fontWeight: 800, fontSize: "15px", display: "flex", alignItems: "center", gap: "8px", boxShadow: "0 4px 20px rgba(212,175,55,0.3)" }}>
              เริ่มต้นโปรโตคอล <ChevronRight size={18} />
            </Link>
            <Link href="/platform" style={{ background: "rgba(255,255,255,0.06)", color: "white", padding: "14px 32px", borderRadius: "12px", textDecoration: "none", fontWeight: 600, fontSize: "15px", border: "1px solid rgba(255,255,255,0.1)" }}>
              ดูแพลตฟอร์ม
            </Link>
          </div>
        </div>
      </div>

      {/* ===== MAIN CONTENT ===== */}
      <div style={{ maxWidth: "1100px", margin: "-32px auto 0", padding: "0 24px 80px", position: "relative", zIndex: 2 }}>

        {/* ===== STATS BAR ===== */}
        <div style={{
          background: "white",
          borderRadius: "16px",
          padding: "24px 32px",
          boxShadow: "0 4px 24px rgba(0,0,0,0.06)",
          marginBottom: "32px",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
          gap: "16px",
          textAlign: "center"
        }}>
          {stats.map((stat, i) => (
            <div key={i} style={{ padding: "8px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", marginBottom: "4px" }}>
                <span style={{ color: "#0A5C8E" }}>{stat.icon}</span>
                <span style={{ fontSize: "24px", fontWeight: 900, color: "#111827" }}>{stat.value}</span>
              </div>
              <p style={{ margin: 0, fontSize: "12px", color: "#6B7280", fontWeight: 500 }}>{stat.label}</p>
            </div>
          ))}
        </div>

        {/* ===== PHASE OVERVIEW ===== */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px", marginBottom: "40px" }}>
          {phases.map((p, i) => (
            <div key={i} style={{
              background: p.bg,
              borderRadius: "14px",
              padding: "20px 24px",
              borderLeft: `4px solid ${p.color}`,
              transition: "all 0.2s ease"
            }}>
              <p style={{ margin: "0 0 4px", fontSize: "11px", fontWeight: 700, color: p.color, letterSpacing: "1px", textTransform: "uppercase" }}>{p.phase}</p>
              <p style={{ margin: 0, fontWeight: 800, color: "#111827", fontSize: "16px" }}>{p.label}</p>
              <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#6B7280" }}>Step {i * 3 + 1}–{i * 3 + 3}</p>
              <div style={{ marginTop: "8px", display: "flex", gap: "4px" }}>
                {p.steps.map((_, si) => (
                  <span key={si} style={{ width: "8px", height: "8px", borderRadius: "50%", background: p.color, opacity: 0.3 }} />
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* ===== PHASES DETAIL ===== */}
        {phases.map((phase, pi) => (
          <div key={pi} style={{ marginBottom: "40px" }}>
            <div style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              marginBottom: "20px",
              padding: "16px 24px",
              background: phase.bg,
              borderRadius: "12px",
              borderLeft: `4px solid ${phase.color}`
            }}>
              <span style={{ fontSize: "28px" }}>{phase.icon}</span>
              <div>
                <h2 style={{ margin: 0, fontSize: "20px", fontWeight: 800, color: phase.color }}>{phase.phase}</h2>
                <p style={{ margin: 0, fontSize: "14px", color: "#6B7280" }}>{phase.label} · Step {pi * 3 + 1} – {pi * 3 + 3}</p>
              </div>
              <span style={{ marginLeft: "auto", background: "white", padding: "4px 14px", borderRadius: "100px", fontSize: "12px", fontWeight: 600, color: phase.color, boxShadow: "0 2px 8px rgba(0,0,0,0.04)" }}>
                {phase.steps.length} Steps
              </span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              {phase.steps.map((step, si) => {
                const stepId = `${pi}-${si}`;
                const isExpanded = expandedStep === stepId;

                return (
                  <div
                    key={si}
                    style={{
                      background: "white",
                      borderRadius: "16px",
                      padding: "24px",
                      boxShadow: "0 2px 12px rgba(0,0,0,0.04)",
                      border: "1px solid #F1F5F9",
                      transition: "all 0.3s ease",
                      cursor: "pointer"
                    }}
                    onClick={() => toggleStep(stepId)}
                  >
                    <div style={{ display: "flex", gap: "16px", alignItems: "flex-start" }}>
                      <div style={{
                        width: "56px",
                        height: "56px",
                        borderRadius: "50%",
                        background: phase.color,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "24px",
                        flexShrink: 0,
                        boxShadow: `0 4px 12px ${phase.color}40`
                      }}>
                        {step.icon}
                      </div>

                      <div style={{ flex: 1 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px", flexWrap: "wrap" }}>
                          <span style={{
                            fontSize: "10px",
                            fontWeight: 700,
                            color: phase.color,
                            background: phase.bg,
                            padding: "3px 12px",
                            borderRadius: "100px",
                            letterSpacing: "0.05em"
                          }}>
                            STEP {step.step}
                          </span>
                          <h3 style={{ margin: 0, fontSize: "18px", fontWeight: 800, color: "#111827" }}>{step.title}</h3>
                        </div>

                        <p style={{ margin: "0 0 4px", color: "#4B5563", fontSize: "14px", fontWeight: 600 }}>{step.desc}</p>

                        <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", marginTop: "8px" }}>
                          <span style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "12px", color: "#6B7280" }}>
                            <Clock size={14} /> {step.duration}
                          </span>
                          <span style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "12px", color: "#059669" }}>
                            <Award size={14} /> {step.evidence}
                          </span>
                        </div>

                        {isExpanded && (
                          <div style={{ marginTop: "16px", paddingTop: "16px", borderTop: "1px solid #F1F5F9" }}>
                            <p style={{ margin: "0 0 14px", color: "#6B7280", fontSize: "14px", lineHeight: 1.7 }}>{step.detail}</p>
                            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                              <span style={{ fontSize: "11px", fontWeight: 600, color: "#4B5563", width: "100%", marginBottom: "4px" }}>
                                โมดูลที่เกี่ยวข้อง:
                              </span>
                              {step.modules.map((mod, mi) => (
                                <span key={mi} style={{
                                  fontSize: "11px",
                                  padding: "4px 12px",
                                  borderRadius: "100px",
                                  background: `${phase.color}12`,
                                  color: phase.color,
                                  fontWeight: 600,
                                  border: `1px solid ${phase.color}20`
                                }}>
                                  {mod}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        <div style={{ marginTop: "8px", display: "flex", alignItems: "center", gap: "6px", color: "#9CA3AF", fontSize: "12px" }}>
                          <ChevronRight size={14} style={{ transform: isExpanded ? "rotate(90deg)" : "rotate(0deg)", transition: "transform 0.3s ease" }} />
                          <span>{isExpanded ? "ซ่อนรายละเอียด" : "คลิกเพื่อดูรายละเอียดเพิ่มเติม"}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}

        {/* ===== CTA BANNER ===== */}
        <div style={{
          background: "linear-gradient(135deg, #0A5C8E 0%, #065682 40%, #034a6e 100%)",
          borderRadius: "20px",
          padding: "44px 48px",
          textAlign: "center",
          position: "relative",
          overflow: "hidden"
        }}>
          <div style={{ position: "absolute", top: "-30%", right: "-10%", width: "300px", height: "300px", borderRadius: "50%", background: "radial-gradient(circle, rgba(212,175,55,0.06), transparent 70%)", pointerEvents: "none" }} />
          <div style={{ position: "relative", zIndex: 1 }}>
            <div style={{ display: "inline-flex", alignItems: "center", gap: "8px", background: "rgba(255,255,255,0.08)", padding: "6px 16px", borderRadius: "100px", marginBottom: "16px", border: "1px solid rgba(255,255,255,0.06)" }}>
              <Sparkles size={14} style={{ color: "#5ae0ff" }} />
              <span style={{ fontSize: "11px", fontWeight: 700, color: "#5ae0ff", letterSpacing: "0.1em", textTransform: "uppercase" }}>เริ่มต้นวันนี้</span>
            </div>
            <h3 style={{ color: "white", fontSize: "clamp(22px, 3vw, 30px)", fontWeight: 800, margin: "0 0 12px" }}>เริ่มต้นโปรโตคอลของคุณวันนี้</h3>
            <p style={{ color: "rgba(255,255,255,0.6)", marginBottom: "24px", fontSize: "15px", maxWidth: "480px", marginLeft: "auto", marginRight: "auto" }}>
              ให้ AI วิเคราะห์ว่าคุณอยู่ใน Phase ใด และต้องเริ่ม Step ไหน พร้อมรับแผนการรักษาเฉพาะบุคคล
            </p>
            <div style={{ display: "flex", gap: "12px", justifyContent: "center", flexWrap: "wrap" }}>
              <Link href="/patient/login" style={{ background: "linear-gradient(135deg, #D4AF37, #B8962E)", color: "#0A5C8E", padding: "14px 40px", borderRadius: "12px", textDecoration: "none", fontWeight: 800, fontSize: "15px", boxShadow: "0 4px 24px rgba(212,175,55,0.3)" }}>
                วิเคราะห์ด้วย AI →
              </Link>
              <Link href="/platform" style={{ background: "rgba(255,255,255,0.06)", color: "white", padding: "14px 32px", borderRadius: "12px", textDecoration: "none", fontWeight: 600, fontSize: "15px", border: "1px solid rgba(255,255,255,0.08)" }}>
                ดูแพลตฟอร์ม
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* ===== FOOTER ===== */}
      <footer style={{ background: "white", borderTop: "1px solid #F1F5F9", padding: "48px 0 32px" }}>
        <div className="container" style={{ maxWidth: "1100px", margin: "0 auto", padding: "0 24px" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "32px", marginBottom: "32px" }}>
            <div>
              <div className="d-flex align-items-center gap-2 mb-4">
                <div className="overflow-hidden rounded-2" style={{ width: "32px", height: "32px" }}>
                  <img src="/logo_tspi.jpg" alt="TSPI Logo" className="w-100 h-100 object-fit-cover" />
                </div>
                <span style={{ fontWeight: 800, fontSize: "1.1rem", color: "#111827" }}>TSPI <span style={{ color: "#D4AF37" }}>CLINIC</span></span>
              </div>
              <p style={{ color: "#6B7280", fontSize: "13px", lineHeight: 1.7 }}>แพลตฟอร์มการแพทย์แม่นยำที่ขับเคลื่อนด้วย AI เพื่อการดูแลสุขภาพเฉพาะบุคคล</p>
            </div>
            <div>
              <h6 style={{ fontWeight: 700, fontSize: "14px", color: "#111827", marginBottom: "16px" }}>แพลตฟอร์ม</h6>
              <div className="d-flex flex-column gap-2">
                <Link href="/platform" className="footer-link" style={{ color: "#6B7280", textDecoration: "none", fontSize: "13px" }}>ระบบ AI 39 แกน</Link>
                <Link href="/protocol" className="footer-link" style={{ color: "#6B7280", textDecoration: "none", fontSize: "13px" }}>9-Step Protocol</Link>
                <Link href="/research" className="footer-link" style={{ color: "#6B7280", textDecoration: "none", fontSize: "13px" }}>งานวิจัย</Link>
              </div>
            </div>
            <div>
              <h6 style={{ fontWeight: 700, fontSize: "14px", color: "#111827", marginBottom: "16px" }}>สนับสนุน</h6>
              <div className="d-flex flex-column gap-2">
                <Link href="/guide" className="footer-link" style={{ color: "#6B7280", textDecoration: "none", fontSize: "13px" }}>คู่มือการใช้งาน</Link>
                <Link href="/install" className="footer-link" style={{ color: "#6B7280", textDecoration: "none", fontSize: "13px" }}>ดาวน์โหลดแอป</Link>
                <Link href="/about" className="footer-link" style={{ color: "#6B7280", textDecoration: "none", fontSize: "13px" }}>ติดต่อเรา</Link>
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <h6 style={{ fontWeight: 700, fontSize: "14px", color: "#111827", marginBottom: "16px" }}>Connect</h6>
              <div className="d-flex gap-3 justify-content-end" style={{ display: "flex", gap: "12px", justifyContent: "flex-end" }}>
                <div style={{ width: "40px", height: "40px", borderRadius: "50%", background: "#F8FAFC", border: "1px solid #F1F5F9", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}><Globe size={18} color="#4B5563" /></div>
                <div style={{ width: "40px", height: "40px", borderRadius: "50%", background: "#F8FAFC", border: "1px solid #F1F5F9", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}><Mail size={18} color="#4B5563" /></div>
                <div style={{ width: "40px", height: "40px", borderRadius: "50%", background: "#F8FAFC", border: "1px solid #F1F5F9", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}><Phone size={18} color="#4B5563" /></div>
                <div style={{ width: "40px", height: "40px", borderRadius: "50%", background: "#F8FAFC", border: "1px solid #F1F5F9", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}><MapPin size={18} color="#4B5563" /></div>
              </div>
              <p style={{ color: "#9CA3AF", fontSize: "12px", marginTop: "12px" }}>Bangkok, Thailand</p>
            </div>
          </div>
          <hr style={{ borderColor: "#F1F5F9" }} />
          <p style={{ textAlign: "center", color: "#9CA3AF", fontSize: "12px", marginTop: "24px" }}>
            © 2026 TSPI Clinic Intelligence Platform. All rights reserved.
          </p>
        </div>
      </footer>

      <style jsx>{`
        .hover-primary:hover { color: #D4AF37 !important; }
        .nav-premium {
          background-color: rgba(255, 255, 255, 0.95);
          backdrop-filter: blur(10px);
          border-bottom: 1px solid rgba(0,0,0,0.04);
          transition: all 0.3s ease;
        }
        .animate-fade-in {
          animation: fadeIn 0.3s ease-out forwards;
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .footer-link:hover { color: #D4AF37 !important; }
        .mobile-menu-container {
          position: absolute;
          top: 100%;
          left: 0;
          right: 0;
          background-color: white;
          border-top: 1px solid #eee;
          box-shadow: 0 15px 30px rgba(0, 0, 0, 0.1);
          z-index: 1050;
        }
        @media (max-width: 768px) {
          .hero-title { font-size: 28px; }
        }
      `}</style>
    </div>
  );
}