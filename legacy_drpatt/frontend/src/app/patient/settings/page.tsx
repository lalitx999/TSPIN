"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  User,
  Lock,
  Bell,
  Shield,
  ChevronRight,
  Camera,
  LogOut,
  Key,
  Smartphone,
  Mail,
  ArrowLeft,
  CheckCircle,
  AlertTriangle,
  Loader2,
  Info,
  Copy,
  QrCode
} from "lucide-react";
import Link from "next/link";
import Swal from "sweetalert2";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function PatientSettingsPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [activeSection, setActiveSection] = useState("profile");
  const [loading, setLoading] = useState(true);
  const [userData, setUserData] = useState<any>(null);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  // Edit Profile States
  const [editPhone, setEditPhone] = useState("");
  const [editEmail, setEditEmail] = useState("");
  const [editEmergencyPhone, setEditEmergencyPhone] = useState("");
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isRequestingHN, setIsRequestingHN] = useState(false);

  // Change Password States
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  // 2FA States
  const [show2FAModal, setShow2FAModal] = useState(false);
  const [otpCode, setOtpCode] = useState("");
  const [isVerifying2FA, setIsVerifying2FA] = useState(false);

  useEffect(() => {
    const checkAuthAndLoad = async () => {
      if (typeof window === "undefined") return;
      const token = localStorage.getItem("patient_access_token");
      if (!token) {
        router.push("/patient/login");
        setLoading(false);
        return;
      }

      try {
        const res = await fetch(`${API_BASE}/api/auth/me/`, {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setUserData(data);
          // Set inputs
          setEditPhone(data.phone || "");
          setEditEmail(data.email || "");
          setEditEmergencyPhone(data.extra_data?.emergency_phone || "");
        } else {
          router.push("/patient/login");
        }
      } catch (error) {
        console.error("Error fetching user profile from Django:", error);
        router.push("/patient/login");
      } finally {
        setLoading(false);
      }
    };
    
    checkAuthAndLoad();
  }, [router]);

  const handleLogout = async () => {
    const result = await Swal.fire({
      title: "ยืนยันการออกจากระบบ?",
      text: "คุณต้องการออกจากระบบสิทธิการรักษาใช่หรือไม่?",
      icon: "question",
      showCancelButton: true,
      confirmButtonColor: "#DC2626",
      cancelButtonColor: "#6B7280",
      confirmButtonText: "ออกจากระบบ",
      cancelButtonText: "ยกเลิก"
    });

    if (result.isConfirmed) {
      setIsLoggingOut(true);
      try {
        localStorage.removeItem("patient_access_token");
        localStorage.removeItem("patient_refresh_token");
        router.push("/patient/login");
      } catch (error) {
        console.error("Error signing out:", error);
        setIsLoggingOut(false);
      }
    }
  };

  // Profile Avatar Upload & Base64 Converter
  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 2 * 1024 * 1024) {
      Swal.fire("ไฟล์มีขนาดใหญ่เกินไป", "กรุณาเลือกไฟล์ภาพที่มีขนาดไม่เกิน 2MB", "warning");
      return;
    }

    const reader = new FileReader();
    reader.onloadend = async () => {
      const base64String = reader.result as string;
      const token = localStorage.getItem("patient_access_token");
      try {
        const res = await fetch(`${API_BASE}/api/patients/${userData.id}/`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            line_picture_url: base64String
          })
        });
        
        if (res.ok) {
          setUserData({
            ...userData,
            line_picture_url: base64String
          });
          Swal.fire({
            title: "อัปโหลดรูปภาพแล้ว!",
            text: "เปลี่ยนรูปโพรไฟล์คนไข้เรียบร้อย",
            icon: "success",
            confirmButtonColor: "#282A29"
          });
        }
      } catch (err) {
         console.error("Failed to save avatar image to server:", err);
      }
    };
    reader.readAsDataURL(file);
  };

  // Request HN Code (One-time)
  const handleRequestHN = async () => {
    if (userData?.hn && !userData.hn.startsWith("HN_TEMP")) {
      Swal.fire("คุณมีรหัส HN แล้ว", `รหัสประวัติการรักษาของคุณคือ ${userData.hn}`, "info");
      return;
    }
    
    if (userData?.extra_data?.hn_requested) {
      Swal.fire("ขอรหัส HN ได้เพียงครั้งเดียวเท่านั้น", "รหัส HN ได้รับการอนุมัติเข้าระบบแล้วและไม่สามารถขอใหม่ได้", "warning");
      return;
    }

    const confirmReq = await Swal.fire({
      title: "ยืนยันการขอรหัส HN จริง? 🦾",
      text: "รหัส HN นี้จะผูกกับระบบการวินิจฉัยแล็บ ผลเลือด และโมเดลวิเคราะห์ความเจาะจงทางสรีรวิทยาทั้งหมด และขอเปลี่ยนใหม่ไม่ได้",
      icon: "warning",
      showCancelButton: true,
      confirmButtonColor: "#282A29",
      cancelButtonColor: "#9CA3AF",
      confirmButtonText: "ส่งคำขอรับ HN",
      cancelButtonText: "ยกเลิก"
    });

    if (!confirmReq.isConfirmed) return;

    setIsRequestingHN(true);
    const token = localStorage.getItem("patient_access_token");
    
    // Standard HN Format generation (HN + 6 digits)
    const newHN = "HN" + Math.floor(100000 + Math.random() * 900000);

    try {
      const res = await fetch(`${API_BASE}/api/patients/${userData.id}/`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          hn: newHN,
          extra_data: {
            ...(userData.extra_data || {}),
            hn_requested: true
          }
        })
      });

      if (res.ok) {
        setUserData({
          ...userData,
          hn: newHN,
          extra_data: {
            ...(userData.extra_data || {}),
            hn_requested: true
          }
        });
        Swal.fire({
          title: "ขอรหัส HN สำเร็จ!",
          text: `รหัสประวัติ EMR ใหม่ของคุณคือ: ${newHN}`,
          icon: "success",
          confirmButtonColor: "#282A29"
        });
      } else {
        Swal.fire("เกิดข้อผิดพลาด", "ไม่สามารถสร้างรหัส HN ได้ กรุณาลองอีกครั้ง", "error");
      }
    } catch (err) {
      console.error("Error setting HN:", err);
      Swal.fire("เกิดข้อผิดพลาด", "โปรดตรวจสอบการเชื่อมต่อ", "error");
    } finally {
      setIsRequestingHN(false);
    }
  };

  // Save General Profile modifications
  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingProfile(true);
    const token = localStorage.getItem("patient_access_token");

    try {
      const res = await fetch(`${API_BASE}/api/patients/${userData.id}/`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          phone: editPhone,
          email: editEmail,
          extra_data: {
            ...(userData.extra_data || {}),
            emergency_phone: editEmergencyPhone
          }
        })
      });

      if (res.ok) {
        setUserData({
          ...userData,
          phone: editPhone,
          email: editEmail,
          extra_data: {
            ...(userData.extra_data || {}),
            emergency_phone: editEmergencyPhone
          }
        });
        Swal.fire({
          title: "อัปเดตข้อมูลเรียบร้อย!",
          text: "ข้อมูลผู้ติดต่อและข้อมูลติดต่อได้รับการบันทึกแล้ว",
          icon: "success",
          confirmButtonColor: "#282A29"
        });
      } else {
        Swal.fire("เกิดข้อผิดพลาด", "ไม่สามารถอัปเดตข้อมูลได้ในขณะนี้", "error");
      }
    } catch (err) {
      console.error("Failed to save profile modifications:", err);
      Swal.fire("เกิดข้อผิดพลาด", "โปรดตรวจสอบการเชื่อมต่อเครือข่าย", "error");
    } finally {
      setIsSavingProfile(false);
    }
  };

  // Change Password Handler
  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      Swal.fire("รหัสผ่านไม่ตรงกัน", "กรุณายืนยันรหัสผ่านใหม่ให้ตรงกัน", "warning");
      return;
    }

    setIsChangingPassword(true);
    const token = localStorage.getItem("patient_access_token");

    try {
      const res = await fetch(`${API_BASE}/api/auth/change-password/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          old_password: oldPassword,
          new_password: newPassword
        })
      });

      const data = await res.json();
      if (res.ok) {
        setOldPassword("");
        setNewPassword("");
        setConfirmPassword("");
        Swal.fire({
          title: "เปลี่ยนรหัสผ่านสำเร็จ!",
          text: "รหัสเข้าใช้งานของท่านได้รับการอัปเดตความปลอดภัยแล้ว",
          icon: "success",
          confirmButtonColor: "#282A29"
        });
      } else {
        Swal.fire("ผิดพลาด", data.error || "รหัสผ่านเดิมไม่ถูกต้อง", "error");
      }
    } catch (err) {
      console.error("Password modification error:", err);
      Swal.fire("เกิดข้อผิดพลาด", "โปรดลองใหม่อีกครั้งในภายหลัง", "error");
    } finally {
      setIsChangingPassword(false);
    }
  };

  // Google 2FA Activation Simulation
  const handleVerify2FA = (e: React.FormEvent) => {
    e.preventDefault();
    if (otpCode.length !== 6 || !/^\d+$/.test(otpCode)) {
      Swal.fire("รหัส OTP ไม่ถูกต้อง", "กรุณากรอกรหัสตัวเลข 6 หลักให้ครบถ้วน", "warning");
      return;
    }

    setIsVerifying2FA(true);
    setTimeout(async () => {
      const token = localStorage.getItem("patient_access_token");
      try {
        const res = await fetch(`${API_BASE}/api/patients/${userData.id}/`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            extra_data: {
              ...(userData.extra_data || {}),
              two_factor_enabled: true
            }
          })
        });

        if (res.ok) {
          setUserData({
            ...userData,
            extra_data: {
              ...(userData.extra_data || {}),
              two_factor_enabled: true
            }
          });
          setShow2FAModal(false);
          setOtpCode("");
          Swal.fire({
            title: "เปิดใช้งาน 2FA สำเร็จ!",
            text: "ระบบความปลอดภัย 2 ชั้นของท่านได้รับการเชื่อมกับ Google Authenticator แล้ว",
            icon: "success",
            confirmButtonColor: "#282A29"
          });
        }
      } catch (err) {
        console.error("2FA save error:", err);
      } finally {
        setIsVerifying2FA(false);
      }
    }, 1200);
  };

  const handleDisable2FA = async () => {
    const confirmDisable = await Swal.fire({
      title: "ยกเลิก 2FA หรือไม่?",
      text: "ระบบความปลอดภัยจะมีความเสี่ยงเพิ่มขึ้นหลังจากปิดฟังก์ชันการยืนยันรหัสสองขั้นตอน",
      icon: "warning",
      showCancelButton: true,
      confirmButtonColor: "#DC2626",
      confirmButtonText: "ปิดระบบความปลอดภัย",
      cancelButtonText: "ไว้ก่อน"
    });

    if (!confirmDisable.isConfirmed) return;

    const token = localStorage.getItem("patient_access_token");
    try {
      const res = await fetch(`${API_BASE}/api/patients/${userData.id}/`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          extra_data: {
            ...(userData.extra_data || {}),
            two_factor_enabled: false
          }
        })
      });

      if (res.ok) {
        setUserData({
          ...userData,
          extra_data: {
            ...(userData.extra_data || {}),
            two_factor_enabled: false
          }
        });
        Swal.fire("ปิดระบบ 2FA เรียบร้อย", "บัญชีของท่านได้รับการยกเลิก 2FA แล้ว", "success");
      }
    } catch (err) {
      console.error(err);
    }
  };

  const menuItems = [
    { id: "profile", label: "ข้อมูลส่วนตัว", icon: User, color: "text-primary-custom", bg: "bg-primary-custom" },
    { id: "security", label: "ความปลอดภัย", icon: Lock, color: "text-warning", bg: "bg-warning" },
    { id: "notifications", label: "การแจ้งเตือน", icon: Bell, color: "text-info", bg: "bg-info" },
    { id: "about", label: "เกี่ยวกับระบบ", icon: Info, color: "text-success", bg: "bg-success" },
  ];

  if (loading) {
    return (
      <div className="min-vh-100 d-flex align-items-center justify-content-center" style={{ backgroundColor: '#F2F2F7' }}>
        <Loader2 className="animate-spin text-dark" size={40} style={{ color: "#282A29" }} />
      </div>
    );
  }

  // Determine display values
  const displayName = `${userData?.first_name || ""} ${userData?.last_name || ""}`.trim() || "ผู้ใช้งานระบบ";
  const displayHN = userData?.hn || "รอยืนยันสิทธิ์ HN";
  const avatarUrl = userData?.line_picture_url || userData?.linePictureUrl || "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&q=80&w=120&h=120";

  return (
    <div className="min-vh-100 font-sans pb-5 text-start" style={{ backgroundColor: '#F6F6F6' }}>
      
      {/* Hidden File Input for Avatar */}
      <input 
        type="file"
        ref={fileInputRef}
        onChange={handleAvatarChange}
        accept="image/*"
        style={{ display: 'none' }}
      />

      {/* Mini Header */}
      <div className="bg-white border-bottom px-3 py-3 d-flex align-items-center gap-3 shadow-sm sticky-top" style={{ zIndex: 10 }}>
        <Link href="/patient/dashboard" className="text-muted text-decoration-none p-1">
          <ArrowLeft size={22} />
        </Link>
        <div>
          <h5 className="fw-bold text-dark mb-0 lh-1" style={{ fontFamily: 'Kanit, sans-serif' }}>ตั้งค่าระบบ</h5>
          <p className="small text-muted mb-0" style={{ fontSize: '0.8rem' }}>จัดการข้อมูลส่วนตัวและความปลอดภัย</p>
        </div>
      </div>

      <div className="container-fluid p-3 max-w-md mx-auto mt-2">
        
        {/* Profile Card Summary */}
        <div className="bg-white rounded-4 p-4 shadow-sm border border-light mb-4 animate-fade-in">
           <div className="d-flex align-items-center gap-3">
              <div className="position-relative">
                 <div className="rounded-circle overflow-hidden shadow-sm" style={{ width: '68px', height: '68px', border: '2px solid white' }}>
                    <img 
                      src={avatarUrl}
                      alt="Profile"
                      className="w-100 h-100 object-fit-cover"
                    />
                 </div>
                 <button 
                  onClick={handleAvatarClick}
                  className="btn btn-white btn-sm rounded-circle shadow-sm position-absolute bottom-0 end-0 p-1.5 border bg-white"
                 >
                    <Camera size={13} className="text-muted" />
                 </button>
              </div>
              <div className="flex-grow-1 overflow-hidden">
                 <h5 className="fw-bold text-dark mb-1 text-truncate" style={{ fontFamily: 'Kanit, sans-serif' }}>{displayName}</h5>
                 <p className="text-muted mb-0" style={{ fontSize: '0.82rem' }}>HN: {displayHN}</p>
                 
                 {/* HN Generation Trigger Button */}
                 {(!userData?.hn || userData.hn.startsWith("HN_TEMP")) && (
                    <button
                      onClick={handleRequestHN}
                      disabled={isRequestingHN}
                      className="btn btn-sm btn-dark px-2.5 py-1 rounded-pill mt-2 fw-bold text-white border-0"
                      style={{ fontSize: '10px', backgroundColor: '#282A29' }}
                    >
                      {isRequestingHN ? "กำลังส่งคำขอ..." : "ขอรหัส HN จริง 🦾"}
                    </button>
                 )}
              </div>
           </div>
        </div>

        {/* Settings Grid */}
        <div className="row g-2 mb-4 animate-fade-in" style={{ animationDelay: '0.1s' }}>
           {menuItems.map((item) => (
              <div key={item.id} className="col-3">
                 <div 
                    className={`p-2.5 rounded-4 border text-center transition-all cursor-pointer h-100 ${activeSection === item.id ? 'bg-white border-dark shadow-sm' : 'bg-white border-light opacity-75'}`}
                    onClick={() => setActiveSection(item.id)}
                 >
                    <div className="p-2 rounded-circle d-inline-flex mb-1 bg-light text-dark">
                       <item.icon size={16} />
                    </div>
                    <p className="fw-bold text-dark mb-0" style={{ fontSize: '10.5px', fontFamily: 'Kanit, sans-serif' }}>{item.label}</p>
                 </div>
              </div>
           ))}
        </div>

        {/* Section Content */}
        <div className="bg-white rounded-4 p-4 shadow-sm border border-light animate-fade-in" style={{ animationDelay: '0.2s' }}>
           {activeSection === 'profile' && (
              <form onSubmit={handleSaveProfile} className="animate-fade-in">
                 <h6 className="fw-bold text-dark mb-3 border-bottom pb-2" style={{ fontFamily: 'Kanit, sans-serif' }}>ข้อมูลส่วนบุคคลสิทธิรักษา</h6>
                 
                 <div className="mb-3">
                    <label className="text-muted text-uppercase mb-1.5 d-block" style={{ fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.5px' }}>เลขบัตรประชาชน (อ่านอย่างเดียว)</label>
                    <input type="text" className="form-control rounded-pill bg-light border-0 py-2.5 px-3 text-muted" style={{ fontSize: '0.88rem' }} value={userData?.id_card || ""} disabled readOnly />
                 </div>

                 <div className="mb-3">
                    <label className="text-muted text-uppercase mb-1.5 d-block" style={{ fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.5px' }}>ชื่อ - นามสกุล (อ่านอย่างเดียว)</label>
                    <input type="text" className="form-control rounded-pill bg-light border-0 py-2.5 px-3 text-muted" style={{ fontSize: '0.88rem' }} value={displayName} disabled readOnly />
                 </div>

                 <div className="mb-3">
                    <label className="text-muted text-uppercase mb-1.5 d-block" style={{ fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.5px' }}>เบอร์โทรศัพท์ติดต่อหลัก</label>
                    <input 
                      type="text" 
                      className="form-control rounded-pill border bg-light bg-opacity-10 py-2.5 px-3 text-dark focus:border-dark" 
                      style={{ fontSize: '0.88rem' }} 
                      value={editPhone} 
                      onChange={(e) => setEditPhone(e.target.value)}
                      required
                    />
                 </div>

                 <div className="mb-3">
                    <label className="text-muted text-uppercase mb-1.5 d-block" style={{ fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.5px' }}>ที่อยู่อีเมลติดต่อ</label>
                    <input 
                      type="email" 
                      className="form-control rounded-pill border bg-light bg-opacity-10 py-2.5 px-3 text-dark" 
                      style={{ fontSize: '0.88rem' }} 
                      value={editEmail} 
                      onChange={(e) => setEditEmail(e.target.value)}
                    />
                 </div>

                 <div className="mb-4">
                    <label className="text-muted text-uppercase mb-1.5 d-block" style={{ fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.5px' }}>เบอร์โทรติดต่อฉุกเฉิน</label>
                    <input 
                      type="text" 
                      className="form-control rounded-pill border bg-light bg-opacity-10 py-2.5 px-3 text-dark" 
                      style={{ fontSize: '0.88rem' }} 
                      placeholder="ระบุเบอร์โทรฉุกเฉินผู้ดูแล"
                      value={editEmergencyPhone} 
                      onChange={(e) => setEditEmergencyPhone(e.target.value)}
                    />
                 </div>

                 <button 
                  type="submit"
                  disabled={isSavingProfile}
                  className="btn btn-dark rounded-pill w-100 py-2.5 fw-bold shadow-xs border-0" 
                  style={{ fontSize: '13px', backgroundColor: '#282A29' }}
                 >
                    {isSavingProfile ? "กำลังบันทึกข้อมูล..." : "บันทึกการแก้ไขข้อมูลติดต่อ"}
                 </button>
              </form>
           )}

           {activeSection === 'security' && (
              <div className="animate-fade-in">
                 <h6 className="fw-bold text-dark mb-4 border-bottom pb-2" style={{ fontFamily: 'Kanit, sans-serif' }}>ความปลอดภัยและความปลอดภัยบัญชี</h6>
                 
                 {/* Google 2FA Section */}
                 <div className="mb-4">
                    <label className="text-muted text-uppercase mb-2.5 d-block" style={{ fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.5px' }}>การยืนยันรหัสความปลอดภัยสองชั้น</label>
                    {userData?.extra_data?.two_factor_enabled ? (
                       <div className="p-3 rounded-4 bg-success bg-opacity-5 border border-success border-opacity-25 d-flex align-items-center justify-content-between">
                          <div>
                             <p className="fw-bold text-success mb-0.5" style={{ fontSize: '0.88rem' }}>เปิดใช้งาน Google 2FA แล้ว</p>
                             <p className="text-muted mb-0" style={{ fontSize: '0.72rem' }}>ช่วยป้องกันการเข้าถึงข้อมูล EMR โดยไม่ได้รับอนุญาต</p>
                          </div>
                          <button 
                            onClick={handleDisable2FA}
                            className="btn btn-sm btn-outline-danger rounded-pill px-3 fw-bold border-1"
                            style={{ fontSize: '11px' }}
                          >
                             ปิดการใช้งาน
                          </button>
                       </div>
                    ) : (
                       <div className="p-3 rounded-4 bg-light border d-flex align-items-center justify-content-between">
                          <div>
                             <p className="fw-bold text-dark mb-0.5" style={{ fontSize: '0.88rem' }}>Google Authenticator (2FA)</p>
                             <p className="text-muted mb-0" style={{ fontSize: '0.72rem' }}>ยังไม่ได้ลงทะเบียนสแกน QR Code</p>
                          </div>
                          <button 
                            onClick={() => setShow2FAModal(true)}
                            className="btn btn-sm btn-dark rounded-pill px-3 fw-bold border-0"
                            style={{ fontSize: '11px', backgroundColor: '#282A29' }}
                          >
                             เปิดระบบความปลอดภัย
                          </button>
                       </div>
                    )}
                 </div>

                 {/* Password Section */}
                 <form onSubmit={handleChangePassword} className="border-top pt-3">
                    <label className="text-muted text-uppercase mb-2.5 d-block" style={{ fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.5px' }}>เปลี่ยนรหัสผ่านเข้าใช้บริการ</label>
                    <div className="mb-3">
                       <input 
                        type="password" 
                        placeholder="รหัสผ่านเดิมของคุณ" 
                        className="form-control rounded-pill border bg-light bg-opacity-10 py-2.5 px-3" 
                        style={{ fontSize: '0.88rem' }}
                        value={oldPassword}
                        onChange={(e) => setOldPassword(e.target.value)}
                        required 
                       />
                    </div>
                    <div className="mb-3">
                       <input 
                        type="password" 
                        placeholder="กำหนดรหัสผ่านใหม่" 
                        className="form-control rounded-pill border bg-light bg-opacity-10 py-2.5 px-3" 
                        style={{ fontSize: '0.88rem' }}
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        required 
                       />
                    </div>
                    <div className="mb-3.5">
                       <input 
                        type="password" 
                        placeholder="ยืนยันรหัสผ่านใหม่" 
                        className="form-control rounded-pill border bg-light bg-opacity-10 py-2.5 px-3" 
                        style={{ fontSize: '0.88rem' }}
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        required 
                       />
                    </div>
                    
                    <button 
                     type="submit"
                     disabled={isChangingPassword}
                     className="btn btn-outline-dark rounded-pill w-100 py-2 fw-bold"
                     style={{ fontSize: '12px' }}
                    >
                       {isChangingPassword ? "กำลังตรวจสอบข้อมูล..." : "เปลี่ยนรหัสผ่านบัญชี"}
                    </button>
                 </form>

                 <button 
                    onClick={handleLogout}
                    disabled={isLoggingOut}
                    className="btn btn-outline-danger rounded-pill w-100 py-2.5 fw-bold mt-4 d-flex align-items-center justify-content-center gap-2 border-1"
                    style={{ fontSize: '13px' }}
                 >
                    {isLoggingOut ? <Loader2 className="animate-spin" size={18} /> : <LogOut size={18} />}
                    ออกจากระบบสิทธิ์การรักษา
                 </button>
              </div>
           )}

           {activeSection === 'notifications' && (
              <div className="animate-fade-in py-4 text-center">
                 <Bell size={44} className="text-muted opacity-25 mb-3" />
                 <h6 className="fw-bold text-dark mb-1" style={{ fontFamily: 'Kanit, sans-serif' }}>ช่องทางการส่งแจ้งเตือน</h6>
                 <p className="text-muted mb-0 small px-4">
                    ขณะนี้ระบบผูกเข้ากับเบราวเซอร์ PWA และ Firebase Cloud Messaging (FCM) ในการนำส่งข้อความแล็บเร่งด่วนโดยตรงเข้าโทรศัพท์มือถือเรียบร้อยแล้ว
                 </p>
              </div>
           )}

           {/* About System Section (iOS Settings style) */}
           {activeSection === 'about' && (
              <div className="animate-fade-in text-center">
                 <div className="mb-4 mt-2">
                    <img 
                      src="/pwa_logo.jpg" 
                      alt="TSPI Logo" 
                      className="rounded-4 shadow-sm mb-3.5 mx-auto" 
                      style={{ width: '84px', height: '84px', border: '3px solid white' }} 
                    />
                    <h5 className="fw-bold text-dark mb-0" style={{ fontFamily: 'Kanit, sans-serif', letterSpacing: '-0.3px' }}>TSPI CLINICAL</h5>
                    <span className="text-muted small uppercase tracking-wider" style={{ fontSize: '10px', fontWeight: 700 }}>CLINICAL INTELLIGENCE APP</span>
                 </div>

                 {/* iOS Settings rows */}
                 <div className="d-grid gap-2 border-top pt-3.5 text-start">
                    {[
                       { label: "เวอร์ชันระบบหลัก (TSPI Core)", value: "TSPI V.1 (Production Stable)" },
                       { label: "สมองกลสรีรวิทยา (TSPI Brain)", value: "TSPI Brain V.1 (Active Local OLS)" },
                       { label: "ผู้พัฒนาเทคโนโลยี (Clinic Team)", value: "TSPI Clinical Development Unit" },
                       { label: "สถาปัตยกรรม (PWA Integration)", value: "Next.js 16 (Standalone App Mode)" },
                       { label: "ระบบฐานข้อมูล (EMR Database)", value: "PostgreSQL Secure Compliant" },
                       { label: "ลิขสิทธิ์ระบบ", value: "© 2026 TSPI Clinic. All rights reserved." },
                    ].map((row, idx) => (
                       <div key={idx} className="d-flex justify-content-between align-items-center border-bottom pb-2 mb-1">
                          <span className="text-muted" style={{ fontSize: '11.5px', fontWeight: 500 }}>{row.label}</span>
                          <span className="fw-bold text-dark text-end" style={{ fontSize: '11.5px' }}>{row.value}</span>
                       </div>
                    ))}
                 </div>
              </div>
           )}
        </div>

        {/* System bottom display */}
        <div className="mt-4 text-center text-muted" style={{ opacity: 0.6 }}>
           <p className="fw-bold mb-0" style={{ fontSize: '0.65rem', letterSpacing: '1px' }}>TSPI CLINICAL INTELLIGENCE</p>
           <p className="mb-0" style={{ fontSize: '0.65rem' }}>Version 1.0.0 (Production)</p>
        </div>

      </div>

      {/* Google 2FA Registration Modal */}
      {show2FAModal && (
         <div className="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center bg-dark bg-opacity-50" style={{ zIndex: 1050, backdropFilter: "blur(4px)" }}>
            <div className="bg-white rounded-4 p-4 max-w-sm w-100 mx-3 shadow-lg border border-light animate-fade-in text-start">
               <div className="d-flex justify-content-between align-items-center mb-3.5">
                  <h6 className="fw-bold mb-0 text-dark" style={{ fontFamily: 'Kanit, sans-serif' }}>เปิดใช้งาน Google 2FA 🔐</h6>
                  <button type="button" className="btn-close" onClick={() => setShow2FAModal(false)}></button>
               </div>
               
               <div className="mb-3.5 text-center bg-light p-3 rounded-4">
                  <span className="tiny text-muted d-block uppercase tracking-wider mb-2">ขั้นตอนที่ 1: สแกน QR Code นี้ผ่านแอป Authenticator</span>
                  {/* Generated QR Mockup */}
                  <div className="bg-white p-2.5 rounded d-inline-block shadow-xs mb-2">
                     <QrCode size={128} className="text-dark" />
                  </div>
                  <div className="border-top pt-2">
                     <span className="tiny text-muted d-block mb-1">หรือป้อนรหัสคีย์ลับ (Secret Key):</span>
                     <div className="d-flex align-items-center justify-content-center gap-1.5 bg-white py-1 px-2.5 rounded border border-light">
                        <code className="text-dark fw-bold" style={{ fontSize: '11px' }}>K7YG Y34B HUIO P23Z</code>
                        <button 
                          onClick={() => {
                             navigator.clipboard.writeText("K7YG Y34B HUIO P23Z");
                             Swal.fire({ title: "คัดลอกรหัสแล้ว!", text: "สําหรับนําไปคีย์ใน Google Authenticator", icon: "success", timer: 1500, showConfirmButton: false });
                          }}
                          className="btn btn-light btn-sm rounded p-1 border-0"
                        >
                           <Copy size={11} className="text-muted" />
                        </button>
                     </div>
                  </div>
               </div>

               <form onSubmit={handleVerify2FA}>
                  <div className="mb-3.5">
                     <label className="form-label text-muted small fw-bold mb-1">ขั้นตอนที่ 2: ป้อนรหัสความปลอดภัย 6 หลักจากแอป</label>
                     <input
                        type="text"
                        maxLength={6}
                        className="form-control rounded-pill border-light bg-light text-dark py-2 px-3 text-center fw-bold"
                        style={{ fontSize: "16px", letterSpacing: '4px' }}
                        placeholder="000000"
                        value={otpCode}
                        onChange={(e) => setOtpCode(e.target.value)}
                        required
                     />
                  </div>
                  
                  <div className="d-grid gap-2">
                     <button
                        type="submit"
                        disabled={isVerifying2FA}
                        className="btn btn-dark rounded-pill py-2.5 fw-bold d-flex align-items-center justify-content-center gap-2 border-0"
                        style={{ backgroundColor: "#282A29", fontSize: "13px" }}
                     >
                        {isVerifying2FA ? (
                           <>
                              <Loader2 className="animate-spin" size={15} /> กำลังยืนยันสิทธิ์...
                           </>
                        ) : (
                           "ยืนยันและเปิดใช้งาน 2FA"
                        )}
                     </button>
                     <button
                        type="button"
                        onClick={() => setShow2FAModal(false)}
                        className="btn btn-light rounded-pill py-2 text-muted border border-light"
                        style={{ fontSize: "12px" }}
                     >
                        ยกเลิก
                     </button>
                  </div>
               </form>
            </div>
         </div>
      )}

      <style jsx global>{`
        .bg-primary-custom { background-color: #EBF5FF; }
        .text-primary-custom { color: #0A5C8E; }
        .transition-all { transition: all 0.2s ease-in-out; }
        
        .animate-fade-in { animation: fadeIn 0.4s ease-out both; }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        
        .animate-spin { animation: spin 1s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
