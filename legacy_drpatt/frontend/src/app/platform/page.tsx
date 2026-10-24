"use client";

import Link from "next/link";
import {
  ArrowLeft,
  Cpu,
  Layers,
  Zap,
  Database,
  Brain,
  Activity,
  ChevronRight,
  Sparkles,
  Shield,
  Microscope,
  Dna,
  HeartPulse,
  Clock,
  Award,
  BarChart3,
  CheckCircle2,
  ArrowUpRight,
  Globe,
  Mail,
  Phone,
  MapPin,
  Menu,
  X,
  Users
} from "lucide-react";
import { useState, useEffect } from "react";

const axes39 = [
  { id: "A01", name: "Systemic Inflammatory Load", thai: "ภาระการอักเสบระบบ", color: "#EF4444", category: "Immune" },
  { id: "A02", name: "Immune Dysregulation", thai: "ความผิดปกติของภูมิคุ้มกัน", color: "#F97316", category: "Immune" },
  { id: "A03", name: "Autonomic Nervous Function", thai: "ระบบประสาทอัตโนมัติ", color: "#EAB308", category: "Neurological" },
  { id: "A04", name: "HPA Axis Dysfunction", thai: "แกน HPA / ความเครียด", color: "#EF4444", category: "Endocrine" },
  { id: "A05", name: "Thyroid Function", thai: "ต่อมไทรอยด์", color: "#8B5CF6", category: "Endocrine" },
  { id: "A06", name: "Sex Hormone Balance", thai: "สมดุลฮอร์โมนเพศ", color: "#EC4899", category: "Endocrine" },
  { id: "A07", name: "Insulin Signaling", thai: "การส่งสัญญาณอินซูลิน", color: "#F97316", category: "Metabolic" },
  { id: "A08", name: "Leptin / Adipokine", thai: "เลปติน / ฮอร์โมนไขมัน", color: "#F97316", category: "Metabolic" },
  { id: "A09", name: "Oxidative Stress", thai: "ความเครียดออกซิเดชั่น", color: "#EF4444", category: "Cellular" },
  { id: "A10", name: "Mitochondrial Function", thai: "การทำงานของไมโตคอนเดรีย", color: "#22C55E", category: "Cellular" },
  { id: "A11", name: "Cellular Energy Metabolism", thai: "การเผาผลาญพลังงานระดับเซลล์", color: "#22C55E", category: "Cellular" },
  { id: "A12", name: "DNA Repair & Genomic Stability", thai: "การซ่อมแซม DNA", color: "#06B6D4", category: "Cellular" },
  { id: "A13", name: "Epigenetic Regulation", thai: "การควบคุม Epigenetic", color: "#06B6D4", category: "Cellular" },
  { id: "A14", name: "mTOR / Autophagy", thai: "การรีไซเคิลเซลล์ mTOR", color: "#8B5CF6", category: "Cellular" },
  { id: "A15", name: "Apoptosis Regulation", thai: "การควบคุมการตายของเซลล์", color: "#8B5CF6", category: "Cellular" },
  { id: "A16", name: "Hepatic Detoxification", thai: "การ Detox ของตับ", color: "#A3E635", category: "Digestive" },
  { id: "A17", name: "Digestive Function", thai: "การย่อยอาหาร", color: "#A3E635", category: "Digestive" },
  { id: "A18", name: "Microbiome Ecology", thai: "ระบบนิเวศของจุลินทรีย์", color: "#22C55E", category: "Digestive" },
  { id: "A19", name: "Gut Barrier Integrity", thai: "ความแข็งแรงของผนังลำไส้", color: "#22C55E", category: "Digestive" },
  { id: "A20", name: "Bile Acid Metabolism", thai: "การเผาผลาญน้ำดี", color: "#A3E635", category: "Digestive" },
  { id: "A21", name: "Endothelial Function", thai: "การทำงานของหลอดเลือด", color: "#EF4444", category: "Cardiovascular" },
  { id: "A22", name: "Coagulation & Fibrinolysis", thai: "การแข็งตัวของเลือด", color: "#EF4444", category: "Cardiovascular" },
  { id: "A23", name: "Lipid Metabolism", thai: "การเผาผลาญไขมัน", color: "#F97316", category: "Cardiovascular" },
  { id: "A24", name: "Cardiovascular Tone", thai: "ความตึงตัวของหลอดเลือดหัวใจ", color: "#EF4444", category: "Cardiovascular" },
  { id: "A25", name: "Tissue Repair & Remodeling", thai: "การซ่อมแซมเนื้อเยื่อ", color: "#22C55E", category: "Cellular" },
  { id: "A26", name: "Bone & Mineral Metabolism", thai: "กระดูกและแร่ธาตุ", color: "#64748B", category: "Musculoskeletal" },
  { id: "A27", name: "Carbohydrate & Fat Balance", thai: "สมดุลคาร์โบไฮเดรตและไขมัน", color: "#F97316", category: "Metabolic" },
  { id: "A28", name: "Protein Turnover", thai: "การหมุนเวียนโปรตีน", color: "#06B6D4", category: "Metabolic" },
  { id: "A29", name: "Angiogenesis", thai: "การสร้างหลอดเลือดใหม่", color: "#EF4444", category: "Cardiovascular" },
  { id: "A30", name: "Neuroinflammation", thai: "การอักเสบในสมอง", color: "#EF4444", category: "Neurological" },
  { id: "A31", name: "Neurotransmitter Balance", thai: "สมดุล Neurotransmitter", color: "#8B5CF6", category: "Neurological" },
  { id: "A32", name: "Neuroplasticity", thai: "ความยืดหยุ่นของสมอง", color: "#8B5CF6", category: "Neurological" },
  { id: "A33", name: "HPA-Reproductive Axis", thai: "แกน HPA-สืบพันธุ์", color: "#EC4899", category: "Endocrine" },
  { id: "A34", name: "Menstrual & Fertility Health", thai: "สุขภาพประจำเดือนและเจริญพันธุ์", color: "#EC4899", category: "Endocrine" },
  { id: "A35", name: "Skin & Integument", thai: "ผิวหนังและเนื้อเยื่อปกคลุม", color: "#A3E635", category: "Integumentary" },
  { id: "A36", name: "Lymphatic & Fluid Balance", thai: "ระบบน้ำเหลืองและของเหลว", color: "#06B6D4", category: "Circulatory" },
  { id: "A37", name: "Musculoskeletal Function", thai: "ระบบกล้ามเนื้อและกระดูก", color: "#64748B", category: "Musculoskeletal" },
  { id: "A38", name: "Circadian Rhythm", thai: "นาฬิกาชีวภาพ", color: "#8B5CF6", category: "Neurological" },
  { id: "A39", name: "Environmental Adaptation", thai: "การปรับตัวต่อสิ่งแวดล้อม", color: "#22C55E", category: "Immune" },
];

const layers = [
  { title: "3 Keys", desc: "สามกุญแจหลักสู่สุขภาพ", count: "3", color: "#0A5C8E", detail: "Genetics · Environment · Lifestyle" },
  { title: "9 Steps", desc: "9 ขั้นตอนการรักษา", count: "9", color: "#1a7ab5", detail: "Assessment → Detox → Gut → Metabolic → Hormonal → Immune → Cellular → Neural → Longevity" },
  { title: "12 Domains", desc: "12 โดเมนชีวการแพทย์", count: "12", color: "#2a99dc", detail: "ครอบคลุมทุกระบบของร่างกาย" },
  { title: "39 Axes", desc: "39 แกนสรีรวิทยา", count: "39", color: "#3abfff", detail: "วัดและวิเคราะห์เชิงลึกทุกมิติ" },
  { title: "180 Networks", desc: "180 ระบบชีวโมเลกุล", count: "180", color: "#4ad0ff", detail: "เชื่อมโยงข้อมูลเชิงระบบ" },
  { title: "200+ Modules", desc: "โมดูลสารสกัดธรรมชาติ", count: "200+", color: "#5ae0ff", detail: "แผนการรักษาเฉพาะบุคคล" },
];

const categories = [
  { name: "Immune", label: "ภูมิคุ้มกัน", color: "#EF4444" },
  { name: "Endocrine", label: "ฮอร์โมน", color: "#EC4899" },
  { name: "Metabolic", label: "เมตาบอลิก", color: "#F97316" },
  { name: "Cellular", label: "ระดับเซลล์", color: "#22C55E" },
  { name: "Neurological", label: "ระบบประสาท", color: "#8B5CF6" },
  { name: "Digestive", label: "ระบบย่อยอาหาร", color: "#A3E635" },
  { name: "Cardiovascular", label: "หัวใจและหลอดเลือด", color: "#EF4444" },
  { name: "Musculoskeletal", label: "กล้ามเนื้อและกระดูก", color: "#64748B" },
  { name: "Integumentary", label: "ผิวหนัง", color: "#A3E635" },
  { name: "Circulatory", label: "ระบบไหลเวียน", color: "#06B6D4" },
];

export default function PlatformPage() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const filteredAxes = selectedCategory
    ? axes39.filter(ax => ax.category === selectedCategory)
    : axes39;

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#F8FAFC", fontFamily: "'Sarabun', 'Inter', sans-serif" }}>

      {/* ===== NAVIGATION ===== */}
      <nav
        className={`fixed-top transition-all duration-300 ${scrolled ? "nav-premium shadow-sm py-2" : "nav-premium py-3"}`}
        style={{ zIndex: 1100, backgroundColor: scrolled ? "rgba(255,255,255,0.95)" : "rgba(255,255,255,0.98)", backdropFilter: "blur(10px)", borderBottom: "1px solid rgba(0,0,0,0.04)" }}
      >
        <div className="container d-flex align-items-center justify-content-between">
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
                style={{ color: item.href === "/platform" ? "#D4AF37" : "#4B5563", fontSize: "0.85rem", fontWeight: item.href === "/platform" ? 700 : 500 }}
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
        background: "linear-gradient(160deg, #0f0c29 0%, #1a1742 30%, #302b63 60%, #24243e 100%)",
        color: "white",
        padding: "120px 0 72px",
        position: "relative",
        overflow: "hidden"
      }}>
        {/* Decorative elements */}
        <div style={{ position: "absolute", top: "-40%", right: "-10%", width: "600px", height: "600px", borderRadius: "50%", background: "radial-gradient(circle, rgba(212,175,55,0.06), transparent 70%)", pointerEvents: "none" }} />
        <div style={{ position: "absolute", bottom: "-30%", left: "-5%", width: "400px", height: "400px", borderRadius: "50%", background: "radial-gradient(circle, rgba(90,224,255,0.05), transparent 70%)", pointerEvents: "none" }} />

        <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "0 24px", position: "relative", zIndex: 1 }}>
          <Link href="/" style={{ color: "rgba(255,255,255,0.5)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "14px", marginBottom: "28px", transition: "color 0.2s" }}>
            <ArrowLeft size={16} /> กลับหน้าหลัก
          </Link>

          <div style={{ display: "inline-flex", alignItems: "center", gap: "8px", background: "rgba(212,175,55,0.12)", padding: "8px 18px", borderRadius: "100px", marginBottom: "20px", fontSize: "12px", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#D4AF37", border: "1px solid rgba(212,175,55,0.15)" }}>
            <Cpu size={14} /> TSPI Platform Architecture
          </div>

          <h1 style={{ fontSize: "clamp(32px, 5.5vw, 52px)", fontWeight: 900, margin: "0 0 16px", lineHeight: 1.15, letterSpacing: "-0.02em" }}>
            แพลตฟอร์ม AI ทางการแพทย์<br />
            <span style={{ background: "linear-gradient(135deg, #D4AF37, #F5E08A, #D4AF37)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>ที่แม่นยำที่สุดในไทย</span>
          </h1>

          <p style={{ opacity: 0.8, fontSize: "16px", maxWidth: "640px", lineHeight: 1.8, marginBottom: "32px" }}>
            TSPI Clinic ใช้สถาปัตยกรรม AI 6 ชั้นในการวิเคราะห์สุขภาพ ตั้งแต่ระดับกลไกระดับโมเลกุล
            ไปจนถึงการสั่งจ่ายโมดูลสารสกัดธรรมชาติเฉพาะบุคคล
          </p>

          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <Link href="/patient/login" style={{ background: "linear-gradient(135deg, #D4AF37, #B8962E)", color: "#0f0c29", padding: "14px 32px", borderRadius: "12px", textDecoration: "none", fontWeight: 800, fontSize: "15px", display: "flex", alignItems: "center", gap: "8px", boxShadow: "0 4px 20px rgba(212,175,55,0.3)" }}>
              ใช้งานแพลตฟอร์ม <ChevronRight size={18} />
            </Link>
            <Link href="/research" style={{ background: "rgba(255,255,255,0.06)", color: "white", padding: "14px 32px", borderRadius: "12px", textDecoration: "none", fontWeight: 600, fontSize: "15px", border: "1px solid rgba(255,255,255,0.1)" }}>
              ดูงานวิจัย
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
          padding: "28px 32px",
          boxShadow: "0 4px 24px rgba(0,0,0,0.06)",
          marginBottom: "32px",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
          gap: "16px",
          textAlign: "center"
        }}>
          {[
            { label: "แกนวิเคราะห์", value: "39", icon: <Activity size={20} color="#D4AF37" /> },
            { label: "โมดูลรักษา", value: "200+", icon: <Database size={20} color="#D4AF37" /> },
            { label: "ผู้ป่วยทั้งหมด", value: "10,000+", icon: <Users size={20} color="#D4AF37" /> },
            { label: "ความแม่นยำ", value: "97.8%", icon: <Award size={20} color="#D4AF37" /> },
          ].map((stat, i) => (
            <div key={i} style={{ padding: "8px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", marginBottom: "4px" }}>
                {stat.icon}
                <span style={{ fontSize: "24px", fontWeight: 900, color: "#111827" }}>{stat.value}</span>
              </div>
              <p style={{ margin: 0, fontSize: "12px", color: "#6B7280", fontWeight: 500 }}>{stat.label}</p>
            </div>
          ))}
        </div>

        {/* ===== HIERARCHY ===== */}
        <div style={{ background: "white", borderRadius: "16px", padding: "36px", boxShadow: "0 4px 24px rgba(0,0,0,0.06)", marginBottom: "32px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "6px" }}>
            <Layers size={24} style={{ color: "#D4AF37" }} />
            <h2 style={{ margin: 0, fontSize: "22px", fontWeight: 800, color: "#111827" }}>สถาปัตยกรรม TSPI 6 ชั้น</h2>
          </div>
          <p style={{ color: "#6B7280", fontSize: "14px", marginBottom: "28px" }}>จากหลักการระดับบนสู่การปฏิบัติระดับล่าง — ทุกชั้นเชื่อมต่อกันอย่างเป็นระบบ</p>

          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {layers.map((l, i) => (
              <div key={i} style={{
                display: "flex",
                alignItems: "center",
                gap: "16px",
                padding: "16px 20px",
                borderRadius: "12px",
                border: "1px solid #F1F5F9",
                background: i % 2 === 0 ? "#FAFBFC" : "white",
                transition: "all 0.2s ease"
              }}>
                <div style={{
                  width: "56px",
                  height: "48px",
                  borderRadius: "10px",
                  background: l.color,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 900,
                  fontSize: "16px",
                  color: "white",
                  flexShrink: 0
                }}>
                  {l.count}
                </div>
                <div style={{ flex: 1 }}>
                  <p style={{ margin: 0, fontWeight: 700, color: "#111827", fontSize: "15px" }}>{l.title}</p>
                  <p style={{ margin: 0, color: "#6B7280", fontSize: "13px" }}>{l.desc}</p>
                  {l.detail && <p style={{ margin: "2px 0 0", color: "#9CA3AF", fontSize: "11px" }}>{l.detail}</p>}
                </div>
                {i < layers.length - 1 && <ChevronRight size={16} color="#D1D5DB" style={{ flexShrink: 0 }} />}
              </div>
            ))}
          </div>
        </div>

        {/* ===== 39 AXES ===== */}
        <div style={{ background: "white", borderRadius: "16px", padding: "36px", boxShadow: "0 4px 24px rgba(0,0,0,0.06)", marginBottom: "32px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "6px", flexWrap: "wrap" }}>
            <Activity size={24} style={{ color: "#D4AF37" }} />
            <h2 style={{ margin: 0, fontSize: "22px", fontWeight: 800, color: "#111827" }}>39 แกนสรีรวิทยา (39 Biological Axes)</h2>
            <span style={{ marginLeft: "auto", background: "#F3F4F6", padding: "4px 14px", borderRadius: "100px", fontSize: "12px", fontWeight: 600, color: "#6B7280" }}>
              {filteredAxes.length} แกน
            </span>
          </div>
          <p style={{ color: "#6B7280", fontSize: "14px", marginBottom: "20px" }}>
            คือแกนหลักที่ AI ใช้วัดสภาพสุขภาพของคุณ — แต่ละแกนครอบคลุมระบบชีววิทยาที่เฉพาะเจาะจง
          </p>

          {/* Category filters */}
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "20px", paddingBottom: "16px", borderBottom: "1px solid #F1F5F9" }}>
            <button
              onClick={() => setSelectedCategory(null)}
              style={{
                padding: "6px 16px",
                borderRadius: "100px",
                border: "1px solid #E5E7EB",
                background: selectedCategory === null ? "#D4AF37" : "transparent",
                color: selectedCategory === null ? "white" : "#4B5563",
                fontWeight: 600,
                fontSize: "12px",
                cursor: "pointer",
                transition: "all 0.2s ease"
              }}
            >
              ทั้งหมด
            </button>
            {categories.map(cat => (
              <button
                key={cat.name}
                onClick={() => setSelectedCategory(cat.name)}
                style={{
                  padding: "6px 16px",
                  borderRadius: "100px",
                  border: `1px solid ${selectedCategory === cat.name ? cat.color : '#E5E7EB'}`,
                  background: selectedCategory === cat.name ? `${cat.color}15` : "transparent",
                  color: selectedCategory === cat.name ? cat.color : "#4B5563",
                  fontWeight: 600,
                  fontSize: "12px",
                  cursor: "pointer",
                  transition: "all 0.2s ease"
                }}
              >
                <span style={{ display: "inline-block", width: "8px", height: "8px", borderRadius: "50%", background: cat.color, marginRight: "6px" }} />
                {cat.label}
              </button>
            ))}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: "8px" }}>
            {filteredAxes.map((ax) => (
              <div key={ax.id} style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "10px 14px",
                background: "#FAFBFC",
                borderRadius: "10px",
                border: "1px solid #F1F5F9",
                transition: "all 0.2s ease"
              }}>
                <span style={{
                  width: "40px",
                  fontSize: "11px",
                  fontWeight: 700,
                  color: ax.color,
                  background: `${ax.color}12`,
                  padding: "3px 6px",
                  borderRadius: "6px",
                  flexShrink: 0,
                  textAlign: "center"
                }}>
                  {ax.id}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ margin: 0, fontSize: "12px", fontWeight: 600, color: "#374151", lineHeight: 1.3 }}>{ax.name}</p>
                  <p style={{ margin: 0, fontSize: "11px", color: "#9CA3AF" }}>{ax.thai}</p>
                </div>
                <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: ax.color, flexShrink: 0 }} />
              </div>
            ))}
          </div>
        </div>

        {/* ===== AI FEATURES ===== */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "24px", marginBottom: "32px" }}>
          {[
            { icon: Brain, title: "Digital Twin Model", color: "#7C3AED", bg: "#F5F3FF", desc: "จำลองร่างกายเฉพาะบุคคลในรูปแบบดิจิทัล วิเคราะห์ความสัมพันธ์ระหว่าง 39 แกนพร้อมกันเพื่อหาแนวทางการรักษาที่เหมาะสมที่สุด" },
            { icon: Zap, title: "Precision Medicine Engine", color: "#D4AF37", bg: "#FEF7E0", desc: "เครื่องยนต์คำนวณแผนการรักษาอัตโนมัติ จับคู่อาการกับโมดูลสารสกัดที่ตรงที่สุด ด้วยอัลกอริทึมการเรียนรู้ของเครื่อง" },
            { icon: Database, title: "RAG Knowledge Base", color: "#059669", bg: "#ECFDF5", desc: "คลังความรู้การแพทย์ขนาดใหญ่ครอบคลุม 200+ โมดูล และงานวิจัยกว่า 10,000 ชิ้น พร้อมระบบค้นหาอัจฉริยะ" },
            { icon: Shield, title: "Clinical Validation", color: "#2563EB", bg: "#EFF6FF", desc: "ผ่านการรับรองจากสถาบันการแพทย์ชั้นนำ ตรวจสอบความแม่นยำและความปลอดภัยก่อนนำไปใช้จริงกับผู้ป่วย" },
          ].map((f, i) => (
            <div key={i} style={{ background: "white", borderRadius: "16px", padding: "28px", boxShadow: "0 4px 24px rgba(0,0,0,0.06)", border: "1px solid #F1F5F9", transition: "all 0.3s ease" }}>
              <div style={{ width: "52px", height: "52px", borderRadius: "14px", background: f.bg, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: "16px" }}>
                <f.icon size={26} color={f.color} />
              </div>
              <h3 style={{ margin: "0 0 8px", fontWeight: 800, fontSize: "17px", color: "#111827" }}>{f.title}</h3>
              <p style={{ margin: 0, fontSize: "13px", color: "#6B7280", lineHeight: 1.7 }}>{f.desc}</p>
            </div>
          ))}
        </div>

        {/* ===== CTA ===== */}
        <div style={{
          background: "linear-gradient(135deg, #0f0c29 0%, #1a1742 40%, #302b63 100%)",
          borderRadius: "20px",
          padding: "44px 48px",
          textAlign: "center",
          position: "relative",
          overflow: "hidden"
        }}>
          <div style={{ position: "absolute", top: "-30%", right: "-10%", width: "300px", height: "300px", borderRadius: "50%", background: "radial-gradient(circle, rgba(212,175,55,0.08), transparent 70%)", pointerEvents: "none" }} />
          <div style={{ position: "relative", zIndex: 1 }}>
            <div style={{ display: "inline-flex", alignItems: "center", gap: "8px", background: "rgba(212,175,55,0.12)", padding: "6px 16px", borderRadius: "100px", marginBottom: "16px", border: "1px solid rgba(212,175,55,0.15)" }}>
              <Sparkles size={14} style={{ color: "#D4AF37" }} />
              <span style={{ fontSize: "11px", fontWeight: 700, color: "#D4AF37", letterSpacing: "0.1em", textTransform: "uppercase" }}>พร้อมใช้งานแล้ว</span>
            </div>
            <h3 style={{ color: "white", fontSize: "clamp(22px, 3vw, 30px)", fontWeight: 800, margin: "0 0 12px" }}>พร้อมสัมผัสแพลตฟอร์มนี้?</h3>
            <p style={{ color: "rgba(255,255,255,0.6)", marginBottom: "24px", fontSize: "15px", maxWidth: "480px", marginLeft: "auto", marginRight: "auto" }}>
              เข้าสู่ระบบเพื่อเริ่มวิเคราะห์สุขภาพด้วย AI 39 แกน และรับแผนการรักษาเฉพาะบุคคล
            </p>
            <div style={{ display: "flex", gap: "12px", justifyContent: "center", flexWrap: "wrap" }}>
              <Link href="/patient/login" style={{ background: "linear-gradient(135deg, #D4AF37, #B8962E)", color: "#0f0c29", padding: "14px 40px", borderRadius: "12px", textDecoration: "none", fontWeight: 800, fontSize: "15px", boxShadow: "0 4px 24px rgba(212,175,55,0.3)" }}>
                เริ่มต้นใช้งาน →
              </Link>
              <Link href="/about" style={{ background: "rgba(255,255,255,0.06)", color: "white", padding: "14px 32px", borderRadius: "12px", textDecoration: "none", fontWeight: 600, fontSize: "15px", border: "1px solid rgba(255,255,255,0.08)" }}>
                เรียนรู้เพิ่มเติม
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