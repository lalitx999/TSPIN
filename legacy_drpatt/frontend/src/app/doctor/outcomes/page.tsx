"use client";

import { useState, useEffect } from "react";
import {
   TrendingUp, TrendingDown, Minus, Plus, RefreshCw,
   User, BarChart2, CheckCircle, AlertTriangle,
   ArrowRight, Info, Pill, Calendar, Activity,
   Trophy, Users, Target, ShieldCheck, ArrowUpRight,
   ArrowDownRight, Loader2, Search, X, FolderHeart,
   ChevronLeft, ChevronRight
} from "lucide-react";
import Link from "next/link";
import { getOutcomes, createOutcome } from "@/utils/api/services";
import "./../theme-inapp.css";
import Swal from "sweetalert2";

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: any; bg: string }> = {
   improved: { label: "อาการดีขึ้น", color: "success", icon: ArrowDownRight, bg: "success" },
   stable: { label: "คงที่", color: "info", icon: Minus, bg: "info" },
   worsened: { label: "เฝ้าระวัง", color: "danger", icon: ArrowUpRight, bg: "danger" },
};

export default function OutcomesPage() {
   const [outcomes, setOutcomes] = useState<any[]>([]);
   const [loading, setLoading] = useState(true);
   const [showForm, setShowForm] = useState(false);
   const [submitting, setSubmitting] = useState(false);

   // Search and Pagination States
   const [searchTerm, setSearchTerm] = useState("");
   const [currentPage, setCurrentPage] = useState(1);
   const itemsPerPage = 10;

   // Reset to page 1 when search query changes
   useEffect(() => {
      setCurrentPage(1);
   }, [searchTerm]);

   // Form state
   const [patientIdentity, setPatientIdentity] = useState("");
   const [baseline, setBaseline] = useState("");
   const [current, setCurrent] = useState("");

   const loadOutcomes = async () => {
      setLoading(true);
      try {
         const data = await getOutcomes();
         setOutcomes(data);
      } catch (err) {
         console.error("Error loading outcomes:", err);
      } finally {
         setLoading(false);
      }
   };

   useEffect(() => {
      loadOutcomes();
   }, []);

   const handleSubmit = async () => {
      if (!patientIdentity || !baseline || !current) {
         Swal.fire({
            icon: 'warning',
            title: 'กรอกข้อมูลไม่ครบถ้วน',
            text: 'กรุณากรอกข้อมูลการประเมินให้ครบถ้วนทุกช่องครับ',
            confirmButtonText: 'ตกลง',
            confirmButtonColor: '#0A5C8E'
         });
         return;
      }
      setSubmitting(true);
      
      const before = Number(baseline);
      const after = Number(current);
      let status = "stable";
      if (after < before) status = "improved";
      else if (after > before) status = "worsened";

      try {
         await createOutcome({
            name: patientIdentity,
            before,
            after,
            status,
         });
         setShowForm(false);
         setPatientIdentity("");
         setBaseline("");
         setCurrent("");
         
         Swal.fire({
            icon: 'success',
            title: 'บันทึกสำเร็จ',
            text: 'บันทึกประวัติการฟื้นตัวของคนไข้เรียบร้อยแล้วครับ',
            confirmButtonText: 'ตกลง',
            confirmButtonColor: '#0A5C8E'
         });
         
         await loadOutcomes();
      } catch (err) {
         console.error("Error saving outcome:", err);
         Swal.fire({
            icon: 'error',
            title: 'เกิดข้อผิดพลาด',
            text: 'ไม่สามารถบันทึกข้อมูลผลลัพธ์ทางคลินิกได้',
            confirmButtonText: 'ตกลง',
            confirmButtonColor: '#0A5C8E'
         });
      } finally {
         setSubmitting(false);
      }
   };

   // Computations for real metrics
   const totalTracked = outcomes.length;
   const improvedCount = outcomes.filter(o => o.status === "improved").length;
   const stableCount = outcomes.filter(o => o.status === "stable").length;
   const improvedRate = totalTracked > 0 ? ((improvedCount / totalTracked) * 100).toFixed(1) : "0.0";
   const stableRate = totalTracked > 0 ? ((stableCount / totalTracked) * 100).toFixed(1) : "0.0";
   
   let totalDelta = 0;
   outcomes.forEach(o => {
      totalDelta += (Number(o.after) - Number(o.before));
   });
   const avgDelta = totalTracked > 0 ? (totalDelta / totalTracked).toFixed(1) : "0.0";

   // Filtered Outcomes
   const filteredOutcomes = outcomes.filter(o => 
      o.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (o.id && String(o.id).toLowerCase().includes(searchTerm.toLowerCase()))
   );

   // Pagination Calculations
   const totalPages = Math.ceil(filteredOutcomes.length / itemsPerPage);
   const paginatedOutcomes = filteredOutcomes.slice(
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
                     <Trophy size={24} />
                  </div>
                  ผลลัพธ์การรักษาทางคลินิก (Clinical Outcomes)
               </h1>
               <p className="text-muted text-xs uppercase font-bold tracking-widest ms-5 mb-0">การวิเคราะห์การฟื้นตัวและประสิทธิภาพการรักษาของคนไข้</p>
            </div>
            <div className="d-flex gap-2">
               <button
                  onClick={loadOutcomes}
                  disabled={loading}
                  className="btn btn-outline-primary fw-bold uppercase tracking-widest text-[10px] py-2 px-3 shadow-sm d-flex align-items-center gap-2 rounded-pill"
               >
                  <RefreshCw size={14} className={loading ? "animate-spin" : ""} /> รีเฟรชข้อมูล
               </button>
               <button
                  onClick={() => setShowForm(!showForm)}
                  className={`btn fw-bold uppercase tracking-widest text-[10px] py-2 px-3 shadow-sm d-flex align-items-center gap-2 rounded-pill ${showForm ? 'btn-light border bg-white text-dark' : 'btn-primary'}`}
               >
                  {showForm ? <X size={14} /> : <Plus size={14} />} {showForm ? 'ยกเลิก' : 'บันทึกผลลัพธ์ใหม่'}
               </button>
            </div>
         </div>

         {/* 📊 High-Level Metrics */}
         <div className="row g-3 mb-4">
            <div className="col-lg-3 col-6">
               <div className="card p-3 border-0 shadow-sm bg-white h-100 rounded-4" style={{ background: 'linear-gradient(145deg, #ffffff, #f8f9fa)'}}>
                  <div className="d-flex justify-content-between align-items-center mb-2">
                     <p className="text-[10px] font-bold text-muted uppercase tracking-widest mb-0">อัตราการฟื้นตัวดีขึ้น</p>
                     <TrendingUp size={16} className="text-success opacity-50" />
                  </div>
                  <h3 className="fw-black mb-1 h3 text-dark">{loading ? "-" : `${improvedRate}%`}</h3>
                  <small className="text-[10px] text-muted font-bold uppercase tracking-tighter">สัดส่วนเคสที่มีทิศทางดีขึ้น</small>
               </div>
            </div>
            <div className="col-lg-3 col-6">
               <div className="card p-3 border-0 shadow-sm bg-white h-100 rounded-4" style={{ background: 'linear-gradient(145deg, #ffffff, #f8f9fa)'}}>
                  <div className="d-flex justify-content-between align-items-center mb-2">
                     <p className="text-[10px] font-bold text-muted uppercase tracking-widest mb-0">สัดส่วนเคสคงที่</p>
                     <Activity size={16} className="text-info opacity-50" />
                  </div>
                  <h3 className="fw-black mb-1 h3 text-dark">{loading ? "-" : `${stableRate}%`}</h3>
                  <small className="text-[10px] text-muted font-bold uppercase tracking-tighter">สัดส่วนเคสที่ทรงระดับอาการได้</small>
               </div>
            </div>
            <div className="col-lg-3 col-6">
               <div className="card p-3 border-0 shadow-sm bg-white h-100 rounded-4" style={{ background: 'linear-gradient(145deg, #ffffff, #f8f9fa)'}}>
                  <div className="d-flex justify-content-between align-items-center mb-2">
                     <p className="text-[10px] font-bold text-muted uppercase tracking-widest mb-0">ความตึงตัวที่ลดลงเฉลี่ย</p>
                     <Target size={16} className="text-primary opacity-50" />
                  </div>
                  <h3 className="fw-black mb-1 h3 text-dark">{loading ? "-" : `${avgDelta}%`}</h3>
                  <small className="text-[10px] text-muted font-bold uppercase tracking-tighter">ค่าเฉลี่ย NSS ที่ลดลงสะสม</small>
               </div>
            </div>
            <div className="col-lg-3 col-6">
               <div className="card p-3 border-0 shadow-sm bg-white h-100 rounded-4" style={{ background: 'linear-gradient(145deg, #ffffff, #f8f9fa)'}}>
                  <div className="d-flex justify-content-between align-items-center mb-2">
                     <p className="text-[10px] font-bold text-muted uppercase tracking-widest mb-0">จำนวนเคสที่ติดตาม</p>
                     <Users size={16} className="text-dark opacity-30" />
                  </div>
                  <h3 className="fw-black mb-1 h3 text-dark">{loading ? "-" : totalTracked}</h3>
                  <small className="text-[10px] text-muted font-bold uppercase tracking-tighter">เคสการรักษาทั้งหมดในระบบ</small>
               </div>
            </div>
         </div>

         <div className="row g-4">
            {/* New Outcome Form Area */}
            {showForm && (
               <div className="col-12 animate-in fade-in slide-in-from-top-4">
                  <div className="card border-0 shadow-sm bg-white rounded-4 overflow-hidden mb-1 border-primary border-opacity-25 border-top border-4">
                     <div className="card-header bg-transparent py-3 px-4 border-0">
                          <h5 className="fw-bold text-primary text-xs uppercase tracking-widest mb-0">บันทึกประวัติการฟื้นตัวของคนไข้ใหม่</h5>
                     </div>
                     <div className="card-body p-4 pt-0">
                        <div className="row g-3">
                           <div className="col-md-4">
                              <label className="text-[10px] font-bold text-muted uppercase tracking-widest mb-2 d-block">ระบุตัวตนคนไข้</label>
                              <div className="position-relative">
                                 <Search size={14} className="position-absolute top-50 start-0 translate-middle-y ms-3 text-muted" />
                                 <input 
                                    type="text" 
                                    className="form-control rounded-pill bg-light border-0 py-2.5 ps-5 pe-3 text-sm font-semibold text-dark" 
                                    placeholder="หมายเลข HN หรือ ชื่อคนไข้..." 
                                    value={patientIdentity}
                                    onChange={(e) => setPatientIdentity(e.target.value)}
                                 />
                              </div>
                           </div>
                           <div className="col-md-4">
                              <label className="text-[10px] font-bold text-muted uppercase tracking-widest mb-2 d-block">คะแนนความตึงตัวเริ่มต้น (NSS Baseline %)</label>
                              <input 
                                 type="number" 
                                 className="form-control rounded-pill bg-light border-0 py-2.5 px-3 text-sm font-semibold text-dark" 
                                 placeholder="คะแนนครั้งก่อน" 
                                 value={baseline}
                                 onChange={(e) => setBaseline(e.target.value)}
                              />
                           </div>
                           <div className="col-md-4">
                              <label className="text-[10px] font-bold text-muted uppercase tracking-widest mb-2 d-block">คะแนนความตึงตัวปัจจุบัน (NSS Current %)</label>
                              <input 
                                 type="number" 
                                 className="form-control rounded-pill bg-light border-0 py-2.5 px-3 text-sm font-semibold text-dark" 
                                 placeholder="คะแนนปัจจุบัน" 
                                 value={current}
                                 onChange={(e) => setCurrent(e.target.value)}
                              />
                           </div>
                           <div className="col-12 mt-4 text-end">
                              <button 
                                 className="btn btn-primary btn-sm px-4 py-2 font-bold uppercase tracking-widest text-[10px] shadow-sm rounded-pill text-white"
                                 onClick={handleSubmit}
                                 disabled={submitting}
                              >
                                 {submitting ? <Loader2 size={14} className="animate-spin d-inline me-1" /> : null}
                                 ยืนยันและบันทึกผลลัพธ์
                              </button>
                           </div>
                        </div>
                     </div>
                  </div>
               </div>
            )}

            {/* 📋 Patient Recovery Progress Registry */}
            <div className="col-12">
               {/* 🔍 Search Hub */}
               <div className="card shadow-sm border-0 mb-4 bg-white rounded-4">
                  <div className="card-body p-3">
                     <div className="position-relative">
                        <Search size={16} className="position-absolute top-50 start-0 translate-middle-y ms-3 text-muted" />
                        <input
                           type="text"
                           className="form-control rounded-pill bg-light border-0 py-2.5 ps-5 pe-3 text-sm font-semibold text-dark"
                           placeholder="ค้นหารายชื่อคนไข้ในทะเบียน..."
                           value={searchTerm}
                           onChange={(e) => setSearchTerm(e.target.value)}
                        />
                     </div>
                  </div>
               </div>

               <div className="card shadow-sm border-0 bg-white overflow-hidden rounded-4">
                  <div className="card-header bg-transparent border-bottom border-light py-4 d-flex justify-content-between align-items-center px-4">
                     <div className="d-flex align-items-center gap-2">
                        <Activity size={16} className="text-primary" />
                        <h3 className="card-title text-[11px] font-bold uppercase text-dark tracking-widest mb-0">ทำเนียบบันทึกประวัติการฟื้นตัวคนไข้</h3>
                     </div>
                     <div className="text-[10px] font-bold text-muted uppercase tracking-widest d-flex align-items-center gap-3">
                        <div className="d-flex align-items-center gap-1"><div className="bg-success rounded-circle" style={{ width: 8, height: 8 }}></div> อาการดีขึ้น</div>
                        <div className="d-flex align-items-center gap-1"><div className="bg-info rounded-circle" style={{ width: 8, height: 8 }}></div> อาการคงที่</div>
                     </div>
                  </div>

                  <div className="table-responsive">
                     <table className="table table-hover align-middle mb-0 text-nowrap">
                        <thead className="bg-light border-bottom text-[10px] uppercase font-bold text-muted tracking-wider">
                           <tr>
                              <th className="px-4 py-3" style={{ minWidth: '180px' }}>ข้อมูลคนไข้</th>
                              <th className="py-3 text-center" style={{ width: '130px' }}>ความตึงตัวเริ่มต้น</th>
                              <th className="py-3 text-center" style={{ width: '150px' }}>ความตึงตัวปัจจุบัน</th>
                              <th className="py-3 text-center" style={{ width: '120px' }}>สถานะผลลัพธ์</th>
                              <th className="py-3" style={{ width: '150px' }}>วันที่บันทึกผลล่าสุด</th>
                              <th className="py-3 text-end pe-4" style={{ width: '100px' }}>จัดการ</th>
                           </tr>
                        </thead>
                        <tbody>
                           {loading ? (
                              <tr><td colSpan={6} className="text-center py-5"><Loader2 className="animate-spin text-primary opacity-20" size={32} /></td></tr>
                           ) : paginatedOutcomes.length === 0 ? (
                              <tr>
                                 <td colSpan={6} className="text-center py-5">
                                    <div className="opacity-10 mb-2"><FolderHeart size={48} className="mx-auto" /></div>
                                    <p className="text-muted text-xs font-bold mb-0">ไม่พบข้อมูลประวัติผลลัพธ์การรักษาที่ระบุ</p>
                                 </td>
                              </tr>
                           ) : paginatedOutcomes.map((o) => {
                              const status = STATUS_CONFIG[o.status] || STATUS_CONFIG.stable;
                              const before = Number(o.before) || 0;
                              const after = Number(o.after) || 0;
                              const delta = before - after;
                              const isPositive = delta >= 0;
                              return (
                                 <tr key={o.id} className="border-bottom border-light transition-all hover:bg-light bg-opacity-30">
                                    <td className="px-4 py-3">
                                       <div className="d-flex align-items-center gap-3">
                                          <div className="bg-primary bg-opacity-10 rounded-circle w-8 h-8 d-flex align-items-center justify-content-center font-bold text-xs text-primary shadow-sm" style={{ width: '32px', height: '32px' }}>
                                             {(o.name || "P").charAt(0)}
                                          </div>
                                          <div>
                                             <div className="text-xs font-black text-dark mb-0 uppercase tracking-tighter">{o.name}</div>
                                             <div className="text-[9px] text-muted font-bold uppercase tracking-widest">TSPI-O-{o.id?.substring(0, 4) || "001"}</div>
                                          </div>
                                       </div>
                                    </td>
                                    <td className="py-3 text-center">
                                       <span className="text-xs font-bold text-muted">{before}%</span>
                                    </td>
                                    <td className="py-3 text-center">
                                       <div className="d-flex align-items-center justify-content-center gap-2">
                                          <span className="text-xs font-black text-dark">{after}%</span>
                                          <div className={`d-flex align-items-center gap-1 text-[10px] font-black ${isPositive ? 'text-success' : 'text-danger'}`}>
                                             {isPositive ? <TrendingDown size={12} /> : <TrendingUp size={12} />}
                                             {Math.abs(delta)}%
                                          </div>
                                       </div>
                                    </td>
                                    <td className="py-3 text-center">
                                       <span className={`badge bg-${status.color} bg-opacity-10 text-${status.color} text-[9px] uppercase px-3 py-1.5 border border-${status.color} border-opacity-20 font-black rounded-pill d-inline-flex align-items-center gap-1`}>
                                          <status.icon size={10} /> {status.label}
                                       </span>
                                    </td>
                                    <td className="py-3">
                                       <div className="d-flex align-items-center gap-2 text-xs font-bold text-muted">
                                          <Calendar size={12} className="opacity-50" /> {o.createdAt ? new Date(o.createdAt).toLocaleDateString("th-TH") : 'N/A'}
                                       </div>
                                    </td>
                                    <td className="py-3 text-end pe-4">
                                       <button className="btn btn-outline-primary btn-sm font-bold uppercase tracking-widest px-2.5 py-1.5 shadow-sm rounded-pill text-[10px]">
                                          ตรวจทาน <ArrowRight size={12} className="ms-1 d-inline" />
                                       </button>
                                    </td>
                                 </tr>
                              );
                           })}
                        </tbody>
                     </table>
                  </div>

                  {/* Pagination Controls */}
                  {totalPages > 1 && (
                     <div className="d-flex justify-content-between align-items-center p-4 border-top border-light bg-light bg-opacity-30">
                        <div className="text-[11px] font-bold text-muted uppercase tracking-wider">
                           แสดง {Math.min(filteredOutcomes.length, (currentPage - 1) * itemsPerPage + 1)} - {Math.min(filteredOutcomes.length, currentPage * itemsPerPage)} จากทั้งหมด {filteredOutcomes.length} รายการ
                        </div>
                        <div className="d-flex gap-1 align-items-center">
                           <button
                              onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                              disabled={currentPage === 1}
                              className="btn btn-sm btn-light border rounded-pill px-3 py-1.5 font-bold text-[10px] d-flex align-items-center gap-1 shadow-sm"
                           >
                              <ChevronLeft size={10} /> ก่อนหน้า
                           </button>
                           
                           <div className="d-flex gap-1 px-2">
                              {renderPageNumbers()}
                           </div>

                           <button
                              onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                              disabled={currentPage === totalPages}
                              className="btn btn-sm btn-light border rounded-pill px-3 py-1.5 font-bold text-[10px] d-flex align-items-center gap-1 shadow-sm"
                           >
                              ถัดไป <ChevronRight size={10} />
                           </button>
                        </div>
                     </div>
                  )}
               </div>
            </div>
         </div>

         <div className="mt-5 p-4 bg-primary bg-opacity-5 rounded-4 border border-primary border-opacity-10 d-flex align-items-center gap-3">
            <div className="bg-primary text-white p-2 rounded-circle shadow-sm">
               <ShieldCheck size={20} />
            </div>
            <div>
               <h6 className="fw-bold text-primary mb-1 text-sm uppercase tracking-widest">โปรโตคอลการควบคุมคุณภาพการรักษา (Clinical QA Governance)</h6>
               <p className="text-[11px] text-muted mb-0">การติดตามผลลัพธ์การรักษาเป็นข้อกำหนดสำคัญในการควบคุมคุณภาพทางคลินิก คะแนนส่วนต่าง (Delta Scores) จะถูกวิเคราะห์อย่างต่อเนื่องเพื่อรับประกันว่าโปรโตคอลการรักษาและตำรับยาสมุนไพรมีประสิทธิภาพสูงสุดตรงตามมาตรฐานการแพทย์ชีววิทยาระดับสากล</p>
            </div>
         </div>
         <style jsx>{`
            .animate-spin { animation: spin 1s linear infinite; }
            @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
            .w-8 { width: 32px; }
            .h-8 { height: 32px; }
         `}</style>
      </div>
   );
}

