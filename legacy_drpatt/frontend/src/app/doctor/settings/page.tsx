"use client";

import { useState, useEffect } from "react";
import {
   Settings, User, Building2, Bell, ShieldCheck,
   Globe, Save, Database, Shield, Key, Plus,
   Mail, Phone, MapPin, Camera, Smartphone,
   Lock, Globe2, Link2, SlidersHorizontal, Loader2, Check
} from "lucide-react";
import Link from "next/link";
import "./../theme-inapp.css";
import Swal from "sweetalert2";
import {
   getDoctorProfile,
   updateDoctorProfile,
   getClinicSettings,
   updateClinicSettings,
   changePassword
} from "@/utils/api/services";

export default function DoctorSettingsPage() {
   const [activeTab, setActiveTab] = useState("profile");
   const [loading, setLoading] = useState(true);
   const [isSaving, setIsSaving] = useState(false);

   // State stores
   const [profile, setProfile] = useState({
      first_name: "",
      last_name: "",
      email: "",
      username: "",
      role: "doctor"
   });

   const [clinic, setClinic] = useState({
      clinic_name: "TSPI Precision Hub",
      location_id: "HUB-TH-001",
      address: "123 Sukhumvit Road, Bangkok, Thailand 10110",
      phone: "+66 2-882-0000"
   });

   const [passwordData, setPasswordData] = useState({
      old_password: "",
      new_password: "",
      confirm_password: ""
   });

   const [notifications, setNotifications] = useState({
      email_alerts: true,
      triage_push: true,
      critical_sms: false
   });

   const [apiStatus, setApiStatus] = useState({
      backend_url: typeof window !== "undefined" ? (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000") : "http://localhost:8000",
      latency: "",
      testing: false
   });

   // Load configurations on mount
   useEffect(() => {
      const loadAllSettings = async () => {
         setLoading(true);
         try {
            // 1. Fetch Doctor Profile
            const profileData = await getDoctorProfile();
            if (profileData) {
               setProfile({
                  first_name: profileData.first_name || "",
                  last_name: profileData.last_name || "",
                  email: profileData.email || "",
                  username: profileData.username || "",
                  role: profileData.role || "doctor"
               });
            }

            // 2. Fetch Clinic Settings
            const clinicData = await getClinicSettings();
            if (clinicData) {
               setClinic(prev => ({
                  ...prev,
                  ...clinicData
               }));
            }

            // 3. Load Notification settings from localstorage if any
            const savedNotifs = localStorage.getItem("settings_notifications");
            if (savedNotifs) {
               try {
                  setNotifications(JSON.parse(savedNotifs));
               } catch (e) {
                  console.error(e);
               }
            }
         } catch (err) {
            console.error("Error loading settings:", err);
         } finally {
            setLoading(false);
         }
      };
      loadAllSettings();
   }, []);

   // General Save Handler (Dispatched based on Active Tab)
   const handleSave = async () => {
      setIsSaving(true);
      try {
         if (activeTab === "profile") {
            await updateDoctorProfile({
               first_name: profile.first_name,
               last_name: profile.last_name
            });
            Swal.fire({
               icon: 'success',
               title: 'บันทึกโปรไฟล์สำเร็จ',
               text: 'ข้อมูลประจำตัวแพทย์ได้รับการอัปเดตเรียบร้อยแล้ว',
               confirmButtonText: 'ตกลง',
               confirmButtonColor: '#0A5C8E'
            });
         } 
         else if (activeTab === "clinic") {
            await updateClinicSettings(clinic);
            Swal.fire({
               icon: 'success',
               title: 'บันทึกข้อมูลคลินิกสำเร็จ',
               text: 'รายละเอียดสถานพยาบาลได้รับการบันทึกแล้ว',
               confirmButtonText: 'ตกลง',
               confirmButtonColor: '#0A5C8E'
            });
         } 
         else if (activeTab === "notifications") {
            localStorage.setItem("settings_notifications", JSON.stringify(notifications));
            Swal.fire({
               icon: 'success',
               title: 'ตั้งค่าการแจ้งเตือนสำเร็จ',
               text: 'ระบบได้จดจำค่าการรับข้อมูลแจ้งเตือนเรียบร้อยแล้ว',
               confirmButtonText: 'ตกลง',
               confirmButtonColor: '#0A5C8E'
            });
         }
      } catch (err: any) {
         console.error("Save Error:", err);
         Swal.fire({
            icon: 'error',
            title: 'บันทึกล้มเหลว',
            text: err.message || 'เกิดข้อผิดพลาดในการเชื่อมต่อกับเซิร์ฟเวอร์หลังบ้าน',
            confirmButtonText: 'ตกลง',
            confirmButtonColor: '#0A5C8E'
         });
      } finally {
         setIsSaving(false);
      }
   };

   // Change Password Handler
   const handleChangePasswordSubmit = async (e: React.FormEvent) => {
      e.preventDefault();
      if (!passwordData.old_password || !passwordData.new_password) {
         Swal.fire({
            icon: 'warning',
            title: 'กรอกข้อมูลไม่ครบ',
            text: 'กรุณากรอกรหัสผ่านเดิมและรหัสผ่านใหม่',
            confirmButtonText: 'ตกลง',
            confirmButtonColor: '#0A5C8E'
         });
         return;
      }

      if (passwordData.new_password !== passwordData.confirm_password) {
         Swal.fire({
            icon: 'error',
            title: 'รหัสผ่านไม่ตรงกัน',
            text: 'กรุณายืนยันรหัสผ่านใหม่ให้ถูกต้องตรงกันอีกครั้ง',
            confirmButtonText: 'ตกลง',
            confirmButtonColor: '#0A5C8E'
         });
         return;
      }

      setIsSaving(true);
      try {
         await changePassword({
            old_password: passwordData.old_password,
            new_password: passwordData.new_password
         });
         
         Swal.fire({
            icon: 'success',
            title: 'เปลี่ยนรหัสผ่านสำเร็จ',
            text: 'ระบบทำการเปลี่ยนรหัสผ่านและสร้างบันทึกตรวจสอบความปลอดภัยเรียบร้อยแล้วครับ',
            confirmButtonText: 'ตกลง',
            confirmButtonColor: '#0A5C8E'
         });
         
         setPasswordData({
            old_password: "",
            new_password: "",
            confirm_password: ""
         });
      } catch (err: any) {
         console.error("Change password error:", err);
         Swal.fire({
            icon: 'error',
            title: 'เปลี่ยนรหัสผ่านไม่สำเร็จ',
            text: err.error || 'รหัสผ่านเดิมไม่ถูกต้อง หรือเกิดข้อผิดพลาดจากเซิร์ฟเวอร์',
            confirmButtonText: 'ตกลง',
            confirmButtonColor: '#0A5C8E'
         });
      } finally {
         setIsSaving(false);
      }
   };

   // Latency Test Connection
   const testApiConnectivity = async () => {
      setApiStatus(prev => ({ ...prev, testing: true }));
      const start = Date.now();
      try {
         const res = await fetch(`${apiStatus.backend_url}/api/patients/list-lightweight/`, {
            headers: {
               "Authorization": localStorage.getItem("doctor_access_token") ? `Bearer ${localStorage.getItem("doctor_access_token")}` : ""
            }
         });
         const end = Date.now();
         if (res.ok) {
            setApiStatus(prev => ({
               ...prev,
               latency: `${end - start} ms (การเชื่อมต่อปกติ)`,
               testing: false
            }));
         } else {
            setApiStatus(prev => ({
               ...prev,
               latency: `ล้มเหลว (Status: ${res.status})`,
               testing: false
            }));
         }
      } catch (err) {
         setApiStatus(prev => ({
            ...prev,
            latency: "ตรวจไม่พบเซิร์ฟเวอร์หลังบ้าน",
            testing: false
         }));
      }
   };

   const tabs = [
      { id: "profile", label: "ข้อมูลแพทย์ประจำตัว", icon: User },
      { id: "clinic", label: "ข้อมูลสถานพยาบาล", icon: Building2 },
      { id: "notifications", label: "การแจ้งเตือนระบบ", icon: Bell },
      { id: "security", label: "ความปลอดภัย & รหัสผ่าน", icon: ShieldCheck },
      { id: "api", label: "การทดสอบเชื่อมต่อ API", icon: Link2 },
   ];

   if (loading) {
      return (
         <div className="py-5 text-center" style={{ fontFamily: "Kanit, sans-serif" }}>
            <Loader2 className="animate-spin text-primary opacity-30 mx-auto mb-3" size={48} />
            <p className="text-muted text-sm font-semibold">กำลังโหลดการตั้งค่าระบบ EMR...</p>
         </div>
      );
   }

   return (
      <div className="pb-5" style={{ fontFamily: "Kanit, sans-serif" }}>
         {/* 🧭 Settings Header */}
         <div className="d-flex justify-content-between align-items-center mb-4">
            <div>
               <h1 className="fs-3 fw-bold mb-1 text-dark d-flex align-items-center gap-2">
                  <div className="bg-primary bg-opacity-10 p-2 rounded-3 text-primary shadow-sm">
                     <Settings size={24} />
                  </div>
                  การตั้งค่าทั่วไป (General Settings)
               </h1>
               <p className="text-muted text-xs uppercase font-bold tracking-widest ms-5 mb-0">แผงควบคุมระบบการแพทย์ส่วนบุคคลและองค์กร</p>
            </div>
            {activeTab !== "security" && activeTab !== "api" && (
               <div className="d-flex gap-2">
                  <button
                     onClick={handleSave}
                     disabled={isSaving}
                     className="btn btn-primary font-bold uppercase tracking-widest text-[10px] px-4 py-2 shadow-sm d-flex align-items-center gap-2 rounded-pill text-white"
                  >
                     {isSaving ? <Loader2 className="animate-spin" size={14} /> : <Save size={14} />} บันทึกการเปลี่ยนแปลง
                  </button>
               </div>
            )}
         </div>

         <div className="row g-4">
            {/* 🛠️ Left Column: Navigation Sidebar */}
            <div className="col-lg-3">
               <div className="card border-0 shadow-sm bg-white overflow-hidden mb-4 rounded-4">
                  <div className="card-header bg-transparent border-bottom border-light py-3">
                     <h3 className="card-title text-[10px] font-bold uppercase text-muted tracking-widest mb-0">รายการเมนูตั้งค่า</h3>
                  </div>
                  <div className="list-group list-group-flush">
                     {tabs.map((tab) => (
                        <button
                           key={tab.id}
                           onClick={() => setActiveTab(tab.id)}
                           className={`list-group-item list-group-item-action border-0 py-3 d-flex align-items-center gap-3 transition-all ${activeTab === tab.id ? 'bg-primary text-white shadow-sm font-bold' : 'text-muted'}`}
                        >
                           <tab.icon size={18} className={activeTab === tab.id ? 'text-white' : 'text-primary opacity-50'} />
                           <span className="text-xs font-bold uppercase tracking-widest">{tab.label}</span>
                        </button>
                     ))}
                  </div>
               </div>

               <div className="p-4 bg-primary bg-opacity-5 rounded-4 border border-primary border-opacity-10">
                  <div className="d-flex align-items-center gap-2 mb-2">
                     <ShieldCheck size={16} className="text-primary" />
                     <h6 className="text-[10px] font-bold text-primary uppercase mb-0 tracking-widest">การคุ้มครองข้อมูลการรักษา</h6>
                  </div>
                  <p className="text-[10px] text-muted mb-0 leading-relaxed">
                     การตั้งค่าและการปรับข้อมูลประจำตัวแพทย์จะถูกเข้ารหัสความปลอดภัยตามข้อกำหนด PDPA และ พรบ. ข้อมูลคอมพิวเตอร์ทางการแพทย์แห่งประเทศไทย
                  </p>
               </div>
            </div>

            {/* 📄 Right Column: Content Area */}
            <div className="col-lg-9">
               <div className="card border-0 shadow-sm bg-white min-h-[500px] overflow-hidden rounded-4">
                  <div className="card-header bg-transparent border-bottom border-light py-3 d-flex justify-content-between align-items-center">
                     <h3 className="card-title text-xs font-bold uppercase text-dark mb-0 tracking-wider">
                        {tabs.find(t => t.id === activeTab)?.label}
                     </h3>
                     <span className="badge bg-light text-muted border text-[9px] font-bold uppercase tracking-tighter py-1.5 px-3 rounded-pill">
                        System ID: TSPI-EMR-{profile.username || "DOCTOR"}
                     </span>
                  </div>
                  <div className="card-body p-4">

                     {/* Tab: Profile */}
                     {activeTab === 'profile' && (
                        <div className="animate-in fade-in slide-in-from-right-4">
                           <div className="row mb-5">
                              <div className="col-md-4 text-center mb-4 mb-md-0 d-flex flex-column align-items-center justify-content-center border-end border-light">
                                 <div className="position-relative">
                                    <div className="bg-light rounded-circle d-flex align-items-center justify-content-center text-muted border border-2 border-white shadow-sm" style={{ width: '130px', height: '130px' }}>
                                       <User size={64} className="opacity-20 text-primary" />
                                    </div>
                                    <button className="btn btn-sm btn-primary rounded-circle position-absolute shadow-lg d-flex align-items-center justify-content-center text-white" style={{ bottom: '5px', right: '5px', width: '36px', height: '36px' }}>
                                       <Camera size={18} />
                                    </button>
                                 </div>
                                 <h5 className="mt-3 fw-bold text-dark mb-1">นพ. {profile.first_name || "แพทย์"} {profile.last_name || ""}</h5>
                                 <span className="badge bg-primary bg-opacity-10 text-primary text-[9px] uppercase font-black px-3 py-1.5 rounded-pill">แพทย์ผู้เชี่ยวชาญการแพทย์แม่นยำ</span>
                                 <p className="text-[10px] text-muted mt-2 uppercase font-bold tracking-widest mb-0">สถานะ: Verified System Access</p>
                              </div>
                              <div className="col-md-8 px-md-5">
                                 <div className="row g-4">
                                    <div className="col-md-6">
                                       <label className="text-[10px] font-bold text-muted uppercase tracking-widest mb-2 d-block">ชื่อจริง (First Name)</label>
                                       <input
                                          type="text"
                                          className="form-control bg-light border-0 text-sm font-semibold p-3 rounded-pill shadow-none"
                                          value={profile.first_name}
                                          onChange={(e) => setProfile({ ...profile, first_name: e.target.value })}
                                       />
                                    </div>
                                    <div className="col-md-6">
                                       <label className="text-[10px] font-bold text-muted uppercase tracking-widest mb-2 d-block">นามสกุล (Last Name)</label>
                                       <input
                                          type="text"
                                          className="form-control bg-light border-0 text-sm font-semibold p-3 rounded-pill shadow-none"
                                          value={profile.last_name}
                                          onChange={(e) => setProfile({ ...profile, last_name: e.target.value })}
                                       />
                                    </div>
                                    <div className="col-md-6">
                                       <label className="text-[10px] font-bold text-muted uppercase tracking-widest mb-2 d-block">อีเมลติดต่อ (Email Address)</label>
                                       <input
                                          type="email"
                                          className="form-control bg-light border-0 text-sm font-semibold p-3 rounded-pill shadow-none"
                                          value={profile.email}
                                          readOnly
                                          aria-describedby="staff-email-help"
                                       />
                                       <small id="staff-email-help">การเปลี่ยนอีเมลเข้าสู่ระบบต้องให้ผู้ดูแลตรวจสอบ</small>
                                    </div>
                                    <div className="col-md-6">
                                       <label className="text-[10px] font-bold text-muted uppercase tracking-widest mb-2 d-block">ชื่อผู้ใช้งานระบบ (Username)</label>
                                       <input
                                          type="text"
                                          className="form-control bg-light border-0 text-sm font-semibold p-3 rounded-pill shadow-none"
                                          value={profile.username}
                                          disabled
                                       />
                                    </div>
                                 </div>
                              </div>
                           </div>

                           <div className="border-top border-light pt-4">
                              <h6 className="text-xs font-bold text-dark uppercase tracking-widest mb-3">ใบรับรองและการรับรองทางการรักษา (Institutional Credentials)</h6>
                              <div className="row g-3">
                                 <div className="col-md-6">
                                    <div className="p-3 bg-light rounded-3 d-flex align-items-center gap-3 border">
                                       <div className="text-primary"><Shield size={20} /></div>
                                       <div>
                                          <div className="text-[9px] font-bold text-muted uppercase tracking-widest">สถานะกองประกอบโรคศิลป์</div>
                                          <div className="text-xs font-bold text-dark">เลขที่ใบอนุญาต: L-99881122 (กำลังใช้งาน)</div>
                                       </div>
                                    </div>
                                 </div>
                                 <div className="col-md-6">
                                    <div className="p-3 bg-light rounded-3 d-flex align-items-center gap-3 border">
                                       <div className="text-success"><Database size={20} /></div>
                                       <div>
                                          <div className="text-[9px] font-bold text-muted uppercase tracking-widest">การใช้พื้นที่บันทึกผลแล็บ</div>
                                          <div className="text-xs font-bold text-dark">4.2 GB / 10 GB (ความปลอดภัย AES-256)</div>
                                       </div>
                                    </div>
                                 </div>
                              </div>
                           </div>
                        </div>
                     )}

                     {/* Tab: Clinic */}
                     {activeTab === 'clinic' && (
                        <div className="animate-in fade-in slide-in-from-right-4">
                           <div className="row g-4 mb-5">
                              <div className="col-md-6">
                                 <label className="text-[10px] font-bold text-muted uppercase tracking-widest mb-2 d-block">ชื่อสถานพยาบาล / คลินิก</label>
                                 <input
                                    type="text"
                                    className="form-control bg-light border-0 text-sm font-semibold p-3 rounded-pill shadow-none"
                                    value={clinic.clinic_name}
                                    onChange={(e) => setClinic({ ...clinic, clinic_name: e.target.value })}
                                 />
                              </div>
                              <div className="col-md-6">
                                 <label className="text-[10px] font-bold text-muted uppercase tracking-widest mb-2 d-block">รหัสสถานที่ประเมินผลแล็บ (Location ID)</label>
                                 <input
                                    type="text"
                                    className="form-control bg-light border-0 text-sm font-semibold p-3 rounded-pill shadow-none"
                                    value={clinic.location_id}
                                    onChange={(e) => setClinic({ ...clinic, location_id: e.target.value })}
                                 />
                              </div>
                              <div className="col-md-12">
                                 <label className="text-[10px] font-bold text-muted uppercase tracking-widest mb-2 d-block">เบอร์โทรศัพท์คลินิก (Clinic Phone)</label>
                                 <input
                                    type="text"
                                    className="form-control bg-light border-0 text-sm font-semibold p-3 rounded-pill shadow-none"
                                    value={clinic.phone}
                                    onChange={(e) => setClinic({ ...clinic, phone: e.target.value })}
                                 />
                              </div>
                              <div className="col-12">
                                 <label className="text-[10px] font-bold text-muted uppercase tracking-widest mb-2 d-block">ที่ตั้งสถานพยาบาลอย่างเป็นทางการ</label>
                                 <textarea
                                    className="form-control bg-light border-0 text-sm font-semibold p-3 rounded-4 shadow-none"
                                    rows={3}
                                    value={clinic.address}
                                    onChange={(e) => setClinic({ ...clinic, address: e.target.value })}
                                 />
                              </div>
                           </div>
                        </div>
                     )}

                     {/* Tab: Notifications */}
                     {activeTab === 'notifications' && (
                        <div className="animate-in fade-in slide-in-from-right-4">
                           <div className="d-flex flex-column gap-3">
                              <div className="p-3 bg-light rounded-3 d-flex align-items-center justify-content-between border">
                                 <div className="d-flex align-items-center gap-3">
                                    <Mail className="text-primary" size={20} />
                                    <div>
                                       <span className="font-bold d-block text-sm text-dark">แจ้งเตือนผ่านช่องทางอีเมล (Email Alerts)</span>
                                       <small className="text-muted text-[10px]">รับสรุปเคสวิเคราะห์คนไข้และข้อบ่งชี้ทางคลินิกเมื่อระบบทำงานเสร็จสิ้น</small>
                                    </div>
                                 </div>
                                 <div className="form-check form-switch">
                                    <input
                                       className="form-check-input"
                                       type="checkbox"
                                       role="switch"
                                       checked={notifications.email_alerts}
                                       onChange={(e) => setNotifications({ ...notifications, email_alerts: e.target.checked })}
                                       style={{ width: '40px', height: '20px' }}
                                    />
                                 </div>
                              </div>

                              <div className="p-3 bg-light rounded-3 d-flex align-items-center justify-content-between border">
                                 <div className="d-flex align-items-center gap-3">
                                    <Smartphone className="text-warning" size={20} />
                                    <div>
                                       <span className="font-bold d-block text-sm text-dark">Push Notifications (คัดกรองเร่งด่วน)</span>
                                       <small className="text-muted text-[10px]">รับการแจ้งเตือนทันทีเมื่อมีคนไข้เช็คอินซักประวัติอัตโนมัติคิวแรก</small>
                                    </div>
                                 </div>
                                 <div className="form-check form-switch">
                                    <input
                                       className="form-check-input"
                                       type="checkbox"
                                       role="switch"
                                       checked={notifications.triage_push}
                                       onChange={(e) => setNotifications({ ...notifications, triage_push: e.target.checked })}
                                       style={{ width: '40px', height: '20px' }}
                                    />
                                 </div>
                              </div>

                              <div className="p-3 bg-light rounded-3 d-flex align-items-center justify-content-between border">
                                 <div className="d-flex align-items-center gap-3">
                                    <Bell className="text-danger" size={20} />
                                    <div>
                                       <span className="font-bold d-block text-sm text-dark">ส่งข้อความ SMS ทันทีกรณีพบเคสวิกฤต (Critical Triage SMS)</span>
                                       <small className="text-muted text-[10px]">ส่ง SMS เมื่อคะแนนแกนเสื่อมชี้วัดความตึงตัวสูงกว่า 70% (เปิดใช้งานการรับส่งเครือข่ายไทย)</small>
                                    </div>
                                 </div>
                                 <div className="form-check form-switch">
                                    <input
                                       className="form-check-input"
                                       type="checkbox"
                                       role="switch"
                                       checked={notifications.critical_sms}
                                       onChange={(e) => setNotifications({ ...notifications, critical_sms: e.target.checked })}
                                       style={{ width: '40px', height: '20px' }}
                                    />
                                 </div>
                              </div>
                           </div>
                        </div>
                     )}

                     {/* Tab: Security */}
                     {activeTab === 'security' && (
                        <div className="animate-in fade-in slide-in-from-right-4">
                           <form onSubmit={handleChangePasswordSubmit} className="col-lg-8">
                              <h6 className="text-xs font-bold text-dark uppercase tracking-widest mb-4">การปรับปรุงรหัสผ่านเพื่อความปลอดภัยทางคลินิก</h6>
                              <div className="d-flex flex-column gap-4 mb-4">
                                 <div>
                                    <label className="text-[10px] font-bold text-muted uppercase tracking-widest mb-2 d-block">รหัสผ่านปัจจุบัน (Current Password)</label>
                                    <input
                                       type="password"
                                       className="form-control bg-light border-0 text-sm font-semibold p-3 rounded-pill shadow-none"
                                       value={passwordData.old_password}
                                       onChange={(e) => setPasswordData({ ...passwordData, old_password: e.target.value })}
                                       placeholder="••••••••••••"
                                    />
                                 </div>
                                 <div>
                                    <label className="text-[10px] font-bold text-muted uppercase tracking-widest mb-2 d-block">รหัสผ่านใหม่ (New Password)</label>
                                    <input
                                       type="password"
                                       className="form-control bg-light border-0 text-sm font-semibold p-3 rounded-pill shadow-none"
                                       value={passwordData.new_password}
                                       onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })}
                                       placeholder="รหัสผ่านใหม่มากกว่า 6 หลัก"
                                    />
                                 </div>
                                 <div>
                                    <label className="text-[10px] font-bold text-muted uppercase tracking-widest mb-2 d-block">ยืนยันรหัสผ่านใหม่ (Confirm Password)</label>
                                    <input
                                       type="password"
                                       className="form-control bg-light border-0 text-sm font-semibold p-3 rounded-pill shadow-none"
                                       value={passwordData.confirm_password}
                                       onChange={(e) => setPasswordData({ ...passwordData, confirm_password: e.target.value })}
                                       placeholder="ยืนยันรหัสผ่านใหม่อีกครั้ง"
                                    />
                                 </div>
                              </div>
                              <button
                                 type="submit"
                                 disabled={isSaving}
                                 className="btn btn-primary font-bold uppercase tracking-widest text-[10px] px-4 py-2.5 shadow-sm d-flex align-items-center gap-2 rounded-pill text-white"
                              >
                                 {isSaving ? <Loader2 className="animate-spin" size={14} /> : <Lock size={14} />} ปรับปรุงรหัสผ่านใหม่
                              </button>
                           </form>
                        </div>
                     )}

                     {/* Tab: API Test */}
                     {activeTab === 'api' && (
                        <div className="animate-in fade-in slide-in-from-right-4">
                           <div className="row g-4">
                              <div className="col-md-7">
                                 <h6 className="text-xs font-bold text-dark uppercase tracking-widest mb-4">สถานะการเชื่อมต่อฐานข้อมูลและประมวลผล</h6>
                                 
                                 <div className="d-flex flex-column gap-3">
                                    <div className="p-3 bg-light rounded-3 border">
                                       <div className="text-[9px] font-bold text-muted uppercase tracking-widest">EMR Django REST API Base URL</div>
                                       <div className="text-xs font-black text-dark font-mono mt-1">{apiStatus.backend_url}</div>
                                    </div>

                                    <div className="p-3 bg-light rounded-3 border">
                                       <div className="text-[9px] font-bold text-muted uppercase tracking-widest">ผลการประเมินความหน่วงเครือข่าย (Latency)</div>
                                       <div className={`text-xs font-black mt-1 ${apiStatus.latency.includes("ปกติ") ? "text-success" : "text-danger"}`}>
                                          {apiStatus.latency || "ยังไม่ได้เริ่มต้นการตรวจสอบ"}
                                       </div>
                                    </div>

                                    <div className="p-3 bg-light rounded-3 border d-flex justify-content-between align-items-center">
                                       <div>
                                          <div className="text-[9px] font-bold text-muted uppercase tracking-widest">ความเข้ากันได้โปรโตคอลระบบ</div>
                                          <div className="text-xs font-bold text-dark">JSON Serializer Core v16.2</div>
                                       </div>
                                       <span className="badge bg-success bg-opacity-10 text-success text-[9px] font-bold px-3 py-1 rounded-pill">ใช้งานได้</span>
                                    </div>
                                 </div>

                                 <button
                                    onClick={testApiConnectivity}
                                    disabled={apiStatus.testing}
                                    className="btn btn-outline-primary btn-sm mt-4 font-bold uppercase tracking-widest text-[9px] py-2.5 px-4 rounded-pill d-flex align-items-center gap-2 shadow-sm bg-white"
                                 >
                                    {apiStatus.testing ? <Loader2 className="animate-spin" size={12} /> : <Globe size={12} />} ทดสอบการหน่วงการตอบสนอง (Test Connection Latency)
                                 </button>
                              </div>

                              <div className="col-md-5">
                                 <div className="p-4 bg-light rounded-4 border d-flex flex-column gap-3">
                                    <h6 className="text-[10px] font-bold text-muted uppercase tracking-widest mb-0">โครงสร้าง Gateway</h6>
                                    
                                    <div className="d-flex align-items-start gap-3">
                                       <Check className="text-success mt-0.5" size={14} />
                                       <div>
                                          <div className="text-[10px] font-bold text-dark">PostgreSQL Gateway</div>
                                          <p className="text-[9px] text-muted mb-0">พอร์ต 5432 - drpatrcl_sys เชื่อมต่อตรงสำหรับการรักษาเสถียรภาพ</p>
                                       </div>
                                    </div>

                                    <div className="d-flex align-items-start gap-3 border-top pt-3">
                                       <Check className="text-success mt-0.5" size={14} />
                                       <div>
                                          <div className="text-[10px] font-bold text-dark">Firebase JWT Handshake</div>
                                          <p className="text-[9px] text-muted mb-0">เซสชันโทเค็นถอดถอนอัตโนมัติเมื่อครบ 24 ชั่วโมง</p>
                                       </div>
                                    </div>
                                 </div>
                              </div>
                           </div>
                        </div>
                     )}

                  </div>
               </div>
            </div>
         </div>
      </div>
   );
}
