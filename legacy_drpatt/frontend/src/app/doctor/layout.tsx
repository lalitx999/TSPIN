"use client";

import { useState, useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
// Firebase Auth connection removed. Converted to Django + PostgreSQL.
import {
  LayoutDashboard, Users, Calendar, MessageSquare,
  Activity, Brain, History, Layers, FlaskConical,
  Microscope, Database, Network, Sliders,
  Cpu, Zap, Trophy, ClipboardCheck, Boxes,
  ShieldCheck, Bot, Settings, LogOut, ChevronLeft,
  ChevronRight, Bell, Search, Menu, Scan, FileText
} from "lucide-react";

import "./theme-inapp.css";

export default function DoctorLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isClient, setIsClient] = useState(false);
  const [doctor, setDoctor] = useState<any>(null);

  useEffect(() => {
    setIsClient(true);

    const checkDoctorAuth = async () => {
      if (typeof window === "undefined") return;
      const isAuthPage = pathname === "/doctor/login" || pathname === "/doctor/register";
      if (isAuthPage) return;

      const token = localStorage.getItem("doctor_access_token");
      if (!token) {
        router.push("/doctor/login");
        return;
      }

      try {
        const apiBase = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";
        const base = apiBase.replace(/\/+$/, "").replace(/\/api$/, "");
        const res = await fetch(`${base}/api/auth/doctor/me/`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        if (res.ok) {
          const data = await res.json();
          setDoctor(data);
        } else {
          localStorage.removeItem("doctor_access_token");
          router.push("/doctor/login");
        }
      } catch (err) {
        console.error("Failed to load doctor profile:", err);
        router.push("/doctor/login");
      }
    };

    checkDoctorAuth();
  }, [router, pathname]);

  const handleLogout = async () => {
    localStorage.removeItem("doctor_access_token");
    localStorage.removeItem("doctor_refresh_token");
    router.push("/doctor/login");
  };

  const navGroups = [
    {
      title: "Clinical Operations",
      items: [
        { name: "Dashboard", href: "/doctor/dashboard", icon: LayoutDashboard },
        { name: "Patient Registry", href: "/doctor/patients", icon: Users },
        { name: "Appointments", href: "/doctor/appointments", icon: Calendar },
        { name: "Clinical Chats", href: "/doctor/chats", icon: MessageSquare },
      ]
    },
    {
      title: "Precision Medicine",
      items: [
        { name: "Digital Twin", href: "/doctor/digital-twin", icon: Activity },
        { name: "AI Physician", href: "/doctor/ai-physician", icon: Brain },
        { name: "Precision Report", href: "/doctor/precision-report", icon: FileText },
        { name: "Lab OCR Scanner", href: "/doctor/lab-ocr", icon: Scan },
        { name: "Biological Timeline", href: "/doctor/axis-timeline", icon: History },
        { name: "Therapeutic Matrix", href: "/doctor/therapeutic-matrix", icon: Layers },
        { name: "Lab Review", href: "/doctor/lab-review", icon: FlaskConical },
      ]
    },
    {
      title: "Mechanistic Analysis",
      items: [
        { name: "Clinical Review", href: "/doctor/clinical-review", icon: Microscope },
        { name: "36 Axes Explorer", href: "/doctor/axes", icon: Database },
        { name: "Axis Graph", href: "/doctor/axis-graph", icon: Network },
        { name: "Axis Weights", href: "/doctor/axis-weights", icon: Sliders },
      ]
    },
    {
      title: "AI Engine",
      items: [
        { name: "TSPI Brain Console", href: "/doctor/tspi-brain", icon: Brain },
        { name: "Voice AI", href: "/doctor/voice-form", icon: Cpu },
        { name: "Automations", href: "/doctor/automations", icon: Zap },
        { name: "Knowledge RAG", href: "/doctor/knowledge-rag", icon: Database },
        { name: "Engine History", href: "/doctor/engine-results", icon: History },
        { name: "Outcomes", href: "/doctor/outcomes", icon: Trophy },
        { name: "Validations", href: "/doctor/validations", icon: ClipboardCheck },
      ]
    },
    {
      title: "System",
      items: [
        { name: "Module Registry", href: "/doctor/modules", icon: Boxes },
        { name: "Audit Trail", href: "/doctor/audit", icon: ShieldCheck },
        { name: "AI Settings", href: "/doctor/ai-settings", icon: Bot },
        { name: "Settings", href: "/doctor/settings", icon: Settings },
      ]
    }
  ];

  if (!isClient) return null;

  const isAuthPage = pathname === "/doctor/login" || pathname === "/doctor/register";

  if (isAuthPage) {
    return <div className="bg-secondary-custom font-kanit min-vh-100">{children}</div>;
  }

  return (
    <div className="inapp-root">
      {/* Mobile Overlay */}
      {mobileOpen && (
        <div
          className="mobile-overlay"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* ==================== SIDEBAR ==================== */}
      <aside className={`inapp-sidebar ${collapsed ? 'collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`}>
        {/* Logo */}
        <div className="sidebar-logo-area">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div className="sidebar-logo-box">T</div>
            {!collapsed && (
              <div>
                <div style={{ fontWeight: 600, fontSize: '18px', color: '#1F2937' }}>TSPI Clinic</div>
                <div style={{ fontSize: '10px', color: '#9CA3AF', letterSpacing: '0.5px' }}>PRECISION MEDICINE</div>
              </div>
            )}
          </div>

          {!collapsed && (
            <button
              onClick={() => setCollapsed(true)}
              className="sidebar-collapse-btn"
            >
              <ChevronLeft size={18} />
            </button>
          )}
        </div>

        {/* Expand button when collapsed */}
        {collapsed && (
          <button
            onClick={() => setCollapsed(false)}
            className="sidebar-expand-btn"
          >
            <ChevronRight size={14} />
          </button>
        )}

        {/* Navigation */}
        <nav className="sidebar-nav">
          {navGroups.map((group, idx) => (
            <div key={idx}>
              {!collapsed && (
                <div className="sidebar-section-title">{group.title}</div>
              )}
              {group.items.map((item) => {
                const isActive = pathname === item.href;
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`nav-link ${isActive ? 'active' : ''} ${collapsed ? 'nav-link-collapsed' : ''}`}
                    title={collapsed ? item.name : undefined}
                    onClick={() => setMobileOpen(false)}
                  >
                    <Icon size={18} />
                    {!collapsed && <span>{item.name}</span>}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        {/* Profile */}
        <div className="sidebar-profile">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', justifyContent: collapsed ? 'center' : 'flex-start' }}>
            <div className="profile-avatar">DR</div>
            {!collapsed && (
              <>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 500, fontSize: '14px', color: '#1F2937' }}>{doctor?.name || "Dr. Phat Jitdee"}</div>
                  <div style={{ fontSize: '11px', color: '#059669' }}>{doctor ? "Verified Physician" : "Loading..."}</div>
                </div>
                <button 
                  onClick={handleLogout}
                  style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#9CA3AF' }}
                  title="ออกจากระบบ"
                >
                  <LogOut size={16} />
                </button>
              </>
            )}
          </div>
        </div>
      </aside>

      {/* ==================== MAIN CONTENT ==================== */}
      {/* Single wrapper — CSS class handles the margin, no inline marginLeft */}
      <div className={`inapp-main ${collapsed ? 'collapsed' : ''}`}>
        {/* Topbar */}
        <header className={`inapp-topbar ${collapsed ? 'collapsed' : ''}`}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flex: 1 }}>
            {/* Mobile menu button */}
            <button
              className="mobile-menu-btn"
              onClick={() => setMobileOpen(true)}
            >
              <Menu size={20} />
            </button>

            <div className="search-bar">
              <Search size={16} style={{ color: '#9CA3AF' }} />
              <input type="text" placeholder="Global Clinical Search..." />
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <button className="topbar-action-btn">
              <Bell size={18} />
            </button>
            <div style={{ paddingLeft: '16px', borderLeft: '1px solid #E5E7EB' }}>
              <div style={{ fontSize: '12px', fontWeight: 500 }}>TSPI Hub 01</div>
              <div style={{ fontSize: '10px', color: '#059669' }}>● Online</div>
            </div>
          </div>
        </header>

        {/* Page Content — padding-top pushes below topbar */}
        <main className="inapp-content">
          <div className="content-container">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
