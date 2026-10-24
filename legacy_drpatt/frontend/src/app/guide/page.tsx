"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import {
  BookOpen, ChevronRight, UserPlus, MessageSquare, BarChart2,
  Calendar, FileText, HelpCircle, ChevronDown, ChevronUp,
  Smartphone, ArrowLeft, CheckCircle, Menu, X,
  Users, Activity, Sparkles, Shield, Clock, Award,
  Globe, Mail, Phone, MapPin, Star, ArrowUpRight,
  PlayCircle, Download, CreditCard, LogIn, Zap, Brain
} from "lucide-react";

const steps = [
  {
    number: "01",
    icon: UserPlus,
    color: "#0A5C8E",
    bg: "#EFF6FF",
    title: "ลงทะเบียนเข้าสู่ระบบ",
    desc: "สมัครสมาชิกด้วยเลขบัตรประชาชน ชื่อ-นามสกุล และเบอร์โทรศัพท์ เพียงไม่กี่ขั้นตอน ระบบจะสร้าง HN (Hospital Number) ให้คุณทันที",
    tips: ["ใช้เลขบัตรประชาชน 13 หลัก", "กรอกวันเดือนปีเกิดให้ถูกต้อง", "ตั้งรหัสผ่านที่จำง่าย"],
    duration: "2-3 นาที",
  },
  {
    number: "02",
    icon: MessageSquare,
    color: "#7C3AED",
    bg: "#F5F3FF",
    title: "ซักประวัติอาการกับ AI",
    desc: "พิมพ์หรือพูดบอกอาการที่รู้สึก AI ของเราจะซักถามรายละเอียดเพิ่มเติมเหมือนพยาบาล เพื่อเก็บข้อมูลสุขภาพให้ครบถ้วนก่อนพบแพทย์",
    tips: ["บอกอาการตามความรู้สึกจริงๆ", "ไม่ต้องใช้ภาษาการแพทย์", "ยิ่งละเอียดยิ่งวิเคราะห์แม่นยำ"],
    duration: "5-10 นาที",
  },
  {
    number: "03",
    icon: BarChart2,
    color: "#059669",
    bg: "#ECFDF5",
    title: "รับผลวิเคราะห์ 39 แกน",
    desc: "AI วิเคราะห์สุขภาพของคุณผ่าน 39 แกนกลไกสรีรวิทยา ตั้งแต่ระบบอักเสบ ฮอร์โมน ไปจนถึงระบบประสาทและพลังงานเซลล์ แสดงผลเป็นกราฟ Digital Twin",
    tips: ["ดูคะแนนแต่ละแกน 0-100", "แกนสีแดง = ต้องเฝ้าระวัง", "กดดูคำอธิบายแต่ละแกนได้"],
    duration: "ทันที",
  },
  {
    number: "04",
    icon: Calendar,
    color: "#D97706",
    bg: "#FFFBEB",
    title: "นัดหมายพบแพทย์",
    desc: "เลือกวันเวลาที่สะดวกจากตารางนัดหมาย ระบบจะส่งการยืนยันผ่าน LINE OA และแจ้งเตือนก่อนถึงวันนัด 1 วัน",
    tips: ["ดูตารางว่างแพทย์แบบ Real-time", "เลือก Telemedicine หรือ On-site", "ยกเลิก/เลื่อนนัดได้ล่วงหน้า 24 ชม."],
    duration: "2-3 นาที",
  },
  {
    number: "05",
    icon: FileText,
    color: "#DC2626",
    bg: "#FEF2F2",
    title: "รับรายงานและแผนการรักษา",
    desc: "หลังพบแพทย์ ระบบจะออกรายงานเชิงลึกรวมถึงแผนการรักษาเฉพาะบุคคล พร้อมดาวน์โหลดเป็น PDF หรือส่งตรงไป LINE ได้ทันที",
    tips: ["รายงานมีทั้งภาษาไทยและอังกฤษ", "ส่งออกไฟล์ PDF บันทึกได้", "ติดตามความคืบหน้าในแอป"],
    duration: "ทันที",
  },
];

const faqs = [
  {
    q: "ข้อมูลสุขภาพของฉันปลอดภัยไหม?",
    a: "ปลอดภัยอย่างแน่นอนครับ ระบบของเราเข้ารหัสข้อมูลด้วยมาตรฐาน AES-256 และปฏิบัติตาม PDPA (พ.ร.บ. คุ้มครองข้อมูลส่วนบุคคล) อย่างเคร่งครัด ข้อมูลของคุณจะไม่ถูกแบ่งปันกับบุคคลภายนอกโดยไม่ได้รับความยินยอม",
    category: "ความปลอดภัย",
  },
  {
    q: "สามารถใช้งานได้บนโทรศัพท์ทุกรุ่นไหม?",
    a: "ใช้ได้ทั้ง iOS (iPhone) และ Android ทุกรุ่น ทั้งผ่านเบราว์เซอร์ Safari, Chrome และสามารถติดตั้งเป็นแอปบนหน้า Home Screen ได้ด้วย (PWA)",
    category: "การใช้งาน",
  },
  {
    q: "ต้องเสียค่าใช้จ่ายในการใช้แอปไหม?",
    a: "การลงทะเบียนและการใช้งานพื้นฐาน (ซักประวัติ AI, ดูผลวิเคราะห์) ไม่มีค่าใช้จ่าย ค่าบริการจะเกิดขึ้นเมื่อนัดหมายพบแพทย์จริงเท่านั้น",
    category: "ค่าบริการ",
  },
  {
    q: "ถ้าลืมรหัสผ่านต้องทำอย่างไร?",
    a: "กดปุ่ม 'ลืมรหัสผ่าน' ในหน้าเข้าสู่ระบบ ระบบจะส่ง OTP ไปยังเบอร์โทรศัพท์ที่ลงทะเบียนไว้ เพื่อให้คุณตั้งรหัสผ่านใหม่",
    category: "การใช้งาน",
  },
  {
    q: "AI วิเคราะห์ได้แม่นยำแค่ไหน?",
    a: "ระบบ TSPI AI มีความแม่นยำ 97.8% ในการวิเคราะห์รูปแบบสุขภาพ อย่างไรก็ตาม AI ทำหน้าที่เป็นผู้ช่วยคลินิก ไม่ใช่ผู้วินิจฉัยโรค การตัดสินใจสุดท้ายขึ้นอยู่กับแพทย์เสมอ",
    category: "เทคโนโลยี",
  },
  {
    q: "ใช้งาน LINE สามารถเชื่อมต่อได้ไหม?",
    a: "ได้เลยครับ ระบบรองรับการเชื่อมต่อ LINE OA เพื่อรับการแจ้งเตือนนัดหมาย ผลตรวจ และข้อความจากแพทย์โดยตรงใน LINE ของคุณ",
    category: "การใช้งาน",
  },
];

const stats = [
  { value: "5", label: "ขั้นตอนง่ายๆ", icon: <CheckCircle size={18} color="#0A5C8E" /> },
  { value: "97.8%", label: "ความแม่นยำ AI", icon: <Brain size={18} color="#7C3AED" /> },
  { value: "24/7", label: "ใช้งานได้ตลอดเวลา", icon: <Clock size={18} color="#059669" /> },
  { value: "10k+", label: "ผู้ใช้งาน", icon: <Users size={18} color="#D97706" /> },
];

export default function GuidePage() {
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [activeTab, setActiveTab] = useState("steps");

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
                style={{ color: item.href === "/guide" ? "#D4AF37" : "#4B5563", fontSize: "0.85rem", fontWeight: item.href === "/guide" ? 700 : 500 }}
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
        background: "linear-gradient(160deg, #0f0c29 0%, #1a1742 30%, #0A5C8E 60%, #1a7ab5 100%)",
        color: "white",
        padding: "120px 0 64px",
        position: "relative",
        overflow: "hidden"
      }}>
        <div style={{ position: "absolute", top: "-40%", right: "-10%", width: "500px", height: "500px", borderRadius: "50%", background: "radial-gradient(circle, rgba(212,175,55,0.04), transparent 70%)", pointerEvents: "none" }} />
        <div style={{ position: "absolute", bottom: "-30%", left: "-5%", width: "400px", height: "400px", borderRadius: "50%", background: "radial-gradient(circle, rgba(90,224,255,0.03), transparent 70%)", pointerEvents: "none" }} />

        <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "0 24px", position: "relative", zIndex: 1 }}>
          <Link href="/" style={{ color: "rgba(255,255,255,0.5)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "14px", marginBottom: "28px", transition: "color 0.2s" }}>
            <ArrowLeft size={16} /> กลับหน้าหลัก
          </Link>

          <div style={{ display: "inline-flex", alignItems: "center", gap: "8px", background: "rgba(255,255,255,0.08)", padding: "8px 18px", borderRadius: "100px", marginBottom: "20px", fontSize: "12px", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", border: "1px solid rgba(255,255,255,0.06)" }}>
            <BookOpen size={14} /> Documentation
          </div>

          <h1 style={{ fontSize: "clamp(32px, 5vw, 48px)", fontWeight: 900, margin: "0 0 16px", lineHeight: 1.15, letterSpacing: "-0.02em" }}>
            คู่มือการใช้งาน <br />
            <span style={{ color: "#5ae0ff" }}>TSPI Clinic</span>
          </h1>

          <p style={{ opacity: 0.85, fontSize: "16px", maxWidth: "640px", lineHeight: 1.8, marginBottom: "32px" }}>
            เรียนรู้วิธีใช้งานระบบดูแลสุขภาพอัจฉริยะของเราตั้งแต่ต้นจนจบ ใน 5 ขั้นตอนง่ายๆ
          </p>

          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <Link href="/patient/login" style={{ background: "linear-gradient(135deg, #D4AF37, #B8962E)", color: "#0f0c29", padding: "14px 32px", borderRadius: "12px", textDecoration: "none", fontWeight: 800, fontSize: "15px", display: "flex", alignItems: "center", gap: "8px", boxShadow: "0 4px 20px rgba(212,175,55,0.3)" }}>
              เริ่มต้นใช้งาน <ChevronRight size={18} />
            </Link>
            <Link href="#steps" style={{ background: "rgba(255,255,255,0.06)", color: "white", padding: "14px 32px", borderRadius: "12px", textDecoration: "none", fontWeight: 600, fontSize: "15px", border: "1px solid rgba(255,255,255,0.1)" }}>
              ดูขั้นตอน
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
          gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
          gap: "16px",
          textAlign: "center"
        }}>
          {stats.map((stat, i) => (
            <div key={i} style={{ padding: "8px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", marginBottom: "4px" }}>
                {stat.icon}
                <span style={{ fontSize: "24px", fontWeight: 900, color: "#111827" }}>{stat.value}</span>
              </div>
              <p style={{ margin: 0, fontSize: "12px", color: "#6B7280", fontWeight: 500 }}>{stat.label}</p>
            </div>
          ))}
        </div>

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
            { id: "steps", label: "5 ขั้นตอน", icon: <CheckCircle size={16} /> },
            { id: "faq", label: "คำถามที่พบบ่อย", icon: <HelpCircle size={16} /> },
            { id: "download", label: "ดาวน์โหลดแอป", icon: <Download size={16} /> },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                document.getElementById(tab.id)?.scrollIntoView({ behavior: "smooth", block: "start" });
              }}
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

        {/* ===== STEPS ===== */}
        <div id="steps" style={{ background: "white", borderRadius: "16px", padding: "36px", boxShadow: "0 4px 24px rgba(0,0,0,0.06)", marginBottom: "28px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
            <BookOpen size={24} style={{ color: "#D4AF37" }} />
            <h2 style={{ fontSize: "22px", fontWeight: 800, color: "#111827", margin: 0 }}>5 ขั้นตอนเริ่มต้นใช้งาน</h2>
            <span style={{ marginLeft: "auto", background: "#FEF7E0", color: "#D4AF37", padding: "4px 14px", borderRadius: "100px", fontSize: "12px", fontWeight: 600 }}>Easy Start</span>
          </div>
          <p style={{ color: "#6B7280", fontSize: "14px", marginBottom: "32px" }}>ทำตามขั้นตอนด้านล่างเพื่อเริ่มต้นรับบริการดูแลสุขภาพเฉพาะบุคคล</p>

          {/* Progress indicator */}
          <div style={{ display: "flex", gap: "8px", marginBottom: "28px", overflow: "auto" }}>
            {steps.map((step, i) => (
              <div key={i} style={{
                flex: 1,
                minWidth: "60px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: "4px"
              }}>
                <div style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "50%",
                  background: step.color,
                  color: "white",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 700,
                  fontSize: "14px"
                }}>
                  {i + 1}
                </div>
                <span style={{ fontSize: "9px", color: "#6B7280", textAlign: "center" }}>{step.title.split(" ")[0]}</span>
              </div>
            ))}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {steps.map((step, i) => (
              <div key={i} style={{
                display: "flex",
                gap: "20px",
                alignItems: "flex-start",
                padding: "24px",
                border: "1px solid #F1F5F9",
                borderRadius: "14px",
                background: step.bg,
                transition: "all 0.3s ease"
              }}>
                <div style={{
                  flexShrink: 0,
                  width: "56px",
                  height: "56px",
                  borderRadius: "50%",
                  background: step.color,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: `0 4px 12px ${step.color}40`
                }}>
                  <step.icon size={24} color="white" />
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px", flexWrap: "wrap" }}>
                    <span style={{
                      fontSize: "10px",
                      fontWeight: 700,
                      color: step.color,
                      background: "white",
                      padding: "2px 12px",
                      borderRadius: "100px",
                      border: `1px solid ${step.color}15`,
                      letterSpacing: "0.05em"
                    }}>
                      STEP {step.number}
                    </span>
                    <span style={{
                      fontSize: "11px",
                      color: "#6B7280",
                      display: "flex",
                      alignItems: "center",
                      gap: "4px"
                    }}>
                      <Clock size={14} /> {step.duration}
                    </span>
                  </div>
                  <h3 style={{ margin: "0 0 8px", fontSize: "18px", fontWeight: 700, color: "#111827" }}>{step.title}</h3>
                  <p style={{ margin: "0 0 14px", color: "#4B5563", fontSize: "14px", lineHeight: 1.7 }}>{step.desc}</p>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                    {step.tips.map((tip, j) => (
                      <span key={j} style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "5px",
                        fontSize: "12px",
                        color: "#4B5563",
                        background: "white",
                        padding: "4px 12px",
                        borderRadius: "100px",
                        border: "1px solid #E5E7EB"
                      }}>
                        <CheckCircle size={12} color={step.color} />
                        {tip}
                      </span>
                    ))}
                  </div>
                </div>
                <ChevronRight size={20} style={{ color: "#9CA3AF", flexShrink: 0, marginTop: "16px" }} />
              </div>
            ))}
          </div>
        </div>

        {/* ===== FAQ ===== */}
        <div id="faq" style={{ background: "white", borderRadius: "16px", padding: "36px", boxShadow: "0 4px 24px rgba(0,0,0,0.06)", marginBottom: "28px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
            <HelpCircle size={24} style={{ color: "#7C3AED" }} />
            <h2 style={{ fontSize: "22px", fontWeight: 800, color: "#111827", margin: 0 }}>คำถามที่พบบ่อย (FAQ)</h2>
            <span style={{ marginLeft: "auto", background: "#F5F3FF", color: "#7C3AED", padding: "4px 14px", borderRadius: "100px", fontSize: "12px", fontWeight: 600 }}>{faqs.length} คำถาม</span>
          </div>
          <p style={{ color: "#6B7280", fontSize: "14px", marginBottom: "24px" }}>คำถามที่ผู้ใช้งานมักสอบถามเข้ามาบ่อยที่สุด</p>

          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {faqs.map((faq, i) => (
              <div key={i} style={{
                border: "1px solid #F1F5F9",
                borderRadius: "12px",
                overflow: "hidden",
                transition: "all 0.2s ease"
              }}>
                <button
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                  style={{
                    width: "100%",
                    padding: "16px 20px",
                    background: openFaq === i ? "#F8FAFC" : "white",
                    border: "none",
                    cursor: "pointer",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    textAlign: "left",
                    transition: "all 0.2s ease"
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <span style={{
                      fontSize: "10px",
                      fontWeight: 700,
                      color: "#0A5C8E",
                      background: "#EFF6FF",
                      padding: "2px 10px",
                      borderRadius: "100px",
                      letterSpacing: "0.05em"
                    }}>
                      {faq.category}
                    </span>
                    <span style={{ fontWeight: 600, fontSize: "15px", color: "#111827" }}>{faq.q}</span>
                  </div>
                  {openFaq === i ? <ChevronUp size={18} color="#0A5C8E" /> : <ChevronDown size={18} color="#9CA3AF" />}
                </button>
                {openFaq === i && (
                  <div style={{
                    padding: "0 20px 20px",
                    color: "#4B5563",
                    fontSize: "14px",
                    lineHeight: 1.8,
                    borderTop: "1px solid #F1F5F9",
                    background: "#FAFBFC"
                  }}>
                    <div style={{ paddingTop: "16px" }}>{faq.a}</div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* ===== DOWNLOAD APP ===== */}
        <div id="download" style={{
          background: "linear-gradient(135deg, #0f0c29 0%, #1a1742 40%, #0A5C8E 100%)",
          borderRadius: "20px",
          padding: "40px 48px",
          position: "relative",
          overflow: "hidden"
        }}>
          <div style={{ position: "absolute", top: "-30%", right: "-10%", width: "300px", height: "300px", borderRadius: "50%", background: "radial-gradient(circle, rgba(212,175,55,0.06), transparent 70%)", pointerEvents: "none" }} />

          <div style={{ position: "relative", zIndex: 1, display: "flex", alignItems: "center", gap: "32px", flexWrap: "wrap" }}>
            <div style={{ flex: 1 }}>
              <div style={{ display: "inline-flex", alignItems: "center", gap: "8px", background: "rgba(212,175,55,0.12)", padding: "6px 16px", borderRadius: "100px", marginBottom: "16px", border: "1px solid rgba(212,175,55,0.1)" }}>
                <Smartphone size={14} style={{ color: "#D4AF37" }} />
                <span style={{ fontSize: "11px", fontWeight: 700, color: "#D4AF37", letterSpacing: "0.1em", textTransform: "uppercase" }}>Mobile App</span>
              </div>
              <h3 style={{ color: "white", fontSize: "clamp(22px, 3vw, 30px)", fontWeight: 800, margin: "0 0 12px" }}>
                ติดตั้งแอปเพื่อประสบการณ์ที่ดียิ่งขึ้น
              </h3>
              <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "15px", maxWidth: "500px", lineHeight: 1.7, marginBottom: "24px" }}>
                ใช้งานแบบ Offline ได้บางส่วน รับแจ้งเตือนนัดหมาย เร็วกว่าเบราว์เซอร์ 3 เท่า
              </p>
              <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
                <Link href="/install" style={{ background: "linear-gradient(135deg, #D4AF37, #B8962E)", color: "#0f0c29", padding: "12px 28px", borderRadius: "12px", textDecoration: "none", fontWeight: 700, fontSize: "14px", display: "flex", alignItems: "center", gap: "8px", boxShadow: "0 4px 20px rgba(212,175,55,0.3)" }}>
                  <Download size={18} /> ดาวน์โหลดแอป
                </Link>
                <Link href="/patient/login" style={{ background: "rgba(255,255,255,0.06)", color: "white", padding: "12px 28px", borderRadius: "12px", textDecoration: "none", fontWeight: 600, fontSize: "14px", display: "flex", alignItems: "center", gap: "8px", border: "1px solid rgba(255,255,255,0.08)" }}>
                  <LogIn size={18} /> เข้าสู่ระบบ
                </Link>
              </div>
            </div>
            <div style={{
              width: "120px",
              height: "120px",
              borderRadius: "50%",
              background: "rgba(212,175,55,0.08)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              border: "2px solid rgba(212,175,55,0.15)"
            }}>
              <Smartphone size={56} style={{ color: "#D4AF37" }} />
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