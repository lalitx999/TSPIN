"use client";

import { useState, useEffect } from "react";
import {
   ClipboardCheck, CheckCircle, XCircle, AlertTriangle,
   Clock, RefreshCw, User, Brain, Edit3, Shield,
   Search, Zap, ShieldCheck,
   ChevronDown, ChevronUp, Loader2, Filter, Settings2,
   ArrowRightCircle, CheckSquare, ChevronLeft, ChevronRight
} from "lucide-react";
import Link from "next/link";
import { getValidations, updateValidationStatus } from "@/utils/api/services";
import "./../theme-inapp.css";
import Swal from "sweetalert2";

const STATUS_MAP: any = {
   ai_generated: { label: "สร้างโดย AI", color: "info" },
   pending_review: { label: "รอแพทย์สอบทาน", color: "warning" },
   staff_reviewed: { label: "ตรวจสอบแล้ว", color: "success" },
   rejected: { label: "ปฏิเสธ / ทบทวน", color: "danger" }
};

export default function ValidationsPage() {
   const [validations, setValidations] = useState<any[]>([]);
   const [loading, setLoading] = useState(true);
   const [expandedId, setExpandedId] = useState<string | null>(null);
   const [searchTerm, setSearchTerm] = useState("");
   const [statusFilter, setStatusFilter] = useState("All");

   // Pagination States
   const [currentPage, setCurrentPage] = useState(1);
   const itemsPerPage = 10;

   // Reset to page 1 when search or filter changes
   useEffect(() => {
      setCurrentPage(1);
   }, [searchTerm, statusFilter]);

   const loadValidations = async () => {
      setLoading(true);
      try {
         const data = await getValidations();
         setValidations(data);
      } catch (err) {
         console.error("Error loading validations:", err);
      } finally {
         setLoading(false);
      }
   };

   useEffect(() => {
      loadValidations();
   }, []);

   const handleUpdateStatus = async (id: string, newStatus: string) => {
      try {
         await updateValidationStatus(id, newStatus);
         
         Swal.fire({
            icon: 'success',
            title: 'อัปเดตสถานะสำเร็จ',
            text: 'ปรับเปลี่ยนสถานะการตรวจสอบความถูกต้องเรียบร้อยแล้วครับ',
            confirmButtonText: 'ตกลง',
            confirmButtonColor: '#0A5C8E',
            timer: 1500
         });
         
         await loadValidations();
      } catch (error) {
         console.error("Error updating validation status:", error);
         Swal.fire({
            icon: 'error',
            title: 'เกิดข้อผิดพลาด',
            text: 'ไม่สามารถปรับเปลี่ยนสถานะการตรวจสอบได้',
            confirmButtonText: 'ตกลง',
            confirmButtonColor: '#0A5C8E'
         });
      }
   };

   const filteredValidations = validations.filter(item => {
      const matchSearch = item.patient?.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          item.type?.toLowerCase().includes(searchTerm.toLowerCase());
      const matchStatus = statusFilter === "All" || item.status === statusFilter;
      return matchSearch && matchStatus;
   });

   // Pagination Calculations
   const totalPages = Math.ceil(filteredValidations.length / itemsPerPage);
   const paginatedValidations = filteredValidations.slice(
      (currentPage - 1) * itemsPerPage,
      currentPage * itemsPerPage
   );

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
         {/* 🧭 Header Section */}
         <div className="d-flex justify-content-between align-items-end mb-4">
            <div>
               <h1 className="fs-3 fw-bold mb-1 text-dark d-flex align-items-center gap-2">
                  <div className="bg-primary bg-opacity-10 p-2 rounded-3 text-primary shadow-sm">
                     <ClipboardCheck size={24} />
                  </div>
                  สอบทานและรับรองผลทางคลินิก (Clinical Validations)
               </h1>
               <p className="text-muted text-xs uppercase font-bold tracking-widest ms-5 mb-0">สถานีสอบทานความถูกต้องและประกอบการตัดสินใจทางการแพทย์</p>
            </div>
            <div className="d-flex gap-2">
               <button 
                  onClick={loadValidations}
                  disabled={loading}
                  className="btn btn-outline-primary fw-bold uppercase tracking-widest text-[10px] py-2 px-4 shadow-sm d-flex align-items-center gap-2 rounded-pill"
               >
                  <RefreshCw size={14} className={loading ? "animate-spin" : ""} /> รีเฟรชรายการ
               </button>
            </div>
         </div>

         <div className="row g-4">
            {/* 🔍 Search & Filters Hub */}
            <div className="col-lg-12">
               <div className="card shadow-sm border-0 bg-white mb-2 rounded-4 overflow-hidden">
                  <div className="card-body p-4">
                     <div className="row align-items-center g-3">
                        <div className="col-md-9">
                           <div className="position-relative">
                              <Search size={16} className="position-absolute top-50 start-0 translate-middle-y ms-3 text-muted" />
                              <input
                                 type="text"
                                 className="form-control rounded-pill bg-light border-0 py-2.5 ps-5 pe-3 text-sm font-semibold text-dark"
                                 placeholder="ค้นหาตามชื่อคนไข้ หรือประเภทการตรวจวิเคราะห์..."
                                 value={searchTerm}
                                 onChange={(e) => setSearchTerm(e.target.value)}
                              />
                           </div>
                        </div>
                        <div className="col-md-3 text-md-end">
                           <select 
                              className="form-select rounded-pill bg-light border-0 text-xs font-bold py-2.5 px-3 shadow-none w-100 text-dark"
                              value={statusFilter}
                              onChange={(e) => setStatusFilter(e.target.value)}
                           >
                              <option value="All">ทุกสถานะการสอบทาน</option>
                              <option value="pending_review">รอแพทย์สอบทาน</option>
                              <option value="staff_reviewed">ตรวจสอบเสร็จสิ้น</option>
                              <option value="ai_generated">วิเคราะห์โดย AI</option>
                           </select>
                        </div>
                     </div>
                  </div>
               </div>
            </div>

            {/* 📋 Validation List */}
            <div className="col-lg-12">
               <div className="d-flex flex-column gap-3">
                  {loading ? (
                     <div className="text-center py-5 card border-0 shadow-sm bg-white rounded-4">
                        <Loader2 className="animate-spin text-primary opacity-20 mx-auto mb-2" size={32} />
                        <p className="text-muted text-xs font-bold mb-0">กำลังโหลดรายการสอบทาน...</p>
                     </div>
                  ) : paginatedValidations.length === 0 ? (
                     <div className="text-center py-5 card border-0 shadow-sm bg-white rounded-4">
                        <div className="opacity-10 mb-2"><CheckSquare size={48} className="mx-auto" /></div>
                        <p className="text-muted text-xs font-bold mb-0">ไม่พบรายการภารกิจการสอบทานที่ตรงตามเงื่อนไข</p>
                     </div>
                  ) : paginatedValidations.map((item) => {
                     const statusConfig = STATUS_MAP[item.status] || STATUS_MAP.pending_review;
                     const isUrgent = item.burden > 70 || item.urgent;
                     return (
                        <div key={item.id} className={`card border-0 shadow-sm bg-white overflow-hidden rounded-4 transition-all hover:shadow-md ${isUrgent ? 'border-start border-4 border-danger' : 'border-start border-4 border-primary'}`}>
                           <div
                              className="card-header bg-transparent py-3 d-flex align-items-center gap-3 cursor-pointer border-0"
                              onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
                           >
                              <div className={`${isUrgent ? 'bg-danger' : 'bg-primary'} text-white rounded-circle shadow-sm d-flex align-items-center justify-content-center`} style={{ width: '42px', height: '42px' }}>
                                 {isUrgent ? <AlertTriangle size={20} /> : <ClipboardCheck size={20} />}
                              </div>
                              <div className="flex-grow-1">
                                 <div className="d-flex align-items-center gap-2 mb-0">
                                    <h6 className="fw-bold text-dark m-0 text-sm">{item.patient || "ไม่ระบุชื่อคนไข้"}</h6>
                                    <span className={`badge bg-${statusConfig.color} bg-opacity-10 text-${statusConfig.color} text-[9px] uppercase px-2 py-1.5 border border-${statusConfig.color} border-opacity-20 font-black rounded-pill`}>
                                       {statusConfig.label}
                                    </span>
                                    {isUrgent && <span className="text-[10px] text-danger font-black uppercase animate-pulse ms-2">● ตรวจสอบด่วน</span>}
                                 </div>
                                 <div className="d-flex gap-3 text-[10px] text-muted font-bold uppercase mt-2 tracking-widest">
                                    <span>ประเภท: {item.type || "การตรวจวิเคราะห์ทั่วไป"}</span>
                                    <span>• {item.createdAt ? new Date(item.createdAt).toLocaleDateString("th-TH") : "เมื่อสักครู่"}</span>
                                    <span className={item.burden > 70 ? 'text-danger fw-black' : 'text-primary'}>คะแนนความตึงตัว (Burden Score): {item.burden || 0}%</span>
                                 </div>
                              </div>
                              <div className="text-muted">
                                 {expandedId === item.id ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                              </div>
                           </div>

                           {expandedId === item.id && (
                              <div className="card-body p-4 pt-0 border-top border-light animate-in fade-in slide-in-from-top-2">
                                 <div className="row g-4 mt-2">
                                    <div className="col-md-8 border-end border-light pr-md-4">
                                       <div className="p-4 bg-light rounded-4 mb-4 border border-light shadow-sm">
                                          <div className="d-flex align-items-center gap-2 mb-2 text-dark">
                                             <Brain size={16} className="text-primary" />
                                             <span className="text-[10px] font-black uppercase tracking-widest">ผลการประเมินวิเคราะห์โดย AI</span>
                                          </div>
                                          <p className="text-xs font-bold text-dark mb-0 leading-relaxed italic">"{item.findings || "ระบบวิเคราะห์พบความผิดปกติที่อาจเกิดขึ้น โปรดให้แพทย์ทบทวนความถูกต้อง"}"</p>
                                       </div>

                                       <div className="d-flex gap-2">
                                          <button 
                                             onClick={() => handleUpdateStatus(item.id, 'staff_reviewed')}
                                             disabled={item.status === 'staff_reviewed'}
                                             className="btn btn-success btn-sm px-4 font-bold uppercase tracking-widest text-[10px] shadow-sm d-flex align-items-center gap-2 py-2 rounded-pill text-white"
                                          >
                                             <CheckCircle size={14} /> อนุมัติผลการวินิจฉัย
                                          </button>
                                          <button 
                                             onClick={() => handleUpdateStatus(item.id, 'rejected')}
                                             disabled={item.status === 'rejected'}
                                             className="btn btn-outline-danger btn-sm px-4 font-bold uppercase tracking-widest text-[10px] shadow-sm d-flex align-items-center gap-2 py-2 bg-white rounded-pill"
                                          >
                                             <XCircle size={14} /> แจ้งให้ทบทวนเพิ่มเติม
                                          </button>
                                       </div>
                                    </div>
                                    <div className="col-md-4 pl-md-4 d-flex flex-column gap-3">
                                       <div className="p-3 bg-primary bg-opacity-5 rounded-4 d-flex align-items-center gap-3 border border-primary border-opacity-10 shadow-sm">
                                          <div className="text-primary bg-white p-2 rounded-circle"><Shield size={16} /></div>
                                          <div>
                                             <div className="text-[9px] font-bold text-muted uppercase tracking-widest">ระดับความเชื่อมั่นของระเบียบการ</div>
                                             <div className="text-xs font-black text-dark tracking-tighter">ได้รับการรับรองระดับ 4</div>
                                          </div>
                                       </div>
                                       <div className="p-3 bg-success bg-opacity-5 border border-success border-opacity-10 rounded-4 d-flex align-items-center gap-3 shadow-sm">
                                          <div className="text-success bg-white p-2 rounded-circle"><ShieldCheck size={16} /></div>
                                          <div>
                                             <div className="text-[9px] font-bold text-muted uppercase tracking-widest">การตรวจสอบอัลกอริทึม</div>
                                             <div className="text-xs font-black text-dark tracking-tighter">ความถูกต้องผ่านการยืนยัน</div>
                                          </div>
                                       </div>
                                    </div>
                                 </div>
                              </div>
                           )}
                        </div>
                     );
                  })}
               </div>

               {/* Pagination Controls */}
               {totalPages > 1 && (
                  <div className="d-flex justify-content-between align-items-center p-4 mt-3 border border-light bg-white rounded-4 shadow-sm">
                     <div className="text-[11px] font-bold text-muted uppercase tracking-wider">
                        แสดง {Math.min(filteredValidations.length, (currentPage - 1) * itemsPerPage + 1)} - {Math.min(filteredValidations.length, currentPage * itemsPerPage)} จากทั้งหมด {filteredValidations.length} รายการ
                     </div>
                     <div className="d-flex gap-1 align-items-center">
                        <button
                           onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                           disabled={currentPage === 1}
                           className="btn btn-sm btn-light border rounded-pill px-3 py-1.5 font-bold text-[10px] d-flex align-items-center gap-1 shadow-sm text-dark"
                        >
                           <ChevronLeft size={10} /> ก่อนหน้า
                        </button>
                        
                        <div className="d-flex gap-1 px-2">
                           {renderPageNumbers()}
                        </div>

                        <button
                           onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                           disabled={currentPage === totalPages}
                           className="btn btn-sm btn-light border rounded-pill px-3 py-1.5 font-bold text-[10px] d-flex align-items-center gap-1 shadow-sm text-dark"
                        >
                           ถัดไป <ChevronRight size={10} />
                        </button>
                     </div>
                  </div>
               )}
            </div>
         </div>

         <div className="mt-5 p-4 bg-primary bg-opacity-5 rounded-4 border border-primary border-opacity-10 d-flex align-items-center gap-3">
            <div className="bg-primary text-white p-2 rounded-circle shadow-sm">
               <ShieldCheck size={20} />
            </div>
            <div>
               <h6 className="fw-bold text-primary mb-1 text-sm uppercase tracking-widest">โปรโตคอลสนับสนุนการตัดสินใจทางสถาบัน (Clinical Decision Support)</h6>
               <p className="text-[11px] text-muted mb-0">การสอบทานความถูกต้องโดยแพทย์ถือเป็นข้อกำหนดที่สำคัญในการรักษามาตรฐานความปลอดภัยคนไข้ ผลวิเคราะห์ทั้งหมดที่สร้างโดย AI จะต้องผ่านการตรวจสอบร่วมกับความเห็นทางคลินิกของแพทย์ผู้เชี่ยวชาญทุกครั้ง ก่อนที่จะทำการบันทึกเข้าสู่เวชระเบียนถาวรของคนไข้</p>
            </div>
         </div>

         <style jsx>{`
            .animate-spin { animation: spin 1s linear infinite; }
            @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
            .shadow-xs { box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
         `}</style>
      </div>
   );
}
