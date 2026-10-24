"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Smartphone, Monitor, ArrowLeft, CheckCircle,
  Share2, MoreVertical, Plus, Download, Menu, X,
  Globe, Mail, Phone, MapPin, Sparkles, Zap,
  Users, Activity, Shield, Clock, Award, Star, ChevronRight
} from "lucide-react";

const iosSteps = [
  { icon: "🌐", title: "เปิด Safari", desc: "ต้องใช้ Safari เท่านั้น (Chrome บน iOS ยังไม่รองรับ PWA)" },
  { icon: "📤", title: "แตะปุ่ม Share", desc: 'กดปุ่ม Share (สัญลักษณ์กล่องมีลูกศรขึ้น) ที่แถบล่างของ Safari' },
  { icon: "🏠", title: "เลือก Add to Home Screen", desc: 'เลื่อนลงในเมนู Share แล้วเลือก "Add to Home Screen"' },
  { icon: "✅", title: "กด Add", desc: 'ตั้งชื่อเป็น "TSPI คลินิก" แล้วกด Add ที่มุมขวาบน' },
];

const androidSteps = [
  { icon: "🌐", title: "เปิด Chrome", desc: "ใช้ Chrome เป็นเบราว์เซอร์หลัก (รองรับ PWA เต็มรูปแบบ)" },
  { icon: "⋮", title: "แตะเมนู 3 จุด", desc: "กดปุ่ม ⋮ ที่มุมขวาบนของ Chrome" },
  { icon: "📲", title: "เลือก Add to Home Screen", desc: 'เลือก "Add to Home Screen" หรือ "Install App" ที่ปรากฏขึ้น' },
  { icon: "✅", title: "กด Install", desc: "ยืนยันการติดตั้ง แอปจะปรากฏบน Home Screen ทันที" },
];

const desktopSteps = [
  { icon: "🌐", title: "เปิด Chrome หรือ Edge", desc: "ใช้ Chrome 76+ หรือ Microsoft Edge 79+ ขึ้นไป" },
  { icon: "📥", title: "มองหาไอคอนติดตั้ง", desc: "มองหาไอคอน Install (⊕) ที่แถบ Address Bar ด้านขวา" },
  { icon: "✅", title: "คลิก Install", desc: 'คลิก "Install TSPI Clinic" ในป๊อปอัปที่ปรากฏขึ้น' },
];

const benefits = [
  { emoji: "⚡", title: "เร็วกว่าเดิม 3 เท่า", desc: "โหลดเนื้อหาจาก Cache ใช้งานได้แม้อินเทอร์เน็ตช้า" },
  { emoji: "🔔", title: "รับแจ้งเตือนได้", desc: "รับ Push Notification นัดหมาย ผลตรวจ และข้อความจากแพทย์" },
  { emoji: "📱", title: "ไม่ต้องผ่านเบราว์เซอร์", desc: "เปิดแอปตรงจาก Home Screen เหมือนแอปทั่วไป" },
  { emoji: "💾", title: "ไม่เปลือง Storage", desc: "ขนาดแค่ 2-3 MB เทียบกับแอปปกติที่หลายสิบ MB" },
];

const stats = [
  { value: "2-3 MB", label: "ขนาดไฟล์", icon: <Download size={18} color="#0A5C8E" /> },
  { value: "3x", label: "เร็วขึ้น", icon: <Zap size={18} color="#D97706" /> },
  { value: "100%", label: "เข้ากันได้", icon: <CheckCircle size={18} color="#059669" /> },
  { value: "10k+", label: "ผู้ใช้งาน", icon: <Users size={18} color="#7C3AED" /> },
];

export default function InstallPage() {
  const [platform, setPlatform] = useState<"ios" | "android" | "desktop">("android");
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [installable, setInstallable] = useState(false);
  const [installed, setInstalled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll);

    // ตรวจจับ Platform อัตโนมัติ
    const ua = navigator.userAgent;
    if (/iPad|iPhone|iPod/.test(ua)) setPlatform("ios");
    else if (/Android/.test(ua)) setPlatform("android");
    else setPlatform("desktop");

    // รับ PWA install prompt
    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setInstallable(true);
    };
    window.addEventListener("beforeinstallprompt", handler);
    window.addEventListener("appinstalled", () => {
      setInstalled(true);
      setInstallable(false);
    });
    return () => {
      window.removeEventListener("scroll", handleScroll);
      window.removeEventListener("beforeinstallprompt", handler);
    };
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === "accepted") {
      setInstalled(true);
      setInstallable(false);
    }
  };

  const currentSteps = platform === "ios" ? iosSteps : platform === "android" ? androidSteps : desktopSteps;
  const platformLabel = platform === "ios" ? "iPhone/iPad" : platform === "android" ? "Android" : "คอมพิวเตอร์";
  const platformBrowser = platform === "ios" ? "Safari" : platform === "android" ? "Chrome" : "Chrome/Edge";

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
                style={{ color: item.href === "/install" ? "#D4AF37" : "#4B5563", fontSize: "0.85rem", fontWeight: item.href === "/install" ? 700 : 500 }}
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
        background: "linear-gradient(160deg, #0f0c29 0%, #1a1742 30%, #0f3460 60%, #0A5C8E 100%)",
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
            <Download size={14} /> Progressive Web App
          </div>

          <h1 style={{ fontSize: "clamp(32px, 5vw, 48px)", fontWeight: 900, margin: "0 0 16px", lineHeight: 1.15, letterSpacing: "-0.02em" }}>
            ติดตั้ง TSPI Clinic <br />
            <span style={{ color: "#5ae0ff" }}>บนอุปกรณ์ของคุณ</span>
          </h1>

          <p style={{ opacity: 0.85, fontSize: "16px", maxWidth: "640px", lineHeight: 1.8, marginBottom: "32px" }}>
            ไม่ต้องดาวน์โหลดจาก App Store — ติดตั้งตรงจากเบราว์เซอร์ ใช้งานได้เหมือนแอปจริง
          </p>

          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            {installable && !installed ? (
              <button
                onClick={handleInstall}
                style={{ background: "linear-gradient(135deg, #D4AF37, #B8962E)", color: "#0f0c29", padding: "14px 32px", borderRadius: "12px", border: "none", fontWeight: 800, fontSize: "15px", display: "flex", alignItems: "center", gap: "8px", boxShadow: "0 4px 20px rgba(212,175,55,0.3)", cursor: "pointer" }}
              >
                <Download size={20} /> ติดตั้งทันที
              </button>
            ) : (
              <Link href="#steps" style={{ background: "linear-gradient(135deg, #D4AF37, #B8962E)", color: "#0f0c29", padding: "14px 32px", borderRadius: "12px", textDecoration: "none", fontWeight: 800, fontSize: "15px", display: "flex", alignItems: "center", gap: "8px", boxShadow: "0 4px 20px rgba(212,175,55,0.3)" }}>
                ดูขั้นตอนการติดตั้ง <ChevronRight size={18} />
              </Link>
            )}
            <Link href="/guide" style={{ background: "rgba(255,255,255,0.06)", color: "white", padding: "14px 32px", borderRadius: "12px", textDecoration: "none", fontWeight: 600, fontSize: "15px", border: "1px solid rgba(255,255,255,0.1)" }}>
              คู่มือการใช้งาน
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

        {/* ===== INSTALLED BANNER ===== */}
        {installed && (
          <div style={{
            background: "#ECFDF5",
            border: "1px solid #A7F3D0",
            borderRadius: "14px",
            padding: "20px 24px",
            display: "flex",
            alignItems: "center",
            gap: "16px",
            marginBottom: "28px",
            boxShadow: "0 2px 12px rgba(5,150,105,0.08)"
          }}>
            <div style={{
              width: "48px",
              height: "48px",
              borderRadius: "50%",
              background: "#05966915",
              display: "flex",
              alignItems: "center",
              justifyContent: "center"
            }}>
              <CheckCircle size={28} color="#059669" />
            </div>
            <div>
              <p style={{ margin: 0, fontWeight: 700, color: "#065F46", fontSize: "16px" }}>ติดตั้งแอปสำเร็จแล้ว! 🎉</p>
              <p style={{ margin: 0, fontSize: "14px", color: "#047857" }}>มองหาไอคอน TSPI คลินิก บน Home Screen ได้เลย</p>
            </div>
          </div>
        )}

        {/* ===== ONE-CLICK INSTALL ===== */}
        {installable && !installed && (
          <div style={{
            background: "linear-gradient(135deg, #0f0c29, #1a1742, #0A5C8E)",
            borderRadius: "20px",
            padding: "32px 40px",
            marginBottom: "28px",
            textAlign: "center",
            position: "relative",
            overflow: "hidden"
          }}>
            <div style={{ position: "absolute", top: "-30%", right: "-10%", width: "200px", height: "200px", borderRadius: "50%", background: "radial-gradient(circle, rgba(212,175,55,0.06), transparent 70%)", pointerEvents: "none" }} />
            <div style={{ position: "relative", zIndex: 1 }}>
              <div style={{ display: "inline-flex", alignItems: "center", gap: "8px", background: "rgba(212,175,55,0.12)", padding: "6px 16px", borderRadius: "100px", marginBottom: "16px", border: "1px solid rgba(212,175,55,0.1)" }}>
                <Sparkles size={14} style={{ color: "#D4AF37" }} />
                <span style={{ fontSize: "11px", fontWeight: 700, color: "#D4AF37", letterSpacing: "0.1em", textTransform: "uppercase" }}>พร้อมติดตั้ง</span>
              </div>
              <p style={{ margin: "0 0 4px", color: "rgba(255,255,255,0.7)", fontSize: "14px", fontWeight: 500 }}>
                อุปกรณ์ของคุณพร้อมติดตั้งแอป TSPI Clinic
              </p>
              <h3 style={{ color: "white", margin: "0 0 20px", fontSize: "22px", fontWeight: 800 }}>กด Install เพื่อติดตั้งทันที</h3>
              <button
                onClick={handleInstall}
                style={{
                  background: "linear-gradient(135deg, #D4AF37, #B8962E)",
                  color: "#0f0c29",
                  border: "none",
                  padding: "14px 40px",
                  borderRadius: "12px",
                  fontWeight: 800,
                  fontSize: "16px",
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "10px",
                  boxShadow: "0 4px 24px rgba(212,175,55,0.3)"
                }}
              >
                <Download size={20} /> ติดตั้ง TSPI Clinic
              </button>
            </div>
          </div>
        )}

        {/* ===== PLATFORM SELECTOR ===== */}
        <div id="steps" style={{ background: "white", borderRadius: "16px", padding: "36px", boxShadow: "0 4px 24px rgba(0,0,0,0.06)", marginBottom: "28px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
            <Smartphone size={24} style={{ color: "#D4AF37" }} />
            <h2 style={{ fontSize: "22px", fontWeight: 800, color: "#111827", margin: 0 }}>เลือกอุปกรณ์ที่ต้องการติดตั้ง</h2>
          </div>
          <p style={{ color: "#6B7280", fontSize: "14px", marginBottom: "24px" }}>เลือกอุปกรณ์ของคุณเพื่อดูขั้นตอนการติดตั้งที่ถูกต้อง</p>

          <div style={{ display: "flex", gap: "12px", marginBottom: "28px", flexWrap: "wrap" }}>
            {[
              { key: "ios", label: "iPhone / iPad", emoji: "🍎", icon: <Smartphone size={18} /> },
              { key: "android", label: "Android", emoji: "🤖", icon: <Smartphone size={18} /> },
              { key: "desktop", label: "คอมพิวเตอร์", emoji: "💻", icon: <Monitor size={18} /> },
            ].map((p) => (
              <button
                key={p.key}
                onClick={() => setPlatform(p.key as any)}
                style={{
                  padding: "12px 24px",
                  borderRadius: "12px",
                  border: "2px solid",
                  borderColor: platform === p.key ? "#D4AF37" : "#E5E7EB",
                  background: platform === p.key ? "#FEF7E0" : "white",
                  color: platform === p.key ? "#B8962E" : "#6B7280",
                  fontWeight: platform === p.key ? 700 : 500,
                  cursor: "pointer",
                  fontSize: "14px",
                  transition: "all 0.2s",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  boxShadow: platform === p.key ? "0 2px 12px rgba(212,175,55,0.15)" : "none"
                }}
              >
                <span style={{ fontSize: "20px" }}>{p.emoji}</span>
                {p.label}
              </button>
            ))}
          </div>

          {/* Steps */}
          <div style={{
            padding: "20px 24px",
            borderRadius: "14px",
            background: "#FAFBFC",
            border: "1px solid #F1F5F9",
            marginBottom: "16px"
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
              <span style={{ fontSize: "20px" }}>{platform === "ios" ? "🍎" : platform === "android" ? "🤖" : "💻"}</span>
              <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#374151", margin: 0 }}>
                ขั้นตอนสำหรับ {platformLabel} ({platformBrowser})
              </h3>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {currentSteps.map((step, i) => (
                <div key={i} style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "16px",
                  padding: "14px 18px",
                  background: "white",
                  borderRadius: "12px",
                  border: "1px solid #F1F5F9",
                  transition: "all 0.2s ease"
                }}>
                  <div style={{
                    width: "40px",
                    height: "40px",
                    borderRadius: "50%",
                    background: "linear-gradient(135deg, #0A5C8E, #1a7ab5)",
                    color: "white",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontWeight: 800,
                    fontSize: "15px",
                    flexShrink: 0
                  }}>
                    {i + 1}
                  </div>
                  <div>
                    <p style={{ margin: "0 0 2px", fontWeight: 700, color: "#111827", fontSize: "14px" }}>
                      <span style={{ marginRight: "6px" }}>{step.icon}</span>
                      {step.title}
                    </p>
                    <p style={{ margin: 0, color: "#6B7280", fontSize: "13px", lineHeight: 1.6 }}>{step.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ===== BENEFITS ===== */}
        <div style={{ background: "white", borderRadius: "16px", padding: "36px", boxShadow: "0 4px 24px rgba(0,0,0,0.06)", marginBottom: "28px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
            <Sparkles size={24} style={{ color: "#D97706" }} />
            <h2 style={{ fontSize: "22px", fontWeight: 800, color: "#111827", margin: 0 }}>ทำไมต้องติดตั้งแอป?</h2>
          </div>
          <p style={{ color: "#6B7280", fontSize: "14px", marginBottom: "24px" }}>ประสบการณ์ใช้งานที่ดีกว่าบนเบราว์เซอร์ทั่วไป</p>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px" }}>
            {benefits.map((b, i) => (
              <div key={i} style={{
                padding: "20px",
                background: "#FAFBFC",
                borderRadius: "14px",
                border: "1px solid #F1F5F9",
                transition: "all 0.3s ease"
              }}>
                <div style={{
                  width: "48px",
                  height: "48px",
                  borderRadius: "12px",
                  background: "white",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: "12px",
                  fontSize: "24px",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.04)"
                }}>
                  {b.emoji}
                </div>
                <p style={{ margin: "0 0 4px", fontWeight: 700, color: "#111827", fontSize: "15px" }}>{b.title}</p>
                <p style={{ margin: 0, color: "#6B7280", fontSize: "13px", lineHeight: 1.6 }}>{b.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* ===== BOTTOM CTA ===== */}
        <div style={{
          textAlign: "center",
          padding: "32px 0 16px",
          borderTop: "1px solid #F1F5F9"
        }}>
          <p style={{ color: "#9CA3AF", fontSize: "14px", marginBottom: "16px" }}>หรือใช้งานผ่านเบราว์เซอร์ได้เลย</p>
          <div style={{ display: "flex", gap: "12px", justifyContent: "center", flexWrap: "wrap" }}>
            <Link href="/patient/login" style={{
              background: "linear-gradient(135deg, #0A5C8E, #1a7ab5)",
              color: "white",
              padding: "12px 28px",
              borderRadius: "12px",
              textDecoration: "none",
              fontWeight: 700,
              fontSize: "14px",
              boxShadow: "0 4px 16px rgba(10,92,142,0.2)"
            }}>
              เข้าสู่ระบบผู้ป่วย →
            </Link>
            <Link href="/guide" style={{
              color: "#0A5C8E",
              textDecoration: "none",
              fontWeight: 600,
              fontSize: "14px",
              padding: "12px 28px",
              borderRadius: "12px",
              border: "1px solid #E5E7EB",
              background: "white"
            }}>
              อ่านคู่มือการใช้งาน
            </Link>
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