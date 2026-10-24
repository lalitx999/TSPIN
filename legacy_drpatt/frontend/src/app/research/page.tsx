"use client";

import Link from "next/link";
import {
  ArrowLeft,
  TrendingUp,
  Microscope,
  BarChart2,
  Star,
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
  FileText,
  BookOpen,
  HeartPulse,
  Dna,
  FlaskConical,
  Brain,
  Database
} from "lucide-react";
import { useState, useEffect } from "react";

const stats = [
  { value: "97.8%", label: "Accuracy Rate", desc: "ความแม่นยำในการวิเคราะห์รูปแบบสุขภาพ", color: "#0A5C8E" },
  { value: "96.2%", label: "Patient Satisfaction", desc: "ความพึงพอใจของผู้ป่วยที่ผ่านโปรโตคอล", color: "#059669" },
  { value: "43%", label: "Faster Recovery", desc: "เร็วกว่าการรักษาแบบดั้งเดิมโดยเฉลี่ย", color: "#7C3AED" },
  { value: "200+", label: "Active Modules", desc: "โมดูลสารสกัดธรรมชาติที่ validated แล้ว", color: "#D97706" },
  { value: "39", label: "Biological Axes", desc: "แกนสรีรวิทยาที่ AI วัดและวิเคราะห์", color: "#0A5C8E" },
  { value: "180", label: "Biological Networks", desc: "ระบบชีวโมเลกุลที่เป็นฐานความรู้", color: "#DC2626" },
];

const biomarkers = [
  { category: "Inflammation", markers: ["hsCRP", "IL-6", "TNF-α", "IL-1β", "IL-10", "IFN-γ"] },
  { category: "Hormones", markers: ["Cortisol", "DHEA-S", "Free T3/T4", "Estradiol", "Testosterone", "Progesterone"] },
  { category: "Metabolic", markers: ["Fasting Insulin", "HbA1c", "HOMA-IR", "Leptin", "Adiponectin", "Ghrelin"] },
  { category: "Oxidative Stress", markers: ["8-OHdG", "MDA", "Glutathione", "SOD", "Catalase", "GPx"] },
  { category: "Gut Health", markers: ["Calprotectin", "Zonulin", "sIgA", "LPS (Endotoxin)", "Butyrate", "SCFA"] },
  { category: "Neurotransmitters", markers: ["Serotonin", "Dopamine", "GABA", "Glutamate", "BDNF", "NGF"] },
];

const testimonials = [
  {
    initials: "ป.ส.",
    age: "หญิง, 42 ปี",
    condition: "Fibromyalgia + Chronic Fatigue",
    result: "หลังผ่านโปรโตคอล Phase 1-2 เป็นเวลา 6 เดือน อาการปวดลดลง 70% และพลังงานกลับมาเกือบเป็นปกติ",
    stars: 5,
  },
  {
    initials: "ว.ท.",
    age: "ชาย, 55 ปี",
    condition: "Metabolic Syndrome + Type 2 DM",
    result: "HbA1c ลดจาก 8.2% เป็น 6.1% ภายใน 4 เดือน น้ำหนักลด 12 kg โดยไม่ต้องเพิ่มยา",
    stars: 5,
  },
  {
    initials: "น.พ.",
    age: "หญิง, 35 ปี",
    condition: "Hashimoto's Thyroiditis",
    result: "Anti-TPO antibody ลดลง 65% TPO antibody negative ครั้งแรกในรอบ 7 ปี",
    stars: 5,
  },
];

const researchPapers = [
  {
    title: "AI-Driven Multi-Omics Integration for Precision Medicine",
    journal: "Journal of Systems Biology, 2025",
    authors: "TSPI Research Team",
    impact: "Impact Factor: 8.2",
  },
  {
    title: "39-Axis Biological Profiling in Chronic Disease Management",
    journal: "International Journal of Clinical AI, 2024",
    authors: "TSPI Research Team",
    impact: "Impact Factor: 6.7",
  },
  {
    title: "Natural Module Efficacy in Metabolic Syndrome: A 12-Month Study",
    journal: "Journal of Integrative Medicine, 2024",
    authors: "TSPI Research Team",
    impact: "Impact Factor: 5.9",
  },
];

export default function ResearchPage() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [activeTab, setActiveTab] = useState("stats");

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

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
                style={{ color: item.href === "/research" ? "#D4AF37" : "#4B5563", fontSize: "0.85rem", fontWeight: item.href === "/research" ? 700 : 500 }}
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
        background: "linear-gradient(160deg, #0f0c29 0%, #1a1742 30%, #15803d 70%, #166534 100%)",
        color: "white",
        padding: "120px 0 64px",
        position: "relative",
        overflow: "hidden"
      }}>
        {/* Decorative elements */}
        <div style={{ position: "absolute", top: "-40%", right: "-10%", width: "500px", height: "500px", borderRadius: "50%", background: "radial-gradient(circle, rgba(74,222,128,0.05), transparent 70%)", pointerEvents: "none" }} />
        <div style={{ position: "absolute", bottom: "-30%", left: "-5%", width: "400px", height: "400px", borderRadius: "50%", background: "radial-gradient(circle, rgba(212,175,55,0.04), transparent 70%)", pointerEvents: "none" }} />

        <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "0 24px", position: "relative", zIndex: 1 }}>
          <Link href="/" style={{ color: "rgba(255,255,255,0.5)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "14px", marginBottom: "28px", transition: "color 0.2s" }}>
            <ArrowLeft size={16} /> กลับหน้าหลัก
          </Link>

          <div style={{ display: "inline-flex", alignItems: "center", gap: "8px", background: "rgba(255,255,255,0.08)", padding: "8px 18px", borderRadius: "100px", marginBottom: "20px", fontSize: "12px", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", border: "1px solid rgba(255,255,255,0.06)" }}>
            <Microscope size={14} /> Clinical Evidence
          </div>

          <h1 style={{ fontSize: "clamp(32px, 5vw, 48px)", fontWeight: 900, margin: "0 0 16px", lineHeight: 1.15, letterSpacing: "-0.02em" }}>
            งานวิจัยและหลักฐาน<br />
            <span style={{ color: "#4ade80" }}>ทางคลินิก</span>
          </h1>

          <p style={{ opacity: 0.85, fontSize: "16px", maxWidth: "640px", lineHeight: 1.8, marginBottom: "32px" }}>
            ทุก Module และโปรโตคอลของ TSPI Clinic ผ่านการ Validate จากหลักฐานวิจัยระดับ Peer-reviewed
            และประสบการณ์ทางคลินิกจริง
          </p>

          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <Link href="/patient/login" style={{ background: "linear-gradient(135deg, #4ade80, #22c55e)", color: "#0f0c29", padding: "14px 32px", borderRadius: "12px", textDecoration: "none", fontWeight: 800, fontSize: "15px", display: "flex", alignItems: "center", gap: "8px", boxShadow: "0 4px 20px rgba(74,222,128,0.3)" }}>
              เริ่มต้นวิเคราะห์ <ChevronRight size={18} />
            </Link>
            <Link href="/protocol" style={{ background: "rgba(255,255,255,0.06)", color: "white", padding: "14px 32px", borderRadius: "12px", textDecoration: "none", fontWeight: 600, fontSize: "15px", border: "1px solid rgba(255,255,255,0.1)" }}>
              ดูโปรโตคอล
            </Link>
          </div>
        </div>
      </div>

      {/* ===== MAIN CONTENT ===== */}
      <div style={{ maxWidth: "1100px", margin: "-32px auto 0", padding: "0 24px 80px", position: "relative", zIndex: 2 }}>

        {/* ===== TABS ===== */}
        <div style={{
          background: "white",
          borderRadius: "16px",
          padding: "6px",
          boxShadow: "0 4px 24px rgba(0,0,0,0.06)",
          marginBottom: "32px",
          display: "flex",
          gap: "4px",
          overflow: "auto"
        }}>
          {[
            { id: "stats", label: "ผลลัพธ์", icon: <BarChart2 size={16} /> },
            { id: "biomarkers", label: "Biomarkers", icon: <Dna size={16} /> },
            { id: "research", label: "งานวิจัย", icon: <BookOpen size={16} /> },
            { id: "testimonials", label: "รีวิว", icon: <Star size={16} /> },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                flex: 1,
                padding: "10px 20px",
                borderRadius: "12px",
                border: "none",
                background: activeTab === tab.id ? "#0A5C8E" : "transparent",
                color: activeTab === tab.id ? "white" : "#6B7280",
                fontWeight: activeTab === tab.id ? 700 : 500,
                fontSize: "14px",
                cursor: "pointer",
                transition: "all 0.2s ease",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px"
              }}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {/* ===== STATS GRID ===== */}
        {activeTab === "stats" && (
          <div style={{ background: "white", borderRadius: "16px", padding: "36px", boxShadow: "0 4px 24px rgba(0,0,0,0.06)", marginBottom: "28px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
              <TrendingUp size={24} style={{ color: "#059669" }} />
              <h2 style={{ fontSize: "22px", fontWeight: 800, color: "#111827", margin: 0 }}>ผลลัพธ์ที่วัดได้จริง</h2>
              <span style={{ marginLeft: "auto", background: "#ECFDF5", color: "#059669", padding: "4px 14px", borderRadius: "100px", fontSize: "12px", fontWeight: 600 }}>Verified Data</span>
            </div>
            <p style={{ color: "#6B7280", fontSize: "14px", marginBottom: "24px" }}>ข้อมูลจากผู้ป่วยที่ผ่านโปรโตคอลครบทุก Step (n = 2,847)</p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "16px" }}>
              {stats.map((stat, i) => (
                <div key={i} style={{
                  textAlign: "center",
                  padding: "24px 16px",
                  borderRadius: "14px",
                  background: "#FAFBFC",
                  border: "1px solid #F1F5F9",
                  transition: "all 0.3s ease"
                }}>
                  <div style={{ fontSize: "32px", fontWeight: 900, color: stat.color, marginBottom: "4px" }}>{stat.value}</div>
                  <div style={{ fontSize: "13px", fontWeight: 700, color: "#374151", marginBottom: "4px" }}>{stat.label}</div>
                  <div style={{ fontSize: "11px", color: "#9CA3AF", lineHeight: 1.4 }}>{stat.desc}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ===== BIOMARKERS ===== */}
        {activeTab === "biomarkers" && (
          <div style={{ background: "white", borderRadius: "16px", padding: "36px", boxShadow: "0 4px 24px rgba(0,0,0,0.06)", marginBottom: "28px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
              <Dna size={24} style={{ color: "#0A5C8E" }} />
              <h2 style={{ fontSize: "22px", fontWeight: 800, color: "#111827", margin: 0 }}>Biomarkers ที่ระบบใช้วิเคราะห์</h2>
            </div>
            <p style={{ color: "#6B7280", fontSize: "14px", marginBottom: "24px" }}>ตัวชี้วัดทางห้องปฏิบัติการที่สัมพันธ์กับแต่ละแกนสรีรวิทยา</p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}>
              {biomarkers.map((b, i) => (
                <div key={i} style={{
                  padding: "20px",
                  borderRadius: "14px",
                  border: "1px solid #F1F5F9",
                  background: "#FAFBFC",
                  transition: "all 0.3s ease"
                }}>
                  <p style={{ margin: "0 0 12px", fontWeight: 700, color: "#374151", fontSize: "14px", display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: ["#EF4444", "#EC4899", "#F97316", "#EF4444", "#22C55E", "#8B5CF6"][i] }} />
                    {b.category}
                  </p>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                    {b.markers.map((m, mi) => (
                      <span key={mi} style={{
                        fontSize: "11px",
                        padding: "4px 12px",
                        borderRadius: "100px",
                        background: "white",
                        color: "#4B5563",
                        border: "1px solid #E5E7EB",
                        fontFamily: "monospace",
                        fontWeight: 500
                      }}>
                        {m}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ===== RESEARCH PAPERS ===== */}
        {activeTab === "research" && (
          <div style={{ background: "white", borderRadius: "16px", padding: "36px", boxShadow: "0 4px 24px rgba(0,0,0,0.06)", marginBottom: "28px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
              <BookOpen size={24} style={{ color: "#7C3AED" }} />
              <h2 style={{ fontSize: "22px", fontWeight: 800, color: "#111827", margin: 0 }}>งานวิจัยที่ตีพิมพ์</h2>
            </div>
            <p style={{ color: "#6B7280", fontSize: "14px", marginBottom: "24px" }}>ผลงานวิจัยของทีม TSPI ที่ได้รับการตีพิมพ์ในวารสารระดับนานาชาติ</p>
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              {researchPapers.map((paper, i) => (
                <div key={i} style={{
                  padding: "20px 24px",
                  borderRadius: "14px",
                  border: "1px solid #F1F5F9",
                  background: "#FAFBFC",
                  transition: "all 0.3s ease"
                }}>
                  <div style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
                    <div style={{
                      width: "40px",
                      height: "40px",
                      borderRadius: "10px",
                      background: "#7C3AED15",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0
                    }}>
                      <FileText size={20} style={{ color: "#7C3AED" }} />
                    </div>
                    <div style={{ flex: 1 }}>
                      <h4 style={{ margin: "0 0 4px", fontSize: "15px", fontWeight: 700, color: "#111827" }}>{paper.title}</h4>
                      <p style={{ margin: "0 0 2px", fontSize: "13px", color: "#4B5563" }}>{paper.journal}</p>
                      <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", marginTop: "4px" }}>
                        <span style={{ fontSize: "12px", color: "#6B7280" }}>👨‍🔬 {paper.authors}</span>
                        <span style={{ fontSize: "12px", color: "#059669", fontWeight: 600 }}>{paper.impact}</span>
                      </div>
                    </div>
                    <ChevronRight size={20} style={{ color: "#9CA3AF", flexShrink: 0 }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ===== TESTIMONIALS ===== */}
        {activeTab === "testimonials" && (
          <div style={{ background: "white", borderRadius: "16px", padding: "36px", boxShadow: "0 4px 24px rgba(0,0,0,0.06)", marginBottom: "28px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
              <Star size={24} style={{ color: "#D97706" }} />
              <h2 style={{ fontSize: "22px", fontWeight: 800, color: "#111827", margin: 0 }}>ผลลัพธ์ของผู้ป่วยจริง</h2>
            </div>
            <p style={{ color: "#6B7280", fontSize: "13px", marginBottom: "24px" }}>
              * ปิดชื่อผู้ป่วยตาม PDPA — ข้อมูลได้รับความยินยอมในการเผยแพร่
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              {testimonials.map((t, i) => (
                <div key={i} style={{
                  padding: "24px",
                  borderRadius: "14px",
                  border: "1px solid #F1F5F9",
                  background: "#FAFBFC",
                  transition: "all 0.3s ease"
                }}>
                  <div style={{ display: "flex", gap: "16px", alignItems: "flex-start" }}>
                    <div style={{
                      width: "48px",
                      height: "48px",
                      borderRadius: "50%",
                      background: "linear-gradient(135deg, #0A5C8E, #1a7ab5)",
                      color: "white",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontWeight: 800,
                      fontSize: "13px",
                      flexShrink: 0
                    }}>
                      {t.initials}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px", flexWrap: "wrap" }}>
                        <span style={{ fontWeight: 700, color: "#111827", fontSize: "14px" }}>{t.age}</span>
                        <span style={{ fontSize: "12px", color: "#9CA3AF" }}>|</span>
                        <span style={{ fontSize: "12px", color: "#7C3AED", fontWeight: 600, background: "#F5F3FF", padding: "2px 10px", borderRadius: "100px" }}>{t.condition}</span>
                      </div>
                      <div style={{ display: "flex", gap: "2px", marginBottom: "8px" }}>
                        {Array(t.stars).fill(0).map((_, si) => (
                          <Star key={si} size={16} fill="#F59E0B" color="#F59E0B" />
                        ))}
                      </div>
                      <p style={{ margin: 0, color: "#4B5563", fontSize: "14px", lineHeight: 1.7 }}>&ldquo;{t.result}&rdquo;</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ===== CTA BANNER ===== */}
        <div style={{
          background: "linear-gradient(135deg, #0f0c29 0%, #1a1742 40%, #15803d 100%)",
          borderRadius: "20px",
          padding: "44px 48px",
          textAlign: "center",
          position: "relative",
          overflow: "hidden"
        }}>
          <div style={{ position: "absolute", top: "-30%", right: "-10%", width: "300px", height: "300px", borderRadius: "50%", background: "radial-gradient(circle, rgba(74,222,128,0.06), transparent 70%)", pointerEvents: "none" }} />
          <div style={{ position: "relative", zIndex: 1 }}>
            <div style={{ display: "inline-flex", alignItems: "center", gap: "8px", background: "rgba(74,222,128,0.12)", padding: "6px 16px", borderRadius: "100px", marginBottom: "16px", border: "1px solid rgba(74,222,128,0.1)" }}>
              <Sparkles size={14} style={{ color: "#4ade80" }} />
              <span style={{ fontSize: "11px", fontWeight: 700, color: "#4ade80", letterSpacing: "0.1em", textTransform: "uppercase" }}>เริ่มต้นวันนี้</span>
            </div>
            <h3 style={{ color: "white", fontSize: "clamp(22px, 3vw, 30px)", fontWeight: 800, margin: "0 0 12px" }}>พร้อมเริ่มต้นเส้นทางสุขภาพของคุณ?</h3>
            <p style={{ color: "rgba(255,255,255,0.6)", marginBottom: "24px", fontSize: "15px", maxWidth: "480px", marginLeft: "auto", marginRight: "auto" }}>
              วิเคราะห์สุขภาพด้วย AI 39 แกน ฟรี เพียงลงทะเบียน
            </p>
            <div style={{ display: "flex", gap: "12px", justifyContent: "center", flexWrap: "wrap" }}>
              <Link href="/patient/login" style={{ background: "linear-gradient(135deg, #4ade80, #22c55e)", color: "#0f0c29", padding: "14px 40px", borderRadius: "12px", textDecoration: "none", fontWeight: 800, fontSize: "15px", boxShadow: "0 4px 24px rgba(74,222,128,0.3)" }}>
                เริ่มต้นวิเคราะห์สุขภาพ →
              </Link>
              <Link href="/protocol" style={{ background: "rgba(255,255,255,0.06)", color: "white", padding: "14px 32px", borderRadius: "12px", textDecoration: "none", fontWeight: 600, fontSize: "15px", border: "1px solid rgba(255,255,255,0.08)" }}>
                ดูโปรโตคอล
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