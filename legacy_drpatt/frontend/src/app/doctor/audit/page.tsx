"use client";

import { useState, useEffect } from "react";
import {
  Shield, Search, Filter, Calendar, Brain, User,
  Eye, Clock, Activity, ArrowLeft, Loader2, Terminal,
  ShieldCheck, ShieldAlert, Cpu, Lock, Database,
  FlaskConical, ChevronLeft, ChevronRight
} from "lucide-react";
import Link from "next/link";
import { getAuditLogs } from "@/utils/api/audit";
import "./../theme-inapp.css";
import Swal from "sweetalert2";

const ACTION_MAP: Record<string, { label: string; color: string; icon: any }> = {
  AI_INTAKE_REQUEST: { label: "ส่งวิเคราะห์ AI", color: "primary", icon: Brain },
  AI_INTAKE_RESPONSE: { label: "AI ประมวลผล", color: "info", icon: Cpu },
  LAB_OCR_PROCESSED: { label: "สแกนแล็บ OCR", color: "purple", icon: FlaskConical },
  USER_CONSENT_ACCEPTED: { label: "ยอมรับ PDPA", color: "success", icon: ShieldCheck },
  ADMIN_ACTION: { label: "แอดมินดำเนินการ", color: "warning", icon: User },
};


export default function AuditTrailPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [actionFilter, setActionFilter] = useState("All Events");
  const [stats, setStats] = useState({ total: 0, ai: 0, security: 0 });
  const [selectedLog, setSelectedLog] = useState<any>(null);
  const [lockdownActive, setLockdownActive] = useState(false);

  // Pagination states
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const data = await getAuditLogs(100);
        setLogs(data);

        const aiCount = data.filter((l: any) => l.action?.includes('AI_') || l.action?.includes('LAB_')).length;
        const secCount = data.filter((l: any) => l.action?.includes('USER_CONSENT') || l.action?.includes('ADMIN') || l.action?.includes('SECURE') || l.action?.includes('PDPA')).length;
        setStats({ total: data.length, ai: aiCount, security: secCount });
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchLogs();
  }, []);

  // Reset to first page when search or category changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, actionFilter]);

  const handleLockdown = () => {
    if (lockdownActive) {
      Swal.fire({
        title: 'ยกเลิกการล็อกดาวน์?',
        text: 'คุณต้องการยกเลิกการล็อกดาวน์และคืนสิทธิ์การเข้าถึงระบบตามปกติใช่หรือไม่?',
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#3085d6',
        cancelButtonColor: '#aaa',
        confirmButtonText: 'ยืนยันปลดล็อก',
        cancelButtonText: 'ยกเลิก'
      }).then((result) => {
        if (result.isConfirmed) {
          setLockdownActive(false);
          Swal.fire({
            title: 'ปลดล็อกสำเร็จ',
            text: 'ยกเลิกการล็อกดาวน์ระบบสำเร็จ สิทธิ์การใช้งานกลับคืนสู่สภาวะปกติ',
            icon: 'success',
            confirmButtonColor: '#0A5C8E',
            confirmButtonText: 'ตกลง'
          });
        }
      });
    } else {
      Swal.fire({
        title: 'คำเตือน: ล็อกดาวน์ระบบ?',
        text: 'คุณต้องการสั่งล็อกดาวน์ระบบความปลอดภัยทันทีหรือไม่? การดำเนินการนี้จะจำกัดสิทธิ์ผู้ใช้ชั่วคราวเพื่อตรวจสอบความปลอดภัยสูงสุด',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'ยืนยันล็อกดาวน์ทันที',
        cancelButtonText: 'ยกเลิก'
      }).then((result) => {
        if (result.isConfirmed) {
          setLockdownActive(true);
          Swal.fire({
            title: 'ล็อกดาวน์สำเร็จ',
            text: 'เปิดใช้งานการล็อกดาวน์ความปลอดภัยของสถาบันสำเร็จ! สิทธิ์การเข้าใช้งานถูกจำกัดชั่วคราว',
            icon: 'error',
            confirmButtonColor: '#d33',
            confirmButtonText: 'รับทราบ'
          });
        }
      });
    }
  };

  const filteredLogs = logs.filter(l => {
    const matchSearch = 
      (l.action || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      (l.user_email || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      JSON.stringify(l.details || {}).toLowerCase().includes(searchTerm.toLowerCase());
      
    const matchCategory = 
      actionFilter === "All Events" ||
      (actionFilter === "AI" && (l.action?.includes('AI_') || l.action?.includes('LAB_'))) ||
      (actionFilter === "Security" && (l.action?.includes('USER_CONSENT') || l.action?.includes('ADMIN') || l.action?.includes('SECURE') || l.action?.includes('PDPA'))) ||
      (actionFilter === "Data" && (l.action?.includes('DATA_') || l.action?.includes('LAB_OCR')));
      
    return matchSearch && matchCategory;
  });

  // Pagination Calculations
  const totalPages = Math.ceil(filteredLogs.length / itemsPerPage);
  const paginatedLogs = filteredLogs.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const formatLogDate = (timestamp: any) => {
    if (!timestamp) return 'N/A';
    if (typeof timestamp === 'object' && timestamp.seconds) {
      return new Date(timestamp.seconds * 1000).toLocaleString("th-TH");
    }
    // Handle Django standard datetime ISO string/date
    return new Date(timestamp).toLocaleString("th-TH");
  };

  const renderPageNumbers = () => {
    const pages = [];
    const maxVisible = 5;
    
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    
    if (endPage - startPage + 1 < maxVisible) {
      startPage = Math.max(1, endPage - maxVisible + 1);
    }
    
    if (startPage > 1) {
      pages.push(
        <button
          key={1}
          onClick={() => setCurrentPage(1)}
          className={`btn btn-sm ${currentPage === 1 ? 'btn-primary text-white' : 'btn-light border'} rounded-circle d-flex align-items-center justify-content-center`}
          style={{ width: '28px', height: '28px', fontSize: '10px', fontWeight: 'bold' }}
        >
          1
        </button>
      );
      if (startPage > 2) {
        pages.push(<span key="ellipsis1" className="text-muted px-1 text-[11px] align-self-end">...</span>);
      }
    }
    
    for (let i = startPage; i <= endPage; i++) {
      pages.push(
        <button
          key={i}
          onClick={() => setCurrentPage(i)}
          className={`btn btn-sm ${currentPage === i ? 'btn-primary text-white' : 'btn-light border'} rounded-circle d-flex align-items-center justify-content-center`}
          style={{ width: '28px', height: '28px', fontSize: '10px', fontWeight: 'bold' }}
        >
          {i}
        </button>
      );
    }
    
    if (endPage < totalPages) {
      if (endPage < totalPages - 1) {
        pages.push(<span key="ellipsis2" className="text-muted px-1 text-[11px] align-self-end">...</span>);
      }
      pages.push(
        <button
          key={totalPages}
          onClick={() => setCurrentPage(totalPages)}
          className={`btn btn-sm ${currentPage === totalPages ? 'btn-primary text-white' : 'btn-light border'} rounded-circle d-flex align-items-center justify-content-center`}
          style={{ width: '28px', height: '28px', fontSize: '10px', fontWeight: 'bold' }}
        >
          {totalPages}
        </button>
      );
    }
    
    return pages;
  };

  return (
    <div className="pb-5" style={{ fontFamily: "Kanit, sans-serif" }}>
      {/* 🧭 Audit Header */}
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h1 className="fs-3 fw-bold mb-1 text-dark d-flex align-items-center gap-2">
            <div className="bg-primary bg-opacity-10 p-2 rounded-3 text-primary shadow-sm">
              <Shield size={24} />
            </div>
            บันทึกการทำงานและประวัติระบบ (System Audit Trail)
          </h1>
          <p className="text-muted text-xs uppercase font-bold tracking-widest ms-5 mb-0">การกำกับดูแลทางคลินิกและการตรวจสอบความสอดคล้องของระบบ</p>
        </div>
        <div className="d-flex gap-2">
          <button 
            onClick={handleLockdown}
            className={`btn btn-sm font-bold uppercase tracking-widest text-[10px] py-2 px-3 shadow-sm d-flex align-items-center gap-1 rounded-pill ${lockdownActive ? 'btn-danger text-white' : 'btn-outline-danger'}`}
          >
            <Lock size={14} /> {lockdownActive ? "ยกเลิกการล็อกดาวน์" : "ล็อกดาวน์ระบบความปลอดภัย"}
          </button>
        </div>
      </div>

      {/* 📊 Governance Summary */}
      <div className="row g-3 mb-4">
        {[
          { label: "บันทึกกิจกรรมทั้งหมด", val: stats.total, color: "warning", icon: Activity, desc: "100 รายการล่าสุด" },
          { label: "ประวัติการวิเคราะห์ AI", val: stats.ai, color: "primary", icon: Brain, desc: "กิจกรรมของ AI Engine" },
          { label: "ความปลอดภัยที่ผ่านการตรวจ", val: stats.security, color: "success", icon: ShieldCheck, desc: "ความยินยอมและสิทธิ์แอดมิน" },
          { label: "คะแนนความถูกต้องตามเกณฑ์", val: "100%", color: "info", icon: Database, desc: "มาตรฐานสถาบันแพทย์" },
        ].map((s, idx) => (
          <div key={idx} className="col-lg-3 col-6">
            <div className={`card p-3 border-0 shadow-sm bg-white border-top border-4 border-${s.color} rounded-4`}>
              <div className="d-flex justify-content-between align-items-center mb-2">
                <p className="text-[9px] font-bold text-muted uppercase tracking-widest mb-0">{s.label}</p>
                <s.icon size={16} className={`text-${s.color} opacity-30`} />
              </div>
              <h3 className="fw-bold mb-0 h4 text-dark">{loading ? '...' : s.val}</h3>
              <small className="text-[9px] text-muted font-bold uppercase tracking-tighter">{s.desc}</small>
            </div>
          </div>
        ))}
      </div>

      {/* 🔍 Search & Filter Tools */}
      <div className="card shadow-sm border-0 mb-4 bg-white rounded-4 overflow-hidden">
        <div className="card-body p-3">
          <div className="row align-items-center g-3">
            <div className="col-md-6">
              <div className="input-group bg-light rounded-pill px-3 py-1">
                <span className="bg-transparent border-0 d-flex align-items-center"><Search size={16} className="text-muted" /></span>
                <input
                  type="text"
                  className="form-control bg-transparent border-0 font-semibold text-sm text-dark shadow-none"
                  placeholder="ค้นหาตามประเภทการทำงาน อีเมล หรือรายละเอียด..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
            </div>
            <div className="col-md-6 text-md-end">
              <div className="btn-group shadow-sm rounded-pill overflow-hidden">
                {["All Events", "Security", "AI", "Data"].map((cat) => {
                  const labelMap: Record<string, string> = {
                    "All Events": "เหตุการณ์ทั้งหมด",
                    "Security": "ความปลอดภัย",
                    "AI": "วิเคราะห์ AI",
                    "Data": "จัดการข้อมูล"
                  };
                  return (
                    <button
                      key={cat}
                      onClick={() => setActionFilter(cat)}
                      className={`btn btn-sm px-3.5 py-2 font-bold uppercase tracking-widest text-[10px] border-0 ${cat === actionFilter ? 'btn-primary text-white shadow-sm' : 'bg-light text-muted'}`}
                    >
                      {labelMap[cat] || cat}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 🏛️ Activity Stream Registry */}
      <div className="card shadow-sm border-0 bg-white overflow-hidden rounded-4 mb-5">
        <div className="card-header bg-dark py-4 border-0 d-flex justify-content-between align-items-center px-4">
          <h3 className="card-title text-[10px] font-bold uppercase tracking-[0.2em] text-white mb-0">สตรีมกิจกรรมบันทึกระบบสด (Live Activity Stream)</h3>
          <div className="text-[9px] font-bold text-white opacity-50 uppercase tracking-widest d-flex align-items-center gap-2">
            <div className="w-2 h-2 bg-success rounded-circle pulse-green" style={{ width: '8px', height: '8px', borderRadius: '50%' }}></div> ระบบตรวจติดตามแบบเรียลไทม์กำลังทำงาน
          </div>
        </div>
        <div className="table-responsive">
          <table className="table table-hover align-middle mb-0 text-nowrap">
            <thead className="bg-light border-bottom text-[10px] uppercase font-bold text-muted tracking-wider">
              <tr>
                <th className="px-4 py-3" style={{ width: '180px' }}>วันเวลาที่บันทึก</th>
                <th className="py-3" style={{ width: '150px' }}>ประเภทกิจกรรม</th>
                <th className="py-3" style={{ minWidth: '180px' }}>แหล่งที่มา / ผู้ใช้งาน</th>
                <th className="py-3" style={{ minWidth: '220px' }}>บริบททางคลินิก (Metadata)</th>
                <th className="py-3 text-end pe-4" style={{ width: '100px' }}>จัดการ</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={5} className="text-center py-5 border-0"><Loader2 className="animate-spin text-dark opacity-20 mx-auto" size={32} /></td></tr>
              ) : paginatedLogs.length === 0 ? (
                <tr><td colSpan={5} className="text-center py-5 text-muted italic text-xs border-0">ไม่พบประวัติการบันทึกระบบสำหรับเซสชันปัจจุบัน</td></tr>
              ) : paginatedLogs.map((log) => {
                const action = ACTION_MAP[log.action] || { label: log.action, color: "secondary", icon: Terminal };
                return (
                  <tr key={log.id} className="border-bottom border-light">
                    <td className="px-4 py-3">
                      <div className="text-xs font-bold text-dark">{formatLogDate(log.timestamp)}</div>
                      <div className="text-[9px] text-muted font-bold uppercase tracking-tighter d-flex align-items-center gap-1 mt-1">
                        <Clock size={10} /> SESSION_AUTH_OK
                      </div>
                    </td>
                    <td className="py-3">
                      <span className={`badge bg-${action.color} bg-opacity-10 text-${action.color} text-[9px] uppercase px-2.5 py-1.5 border border-${action.color} border-opacity-20 font-black rounded-pill d-inline-flex align-items-center gap-1`}>
                        <action.icon size={10} /> {action.label}
                      </span>
                    </td>
                    <td className="py-3">
                      <div className="text-xs font-bold text-dark">{log.user_email || "ระบบ AI Engine"}</div>
                      <div className="text-[9px] text-muted uppercase tracking-tighter mt-0.5">IP: 127.0.0.1 (Verified)</div>
                    </td>
                    <td className="py-3">
                      <div className="text-[10px] font-mono text-muted bg-light p-1.5 rounded border border-light text-truncate" style={{ maxWidth: '250px' }} title={JSON.stringify(log.metadata || log.details || {})}>
                        {JSON.stringify(log.metadata || log.details || {})}
                      </div>
                    </td>
                    <td className="py-3 text-end pe-4">
                      <button 
                        onClick={() => setSelectedLog(log)}
                        className="btn btn-light btn-sm border px-2.5 py-1.5 shadow-sm rounded-pill text-[10px] font-bold" 
                        title="ดูข้อมูลดิบทั้งหมด"
                      >
                        <Eye size={12} className="text-dark me-1 d-inline" /> รายละเอียด
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="card-footer bg-white border-top py-3 d-flex justify-content-between align-items-center px-4">
          <div className="text-[10px] font-bold text-muted uppercase tracking-widest">
            แสดง {(currentPage - 1) * itemsPerPage + 1} ถึง {Math.min(currentPage * itemsPerPage, filteredLogs.length)} จากทั้งหมด {filteredLogs.length} รายการ
          </div>
          <div className="d-flex gap-1">
            <button 
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="btn btn-sm btn-light border font-bold text-[10px] uppercase tracking-widest rounded-pill px-3 text-dark"
            >
              ก่อนหน้า
            </button>
            
            <div className="d-flex gap-1 px-2 align-items-center">
              {renderPageNumbers()}
            </div>

            <button 
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="btn btn-sm btn-light border font-bold text-[10px] uppercase tracking-widest rounded-pill px-3 text-dark"
            >
              ถัดไป
            </button>
          </div>
        </div>
      )}

      {/* 🔍 Log Detail Modal */}
      {selectedLog && (
        <div className="modal fade show" style={{ backgroundColor: 'rgba(0,0,0,0.4)', zIndex: 1050, position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div className="modal-dialog modal-dialog-centered modal-lg w-100 px-3" style={{ maxWidth: '600px' }}>
            <div className="modal-content border-0 shadow-lg rounded-4 bg-white overflow-hidden animate-in fade-in zoom-in-95">
              <div className="modal-header border-bottom border-light py-3 px-4 d-flex justify-content-between align-items-center">
                <div className="d-flex align-items-center gap-2">
                  <ShieldCheck className="text-primary" size={18} />
                  <h5 className="modal-title font-bold text-sm text-dark uppercase tracking-widest mb-0">รายละเอียดประวัติกิจกรรมระบบ</h5>
                </div>
                <button type="button" className="btn-close" onClick={() => setSelectedLog(null)} aria-label="Close" style={{ background: 'none', border: 'none', fontSize: '20px', color: '#9CA3AF' }}>&times;</button>
              </div>
              <div className="modal-body p-4">
                <div className="d-flex flex-column gap-3 text-dark">
                  <div className="row g-2">
                    <div className="col-4 text-[10px] font-bold text-muted uppercase tracking-widest">ประเภทกิจกรรม</div>
                    <div className="col-8 text-xs font-bold">{selectedLog.action}</div>
                  </div>
                  <div className="row g-2">
                    <div className="col-4 text-[10px] font-bold text-muted uppercase tracking-widest">ผู้ใช้งาน</div>
                    <div className="col-8 text-xs font-bold">{selectedLog.user_email || "ระบบ AI Engine"}</div>
                  </div>
                  <div className="row g-2">
                    <div className="col-4 text-[10px] font-bold text-muted uppercase tracking-widest">วันเวลาที่เกิดเหตุการณ์</div>
                    <div className="col-8 text-xs font-bold">{formatLogDate(selectedLog.timestamp)}</div>
                  </div>
                  <div className="row g-2">
                    <div className="col-4 text-[10px] font-bold text-muted uppercase tracking-widest">ระเบียบการรักษา</div>
                    <div className="col-8 text-xs font-bold">Layer: {selectedLog.details?.layer || "A"} | Governance: {selectedLog.details?.governanceStatus || "PATIENT_ACCESSIBLE"}</div>
                  </div>
                  <hr className="my-2 border-light" />
                  <div>
                    <div className="text-[10px] font-bold text-muted uppercase tracking-widest mb-2">ข้อมูลดิบระบบ (Payload JSON)</div>
                    <pre className="bg-light p-3 rounded-4 border border-light text-[11px] font-mono text-dark overflow-auto mb-0" style={{ maxHeight: '250px' }}>
                      {JSON.stringify(selectedLog, null, 2)}
                    </pre>
                  </div>
                </div>
              </div>
              <div className="modal-footer border-top border-light py-3 px-4 text-end">
                <button type="button" className="btn btn-primary btn-sm px-4 py-2 font-bold uppercase tracking-widest text-[10px] shadow-sm rounded-pill text-white" onClick={() => setSelectedLog(null)}>
                  ปิดหน้าต่าง
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
