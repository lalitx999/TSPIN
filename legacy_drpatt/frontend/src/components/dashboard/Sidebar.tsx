"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Brain,
  Layers,
  FlaskConical,
  Calendar,
  Settings,
  LogOut,
  ChevronRight,
  Shield,
  Activity,
  ClipboardList,
  BarChart2,
  CheckCircle2,
  Mic,
  Pill,
  Sliders,
  History,
  Database,
  Cpu,
  Zap,
  Bot,
  Home,
  User,
  FileText,
  MessageCircle,
  HeartPulse,
  Award,
  ChevronDown,
  Sparkles,
  Microscope,
  Dna,
  Scan,
  TrendingUp
} from "lucide-react";

interface SidebarProps {
  role?: "patient" | "doctor" | string;
  userName?: string;
  isMobile?: boolean;
}

export default function Sidebar({ role = "patient", userName = "ผู้ป่วย", isMobile = false }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = () => {
    if (typeof window !== "undefined") {
      if (role === "doctor") {
        localStorage.removeItem("doctor_access_token");
        localStorage.removeItem("doctor_refresh_token");
      } else {
        localStorage.removeItem("patient_access_token");
        localStorage.removeItem("patient_refresh_token");
      }
    }
    router.push("/");
  };

  // ===== PATIENT SECTIONS =====
  const patientSections = [
    {
      label: "หน้าแรก",
      icon: Home,
      items: [
        { title: "แดชบอร์ดสุขภาพ", icon: LayoutDashboard, href: "/patient/dashboard", desc: "ภาพรวมสุขภาพของคุณ" },
        { title: "ประวัติการรักษา", icon: History, href: "/patient/history", desc: "บันทึกการรักษาทั้งหมด" },
        { title: "นัดหมายของฉัน", icon: Calendar, href: "/patient/appointments", desc: "ตารางนัดหมาย" },
      ]
    },
    {
      label: "AI & การประเมิน",
      icon: Brain,
      items: [
        { title: "ประเมินอาการด้วย AI", icon: MessageCircle, href: "/patient/ai-intake", desc: "แชทกับ AI พยาบาล" },
        { title: "ผลวิเคราะห์ 39 แกน", icon: Activity, href: "/patient/axes-result", desc: "ดูผลการวิเคราะห์สุขภาพ" },
        { title: "Digital Twin", icon: HeartPulse, href: "/patient/digital-twin", desc: "แบบจำลองสุขภาพของคุณ" },
      ]
    },
    {
      label: "เอกสาร & ข้อมูล",
      icon: FileText,
      items: [
        { title: "รายงานห้องแล็บ", icon: FlaskConical, href: "/patient/download", desc: "ดาวน์โหลดผลตรวจ" },
        { title: "ความยินยอมรักษา", icon: Shield, href: "/patient/consent", desc: "เอกสารยินยอม" },
        { title: "คู่มือการใช้งาน", icon: Sparkles, href: "/guide", desc: "วิธีใช้ระบบ" },
      ]
    },
    {
      label: "โปรไฟล์",
      icon: User,
      items: [
        { title: "ตั้งค่าโปรไฟล์", icon: Settings, href: "/patient/settings", desc: "แก้ไขข้อมูลส่วนตัว" },
        { title: "รางวัลสุขภาพ", icon: Award, href: "/patient/rewards", desc: "แต้มและสิทธิพิเศษ" },
      ]
    }
  ];

  // ===== DOCTOR SECTIONS (ปรับปรุงใหม่) =====
  const doctorSections = [
    {
      label: "ภาพรวม",
      icon: LayoutDashboard,
      items: [
        { title: "แดชบอร์ด", icon: LayoutDashboard, href: "/doctor/dashboard", desc: "ภาพรวมคนไข้และสถิติ" },
        { title: "รายชื่อคนไข้", icon: Users, href: "/doctor/patients", desc: "จัดการข้อมูลคนไข้ทั้งหมด" },
        { title: "นัดหมายวันนี้", icon: Calendar, href: "/doctor/appointments", desc: "ตารางนัดหมายประจำวัน" },
        { title: "ห้องตรวจ AI", icon: Brain, href: "/doctor/chats", desc: "ดูประวัติการคัดกรอง AI" },
      ]
    },
    {
      label: "การวิเคราะห์ทางคลินิก",
      icon: Microscope,
      items: [
        { title: "39 Biological Axes", icon: Activity, href: "/doctor/axes", desc: "ดูแกนสรีรวิทยาทั้งหมด" },
        { title: "Digital Twin HUD", icon: Dna, href: "/doctor/digital-twin", desc: "แบบจำลองสุขภาพคนไข้" },
        { title: "Pre-visit Intelligence", icon: Zap, href: "/doctor/pre-visit", desc: "ข้อมูลก่อนพบคนไข้" },
        { title: "Clinical Review", icon: ClipboardList, href: "/doctor/clinical-review", desc: "ทบทวนประวัติทางคลินิก" },
        { title: "Voice Clinical Form", icon: Mic, href: "/doctor/voice-form", desc: "บันทึกเสียงระหว่างตรวจ" },
        { title: "Lab Review", icon: FlaskConical, href: "/doctor/lab-review", desc: "ตรวจสอบผลแล็บ" },
        { title: "Lab OCR", icon: Scan, href: "/doctor/lab-ocr", desc: "สแกนเอกสารแล็บ" },
      ]
    },
    {
      label: "ผลลัพธ์ & การติดตาม",
      icon: TrendingUp,
      items: [
        { title: "Health Outcomes", icon: BarChart2, href: "/doctor/outcomes", desc: "ผลลัพธ์การรักษา" },
        { title: "Validations", icon: CheckCircle2, href: "/doctor/validations", desc: "การยืนยันผลการรักษา" },
        { title: "Engine Results", icon: History, href: "/doctor/engine-results", desc: "ผลการประมวลผล AI" },
      ]
    },
    {
      label: "ระบบ AI & การตั้งค่า",
      icon: Settings,
      items: [
        { title: "TSPI Brain Console", icon: Brain, href: "/doctor/tspi-brain", desc: "ศูนย์ควบคุม AI" },
        { title: "AI Settings", icon: Cpu, href: "/doctor/ai-settings", desc: "ตั้งค่าระบบ AI" },
        { title: "Clinical Automations", icon: Bot, href: "/doctor/automations", desc: "ระบบอัตโนมัติ" },
        { title: "Modules Management", icon: Pill, href: "/doctor/modules", desc: "จัดการโมดูลการรักษา" },
        { title: "Axis Weights", icon: Sliders, href: "/doctor/axis-weights", desc: "ปรับค่าน้ำหนักแกน" },
        { title: "Axes Mapping", icon: Layers, href: "/doctor/axes-mapping", desc: "จับคู่แกนกับโรค" },
        { title: "Import Framework", icon: Database, href: "/doctor/import-axes", desc: "นำเข้าโครงสร้างข้อมูล" },
      ]
    },
    {
      label: "ระบบ & ความปลอดภัย",
      icon: Shield,
      items: [
        { title: "Audit Logs", icon: Shield, href: "/doctor/audit", desc: "บันทึกการใช้งานระบบ" },
        { title: "ตั้งค่าระบบ", icon: Settings, href: "/doctor/settings", desc: "ตั้งค่าทั่วไป" },
      ]
    }
  ];

  const isDoc = role === "doctor";
  const menuSections = isDoc ? doctorSections : patientSections;
  const primaryColor = isDoc ? "#0A5C8E" : "#D4AF37";
  const primaryGradient = isDoc 
    ? "linear-gradient(135deg, #0A5C8E 0%, #1a7ab5 100%)" 
    : "linear-gradient(135deg, #D4AF37 0%, #B8962E 100%)";
  const hoverBgColor = isDoc 
    ? "rgba(10, 92, 142, 0.05)" 
    : "rgba(212, 175, 55, 0.05)";
  const roleLabel = isDoc ? "แพทย์ผู้เชี่ยวชาญ" : "ผู้ป่วย";

  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});

  useEffect(() => {
    setExpandedSections(isDoc ? {
      "ภาพรวม": true,
      "การวิเคราะห์ทางคลินิก": true,
      "ผลลัพธ์ & การติดตาม": false,
      "ระบบ AI & การตั้งค่า": false,
      "ระบบ & ความปลอดภัย": false
    } : {
      "หน้าแรก": true,
      "AI & การประเมิน": true,
      "เอกสาร & ข้อมูล": false,
      "โปรไฟล์": false
    });
  }, [role]);

  const toggleSection = (label: string) => {
    setExpandedSections(prev => ({ ...prev, [label]: !prev[label] }));
  };

  // ตรวจจับหน้าปัจจุบันเพื่อไฮไลต์
  const isActivePath = (href: string) => {
    if (href === "/doctor/dashboard" || href === "/patient/dashboard") {
      return pathname === href || pathname === "/doctor" || pathname === "/patient";
    }
    return pathname === href;
  };

  return (
    <div 
      className="d-flex flex-column h-100 sidebar-content-wrapper bg-transparent"
      style={{
        // Define native CSS variables to prevent Turbopack styled-jsx interpolation hangs
        ["--sidebar-primary" as any]: primaryColor,
        ["--sidebar-gradient" as any]: primaryGradient,
        ["--sidebar-hover-bg" as any]: hoverBgColor,
      }}
    >

      {/* ===== HEADER / USER INFO ===== */}
      <div className="sidebar-header px-3 pt-3 pb-2 d-flex align-items-center gap-3 border-bottom">
        <div
          className="rounded-circle d-flex align-items-center justify-content-center flex-shrink-0"
          style={{
            width: '44px',
            height: '44px',
            background: primaryGradient,
            color: 'white',
            fontWeight: 700,
            fontSize: '18px'
          }}
        >
          {userName.charAt(0).toUpperCase()}
        </div>
        <div className="flex-grow-1 overflow-hidden">
          <div className="fw-bold text-dark" style={{ fontSize: '14px' }}>{userName}</div>
          <div className="text-muted" style={{ fontSize: '11px' }}>{roleLabel}</div>
        </div>
        <div className="status-dot-online"></div>
      </div>

      {/* ===== NAVIGATION MENU ===== */}
      <div className="sidebar-menu-wrapper flex-grow-1 px-2 overflow-auto custom-scrollbar pt-2">
        <nav>
          <ul className="nav nav-pills nav-sidebar flex-column gap-1">
            {menuSections.map((section, sectionIdx) => {
              const isExpanded = expandedSections[section.label];
              const SectionIcon = section.icon;

              return (
                <li key={sectionIdx} className="nav-item mb-1">
                  <button
                    onClick={() => toggleSection(section.label)}
                    className="nav-link border-0 bg-transparent d-flex align-items-center justify-content-between w-100 px-3 py-2 rounded-3 text-muted fw-semibold small text-uppercase tracking-wider hover-bg"
                    style={{ fontSize: '11px', letterSpacing: '0.05em' }}
                  >
                    <div className="d-flex align-items-center gap-2">
                      <SectionIcon size={14} className="text-primary-custom" />
                      <span>{section.label}</span>
                    </div>
                    <ChevronDown size={14} className={`transition-all ${isExpanded ? 'rotate-180' : ''}`} />
                  </button>

                  <ul className={`nav nav-treeview d-grid gap-1 mt-1 ps-2 transition-all overflow-hidden ${isExpanded ? 'max-h-500' : 'max-h-0'}`}>
                    {section.items.map((item, i) => {
                      const isActive = isActivePath(item.href);
                      const ItemIcon = item.icon;

                      return (
                        <li key={i} className="nav-item">
                          <Link
                            href={item.href}
                            className={`nav-link d-flex align-items-center gap-3 px-3 py-2 rounded-3 text-decoration-none transition-all ${isActive
                                ? "bg-primary-custom text-white shadow-sm active-item"
                                : "text-dark text-opacity-70 hover-item"
                              }`}
                          >
                            <ItemIcon size={18} className={isActive ? 'text-white' : 'text-primary-custom opacity-70'} />
                            <div className="d-flex flex-column">
                              <span className="small fw-medium" style={{ fontSize: '13px' }}>{item.title}</span>
                              {item.desc && (
                                <span className="text-muted" style={{ fontSize: '10px' }}>{item.desc}</span>
                              )}
                            </div>
                          </Link>
                        </li>
                      );
                    })}
                  </ul>
                </li>
              );
            })}
          </ul>
        </nav>
      </div>

      {/* ===== FOOTER ===== */}
      <div className="sidebar-footer p-3 border-top mt-auto d-flex flex-column gap-2">
        <Link
          href={isDoc ? "/doctor/settings" : "/patient/settings"}
          className="nav-link d-flex align-items-center gap-3 px-3 py-2 text-muted text-decoration-none hover-item rounded-3"
        >
          <Settings size={18} className="text-muted" />
          <span className="small fw-medium">{isDoc ? "ตั้งค่าระบบ" : "ตั้งค่าโปรไฟล์"}</span>
        </Link>

        <button
          onClick={handleLogout}
          className="btn btn-link nav-link d-flex align-items-center gap-3 px-3 py-2 text-danger text-decoration-none hover-logout rounded-3 border-0 text-start w-100"
        >
          <LogOut size={18} className="text-danger" />
          <span className="small fw-medium">ออกจากระบบ</span>
        </button>

        <div className="text-center text-muted mt-1" style={{ fontSize: '9px' }}>
          {isDoc ? "TSPI Clinic Doctor v2.0" : "TSPI Clinic v2.0"}
        </div>
      </div>

      <style jsx>{`
        .sidebar-content-wrapper { 
          height: 100%; 
          background-color: #f8f9fa;
        }
        
        .sidebar-header {
          background: white;
        }
        
        .status-dot-online {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #10b981;
          border: 2px solid white;
          box-shadow: 0 0 0 2px #10b981;
        }
        
        .hover-bg:hover { 
          background-color: var(--sidebar-hover-bg); 
          color: var(--sidebar-primary) !important; 
        }
        
        .hover-item { 
          transition: all 0.2s ease;
        }
        .hover-item:hover { 
          background-color: white; 
          box-shadow: 0 2px 8px rgba(0,0,0,0.04);
          transform: translateX(4px);
          color: var(--sidebar-primary) !important;
        }
        .hover-item:hover .text-primary-custom {
          color: var(--sidebar-primary) !important;
        }
        
        .hover-logout:hover {
          background-color: rgba(220, 53, 69, 0.05) !important;
          color: #dc3545 !important;
          transform: translateX(4px);
        }
        
        .rotate-180 { transform: rotate(180deg); }
        .max-h-0 { 
          max-height: 0; 
          opacity: 0; 
          pointer-events: none; 
          padding: 0;
        }
        .max-h-500 { 
          max-height: 500px; 
          opacity: 1; 
        }
        .transition-all { 
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); 
        }
        
        .active-item { 
          font-weight: 600 !important; 
          border-left: 3px solid var(--sidebar-primary);
          border-radius: 0 8px 8px 0 !important;
          margin-left: -0.5rem;
          padding-left: 1rem !important;
          background: var(--sidebar-gradient) !important;
        }
        .active-item .text-primary-custom {
          color: white !important;
        }
        
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { 
          background: rgba(0, 0, 0, 0.05); 
          border-radius: 10px; 
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(0, 0, 0, 0.1);
        }
      `}</style>

    </div>
  );
}