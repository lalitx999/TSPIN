"use client";

import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { useLiff } from "@/components/providers/LiffProvider";
import {
  Menu,
  X,
  ArrowRight,
  Activity,
  Sparkles,
  Brain,
  ChevronRight,
  FileText,
  LayoutGrid,
  Shield,
  Clock,
  Users,
  Star,
  TrendingUp,
  Microscope,
  CircleCheck,
  GraduationCap,
  Globe,
  Mail,
  Phone,
  MapPin,
  Stethoscope,
  LogIn,
  FlaskConical,
  HeartPulse,
  Zap,
  CreditCard,
  Award,
  Target,
  BarChart3,
  CheckCircle2,
  ArrowUpRight,
  PlayCircle,
  PhoneCall,
  MessageCircle,
  CalendarDays,
  Pill,
  Syringe,
  Bone,
  Dna,
  Leaf,
  Moon,
  Sun,
  Droplets,
  Waves,
  Wind,
  Flame,
  Snowflake,
  UserPlus  // <-- เพิ่มตรงนี้
} from "lucide-react";

export default function Home() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [djangoUser, setDjangoUser] = useState<any>(null);
  const { liff, isLoggedIn, profile } = useLiff();
  const router = useRouter();

  // Django patient profile check
  useEffect(() => {
    const checkDjangoAuth = async () => {
      const token = localStorage.getItem("patient_access_token");
      if (!token) {
        setCheckingAuth(false);
        return;
      }
      try {
        const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const res = await fetch(`${apiBase}/api/auth/me/`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        if (res.ok) {
          const data = await res.json();
          setDjangoUser({
            id: data.id,
            displayName: `${data.first_name || ""} ${data.last_name || ""}`.trim() || "คนไข้"
          });
        } else {
          localStorage.removeItem("patient_access_token");
        }
      } catch (err) {
        console.error("Failed to fetch patient profile:", err);
      } finally {
        setCheckingAuth(false);
      }
    };
    checkDjangoAuth();
  }, []);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Protocol steps data
  const protocolSteps = [
    { step: "01", phase: "Phase 1", title: "Deep Assessment", desc: "วิเคราะห์เชิงลึกด้วย AI 36 แกน", icon: <Microscope size={24} /> },
    { step: "02", phase: "Phase 1", title: "Detoxification", desc: "กำจัดสารพิษระดับเซลล์", icon: <Droplets size={24} /> },
    { step: "03", phase: "Phase 1", title: "Gut Restoration", desc: "ฟื้นฟูสมดุลลำไส้", icon: <Leaf size={24} /> },
    { step: "04", phase: "Phase 2", title: "Metabolic Reset", desc: "ปรับสมดุลระบบเผาผลาญ", icon: <Flame size={24} /> },
    { step: "05", phase: "Phase 2", title: "Hormonal Balance", desc: "ปรับสมดุลฮอร์โมน", icon: <Waves size={24} /> },
    { step: "06", phase: "Phase 2", title: "Immune Modulation", desc: "ปรับสมดุลภูมิคุ้มกัน", icon: <Shield size={24} /> },
    { step: "07", phase: "Phase 3", title: "Cellular Repair", desc: "ซ่อมแซมระดับเซลล์", icon: <Dna size={24} /> },
    { step: "08", phase: "Phase 3", title: "Neuroplasticity", desc: "ฟื้นฟูระบบประสาท", icon: <Brain size={24} /> },
    { step: "09", phase: "Phase 3", title: "Longevity Protocol", desc: "ดูแลสุขภาพระยะยาว", icon: <Sparkles size={24} /> },
  ];

  // Features data
  const features = [
    { icon: <HeartPulse size={20} />, text: "Personalized protocols" },
    { icon: <Activity size={20} />, text: "Real-time monitoring" },
    { icon: <Microscope size={20} />, text: "Evidence-based modules" },
    { icon: <Brain size={20} />, text: "24/7 AI clinical support" }
  ];

  // Stats data
  const stats = [
    { number: "10k+", label: "Patients" },
    { number: "38", label: "Bio-Axes" },
    { number: "98%", label: "Success" }
  ];

  return (
    <div className="bg-white">
      {/* ========== NAVIGATION ========== */}
      <nav
        className={`fixed-top transition-all duration-300 ${scrolled ? "nav-premium shadow-sm py-2" : "nav-premium py-3"}`}
        style={{ zIndex: 1100 }}
      >
        <div className="container d-flex align-items-center justify-content-between">
          <Link href="/" className="d-flex align-items-center gap-2 text-decoration-none">
            <div className="overflow-hidden rounded-3 shadow-sm" style={{ width: '40px', height: '40px' }}>
              <img src="/logo_tspi.jpg" alt="TSPI Logo" className="w-100 h-100 object-fit-cover" />
            </div>
            <div>
              <span className={`h5 fw-bold mb-0 d-block ${scrolled ? "text-dark" : "text-dark"}`}>
                TSPI <span className="text-primary-custom">CLINIC</span>
              </span>
              <p className="small text-muted mb-0" style={{ fontSize: '10px' }}>Systems Biology AI Expert</p>
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
                className="text-decoration-none text-dark fw-medium small hover-primary"
                style={{ fontSize: '0.85rem', fontWeight: '500' }}
              >
                {item.label}
              </Link>
            ))}
            <div className="d-flex gap-2 ms-3">
              <Link
                href="/patient/login"
                className="btn btn-gold btn-sm px-4 shadow-sm text-decoration-none d-flex align-items-center justify-content-center"
                style={{ fontSize: '13px', borderRadius: '10px' }}
              >
                เข้าสู่ระบบ
              </Link>
            </div>
          </div>

          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="btn d-md-none border-0 p-2"
            style={{ color: 'var(--drpat-primary-dark)' }}
          >
            {mobileMenuOpen ? <X size={28} /> : <Menu size={28} />}
          </button>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="mobile-menu-container d-md-none animate-fade-in">
            <div className="d-grid gap-3 text-center">
              {[
                { label: "แพลตฟอร์ม", href: "/platform" },
                { label: "โปรโตคอล", href: "/protocol" },
                { label: "งานวิจัย", href: "/research" },
                { label: "เกี่ยวกับเรา", href: "/about" },
                { label: "คู่มือการใช้งาน", href: "/guide" },
                { label: "ดาวน์โหลดแอป", href: "/install" },
              ].map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="text-decoration-none text-dark fw-bold py-2 border-bottom border-light"
                  style={{ fontSize: '1rem' }}
                >
                  {item.label}
                </Link>
              ))}
              <div className="d-grid gap-2 mt-2 px-3">
                <Link
                  href="/patient/login"
                  className="btn btn-gold shadow-sm text-decoration-none fw-bold py-3"
                  style={{ borderRadius: '12px' }}
                >
                  เข้าสู่ระบบคนไข้
                </Link>
              </div>
            </div>
          </div>
        )}
      </nav>

      {/* ========== HERO SECTION ========== */}
      <section className="hero-section">
        <div className="container position-relative" style={{ paddingTop: '6rem', paddingBottom: '4rem' }}>
          <div className="row align-items-center g-5">
            <div className="col-lg-6 text-center text-lg-start">
              <div className="hero-badge mb-4 mx-auto mx-lg-0">
                <Sparkles size={14} />
                <span>Next-Generation Healthcare AI</span>
              </div>

              <h1 className="hero-title mb-4">
                {djangoUser ? (
                  <>สวัสดีคุณ <span className="highlight">{djangoUser.displayName}</span></>
                ) : isLoggedIn && profile ? (
                  <>สวัสดีคุณ <span className="highlight">{profile.displayName}</span></>
                ) : (
                  <>
                    ดูแลสุขภาพด้วย <br />
                    <span className="highlight">TSPI CLINIC AI</span>
                  </>
                )}
              </h1>

              <p className="hero-subtitle mb-4 mx-auto mx-lg-0">
                ยินดีต้อนรับสู่ระบบ <strong>TSPI CLINIC™</strong> นวัตกรรมการรักษายุคใหม่
                วิเคราะห์เชิงลึกด้วยกลไกชีววิทยา 38 แกน เพื่อผลลัพธ์ที่แม่นยำที่สุด
              </p>

              <div className="d-flex flex-wrap gap-3 justify-content-center justify-content-lg-start mb-5">
                <Link
                  href="/patient/login"
                  className="btn btn-gold btn-gold-lg"
                >
                  <CreditCard size={20} />
                  เข้าสู่ระบบสำหรับคนไข้
                </Link>
                <Link
                  href="/patient/register"
                  className="btn btn-gold-outline btn-gold-lg"
                >
                  <UserPlus size={20} />
                  ลงทะเบียนใหม่
                </Link>
              </div>

              <div className="hero-stats justify-content-center justify-content-lg-start">
                {stats.map((stat, index) => (
                  <div key={index} className="stat-item">
                    <div className="stat-number">{stat.number}</div>
                    <div className="stat-label">{stat.label}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="col-lg-6">
              <div className="hero-image-wrapper">
                <img
                  src="/images/hero.png"
                  alt="Medical AI"
                  className="img-fluid w-100"
                  style={{ display: 'block' }}
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ========== 9-STEP PROTOCOL ========== */}
      <section className="py-5 bg-white">
        <div className="container py-lg-5">
          <div className="text-center mb-5">
            <div className="section-badge mx-auto mb-3">Clinical Protocol</div>
            <h2 className="section-title mb-3">TSPI CLINIC 9-Step Recovery Protocol</h2>
            <p className="section-subtitle mx-auto">
              มาตรฐานการดูแลรักษาที่เน้นการกำจัดสาเหตุระดับกลไก (Mechanistic) เพื่อการฟื้นฟูสุขภาพอย่างยั่งยืน
            </p>
          </div>

          <div className="row g-4 mt-2">
            {protocolSteps.map((item, i) => (
              <div key={i} className="col-12 col-sm-6 col-lg-4">
                <div className="protocol-card animate-fade-in-up" style={{ animationDelay: `${i * 0.05}s` }}>
                  <span className="step-number">{item.step}</span>
                  <div className="protocol-icon">{item.icon}</div>
                  <span className="phase-badge">{item.phase}</span>
                  <h4 className="protocol-title mt-2">{item.title}</h4>
                  <p className="protocol-desc">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ========== WHY US / CLINICAL VALIDATION ========== */}
      <section className="py-5 bg-secondary-custom">
        <div className="container py-lg-5 px-4">
          <div className="row align-items-center g-5">
            <div className="col-lg-6 text-center text-lg-start">
              <div className="section-badge mb-3">Why TSPI Clinic</div>
              <h2 className="section-title mb-4">Precision Medicine <br />Reimagined</h2>
              <p className="section-subtitle mb-4" style={{ maxWidth: '100%' }}>
                เราใช้เทคโนโลยี AI วิเคราะห์ข้อมูลสุขภาพเชิงลึกผ่าน 38 แกนกลไกชีววิทยา เพื่อสร้างแผนการรักษาที่แม่นยำที่สุดสำหรับคนไข้รายบุคคล
              </p>

              <div className="row g-3">
                {features.map((item, i) => (
                  <div key={i} className="col-12 col-sm-6">
                    <div className="feature-card">
                      <div className="feature-icon">{item.icon}</div>
                      <span className="feature-text">{item.text}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="col-lg-6">
              <div className="bg-white p-4 p-lg-5 rounded-5 shadow-lg border-0">
                <div className="d-flex align-items-center gap-3 mb-4">
                  <div className="feature-icon" style={{ width: '48px', height: '48px', borderRadius: '14px' }}>
                    <GraduationCap size={24} />
                  </div>
                  <div>
                    <h5 className="fw-bold mb-0" style={{ fontSize: '1.1rem' }}>AI Clinical Validation</h5>
                    <p className="text-muted mb-0" style={{ fontSize: '0.8rem' }}>Certified Medical AI System</p>
                  </div>
                </div>
                <hr />
                <div className="mt-4">
                  {[
                    { label: "Accuracy Rate", val: "97.8%" },
                    { label: "Patient Satisfaction", val: "96.2%" },
                    { label: "Recovery Timeline", val: "43%" }
                  ].map((stat, i) => (
                    <div key={i} className="mb-3 mb-lg-4">
                      <div className="d-flex justify-content-between mb-2">
                        <span className="text-muted" style={{ fontSize: '0.75rem', fontWeight: '600' }}>{stat.label}</span>
                        <span style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--drpat-primary-dark)' }}>{stat.val}</span>
                      </div>
                      <div className="progress-premium">
                        <div className="progress-bar-premium h-100" style={{ width: stat.val }}></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ========== CTA BANNER ========== */}
      <section className="container py-5 my-5">
        <div className="cta-banner-modern text-center">
          <div className="position-relative" style={{ zIndex: 1 }}>
            <h2 className="cta-title mb-3">พร้อมเริ่มต้นการรักษาของคุณหรือยัง?</h2>
            <p className="cta-subtitle mx-auto mb-4">
              เข้าร่วมกับผู้ป่วยมากกว่า 10,000 รายที่ไว้วางใจ TSPI CLINIC AI ให้ดูแลสุขภาพของคุณในระยะยาว
            </p>
            <Link
              href="/patient/login"
              className="btn btn-gold btn-gold-lg"
              style={{ fontSize: '1rem' }}
            >
              <CreditCard size={20} />
              เข้าสู่ระบบสำหรับคนไข้
            </Link>
          </div>
        </div>
      </section>

      {/* ========== FOOTER ========== */}
      <footer className="footer-modern">
        <div className="container">
          <div className="row g-4 mb-5">
            <div className="col-md-4">
              <div className="d-flex align-items-center gap-2 mb-4">
                <div className="overflow-hidden rounded-2" style={{ width: '32px', height: '32px' }}>
                  <img src="/logo_tspi.jpg" alt="TSPI Logo" className="w-100 h-100 object-fit-cover" />
                </div>
                <span className="h5 fw-bold mb-0" style={{ fontSize: '1.1rem' }}>
                  TSPI <span style={{ color: 'var(--drpat-primary-dark)' }}>CLINIC</span>
                </span>
              </div>
              <p className="text-muted" style={{ fontSize: '0.85rem', lineHeight: '1.7', maxWidth: '90%' }}>
                แพลตฟอร์มการแพทย์แม่นยำที่ขับเคลื่อนด้วย AI เพื่อการดูแลสุขภาพเฉพาะบุคคลที่เข้าถึงง่ายและมีประสิทธิภาพสูงสุด
              </p>
            </div>

            <div className="col-6 col-md-2">
              <h6 className="fw-bold mb-4" style={{ fontSize: '0.85rem', color: '#1a1a1a' }}>แพลตฟอร์ม</h6>
              <div className="d-flex flex-column gap-2">
                <Link href="/platform" className="footer-link">ระบบ AI 39 แกน</Link>
                <Link href="/protocol" className="footer-link">9-Step Protocol</Link>
                <Link href="/research" className="footer-link">งานวิจัย</Link>
              </div>
            </div>

            <div className="col-6 col-md-2">
              <h6 className="fw-bold mb-4" style={{ fontSize: '0.85rem', color: '#1a1a1a' }}>สนับสนุน</h6>
              <div className="d-flex flex-column gap-2">
                <Link href="/guide" className="footer-link">คู่มือการใช้งาน</Link>
                <Link href="/install" className="footer-link">ดาวน์โหลดแอป</Link>
                <Link href="/about" className="footer-link">ติดต่อเรา</Link>
                <Link href="/legal/privacy" className="footer-link">นโยบายความเป็นส่วนตัว</Link>
              </div>
            </div>

            <div className="col-md-4 text-md-end">
              <h6 className="fw-bold mb-4" style={{ fontSize: '0.85rem', color: '#1a1a1a' }}>Connect With Us</h6>
              <div className="d-flex gap-3 justify-content-md-end mb-4">
                <div className="social-icon"><Globe size={18} /></div>
                <div className="social-icon"><Mail size={18} /></div>
                <div className="social-icon"><Phone size={18} /></div>
                <div className="social-icon"><MapPin size={18} /></div>
              </div>
              <p className="text-muted" style={{ fontSize: '0.75rem', lineHeight: '1.6' }}>
                123 Clinical Center, Innovation District<br />
                Bangkok, Thailand
              </p>
            </div>
          </div>

          <hr style={{ borderColor: 'rgba(0,0,0,0.04)' }} />
          <p className="text-center text-muted mb-0 pt-4" style={{ fontSize: '0.75rem' }}>
            © 2026 TSPI Clinic Intelligence Platform. All rights reserved.
          </p>
        </div>
      </footer>

      {/* ========== LOGIN MODAL ========== */}
      {showRoleModal && (
        <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)', zIndex: 1060 }}>
          <div className="modal-dialog modal-dialog-centered" style={{ maxWidth: '480px' }}>
            <div className="modal-content border-0 rounded-4 p-4 overflow-hidden position-relative" style={{ boxShadow: '0 30px 60px rgba(0,0,0,0.15)' }}>
              <div className="position-absolute top-0 end-0 p-3">
                <button
                  onClick={() => setShowRoleModal(false)}
                  className="btn btn-light rounded-circle p-2 d-flex align-items-center justify-content-center"
                  style={{ width: '36px', height: '36px', border: 'none' }}
                >
                  <X size={18} />
                </button>
              </div>
              <div className="text-center mb-4 mt-2">
                <div className="rounded-circle d-inline-flex p-4 mb-3" style={{ background: 'rgba(212,175,55,0.08)' }}>
                  <LogIn size={40} style={{ color: 'var(--drpat-primary-dark)' }} />
                </div>
                <h3 className="fw-bold mb-1" style={{ fontSize: '1.4rem' }}>เลือกประเภทผู้ใช้งาน</h3>
                <p className="text-muted" style={{ fontSize: '0.85rem' }}>กรุณาเลือกบทบาทเพื่อเข้าสู่ระบบที่เหมาะสม</p>
              </div>

              <div className="d-grid gap-3 p-2">
                <Link
                  href="/patient/login"
                  className="d-flex align-items-center gap-4 p-4 border rounded-4 text-decoration-none text-dark transition-all"
                  style={{ borderColor: 'rgba(0,0,0,0.06)', transition: 'all 0.3s ease' }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'var(--drpat-primary)';
                    e.currentTarget.style.backgroundColor = 'rgba(212,175,55,0.04)';
                    e.currentTarget.style.transform = 'scale(1.02)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'rgba(0,0,0,0.06)';
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.transform = 'scale(1)';
                  }}
                >
                  <div className="p-3 rounded-4" style={{ background: 'rgba(212,175,55,0.08)' }}>
                    <Users size={28} style={{ color: 'var(--drpat-primary-dark)' }} />
                  </div>
                  <div className="flex-grow-1">
                    <p className="fw-bold mb-0" style={{ fontSize: '0.95rem' }}>ผู้ป่วย</p>
                    <p className="text-muted mb-0" style={{ fontSize: '0.8rem' }}>ดูประวัติการรักษาและนัดหมาย</p>
                  </div>
                  <ChevronRight size={20} className="text-muted" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}