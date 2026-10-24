"use client";

import { useState, useEffect } from "react";
import Sidebar from "@/components/dashboard/Sidebar";
import { Menu, X, Bell, User, Shield, Home, MessageSquare, Calendar, Settings, History, Download } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
// Firebase Auth connection removed. Converted to Django + PostgreSQL.

const DJANGO_BASE = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";

export default function PatientLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [user, setUser] = useState<any>(null);
  const [patientData, setPatientData] = useState<any>(null);
  const [deferredInstallPrompt, setDeferredInstallPrompt] = useState<any>(null);
  const [showInstallBadge, setShowInstallBadge] = useState(false);

  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [pathname]);

  const isAuthPage = pathname === "/patient/login" || pathname === "/patient/register";

  useEffect(() => {
    const checkAuth = async () => {
      if (typeof window === "undefined") return;
      const token = localStorage.getItem("patient_access_token");
      if (!token) {
        setUser(null);
        setPatientData(null);
        if (!isAuthPage) {
          router.push("/");
        }
        return;
      }

      try {
        const res = await fetch(`${DJANGO_BASE}/api/auth/me/`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        if (res.ok) {
          const data = await res.json();
          setUser({ uid: String(data.id_card), displayName: data.first_name });
          setPatientData({
            id: data.id,
            fname: data.first_name,
            lname: data.last_name,
            hn: data.hn,
            phone: data.phone,
            email: data.email,
            gender: data.gender,
            birth_date: data.birth_date,
            ...data
          });
        } else {
          localStorage.removeItem("patient_access_token");
          setUser(null);
          setPatientData(null);
          if (!isAuthPage) {
            router.push("/");
          }
        }
      } catch (err) {
        console.error("Failed to load patient profile from Django:", err);
        if (!isAuthPage) {
          router.push("/");
        }
      }
    };

    checkAuth();
  }, [isAuthPage, router]);

  // PWA Install Prompt
  useEffect(() => {
    const handleBeforeInstall = (e: Event) => {
      e.preventDefault();
      setDeferredInstallPrompt(e);
      setShowInstallBadge(true);
    };
    window.addEventListener("beforeinstallprompt", handleBeforeInstall);
    window.addEventListener("appinstalled", () => {
      setShowInstallBadge(false);
      setDeferredInstallPrompt(null);
    });
    return () => window.removeEventListener("beforeinstallprompt", handleBeforeInstall);
  }, []);

  const handleInstallApp = async () => {
    if (!deferredInstallPrompt) {
      window.open("/install", "_blank");
      return;
    }
    deferredInstallPrompt.prompt();
    const { outcome } = await deferredInstallPrompt.userChoice;
    if (outcome === "accepted") setShowInstallBadge(false);
  };

  // Hide sidebar and header for non-authenticated pages or explicitly on login/register
  const showBars = !isAuthPage && user;
  const isChatPage = pathname === "/patient/ai-intake";
  const showHeader = showBars && !isChatPage;

  const patientName = patientData 
    ? `${patientData.fname || ""} ${patientData.lname || ""}`.trim() 
    : (user?.displayName || "คนไข้");

  return (
    <div className="d-flex vh-100 overflow-hidden font-sans" style={{ backgroundColor: '#F6F6F6' }}>
      {/* Desktop Sidebar Container */}
      {showBars && (
        <aside className="d-none d-lg-block shadow-sm h-100 sticky-top border-end animate-fade-in" style={{ width: '280px', backgroundColor: 'var(--drpat-card)', zIndex: 1040 }}>
          {/* Branding Area for Patient Portal */}
          <div className="border-bottom px-4 d-flex align-items-center bg-white" style={{ height: '64px' }}>
            <Link href="/" className="d-flex align-items-center gap-3 text-decoration-none">
              <div className="bg-primary-custom shadow-sm rounded-circle d-flex align-items-center justify-content-center" style={{ width: '34px', height: '34px' }}>
                <Shield size={18} className="text-white" />
              </div>
              <span className="fw-bold text-dark fs-5 mb-0">TSPI <span className="text-primary-custom">Clinic</span></span>
            </Link>
          </div>
          <Sidebar role="patient" userName={patientName} />
        </aside>
      )}

      {/* Main Content Container */}
      <div className="flex-grow-1 d-flex flex-column h-100 position-relative">

        {/* Header Area (Only shown on Desktop, since mobile has dashboard greeting header) */}
        {showHeader && (
          <div className="bg-white border-bottom px-4 py-3 d-none d-lg-flex align-items-center justify-content-between sticky-top shadow-xs animate-fade-in">
            <div className="d-flex align-items-center gap-3">
              <div className="d-flex flex-column">
                <h5 className="fw-bold mb-0 text-dark">Patient Portal</h5>
                <p className="tiny text-muted mb-0">ดูแลสุขภาพอัจฉริยะแบบเจาะจงบุคคล</p>
              </div>
            </div>
            <div className="d-flex align-items-center gap-3">
              <button className="btn btn-light rounded-circle p-2 position-relative shadow-sm border">
                <Bell size={20} className="text-muted" />
                <span className="position-absolute top-0 start-100 translate-middle p-1 bg-danger border border-white rounded-circle"></span>
              </button>
              <div className="d-flex align-items-center gap-3 border-start ps-3">
                <div className="text-end">
                  <p className="small fw-bold mb-0 text-dark">{patientName}</p>
                  <p className="tiny text-primary-custom mb-0 text-uppercase fw-bold tracking-wider">Member ID: TSPI-{patientData?.hn || user?.uid?.slice(0, 4)}</p>
                </div>
                <div className="bg-primary-custom bg-opacity-10 border border-primary-custom border-opacity-20 rounded-circle text-primary-custom d-flex align-items-center justify-content-center fw-bold shadow-sm" style={{ width: '42px', height: '42px' }}>
                  <User size={20} />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Mobile Sidebar Slide-out (Preserved for backup/desktop settings menu) */}
        {showBars && (
          <div className={`d-lg-none position-fixed inset-0 mobile-sidebar-overlay ${isMobileMenuOpen ? 'active' : ''}`} style={{ zIndex: 1050 }}>
            <div className="backdrop-dim" onClick={() => setIsMobileMenuOpen(false)}></div>
            <div className={`sidebar-slide-content h-100 shadow-2xl ${isMobileMenuOpen ? 'show' : ''}`} style={{ width: '280px' }}>
              <Sidebar role="patient" userName={patientName} isMobile={true} />
              <button
                onClick={() => setIsMobileMenuOpen(false)}
                className="position-absolute top-0 end-0 m-3 btn btn-dark rounded-circle p-2 border border-white border-opacity-10 shadow-lg"
                style={{ zIndex: 1200 }}
              >
                <X size={20} className="text-white" />
              </button>
            </div>
          </div>
        )}

        {/* Page Content */}
        <main className={`flex-grow-1 ${isChatPage ? "overflow-hidden d-flex flex-column h-100" : "overflow-auto"}`} style={{ backgroundColor: '#F6F6F6' }}>
          {children}
          {/* Spacer to prevent content cut-off by the bottom nav bar on mobile */}
          {showBars && !isChatPage && <div className="d-lg-none" style={{ height: '85px' }}></div>}
        </main>

        {/* Mobile Bottom Navigation Bar (App Shell style) */}
        {showBars && !isChatPage && (
          <nav className="d-lg-none fixed-bottom bg-white border-top d-flex justify-content-around align-items-center shadow-lg" style={{ height: '70px', zIndex: 1040, borderTopLeftRadius: '24px', borderTopRightRadius: '24px', paddingBottom: 'env(safe-area-inset-bottom)' }}>
            {[
              { label: "Home", href: "/patient/dashboard", icon: Home },
              { label: "นัดหมาย", href: "/patient/appointments", icon: Calendar },
              { label: "AI", href: "/patient/ai-intake", icon: MessageSquare },
              { label: "ประวัติ", href: "/patient/history", icon: History },
              { label: "เมนู", isDrawer: true, icon: Menu },
            ].map((item, idx) => {
              const isActive = item.isDrawer ? isMobileMenuOpen : pathname === item.href;
              
              if (item.isDrawer) {
                return (
                  <button
                    key={idx}
                    onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                    className="d-flex flex-column align-items-center text-decoration-none border-0 bg-transparent py-2"
                    style={{ width: showInstallBadge ? '16%' : '20%', color: isActive ? '#282A29' : '#9CA3AF', transition: 'all 0.2s', outline: 'none' }}
                  >
                    <item.icon size={22} style={{ strokeWidth: isActive ? 2.5 : 2 }} />
                    <span style={{ fontSize: '10px', fontWeight: isActive ? 700 : 500, marginTop: '4px', fontFamily: 'sans-serif', letterSpacing: '0.2px' }}>
                      {item.label}
                    </span>
                  </button>
                );
              }

              return (
                <Link
                  key={idx}
                  href={item.href || "#"}
                  className="d-flex flex-column align-items-center text-decoration-none border-0 bg-transparent py-2"
                  style={{ width: showInstallBadge ? '16%' : '20%', color: isActive ? '#282A29' : '#9CA3AF', transition: 'all 0.2s' }}
                >
                  <item.icon size={22} style={{ strokeWidth: isActive ? 2.5 : 2 }} />
                  <span style={{ fontSize: '10px', fontWeight: isActive ? 700 : 500, marginTop: '4px', fontFamily: 'sans-serif', letterSpacing: '0.2px' }}>
                    {item.label}
                  </span>
                </Link>
              );
            })}
            {showInstallBadge && (
              <button
                onClick={handleInstallApp}
                className="d-flex flex-column align-items-center border-0 bg-transparent py-2 position-relative"
                style={{ width: '16%', color: '#0A5C8E', transition: 'all 0.2s', cursor: 'pointer' }}
              >
                <span className="position-absolute top-0 start-50 translate-middle-x badge rounded-pill bg-danger" style={{ fontSize: '8px', padding: '2px 4px' }}>ใหม่</span>
                <Download size={22} style={{ strokeWidth: 2 }} />
                <span style={{ fontSize: '10px', fontWeight: 600, marginTop: '4px', fontFamily: 'sans-serif' }}>ติดตั้งแอป</span>
              </button>
            )}
          </nav>
        )}
      </div>

    </div>
  );
}
