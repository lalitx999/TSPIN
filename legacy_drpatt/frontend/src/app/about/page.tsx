"use client";

import Link from "next/link";
import {
  ArrowLeft,
  MapPin,
  Phone,
  Mail,
  Clock,
  Globe,
  MessageSquare,
  ChevronRight,
  Heart,
  Menu,
  X,
  Users,
  Activity,
  Sparkles,
  Shield,
  Award,
  Star,
  CheckCircle2,
  ArrowUpRight,
  CalendarDays,
  Building2,
  User,
  Stethoscope,
  Microscope,
  Dna,
  FlaskConical,
  Brain,
  Database,
  Zap,
  Target,
  Lock
} from "lucide-react";
import { useState, useEffect } from "react";

const contactChannels = [
  {
    icon: Phone, color: "#059669", bg: "#ECFDF5",
    title: "โทรศัพท์", value: "02-XXX-XXXX",
    sub: "จันทร์–ศุกร์ 8:00–18:00 น.",
  },
  {
    icon: Mail, color: "#0A5C8E", bg: "#EFF6FF",
    title: "อีเมล", value: "contact@tspiclinic.com",
    sub: "ตอบภายใน 1 วันทำการ",
  },
  {
    icon: MessageSquare, color: "#06C755", bg: "#F0FFF4",
    title: "LINE OA", value: "@tspiclinic",
    sub: "แชทได้ตลอด 24 ชั่วโมง",
  },
  {
    icon: Globe, color: "#7C3AED", bg: "#F5F3FF",
    title: "เว็บไซต์", value: "www.tspiclinic.com",
    sub: "ข้อมูลและบริการออนไลน์",
  },
];

const teamMembers = [
  {
    name: "นพ. ดร. [ชื่อแพทย์]",
    role: "แพทย์ผู้เชี่ยวชาญ Functional & Precision Medicine",
    specialty: "Systems Biology, Endocrinology",
    initials: "MD",
    color: "#0A5C8E",
    bg: "#EFF6FF",
  },
  {
    name: "นพ. [ชื่อแพทย์]",
    role: "แพทย์ระบบสรีรวิทยาเชิงลึก",
    specialty: "Integrative Medicine, Metabolic Health",
    initials: "MD",
    color: "#7C3AED",
    bg: "#F5F3FF",
  },
  {
    name: "ทีม AI & Data Science",
    role: "วิศวกรระบบปัญญาประดิษฐ์",
    specialty: "Machine Learning, Bioinformatics",
    initials: "AI",
    color: "#059669",
    bg: "#ECFDF5",
  },
  {
    name: "ทีมพัฒนาระบบ",
    role: "วิศวกรซอฟต์แวร์และ DevOps",
    specialty: "Cloud Architecture, Security",
    initials: "Dev",
    color: "#D97706",
    bg: "#FFFBEB",
  },
];

const hours = [
  { day: "จันทร์ – ศุกร์", time: "08:00 – 18:00 น." },
  { day: "เสาร์", time: "08:00 – 14:00 น." },
  { day: "อาทิตย์", time: "ปิดทำการ" },
];

const values = [
  { emoji: "🔬", title: "Science-First", desc: "ทุกการรักษาอ้างอิงหลักฐานวิจัยทางวิทยาศาสตร์เท่านั้น", icon: <Microscope size={20} /> },
  { emoji: "🎯", title: "Precision Care", desc: "ไม่มีสูตรสำเร็จ ทุกแผนการรักษาออกแบบเฉพาะบุคคล", icon: <Target size={20} /> },
  { emoji: "🤝", title: "Patient Empowerment", desc: "ให้ผู้ป่วยเข้าใจและมีส่วนร่วมในการดูแลสุขภาพตนเอง", icon: <Users size={20} /> },
  { emoji: "🔒", title: "Privacy & Trust", desc: "ข้อมูลทุกชิ้นถูกปกป้องตามมาตรฐาน PDPA และ HIPAA", icon: <Lock size={20} /> },
];

const milestones = [
  { year: "2022", title: "ก่อตั้ง TSPI Clinic", desc: "เริ่มต้นด้วยทีมแพทย์และนักวิทยาศาสตร์ 5 คน" },
  { year: "2023", title: "เปิดตัว AI Platform", desc: "ระบบวิเคราะห์สุขภาพด้วย AI 39 แกนแรกของไทย" },
  { year: "2024", title: "ผู้ป่วย 10,000+ ราย", desc: "ขยายทีมและเปิดสาขาเพิ่ม 3 สาขา" },
  { year: "2025", title: "งานวิจัยตีพิมพ์", desc: "ผลงานวิจัยในวารสารระดับนานาชาติ 3 ฉบับ" },
];

export default function AboutPage() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [activeSection, setActiveSection] = useState("mission");

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
                style={{ color: item.href === "/about" ? "#D4AF37" : "#4B5563", fontSize: "0.85rem", fontWeight: item.href === "/about" ? 700 : 500 }}
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
        background: "linear-gradient(160deg, #0f0c29 0%, #1a1742 30%, #1e3a5f 60%, #0A5C8E 100%)",
        color: "white",
        padding: "120px 0 64px",
        position: "relative",
        overflow: "hidden"
      }}>
        {/* Decorative elements */}
        <div style={{ position: "absolute", top: "-40%", right: "-10%", width: "500px", height: "500px", borderRadius: "50%", background: "radial-gradient(circle, rgba(212,175,55,0.05), transparent 70%)", pointerEvents: "none" }} />
        <div style={{ position: "absolute", bottom: "-30%", left: "-5%", width: "400px", height: "400px", borderRadius: "50%", background: "radial-gradient(circle, rgba(90,224,255,0.03), transparent 70%)", pointerEvents: "none" }} />

        <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "0 24px", position: "relative", zIndex: 1 }}>
          <Link href="/" style={{ color: "rgba(255,255,255,0.5)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "14px", marginBottom: "28px", transition: "color 0.2s" }}>
            <ArrowLeft size={16} /> กลับหน้าหลัก
          </Link>

          <div style={{ display: "inline-flex", alignItems: "center", gap: "8px", background: "rgba(255,255,255,0.08)", padding: "8px 18px", borderRadius: "100px", marginBottom: "20px", fontSize: "12px", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", border: "1px solid rgba(255,255,255,0.06)" }}>
            <Heart size={14} /> About TSPI Clinic
          </div>

          <h1 style={{ fontSize: "clamp(32px, 5vw, 48px)", fontWeight: 900, margin: "0 0 16px", lineHeight: 1.15, letterSpacing: "-0.02em" }}>
            เกี่ยวกับ <br />
            <span style={{ background: "linear-gradient(135deg, #D4AF37, #F5E08A, #D4AF37)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>TSPI Clinic</span>
          </h1>

          <p style={{ opacity: 0.85, fontSize: "16px", maxWidth: "640px", lineHeight: 1.8, marginBottom: "32px" }}>
            คลินิกการแพทย์แม่นยำที่ผสานเทคโนโลยี AI เข้ากับศาสตร์ Systems Biology
            เพื่อดูแลสุขภาพของคุณในระดับกลไกชีววิทยาที่ลึกที่สุด
          </p>

          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <Link href="/patient/login" style={{ background: "linear-gradient(135deg, #D4AF37, #B8962E)", color: "#0f0c29", padding: "14px 32px", borderRadius: "12px", textDecoration: "none", fontWeight: 800, fontSize: "15px", display: "flex", alignItems: "center", gap: "8px", boxShadow: "0 4px 20px rgba(212,175,55,0.3)" }}>
              เริ่มต้นดูแลสุขภาพ <ChevronRight size={18} />
            </Link>
            <Link href="#contact" style={{ background: "rgba(255,255,255,0.06)", color: "white", padding: "14px 32px", borderRadius: "12px", textDecoration: "none", fontWeight: 600, fontSize: "15px", border: "1px solid rgba(255,255,255,0.1)" }}>
              ติดต่อเรา
            </Link>
          </div>
        </div>
      </div>

      {/* ===== MAIN CONTENT ===== */}
      <div style={{ maxWidth: "1100px", margin: "-32px auto 0", padding: "0 24px 80px", position: "relative", zIndex: 2 }}>

        {/* ===== SECTION NAV ===== */}
        <div style={{
          background: "white",
          borderRadius: "16px",
          padding: "12px",
          boxShadow: "0 4px 24px rgba(0,0,0,0.06)",
          marginBottom: "32px",
          display: "flex",
          gap: "8px",
          overflow: "auto",
          flexWrap: "wrap"
        }}>
          {[
            { id: "mission", label: "พันธกิจ", icon: <Target size={16} /> },
            { id: "team", label: "ทีมแพทย์", icon: <Stethoscope size={16} /> },
            { id: "milestones", label: "ความสำเร็จ", icon: <Award size={16} /> },
            { id: "contact", label: "ติดต่อ", icon: <Phone size={16} /> },
          ].map((section) => (
            <button
              key={section.id}
              onClick={() => {
                setActiveSection(section.id);
                document.getElementById(section.id)?.scrollIntoView({ behavior: "smooth", block: "start" });
              }}
              style={{
                flex: 1,
                padding: "10px 20px",
                borderRadius: "12px",
                border: "none",
                background: activeSection === section.id ? "#0A5C8E" : "transparent",
                color: activeSection === section.id ? "white" : "#6B7280",
                fontWeight: activeSection === section.id ? 700 : 500,
                fontSize: "14px",
                cursor: "pointer",
                transition: "all 0.2s ease",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                minWidth: "120px"
              }}
            >
              {section.icon}
              {section.label}
            </button>
          ))}
        </div>

        {/* ===== MISSION ===== */}
        <div id="mission" style={{ background: "white", borderRadius: "16px", padding: "36px", boxShadow: "0 4px 24px rgba(0,0,0,0.06)", marginBottom: "28px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
            <Target size={24} style={{ color: "#D4AF37" }} />
            <h2 style={{ fontSize: "22px", fontWeight: 800, color: "#111827", margin: 0 }}>พันธกิจของเรา</h2>
            <span style={{ marginLeft: "auto", background: "#FEF7E0", color: "#D4AF37", padding: "4px 14px", borderRadius: "100px", fontSize: "12px", fontWeight: 600 }}>Why We Exist</span>
          </div>

          <p style={{ color: "#4B5563", fontSize: "15px", lineHeight: 1.9, marginBottom: "24px" }}>
            TSPI Clinic ก่อตั้งขึ้นจากความเชื่อที่ว่า <strong style={{ color: "#0A5C8E" }}>การรักษาที่แท้จริงต้องเข้าถึงสาเหตุ ไม่ใช่แค่ปกปิดอาการ</strong>
            เราใช้หลักการ Systems Biology วิเคราะห์สุขภาพใน 39 มิติ เพื่อสร้างแผนการรักษาที่ตรงกับ
            กลไกชีววิทยาของแต่ละบุคคล ผ่านเทคโนโลยี AI ที่ฉลาดและแม่นยำที่สุดในประเทศไทย
          </p>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
            {values.map((v, i) => (
              <div key={i} style={{
                padding: "20px",
                borderRadius: "14px",
                background: "#FAFBFC",
                border: "1px solid #F1F5F9",
                transition: "all 0.3s ease"
              }}>
                <div style={{
                  width: "44px",
                  height: "44px",
                  borderRadius: "12px",
                  background: "#FEF7E0",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: "12px"
                }}>
                  <span style={{ fontSize: "20px" }}>{v.emoji}</span>
                </div>
                <p style={{ margin: "0 0 4px", fontWeight: 700, color: "#111827", fontSize: "15px" }}>{v.title}</p>
                <p style={{ margin: 0, color: "#6B7280", fontSize: "13px", lineHeight: 1.6 }}>{v.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* ===== TEAM ===== */}
        <div id="team" style={{ background: "white", borderRadius: "16px", padding: "36px", boxShadow: "0 4px 24px rgba(0,0,0,0.06)", marginBottom: "28px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
            <Stethoscope size={24} style={{ color: "#7C3AED" }} />
            <h2 style={{ fontSize: "22px", fontWeight: 800, color: "#111827", margin: 0 }}>ทีมแพทย์และผู้เชี่ยวชาญ</h2>
          </div>
          <p style={{ color: "#6B7280", fontSize: "14px", marginBottom: "24px" }}>ผู้เชี่ยวชาญหลากหลายสาขาที่มุ่งมั่นเพื่อสุขภาพที่ดีที่สุดของคุณ</p>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}>
            {teamMembers.map((member, i) => (
              <div key={i} style={{
                display: "flex",
                alignItems: "center",
                gap: "16px",
                padding: "20px 24px",
                borderRadius: "14px",
                border: "1px solid #F1F5F9",
                background: member.bg,
                transition: "all 0.3s ease"
              }}>
                <div style={{
                  width: "56px",
                  height: "56px",
                  borderRadius: "50%",
                  background: member.color,
                  color: "white",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 800,
                  fontSize: "15px",
                  flexShrink: 0,
                  boxShadow: `0 4px 12px ${member.color}40`
                }}>
                  {member.initials}
                </div>
                <div style={{ flex: 1 }}>
                  <p style={{ margin: "0 0 2px", fontWeight: 700, color: "#111827", fontSize: "15px" }}>{member.name}</p>
                  <p style={{ margin: "0 0 4px", color: "#4B5563", fontSize: "13px" }}>{member.role}</p>
                  <span style={{
                    fontSize: "11px",
                    color: member.color,
                    background: `${member.color}15`,
                    padding: "3px 12px",
                    borderRadius: "100px",
                    fontWeight: 600
                  }}>
                    {member.specialty}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ===== MILESTONES ===== */}
        <div id="milestones" style={{ background: "white", borderRadius: "16px", padding: "36px", boxShadow: "0 4px 24px rgba(0,0,0,0.06)", marginBottom: "28px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
            <Award size={24} style={{ color: "#D97706" }} />
            <h2 style={{ fontSize: "22px", fontWeight: 800, color: "#111827", margin: 0 }}>เส้นทางความสำเร็จ</h2>
          </div>
          <p style={{ color: "#6B7280", fontSize: "14px", marginBottom: "24px" }}>ก้าวสำคัญของ TSPI Clinic สู่การเป็นผู้นำด้านการแพทย์แม่นยำในไทย</p>

          <div style={{ display: "flex", flexDirection: "column", gap: "0", position: "relative" }}>
            {/* Timeline line */}
            <div style={{ position: "absolute", left: "24px", top: "20px", bottom: "20px", width: "2px", background: "#E5E7EB", zIndex: 0 }} />

            {milestones.map((m, i) => (
              <div key={i} style={{ display: "flex", gap: "20px", padding: "12px 0", position: "relative", zIndex: 1 }}>
                <div style={{
                  width: "48px",
                  height: "48px",
                  borderRadius: "50%",
                  background: i === milestones.length - 1 ? "#D4AF37" : "#0A5C8E",
                  color: "white",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 900,
                  fontSize: "14px",
                  flexShrink: 0,
                  boxShadow: `0 4px 12px ${i === milestones.length - 1 ? "#D4AF3740" : "#0A5C8E40"}`
                }}>
                  {m.year.slice(-2)}
                </div>
                <div style={{ flex: 1, paddingTop: "4px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
                    <span style={{ fontSize: "13px", fontWeight: 700, color: i === milestones.length - 1 ? "#D4AF37" : "#0A5C8E" }}>{m.year}</span>
                    <h4 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "#111827" }}>{m.title}</h4>
                  </div>
                  <p style={{ margin: "4px 0 0", color: "#6B7280", fontSize: "14px" }}>{m.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ===== CONTACT ===== */}
        <div id="contact" style={{ background: "white", borderRadius: "16px", padding: "36px", boxShadow: "0 4px 24px rgba(0,0,0,0.06)", marginBottom: "28px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
            <Phone size={24} style={{ color: "#059669" }} />
            <h2 style={{ fontSize: "22px", fontWeight: 800, color: "#111827", margin: 0 }}>ติดต่อเรา</h2>
          </div>
          <p style={{ color: "#6B7280", fontSize: "14px", marginBottom: "24px" }}>ช่องทางติดต่อทุกช่องทาง พร้อมให้บริการคุณ</p>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px", marginBottom: "28px" }}>
            {contactChannels.map((ch, i) => (
              <div key={i} style={{
                padding: "20px",
                borderRadius: "14px",
                background: ch.bg,
                border: `1px solid ${ch.color}15`,
                transition: "all 0.3s ease"
              }}>
                <div style={{
                  width: "44px",
                  height: "44px",
                  borderRadius: "12px",
                  background: "white",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: "12px",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.04)"
                }}>
                  <ch.icon size={20} color={ch.color} />
                </div>
                <p style={{ margin: "0 0 2px", fontSize: "11px", fontWeight: 600, color: "#6B7280", textTransform: "uppercase", letterSpacing: "0.5px" }}>{ch.title}</p>
                <p style={{ margin: "0 0 2px", fontWeight: 700, color: "#111827", fontSize: "15px" }}>{ch.value}</p>
                <p style={{ margin: 0, fontSize: "12px", color: "#9CA3AF" }}>{ch.sub}</p>
              </div>
            ))}
          </div>

          {/* Address & Hours */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "20px" }}>
            <div style={{ padding: "24px", borderRadius: "14px", background: "#FAFBFC", border: "1px solid #F1F5F9" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
                <MapPin size={18} color="#0A5C8E" />
                <p style={{ margin: 0, fontWeight: 700, color: "#111827", fontSize: "14px" }}>ที่อยู่คลินิก</p>
              </div>
              <p style={{ margin: "0 0 8px", color: "#4B5563", fontSize: "14px", lineHeight: 1.7 }}>
                123 อาคาร Clinical Center<br />
                Innovation District<br />
                กรุงเทพมหานคร 10110
              </p>
              <a
                href="https://maps.google.com"
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  color: "#0A5C8E",
                  fontSize: "13px",
                  fontWeight: 600,
                  textDecoration: "none",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "4px",
                  padding: "6px 16px",
                  borderRadius: "100px",
                  background: "#EFF6FF",
                  transition: "all 0.2s ease"
                }}
              >
                ดูแผนที่ Google Maps <ChevronRight size={14} />
              </a>
            </div>
            <div style={{ padding: "24px", borderRadius: "14px", background: "#FAFBFC", border: "1px solid #F1F5F9" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
                <Clock size={18} color="#0A5C8E" />
                <p style={{ margin: 0, fontWeight: 700, color: "#111827", fontSize: "14px" }}>เวลาทำการ</p>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {hours.map((h, i) => (
                  <div key={i} style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    paddingBottom: i < hours.length - 1 ? "8px" : "0",
                    borderBottom: i < hours.length - 1 ? "1px solid #F1F5F9" : "none"
                  }}>
                    <span style={{ fontSize: "14px", color: "#4B5563" }}>{h.day}</span>
                    <span style={{
                      fontSize: "14px",
                      fontWeight: 700,
                      color: h.time === "ปิดทำการ" ? "#EF4444" : "#059669"
                    }}>
                      {h.time}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* ===== CTA BANNER ===== */}
        <div style={{
          background: "linear-gradient(135deg, #0f0c29 0%, #1a1742 40%, #0A5C8E 100%)",
          borderRadius: "20px",
          padding: "44px 48px",
          textAlign: "center",
          position: "relative",
          overflow: "hidden"
        }}>
          <div style={{ position: "absolute", top: "-30%", right: "-10%", width: "300px", height: "300px", borderRadius: "50%", background: "radial-gradient(circle, rgba(212,175,55,0.06), transparent 70%)", pointerEvents: "none" }} />
          <div style={{ position: "relative", zIndex: 1 }}>
            <div style={{ display: "inline-flex", alignItems: "center", gap: "8px", background: "rgba(212,175,55,0.12)", padding: "6px 16px", borderRadius: "100px", marginBottom: "16px", border: "1px solid rgba(212,175,55,0.1)" }}>
              <Sparkles size={14} style={{ color: "#D4AF37" }} />
              <span style={{ fontSize: "11px", fontWeight: 700, color: "#D4AF37", letterSpacing: "0.1em", textTransform: "uppercase" }}>เริ่มต้นวันนี้</span>
            </div>
            <h3 style={{ color: "white", fontSize: "clamp(22px, 3vw, 30px)", fontWeight: 800, margin: "0 0 12px" }}>เริ่มต้นดูแลสุขภาพกับเรา</h3>
            <p style={{ color: "rgba(255,255,255,0.6)", marginBottom: "24px", fontSize: "15px", maxWidth: "480px", marginLeft: "auto", marginRight: "auto" }}>
              ลงทะเบียนออนไลน์ฟรี หรือนัดปรึกษาแพทย์ได้ทันที
            </p>
            <div style={{ display: "flex", gap: "12px", justifyContent: "center", flexWrap: "wrap" }}>
              <Link href="/patient/login" style={{ background: "linear-gradient(135deg, #D4AF37, #B8962E)", color: "#0f0c29", padding: "14px 40px", borderRadius: "12px", textDecoration: "none", fontWeight: 800, fontSize: "15px", boxShadow: "0 4px 24px rgba(212,175,55,0.3)" }}>
                เข้าสู่ระบบ →
              </Link>
              <Link href="/guide" style={{ background: "rgba(255,255,255,0.06)", color: "white", padding: "14px 32px", borderRadius: "12px", textDecoration: "none", fontWeight: 600, fontSize: "15px", border: "1px solid rgba(255,255,255,0.08)" }}>
                ดูคู่มือใช้งาน
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