"use client";

import { useState, useEffect } from "react";
import {
  Calendar, Clock, RefreshCw, Plus,
  Check, Stethoscope, X,
  CalendarDays, CheckCircle2,
  Brain
} from "lucide-react";
import Link from "next/link";
import { 
  getAppointments, 
  updateAppointment, 
  getAllPatients, 
  createAppointment 
} from "@/utils/api/services";

// Status configuration (resilient to lowercase and translated terms)
const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  "ยืนยันแล้ว": { label: "ยืนยันแล้ว", color: "#059669", bg: "#ECFDF5" },
  "Confirmed": { label: "ยืนยันแล้ว", color: "#059669", bg: "#ECFDF5" },
  "confirmed": { label: "ยืนยันแล้ว", color: "#059669", bg: "#ECFDF5" },
  "รอยืนยัน": { label: "รอยืนยัน", color: "#D97706", bg: "#FFFBEB" },
  "Pending": { label: "รอยืนยัน", color: "#D97706", bg: "#FFFBEB" },
  "pending": { label: "รอยืนยัน", color: "#D97706", bg: "#FFFBEB" },
  "เสร็จสิ้น": { label: "เสร็จสิ้น", color: "#6B7280", bg: "#F3F4F6" },
  "Completed": { label: "เสร็จสิ้น", color: "#6B7280", bg: "#F3F4F6" },
  "completed": { label: "เสร็จสิ้น", color: "#6B7280", bg: "#F3F4F6" },
  "ยกเลิก": { label: "ยกเลิกแล้ว", color: "#DC2626", bg: "#FEF2F2" },
  "Cancelled": { label: "ยกเลิกแล้ว", color: "#DC2626", bg: "#FEF2F2" },
  "cancelled": { label: "ยกเลิกแล้ว", color: "#DC2626", bg: "#FEF2F2" },
};

export default function DoctorAppointments() {
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split("T")[0]);
  const [selectedStatus, setSelectedStatus] = useState("all");
  
  // States
  const [allAppointments, setAllAppointments] = useState<any[]>([]);
  const [patients, setPatients] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Calendar states
  const [currentYear, setCurrentYear] = useState(new Date().getFullYear());
  const [currentMonth, setCurrentMonth] = useState(new Date().getMonth());
  
  // Modal states
  const [showModal, setShowModal] = useState(false);
  const [formPatientId, setFormPatientId] = useState("");
  const [formDate, setFormDate] = useState(selectedDate);
  const [formTime, setFormTime] = useState("09:00");
  const [formServiceType, setFormServiceType] = useState("Precision Consultation");
  const [formSymptoms, setFormSymptoms] = useState("");
  const [formStatus, setFormStatus] = useState("confirmed");
  const [submitting, setSubmitting] = useState(false);

  // 1. Fetch ALL appointments once to render calendar marks and compute pipeline counts
  const loadData = async () => {
    setLoading(true);
    try {
      const [apptsData, patientsData] = await Promise.all([
        getAppointments(), 
        getAllPatients()
      ]);
      setAllAppointments(apptsData);
      setPatients(patientsData);
      if (patientsData.length > 0 && !formPatientId) {
        setFormPatientId(patientsData[0].id);
      }
    } catch (err) {
      console.error("Error loading clinical data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Sync date form field in modal with highlighted date
  useEffect(() => {
    setFormDate(selectedDate);
  }, [selectedDate]);

  // Handle status pipeline transitions (e.g. click confirm/cancel)
  const handleStatusChange = async (id: string, newStatus: string) => {
    try {
      await updateAppointment(id, { status: newStatus });
      setAllAppointments(prev =>
        prev.map(a => a.id === id ? { ...a, status: newStatus } : a)
      );
    } catch (err) {
      console.error("Failed to update status:", err);
    }
  };

  // Create real appointment in Firestore
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formPatientId) return;

    setSubmitting(true);
    try {
      const selectedPatient = patients.find(p => p.id === formPatientId);
      const patientName = selectedPatient 
        ? `${selectedPatient.fname || ""} ${selectedPatient.lname || ""}`.trim()
        : "Unknown Patient";
      const patientHn = selectedPatient?.hn || String(selectedPatient?.id || '').slice(0, 8) || "TSPI-999";

      const appointmentData = {
        patientId: formPatientId,
        patient_name: patientName,
        patient_hn: patientHn,
        doctorName: "Dr. Pat",
        date: formDate,
        time: formTime,
        type: formServiceType,
        symptoms: formSymptoms,
        status: formStatus // "confirmed" or "pending"
      };

      await createAppointment(appointmentData);

      // Clear form and close modal
      setFormSymptoms("");
      setShowModal(false);

      // Re-fetch live appointments instantly
      await loadData();

    } catch (err) {
      console.error("Error creating appointment:", err);
    } finally {
      setSubmitting(false);
    }
  };

  // Status Counts calculated directly from the FULL database collection (Requirement 2)
  const statusCounts = {
    all: allAppointments.length,
    confirmed: allAppointments.filter(a => {
      const s = String(a.status || "").toLowerCase();
      return s === "ยืนยันแล้ว" || s === "confirmed";
    }).length,
    pending: allAppointments.filter(a => {
      const s = String(a.status || "").toLowerCase();
      return s === "รอยืนยัน" || s === "pending";
    }).length,
    completed: allAppointments.filter(a => {
      const s = String(a.status || "").toLowerCase();
      return s === "เสร็จสิ้น" || s === "completed";
    }).length,
    cancelled: allAppointments.filter(a => {
      const s = String(a.status || "").toLowerCase();
      return s === "ยกเลิก" || s === "cancelled";
    }).length,
  };

  const statusFilters = [
    { id: "all", label: "นัดหมายทั้งหมด", count: statusCounts.all },
    { id: "confirmed", label: "ยืนยันแล้ว", count: statusCounts.confirmed },
    { id: "pending", label: "รอการยืนยัน", count: statusCounts.pending },
    { id: "completed", label: "เสร็จสิ้นแล้ว", count: statusCounts.completed },
    { id: "cancelled", label: "ยกเลิกแล้ว", count: statusCounts.cancelled },
  ];

  // Calendar Helper Calculation
  const getDaysInMonth = (year: number, month: number) => {
    return new Date(year, month + 1, 0).getDate();
  };

  const getFirstDayOfMonth = (year: number, month: number) => {
    return new Date(year, month, 1).getDay();
  };

  const daysInMonth = getDaysInMonth(currentYear, currentMonth);
  const firstDay = getFirstDayOfMonth(currentYear, currentMonth);

  const calendarCells: (number | null)[] = [];
  for (let i = 0; i < firstDay; i++) {
    calendarCells.push(null);
  }
  for (let d = 1; d <= daysInMonth; d++) {
    calendarCells.push(d);
  }

  const thMonths = [
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
  ];
  
  const thWeekdays = ["อา.", "จ.", "อ.", "พ.", "พฤ.", "ศ.", "ส."];

  const handlePrevMonth = () => {
    if (currentMonth === 0) {
      setCurrentMonth(11);
      setCurrentYear(prev => prev - 1);
    } else {
      setCurrentMonth(prev => prev - 1);
    }
  };

  const handleNextMonth = () => {
    if (currentMonth === 11) {
      setCurrentMonth(0);
      setCurrentYear(prev => prev + 1);
    } else {
      setCurrentMonth(prev => prev + 1);
    }
  };

  // Filter Queue for the selected calendar date
  const appointmentsForSelectedDate = allAppointments.filter(a => a.date === selectedDate);

  const filteredApptsForDate = appointmentsForSelectedDate.filter(a => {
    const status = String(a.status || "").toLowerCase();
    if (selectedStatus === "all") return true;
    if (selectedStatus === "confirmed") return status === "ยืนยันแล้ว" || status === "confirmed";
    if (selectedStatus === "pending") return status === "รอยืนยัน" || status === "pending";
    if (selectedStatus === "completed") return status === "เสร็จสิ้น" || status === "completed";
    if (selectedStatus === "cancelled") return status === "ยกเลิก" || status === "cancelled";
    return true;
  });

  const formatThaiDateString = (dateStr: string) => {
    if (!dateStr) return "";
    const date = new Date(dateStr);
    return `${date.getDate()} ${thMonths[date.getMonth()]} ${date.getFullYear() + 543}`;
  };

  return (
    <div>
      {/* ==================== HEADER ==================== */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '22px', fontWeight: 600, color: '#1F2937', marginBottom: '4px' }}>
            ตารางเวลานัดหมายคลินิก
          </h1>
          <p style={{ fontSize: '12px', color: '#6B7280', letterSpacing: '0.3px', margin: 0 }}>
            ระบบจัดการนัดหมายและการวิเคราะห์สุขภาพคนไข้เชิงชีววิทยา (ซิงค์ตรงกับฐานข้อมูล Firestore)
          </p>
        </div>
        <button 
          onClick={() => setShowModal(true)}
          className="btn btn-primary" 
          style={{ fontSize: '12px', padding: '7px 14px', borderRadius: '6px' }}
        >
          <Plus size={14} style={{ marginRight: '6px' }} /> นัดหมายผู้ป่วยใหม่
        </button>
      </div>

      {/* ==================== LAYOUT ==================== */}
      <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: '24px', alignItems: 'start' }}>

        {/* ==================== LEFT SIDEBAR ==================== */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

          {/* วันที่กำลังสังเกตการณ์ */}
          <div className="card">
            <div className="card-header">
              <span style={{ fontSize: '11px', fontWeight: 600, color: '#6B7280', letterSpacing: '0.3px' }}>
                เลือกวันที่สังเกตการณ์
              </span>
            </div>
            <div>
              <label style={{ fontSize: '11px', fontWeight: 500, color: '#374151', marginBottom: '8px', display: 'block' }}>
                วันที่เลือกนัด
              </label>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                border: '1px solid #E5E7EB',
                borderRadius: '4px',
                background: '#F9FAFB',
                padding: '7px 12px',
                gap: '8px'
              }}>
                <CalendarDays size={14} style={{ color: '#9CA3AF', flexShrink: 0 }} />
                <input
                  type="date"
                  style={{
                    background: 'transparent',
                    border: 'none',
                    fontSize: '13px',
                    outline: 'none',
                    flex: 1,
                    color: '#1F2937'
                  }}
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* คัดกรองผ่านสถานะ (ดึงข้อมูลจริงทั้งฐานข้อมูล) */}
          <div className="card">
            <div className="card-header">
              <span style={{ fontSize: '11px', fontWeight: 600, color: '#6B7280', letterSpacing: '0.3px' }}>
                สถานะของระบบนัดหมาย
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              {statusFilters.map((s) => {
                const active = selectedStatus === s.id;
                return (
                  <button
                    key={s.id}
                    onClick={() => setSelectedStatus(s.id)}
                    style={{
                      width: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '9px 10px',
                      background: active ? '#E8F0F5' : 'transparent',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      transition: 'background 0.15s ease',
                    }}
                  >
                    <span style={{
                      fontSize: '13px',
                      fontWeight: active ? 600 : 400,
                      color: active ? '#0A5C8E' : '#4B5563',
                    }}>
                      {s.label}
                    </span>
                    <span style={{
                      fontSize: '11px',
                      fontWeight: 600,
                      color: active ? '#0A5C8E' : '#9CA3AF',
                    }}>
                      {s.count}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* คำแนะนำเชิงลึก */}
          <div className="card" style={{ background: '#F9FAFB' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
              <Clock size={13} style={{ color: '#0A5C8E' }} />
              <span style={{ fontSize: '10px', fontWeight: 600, color: '#0A5C8E', letterSpacing: '0.3px' }}>
                คำแนะนำเชิงระบบ
              </span>
            </div>
            <p style={{ fontSize: '11.5px', color: '#6B7280', margin: 0, lineHeight: 1.6 }}>
              การโทรยืนยันนัดหมายล่วงหน้า 24 ชั่วโมง ช่วยลดโอกาสการปฏิเสธการเข้าพบแพทย์และเพิ่มประสิทธิภาพการไหลเวียนของระบบคนไข้ได้ถึง 15%
            </p>
          </div>
        </div>

        {/* ==================== RIGHT SIDE: CALENDAR & DETAILED TABLE ==================== */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          {/* ปฏิทินแสดงผลรายเดือน */}
          <div className="card border-0 shadow-sm p-4" style={{ borderRadius: '12px', background: '#ffffff', border: '1px solid #E5E7EB' }}>
            <div className="d-flex justify-content-between align-items-center mb-4">
              <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#1F2937', margin: 0 }}>
                ปฏิทินตรวจนัดประจำเดือน: {thMonths[currentMonth]} {currentYear + 543}
              </h3>
              <div className="d-flex gap-2">
                <button 
                  onClick={handlePrevMonth} 
                  className="btn btn-outline" 
                  style={{ padding: '4px 10px', fontSize: '11px', fontWeight: 600 }}
                >
                  ก่อนหน้า
                </button>
                <button 
                  onClick={() => {
                    const today = new Date();
                    setCurrentMonth(today.getMonth());
                    setCurrentYear(today.getFullYear());
                    setSelectedDate(today.toISOString().split("T")[0]);
                  }} 
                  className="btn btn-outline" 
                  style={{ padding: '4px 10px', fontSize: '11px', fontWeight: 600 }}
                >
                  เดือนนี้
                </button>
                <button 
                  onClick={handleNextMonth} 
                  className="btn btn-outline" 
                  style={{ padding: '4px 10px', fontSize: '11px', fontWeight: 600 }}
                >
                  ถัดไป
                </button>
              </div>
            </div>

            {/* ส่วนหัววันในสัปดาห์ */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(7, 1fr)',
              textAlign: 'center',
              marginBottom: '10px',
              borderBottom: '1px solid #F3F4F6',
              paddingBottom: '8px'
            }}>
              {thWeekdays.map((w, idx) => (
                <span key={w} style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  color: idx === 0 ? '#DC2626' : idx === 6 ? '#0A5C8E' : '#6B7280'
                }}>
                  {w}
                </span>
              ))}
            </div>

            {/* ตารางวันปฏิทิน */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(7, 1fr)',
              gap: '6px'
            }}>
              {calendarCells.map((day, idx) => {
                if (day === null) {
                  return <div key={`empty-${idx}`} style={{ minHeight: '52px' }} />;
                }

                const cellDate = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                const isSelected = cellDate === selectedDate;
                
                // Get all appointments for this date cell
                const dayAppts = allAppointments.filter(a => a.date === cellDate);
                const hasAppts = dayAppts.length > 0;
                
                return (
                  <div
                    key={`day-${day}`}
                    onClick={() => setSelectedDate(cellDate)}
                    style={{
                      minHeight: '52px',
                      padding: '6px',
                      background: isSelected ? '#EFF6FF' : '#ffffff',
                      border: isSelected ? '1px solid #3B82F6' : '1px solid #E5E7EB',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      transition: 'all 0.15s ease',
                      position: 'relative'
                    }}
                    onMouseEnter={e => {
                      if (!isSelected) e.currentTarget.style.background = '#F9FAFB';
                    }}
                    onMouseLeave={e => {
                      if (!isSelected) e.currentTarget.style.background = '#ffffff';
                    }}
                  >
                    <span style={{
                      fontSize: '11.5px',
                      fontWeight: isSelected ? 700 : 500,
                      color: isSelected ? '#1E40AF' : '#374151'
                    }}>
                      {day}
                    </span>

                    {/* มาร์กพิเศษเมื่อมีนัดหมาย */}
                    {hasAppts && (
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        background: '#ECFDF5',
                        border: '1px solid #10B981',
                        borderRadius: '4px',
                        padding: '1px 3px',
                        marginTop: '4px'
                      }}>
                        <span style={{
                          fontSize: '8.5px',
                          fontWeight: 700,
                          color: '#047857',
                          whiteSpace: 'nowrap'
                        }}>
                          🟢 {dayAppts.length} เคส
                        </span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* ตารางคิวนัดหมายประจำวันที่เลือก */}
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            {/* Table Header */}
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '16px 20px',
              borderBottom: '1px solid #E5E7EB'
            }}>
              <span style={{ fontSize: '11px', fontWeight: 600, color: '#6B7280', letterSpacing: '0.3px' }}>
                รายการนัดหมายสำหรับวันที่: {formatThaiDateString(selectedDate)} ({filteredApptsForDate.length})
              </span>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  onClick={() => {
                    const todayStr = new Date().toISOString().split("T")[0];
                    setSelectedDate(todayStr);
                    const todayDate = new Date();
                    setCurrentMonth(todayDate.getMonth());
                    setCurrentYear(todayDate.getFullYear());
                  }}
                  className="btn btn-outline"
                  style={{ fontSize: '11px', padding: '5px 12px' }}
                >
                  วันนี้
                </button>
                <button
                  onClick={loadData}
                  className="btn btn-outline"
                  style={{ padding: '5px 9px' }}
                >
                  <RefreshCw size={12} />
                </button>
              </div>
            </div>

            {/* Table */}
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: '#F9FAFB', borderBottom: '1px solid #E5E7EB' }}>
                    {["เวลาตรวจ", "ข้อมูลคนไข้", "บริการตรวจรักษา", "สถานะ", "การดำเนินการ"].map((col, i) => (
                      <th
                        key={col}
                        style={{
                          padding: '11px 16px',
                          textAlign: i === 3 ? 'center' : i === 4 ? 'right' : 'left',
                          fontSize: '11px',
                          fontWeight: 600,
                          color: '#6B7280',
                          letterSpacing: '0.3px',
                          whiteSpace: 'nowrap'
                        }}
                      >
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr>
                      <td colSpan={5} style={{ textAlign: 'center', padding: '56px 16px' }}>
                        <div style={{
                          width: '28px',
                          height: '28px',
                          border: '2px solid #E5E7EB',
                          borderTopColor: '#0A5C8E',
                          borderRadius: '50%',
                          animation: 'spin 0.7s linear infinite',
                          margin: '0 auto'
                        }} />
                      </td>
                    </tr>
                  ) : filteredApptsForDate.length === 0 ? (
                    <tr>
                      <td colSpan={5} style={{ textAlign: 'center', padding: '64px 16px' }}>
                        <Calendar size={44} style={{ color: '#9CA3AF', marginBottom: '16px', opacity: 0.6 }} />
                        <h4 style={{ fontSize: '15px', fontWeight: 600, color: '#374151', marginBottom: '6px' }}>
                          ไม่มีนัดหมายในวันที่เลือก
                        </h4>
                        <p style={{ fontSize: '12px', color: '#6B7280', marginBottom: '20px', maxWidth: '320px', marginInline: 'auto', lineHeight: 1.6 }}>
                          ไม่มีการนัดเข้าตรวจรักษาชีววิทยาสำหรับวันนี้ เริ่มต้นสร้างการจองเพื่อประเมินผลแล็บหรือซักประวัติของคุณหมอได้ทันที
                        </p>
                        <button 
                          onClick={() => setShowModal(true)}
                          className="btn btn-primary"
                          style={{
                            fontSize: '12px',
                            padding: '8px 16px',
                            borderRadius: '6px',
                            fontWeight: 600,
                            boxShadow: '0 2px 4px rgba(13, 148, 136, 0.15)'
                          }}
                        >
                          <Plus size={14} style={{ marginRight: '6px', strokeWidth: 2.5 }} /> นัดหมายผู้ป่วย
                        </button>
                      </td>
                    </tr>
                  ) : (
                    filteredApptsForDate.map((appt) => {
                      const sc = STATUS_CONFIG[appt.status] ?? { label: appt.status || "รอยืนยัน", color: "#6B7280", bg: "#F3F4F6" };
                      const isPending = appt.status === "รอยืนยัน" || appt.status === "Pending" || appt.status === "pending";
                      const isConfirmed = appt.status === "ยืนยันแล้ว" || appt.status === "Confirmed" || appt.status === "confirmed";
                      const isDone = appt.status === "เสร็จสิ้น" || appt.status === "Completed" || appt.status === "completed";
                      const isCancelled = appt.status === "ยกเลิก" || appt.status === "Cancelled" || appt.status === "cancelled";

                      return (
                        <tr
                          key={appt.id}
                          style={{ borderBottom: '1px solid #F3F4F6', transition: 'background 0.1s' }}
                          onMouseEnter={e => (e.currentTarget.style.background = '#FAFAFA')}
                          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                        >
                          {/* TIME */}
                          <td style={{ padding: '14px 16px', verticalAlign: 'middle' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <Clock size={12} style={{ color: '#9CA3AF' }} />
                              <span style={{ fontSize: '13px', fontWeight: 600, color: '#1F2937' }}>
                                {appt.time || "09:00"} น.
                              </span>
                            </div>
                            <div style={{ fontSize: '10px', color: '#9CA3AF', marginTop: '3px', paddingLeft: '18px' }}>
                              30 นาที
                            </div>
                          </td>

                          {/* PATIENT */}
                          <td style={{ padding: '14px 16px', verticalAlign: 'middle' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                              <div style={{
                                width: '34px',
                                height: '34px',
                                background: '#E8F0F5',
                                borderRadius: '4px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontWeight: 600,
                                fontSize: '13px',
                                color: '#0A5C8E',
                                flexShrink: 0
                              }}>
                                {(appt.patient_name || "P").charAt(0).toUpperCase()}
                              </div>
                              <div>
                                <div style={{ fontWeight: 600, fontSize: '13.5px', color: '#1F2937' }}>
                                  {appt.patient_name || "ไม่ทราบชื่อคนไข้"}
                                </div>
                                <div style={{ fontSize: '10px', color: '#9CA3AF', letterSpacing: '0.2px', marginTop: '1px' }}>
                                  HN: {appt.patient_hn || "TSPI-001"}
                                </div>
                              </div>
                            </div>
                          </td>

                          {/* SERVICE */}
                          <td style={{ padding: '14px 16px', verticalAlign: 'middle' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <Stethoscope size={11} style={{ color: '#9CA3AF', flexShrink: 0 }} />
                              <span style={{ fontSize: '12px', color: '#4B5563' }}>
                                {appt.type === "Precision Consultation" ? "การให้คำปรึกษาการแพทย์แม่นยำ" :
                                 appt.type === "Biological Balance Follow-up" ? "ติดตามสมดุลระบบชีววิทยา" :
                                 appt.type === "Mitochondrial Function Assessment" ? "ตรวจประเมินกำลังไมโตคอนเดรีย" :
                                 appt.type === "Silent Inflammation Assessment" ? "ประเมินระดับการอักเสบแอบแฝง" :
                                 appt.type === "Clinical RAG Diagnostics Review" ? "ตรวจสอบวินิจฉัย Clinical RAG" :
                                 appt.type || "การตรวจรักษาทั่วไป"}
                              </span>
                            </div>
                          </td>

                          {/* STATUS */}
                          <td style={{ padding: '14px 16px', verticalAlign: 'middle', textAlign: 'center' }}>
                            <span style={{
                              display: 'inline-block',
                              background: sc.bg,
                              color: sc.color,
                              fontSize: '11px',
                              fontWeight: 600,
                              padding: '3px 10px',
                              borderRadius: '4px',
                              whiteSpace: 'nowrap'
                            }}>
                              {sc.label}
                            </span>
                          </td>

                          {/* ACTIONS */}
                          <td style={{ padding: '14px 16px', verticalAlign: 'middle', textAlign: 'right' }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '4px' }}>
                              {/* AI Analysis */}
                              <Link
                                href={`/doctor/ai-physician?id=${appt.patient_id || appt.patientId}`}
                                className="btn btn-ghost"
                                style={{ padding: '5px 8px' }}
                                title="วิเคราะห์ด้วย AI"
                              >
                                <Brain size={15} style={{ color: '#0A5C8E' }} />
                              </Link>

                              {/* Confirm (Pending only) */}
                              {isPending && (
                                <button
                                  onClick={() => handleStatusChange(appt.id, "confirmed")}
                                  className="btn btn-ghost"
                                  style={{ padding: '5px 8px' }}
                                  title="ยืนยันนัดหมาย"
                                >
                                  <Check size={15} style={{ color: '#059669' }} />
                                </button>
                              )}

                              {/* Complete (Confirmed only) */}
                              {isConfirmed && (
                                <button
                                  onClick={() => handleStatusChange(appt.id, "completed")}
                                  className="btn btn-ghost"
                                  style={{ padding: '5px 8px' }}
                                  title="ทำเครื่องหมายเสร็จสิ้น"
                                >
                                  <CheckCircle2 size={15} style={{ color: '#0A5C8E' }} />
                                </button>
                              )}

                              {/* Cancel (not done/cancelled) */}
                              {!isDone && !isCancelled && (
                                <button
                                  onClick={() => handleStatusChange(appt.id, "cancelled")}
                                  className="btn btn-ghost"
                                  style={{ padding: '5px 8px' }}
                                  title="ยกเลิกนัดหมาย"
                                >
                                  <X size={15} style={{ color: '#DC2626' }} />
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
          
        </div>
      </div>

      {/* ==================== CREATE APPOINTMENT MODAL ==================== */}
      {showModal && (
        <div style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: "rgba(17, 24, 39, 0.6)",
          backdropFilter: "blur(4px)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 1050,
          animation: "fadeIn 0.15s ease-out"
        }}>
          <div className="card p-5 border-0 shadow-lg animate-fade-in" style={{
            width: "500px",
            background: "#ffffff",
            borderRadius: "16px",
            border: "1px solid rgba(0, 0, 0, 0.05)"
          }}>
            {/* Modal Header */}
            <div className="d-flex align-items-center justify-content-between mb-4 pb-2 border-bottom border-light">
              <div className="d-flex align-items-center gap-2">
                <CalendarDays size={18} style={{ color: '#0A5C8E' }} />
                <h3 className="mb-0 fs-6 fw-bold text-gray-800" style={{ letterSpacing: '0.3px', fontSize: '15px' }}>
                  สร้างนัดหมายเข้าตรวจรักษาใหม่
                </h3>
              </div>
              <button 
                onClick={() => setShowModal(false)}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#9CA3AF' }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Body / Form */}
            <form onSubmit={handleSubmit}>
              
              {/* Patient Selector */}
              <div className="mb-3">
                <label className="text-xs fw-semibold text-gray-700 mb-1.5 block" style={{ fontSize: '12px' }}>
                  เลือกผู้ป่วยที่จะนัดหมาย
                </label>
                <select
                  className="form-select text-sm text-gray-800 rounded-3 border-gray-300 shadow-sm"
                  style={{ fontSize: '13px', padding: '8px' }}
                  value={formPatientId}
                  onChange={(e) => setFormPatientId(e.target.value)}
                  required
                >
                  <option value="" disabled>-- เลือกคนไข้ --</option>
                  {patients.length === 0 ? (
                    <option value="" disabled>ไม่มีข้อมูลคนไข้ในระบบ</option>
                  ) : (
                    patients.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.fname} {p.lname} (HN: {p.hn || String(p.id || '').slice(0, 8)})
                      </option>
                    ))
                  )}
                </select>
              </div>

              <div className="row g-3 mb-3">
                {/* Date Picker */}
                <div className="col-6">
                  <label className="text-xs fw-semibold text-gray-700 mb-1.5 block" style={{ fontSize: '12px' }}>วันที่นัดตรวจ</label>
                  <input
                    type="date"
                    className="form-control text-sm text-gray-800 rounded-3 border-gray-300 shadow-sm"
                    style={{ fontSize: '13px' }}
                    value={formDate}
                    onChange={(e) => setFormDate(e.target.value)}
                    required
                  />
                </div>

                {/* Time Picker */}
                <div className="col-6">
                  <label className="text-xs fw-semibold text-gray-700 mb-1.5 block" style={{ fontSize: '12px' }}>เวลานัดหมาย</label>
                  <input
                    type="time"
                    className="form-control text-sm text-gray-800 rounded-3 border-gray-300 shadow-sm"
                    style={{ fontSize: '13px' }}
                    value={formTime}
                    onChange={(e) => setFormTime(e.target.value)}
                    required
                  />
                </div>
              </div>

              {/* Service Type */}
              <div className="mb-3">
                <label className="text-xs fw-semibold text-gray-700 mb-1.5 block" style={{ fontSize: '12px' }}>บริการตรวจรักษาเชิงลึก</label>
                <select
                  className="form-select text-sm text-gray-800 rounded-3 border-gray-300 shadow-sm"
                  style={{ fontSize: '13px', padding: '8px' }}
                  value={formServiceType}
                  onChange={(e) => setFormServiceType(e.target.value)}
                  required
                >
                  <option value="Precision Consultation">การให้คำปรึกษาการแพทย์แม่นยำ (Precision Medicine)</option>
                  <option value="Biological Balance Follow-up">ติดตามสมดุลระบบชีววิทยา (Biological Balance)</option>
                  <option value="Mitochondrial Function Assessment">ตรวจประเมินกำลังไมโตคอนเดรีย (Mitochondrial)</option>
                  <option value="Silent Inflammation Assessment">ประเมินระดับการอักเสบแอบแฝง (Silent Inflammation)</option>
                  <option value="Clinical RAG Diagnostics Review">ตรวจสอบวินิจฉัยด้วยระบบ RAG (Clinical RAG)</option>
                </select>
              </div>

              {/* Status */}
              <div className="mb-4">
                <label className="text-xs fw-semibold text-gray-700 mb-1.5 block" style={{ fontSize: '12px' }}>สถานะการส่งตรวจ</label>
                <div className="d-flex gap-4">
                  <label className="d-flex align-items-center gap-1.5 text-xs text-gray-700 cursor-pointer" style={{ fontSize: '12px' }}>
                    <input 
                      type="radio" 
                      name="status" 
                      value="confirmed" 
                      checked={formStatus === "confirmed"} 
                      onChange={() => setFormStatus("confirmed")} 
                    />
                    ยืนยันนัดทันที (Confirmed)
                  </label>
                  <label className="d-flex align-items-center gap-1.5 text-xs text-gray-700 cursor-pointer" style={{ fontSize: '12px' }}>
                    <input 
                      type="radio" 
                      name="status" 
                      value="pending" 
                      checked={formStatus === "pending"} 
                      onChange={() => setFormStatus("pending")} 
                    />
                    รอการยืนยันนัดตรวจ (Pending)
                  </label>
                </div>
              </div>

              {/* Symptoms / Notes */}
              <div className="mb-4">
                <label className="text-xs fw-semibold text-gray-700 mb-1.5 block" style={{ fontSize: '12px' }}>อาการเบื้องต้น / เหตุผลในการนัดตรวจ (ไม่จำเป็นต้องกรอกก็ได้)</label>
                <textarea
                  rows={3}
                  className="form-control text-sm text-gray-800 rounded-3 border-gray-300 shadow-sm"
                  style={{ fontSize: '13px' }}
                  placeholder="เช่น อ่อนเพลียเรื้อรัง ตรวจประเมินไมโตคอนเดรียเสื่อม หรือนัดหมายรับการวิเคราะห์ผล RAG Chapter 1-18 รายบุคคล"
                  value={formSymptoms}
                  onChange={(e) => setFormSymptoms(e.target.value)}
                />
              </div>

              {/* Action Buttons */}
              <div className="d-flex gap-3 justify-content-end">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="btn btn-outline text-xs font-semibold py-2 px-4"
                  style={{ borderRadius: '6px', fontSize: '12px' }}
                >
                  ยกเลิก
                </button>
                <button
                  type="submit"
                  disabled={submitting || patients.length === 0}
                  className="btn btn-primary text-xs font-semibold py-2 px-4"
                  style={{ borderRadius: '6px', fontSize: '12px' }}
                >
                  {submitting ? "กำลังส่งนัด..." : "สร้างนัดหมายผู้ป่วย"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Spinner keyframes */}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @media (max-width: 900px) {
          .appt-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  );
}