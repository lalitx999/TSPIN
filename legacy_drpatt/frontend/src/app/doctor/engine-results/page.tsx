"use client";

import { useState, useEffect } from "react";
import {
   ClipboardList, CheckCircle, AlertTriangle, Clock,
   ChevronDown, ChevronUp, Search, RefreshCw, User,
   Brain, FileText, Star, Zap, Activity, Loader2,
   ShieldCheck, Cpu, Target, ArrowRightCircle,
   ChevronRight, ChevronLeft, Database
} from "lucide-react";
import Link from "next/link";
import { getEngineResults } from "@/utils/api/services";
import "./../theme-inapp.css";

const BURDEN_COLORS: Record<string, string> = {
   high: "danger",
   medium: "warning",
   low: "success"
};

export default function EngineResultsPage() {
   const [results, setResults] = useState<any[]>([]);
   const [loading, setLoading] = useState(true);
   const [searchTerm, setSearchTerm] = useState("");
   const [statusFilter, setStatusFilter] = useState("All Statuses");

   // Pagination States
   const [currentPage, setCurrentPage] = useState(1);
   const itemsPerPage = 10;

   // Reset pagination when search or filters change
   useEffect(() => {
      setCurrentPage(1);
   }, [searchTerm, statusFilter]);

   const loadResults = async () => {
      setLoading(true);
      try {
         const data = await getEngineResults();
         setResults(data);
      } catch (err) {
         console.error("Error loading engine results:", err);
      } finally {
         setLoading(false);
      }
   };

   useEffect(() => {
      loadResults();
   }, []);

   const getBurdenLevel = (score: number) => {
      if (score > 70) return "high";
      if (score > 40) return "medium";
      return "low";
   };

   // Computations for real metrics
   const totalRuns = results.length;
   const urgentReviews = results.filter(r => r.burden_score > 70).length;
   const pendingAudits = results.filter(r => r.status !== 'Verified').length;
   const avgBurden = totalRuns > 0 ? (results.reduce((acc, r) => acc + (Number(r.burden_score) || 0), 0) / totalRuns).toFixed(1) : "0.0";

   // Filter results
   const filteredResults = results.filter(run => {
      const matchSearch = 
         run.patient_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
         run.patient_hn?.toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchStatus = statusFilter === "All Statuses" || 
         (statusFilter === "Critical" && run.burden_score > 70) ||
         (statusFilter === "Completed" && run.status === "Verified");
         
      return matchSearch && matchStatus;
   });

   // Pagination Calculations
   const totalPages = Math.ceil(filteredResults.length / itemsPerPage);
   const paginatedResults = filteredResults.slice(
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
                     <ClipboardList size={24} />
                  </div>
                  ประวัติการประมวลผลระบบผู้ช่วยวิเคราะห์ (Engine Run History)
               </h1>
               <p className="text-muted text-xs uppercase font-bold tracking-widest ms-5 mb-0">บันทึกการประมวลผลและการจัดเก็บผลลัพธ์ของระบบคัดกรอง AI</p>
            </div>
            <div className="d-flex gap-2">
               <button 
                  onClick={loadResults}
                  disabled={loading}
                  className="btn btn-outline-primary fw-bold uppercase tracking-widest text-[10px] py-2 px-4 shadow-sm d-flex align-items-center gap-2 rounded-pill"
               >
                  <RefreshCw size={14} className={loading ? "animate-spin" : ""} /> ซิงก์ข้อมูลคลังประมวลผล
               </button>
            </div>
         </div>

         {/* 📊 High-Level Metrics */}
         <div className="row g-3 mb-4">
            <div className="col-lg-3 col-6">
               <div className="card p-3 border-0 shadow-sm bg-white h-100 rounded-4" style={{ background: 'linear-gradient(145deg, #ffffff, #f8f9fa)'}}>
                  <div className="d-flex justify-content-between align-items-center mb-2">
                     <p className="text-[10px] font-bold text-muted uppercase tracking-widest mb-0">การประมวลผลสะสม</p>
                     <Database size={16} className="text-primary opacity-50" />
                  </div>
                  <h3 className="fw-black mb-1 h3 text-dark">{loading ? "-" : totalRuns}</h3>
                  <small className="text-[10px] text-muted font-bold uppercase tracking-tighter">จำนวนครั้งที่ AI วิเคราะห์</small>
               </div>
            </div>
            <div className="col-lg-3 col-6">
               <div className="card p-3 border-0 shadow-sm bg-white h-100 rounded-4" style={{ background: 'linear-gradient(145deg, #ffffff, #f8f9fa)'}}>
                  <div className="d-flex justify-content-between align-items-center mb-2">
                     <p className="text-[10px] font-bold text-muted uppercase tracking-widest mb-0">เคสวิกฤต (ตึงตัวสูง)</p>
                     <AlertTriangle size={16} className="text-danger opacity-50" />
                  </div>
                  <h3 className="fw-black mb-1 h3 text-dark">{loading ? "-" : urgentReviews}</h3>
                  <small className="text-[10px] text-muted font-bold uppercase tracking-tighter">ความตึงตัว &gt;70% ที่ต้องดูแล</small>
               </div>
            </div>
            <div className="col-lg-3 col-6">
               <div className="card p-3 border-0 shadow-sm bg-white h-100 rounded-4" style={{ background: 'linear-gradient(145deg, #ffffff, #f8f9fa)'}}>
                  <div className="d-flex justify-content-between align-items-center mb-2">
                     <p className="text-[10px] font-bold text-muted uppercase tracking-widest mb-0">รอสอบทานทางคลินิก</p>
                     <Clock size={16} className="text-warning opacity-50" />
                  </div>
                  <h3 className="fw-black mb-1 h3 text-dark">{loading ? "-" : pendingAudits}</h3>
                  <small className="text-[10px] text-muted font-bold uppercase tracking-tighter">รอแพทย์ยืนยันผลลัพธ์</small>
               </div>
            </div>
            <div className="col-lg-3 col-6">
               <div className="card p-3 border-0 shadow-sm bg-white h-100 rounded-4" style={{ background: 'linear-gradient(145deg, #ffffff, #f8f9fa)'}}>
                  <div className="d-flex justify-content-between align-items-center mb-2">
                     <p className="text-[10px] font-bold text-muted uppercase tracking-widest mb-0">ค่าความตึงตัวเฉลี่ย</p>
                     <Activity size={16} className="text-success opacity-50" />
                  </div>
                  <h3 className="fw-black mb-1 h3 text-dark">{loading ? "-" : `${avgBurden}%`}</h3>
                  <small className="text-[10px] text-muted font-bold uppercase tracking-tighter">ภาพรวมคะแนนเฉลี่ยสะสม</small>
               </div>
            </div>
         </div>

         {/* 🔍 Search & Filters Hub */}
         <div className="card shadow-sm border-0 mb-4 bg-white rounded-4">
            <div className="card-body p-4">
               <div className="row align-items-center g-3">
                  <div className="col-md-9">
                     <div className="position-relative">
                        <Search size={16} className="position-absolute top-50 start-0 translate-middle-y ms-3 text-muted" />
                        <input
                           type="text"
                           className="form-control rounded-pill bg-light border-0 py-2.5 ps-5 pe-3 text-sm font-semibold text-dark"
                           placeholder="ค้นหาตามชื่อคนไข้ หรือ หมายเลข HN..."
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
                        <option value="All Statuses">ทุกสถานะการตรวจสอบ</option>
                        <option value="Critical">เคสวิกฤต (ความตึงตัว &gt;70%)</option>
                        <option value="Completed">ตรวจสอบเสร็จสิ้น (Verified)</option>
                     </select>
                  </div>
               </div>
            </div>
         </div>

         {/* 🏟️ Neural Run Board */}
         <div className="card shadow-sm border-0 bg-white overflow-hidden rounded-4">
            <div className="card-header bg-transparent border-bottom border-light py-4 d-flex justify-content-between align-items-center px-4">
               <div className="d-flex align-items-center gap-2">
                  <Cpu size={16} className="text-primary" />
                  <h3 className="card-title text-[11px] font-bold uppercase text-dark tracking-widest mb-0">ทะเบียนบันทึกการคำนวณและประมวลผล AI</h3>
               </div>
               <div className="text-[10px] font-bold text-muted uppercase tracking-widest d-flex align-items-center gap-3">
                  <div className="d-flex align-items-center gap-1"><div className="bg-success rounded-circle" style={{ width: 8, height: 8 }}></div> ตรวจสอบแล้ว</div>
                  <div className="d-flex align-items-center gap-1"><div className="bg-warning rounded-circle" style={{ width: 8, height: 8 }}></div> กำลังสอบทาน</div>
               </div>
            </div>

            <div className="table-responsive">
               <table className="table table-hover align-middle mb-0 text-nowrap">
                  <thead className="bg-light border-bottom text-[10px] uppercase font-bold text-muted tracking-wider">
                     <tr>
                        <th className="px-4 py-3" style={{ width: '50px' }}>ลำดับ</th>
                        <th className="py-3" style={{ width: '130px' }}>วันเวลาประมวลผล</th>
                        <th className="py-3" style={{ minWidth: '180px' }}>ข้อมูลคนไข้</th>
                        <th className="py-3 text-center" style={{ width: '150px' }}>คะแนนความตึงตัว (NSS)</th>
                        <th className="py-3 text-center" style={{ width: '100px' }}>สถานะ</th>
                        <th className="py-3 text-end pe-4" style={{ width: '100px' }}>จัดการ</th>
                     </tr>
                  </thead>
                  <tbody>
                     {loading ? (
                        <tr><td colSpan={6} className="text-center py-5"><Loader2 className="animate-spin text-primary opacity-20" size={32} /></td></tr>
                     ) : paginatedResults.length === 0 ? (
                        <tr>
                           <td colSpan={6} className="text-center py-5">
                              <div className="opacity-10 mb-2"><Database size={48} className="mx-auto" /></div>
                              <p className="text-muted text-xs font-bold mb-0">ไม่พบประวัติบันทึกผลการคำนวณของ AI ที่ตรงกับเงื่อนไขที่กำหนด</p>
                           </td>
                        </tr>
                     ) : paginatedResults.map((run, index) => {
                        const burdenLevel = getBurdenLevel(run.burden_score);
                        const absoluteIndex = (currentPage - 1) * itemsPerPage + index + 1;
                        return (
                           <tr key={run.id} className="border-bottom border-light transition-all cursor-pointer hover:bg-light bg-opacity-30">
                              <td className="px-4 py-3">
                                 <span className="text-[10px] font-mono text-muted font-bold">#{absoluteIndex}</span>
                              </td>
                              <td className="py-3">
                                 <div className="d-flex align-items-center gap-2 text-xs font-bold text-dark">
                                    <Clock size={12} className="text-primary opacity-50" />
                                    {run.createdAt ? new Date(run.createdAt).toLocaleString("th-TH", { hour: '2-digit', minute: '2-digit', day: '2-digit', month: 'short' }) : 'N/A'} น.
                                 </div>
                              </td>
                              <td className="py-3">
                                 <div className="d-flex align-items-center gap-3">
                                    <div className="bg-primary bg-opacity-10 rounded-circle w-8 h-8 d-flex align-items-center justify-content-center font-bold text-xs text-primary shadow-sm" style={{ width: '32px', height: '32px' }}>
                                       {(run.patient_name || "P").charAt(0)}
                                    </div>
                                    <div>
                                       <div className="text-xs font-black text-dark mb-0 uppercase tracking-tighter">{run.patient_name || "ไม่ระบุตัวตนคนไข้"}</div>
                                       <div className="text-[9px] text-muted font-bold uppercase tracking-widest">HN: {run.patient_hn || "N/A"}</div>
                                    </div>
                                 </div>
                              </td>
                              <td className="py-3 text-center">
                                 <div className="d-flex flex-column align-items-center">
                                    <div className="fw-black text-dark text-xs mb-1">{run.burden_score || 0}%</div>
                                    <div className="progress w-100 bg-light" style={{ height: '4px', maxWidth: '80px' }}>
                                       <div className={`progress-bar bg-${BURDEN_COLORS[burdenLevel]}`} style={{ width: `${run.burden_score || 0}%` }}></div>
                                    </div>
                                 </div>
                              </td>
                              <td className="py-3 text-center">
                                 <span className={`badge bg-${run.status === 'Verified' ? 'success' : 'warning'} bg-opacity-10 text-${run.status === 'Verified' ? 'success' : 'warning'} text-[9px] uppercase px-3 py-1.5 border border-${run.status === 'Verified' ? 'success' : 'warning'} border-opacity-20 font-black rounded-pill`}>
                                    {run.status === 'Verified' ? "ตรวจสอบแล้ว" : "กำลังสอบทาน"}
                                 </span>
                              </td>
                              <td className="py-3 text-end pe-4">
                                 <Link href={`/doctor/ai-physician?id=${run.patient_id}`} className="btn btn-outline-primary btn-sm font-bold uppercase tracking-widest px-2.5 py-1.5 shadow-sm rounded-pill text-[10px]">
                                    วิเคราะห์ <ChevronRight size={12} className="ms-1 d-inline" />
                                 </Link>
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
                     แสดง {Math.min(filteredResults.length, (currentPage - 1) * itemsPerPage + 1)} - {Math.min(filteredResults.length, currentPage * itemsPerPage)} จากทั้งหมด {filteredResults.length} รายการ
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

         <div className="mt-5 p-4 bg-primary bg-opacity-5 rounded-4 border border-primary border-opacity-10 d-flex align-items-center gap-3">
            <div className="bg-primary text-white p-2 rounded-circle shadow-sm">
               <ShieldCheck size={20} />
            </div>
            <div>
               <h6 className="fw-bold text-primary mb-1 text-sm uppercase tracking-widest">โปรโตคอลการกำกับดูแลความปลอดภัย AI (EMR Governance)</h6>
               <p className="text-[11px] text-muted mb-0">ผลลัพธ์การคำนวณของ AI ทั้งหมดจะถูกบันทึกและประทับเวลาไว้อย่างถาวร เพื่อใช้ในการตรวจสอบประวัติการรักษาทางคลินิกและการติดตามคนไข้ในระยะยาว เคสที่มีคะแนนความตึงตัวเกิน 70% จะต้องได้รับการยืนยันโดยแพทย์ด้วยตนเอง</p>
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
