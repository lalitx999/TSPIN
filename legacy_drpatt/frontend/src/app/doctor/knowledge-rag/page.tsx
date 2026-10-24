"use client";

import { useState, useEffect } from "react";
import {
   Database, BookOpen, CheckCircle, AlertCircle,
   Trash2, Plus, Loader2, Search, Sliders,
   Layers, FileText, Send, RefreshCw, Clock
} from "lucide-react";
import "./../theme-inapp.css";
import { getAxesDefinitions, getAxisName } from "@/lib/axis-definitions";

// ✅ ลบ AXES_OPTIONS ออกทั้งหมด (บรรทัด ~15-56)

// ดึงข้อมูลแกนจาก JSON
const axesData = getAxesDefinitions();
const AXES_OPTIONS = axesData.map(axis => ({
   id: axis.axis_id,
   name: `${axis.name} (${axis.axis_id})`
}));

const TYPE_TRANSLATIONS: Record<string, string> = {
   "clinical_guideline": "แนวทางการรักษาทางคลินิก",
   "research_paper": "เอกสารงานวิจัยทางวิทยาศาสตร์",
   "patient_case_study": "กรณีศึกษาผู้ป่วยจริง",
   "nutraceutical_synergy": "สูตรสมุนไพรและพฤกษเคมีเสริมฤทธิ์"
};

export default function KnowledgeRagPage() {
   // Form States
   const [text, setText] = useState("");
   const [source, setSource] = useState("");
   const [axis, setAxis] = useState("General");
   const [type, setType] = useState("clinical_guideline");

   // App States
   const [knowledgeList, setKnowledgeList] = useState<any[]>([]);
   const [loading, setLoading] = useState(true);
   const [isSubmitting, setIsSubmitting] = useState(false);
   const [searchTerm, setSearchTerm] = useState("");
   const [filterAxis, setFilterAxis] = useState("All");
   const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "" }>({ message: "", type: "" });

   const loadKnowledgeBase = async () => {
      try {
         setLoading(true);
         const token = localStorage.getItem("doctor_access_token");
         const apiBase = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";
         const res = await fetch(`${apiBase}/api/knowledge-segments/?no_pagination=true`, {
            headers: {
               ...(token ? { "Authorization": `Bearer ${token}` } : {})
            }
         });
         if (!res.ok) throw new Error("Failed to load knowledge from Django");
         const list = await res.json();
         const data = Array.isArray(list) ? list : (list.results || []);

         const mappedList = data.map((item: any) => {
            // ✅ ใช้ getAxisName จาก utility
            const axisName = item.axis_id ? getAxisName(item.axis_id) : "General";
            const axisLabel = item.axis_id ? `Axis ${item.axis_id}: ${axisName}` : "General";

            return {
               id: String(item.id),
               text: item.content || "",
               source: item.source || item.title || "ไม่ระบุแหล่งที่มา",
               axis: axisLabel,
               axis_id: item.axis_id,
               type: item.type || "clinical_guideline",
               createdAt: item.created_at,
               updatedAt: item.updated_at
            };
         });
         setKnowledgeList(mappedList);
      } catch (error) {
         console.error("Error loading knowledge base:", error);
         showToast("ไม่สามารถโหลดฐานข้อมูล RAG ได้", "error");
      } finally {
         setLoading(false);
      }
   };

   useEffect(() => {
      loadKnowledgeBase();
   }, []);

   const showToast = (message: string, type: "success" | "error") => {
      setToast({ message, type });
      setTimeout(() => setToast({ message: "", type: "" }), 3000);
   };

   const handleSubmit = async (e: React.FormEvent) => {
      e.preventDefault();
      if (!text.trim() || !source.trim()) {
         showToast("กรุณากรอกข้อความและแหล่งข้อมูลอ้างอิงให้ครบถ้วน", "error");
         return;
      }

      setIsSubmitting(true);
      try {
         const token = localStorage.getItem("doctor_access_token");
         const response = await fetch("/api/ai/index-knowledge", {
            method: "POST",
            headers: {
               "Content-Type": "application/json",
               ...(token ? { "Authorization": `Bearer ${token}` } : {})
            },
            body: JSON.stringify({ text, source, axis, type })
         });

         if (!response.ok) {
            throw new Error("Failed to index knowledge module");
         }

         showToast("บันทึกข้อมูลและคำนวณเวกเตอร์เข้าระบบ RAG สำเร็จ!", "success");
         setText("");
         setSource("");
         setAxis("General");
         loadKnowledgeBase();
      } catch (error: any) {
         console.error("Error indexing knowledge:", error);
         showToast("เกิดข้อผิดพลาดในการลงทะเบียนความรู้", "error");
      } finally {
         setIsSubmitting(false);
      }
   };

   const handleDelete = async (id: string) => {
      if (!confirm("คุณต้องการลบข้อมูลชุดนี้ออกจากคลังความรู้ RAG ใช่หรือไม่?")) return;

      try {
         const token = localStorage.getItem("doctor_access_token");
         const apiBase = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";
         const res = await fetch(`${apiBase}/api/knowledge-segments/${id}/`, {
            method: "DELETE",
            headers: {
               ...(token ? { "Authorization": `Bearer ${token}` } : {})
            }
         });
         if (!res.ok) throw new Error("Failed to delete from Django");
         showToast("ลบข้อมูลออกจากคลังความรู้ RAG เรียบร้อยแล้ว", "success");
         loadKnowledgeBase();
      } catch (error) {
         console.error("Error deleting knowledge:", error);
         showToast("เกิดข้อผิดพลาดในการลบข้อมูล", "error");
      }
   };

   const parseDate = (createdVal: any) => {
      if (!createdVal) return "ไม่ระบุวันที่";
      const date = new Date(createdVal);
      return date.toLocaleDateString("th-TH", {
         year: "numeric",
         month: "short",
         day: "numeric",
         hour: "2-digit",
         minute: "2-digit"
      }) + " น.";
   };

   // Filtering logic
   const filteredList = knowledgeList.filter(item => {
      const matchesSearch =
         item.text?.toLowerCase().includes(searchTerm.toLowerCase()) ||
         item.source?.toLowerCase().includes(searchTerm.toLowerCase()) ||
         item.axis?.toLowerCase().includes(searchTerm.toLowerCase());

      let matchesFilter = true;
      if (filterAxis !== "All") {
         if (filterAxis === "General") {
            matchesFilter = !item.axis_id || item.axis_id === 0;
         } else {
            const match = filterAxis.match(/Axis\s+(\d+)/i);
            const targetId = match ? parseInt(match[1]) : 0;
            matchesFilter = item.axis_id === targetId;
         }
      }

      return matchesSearch && matchesFilter;
   });

   return (
      <div className="pb-5 font-kanit text-start">
         {/* Toast Notification */}
         {toast.message && (
            <div
               className={`position-fixed bottom-0 end-0 m-4 p-3 rounded-3 shadow-lg d-flex align-items-center gap-3`}
               style={{
                  zIndex: 9999,
                  background: toast.type === "success" ? "#ECFDF5" : "#FEF2F2",
                  border: `1px solid ${toast.type === "success" ? "#10B981" : "#EF4444"}`,
                  color: toast.type === "success" ? "#065F46" : "#991B1B",
                  animation: 'fadeInDown 0.3s ease'
               }}
            >
               {toast.type === "success" ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
               <span className="small fw-semibold">{toast.message}</span>
            </div>
         )}

         {/* ==================== HEADER ==================== */}
         <div className="d-flex justify-content-between align-items-end mb-4">
            <div>
               <h1 className="fs-3 fw-bold mb-1 text-dark d-flex align-items-center gap-2">
                  <div className="bg-primary bg-opacity-10 p-2 rounded-3 text-primary shadow-sm">
                     <BookOpen size={24} />
                  </div>
                  การจัดการความรู้โมเดลค้นคืน (Institutional RAG Core)
               </h1>
               <p className="text-muted text-xs uppercase font-bold tracking-widest ms-5 mb-0" style={{ fontSize: "10px" }}>
                  ระบบอัปโหลดบทความทางการแพทย์และเอกสารงานวิจัยเพื่อสร้างเวกเตอร์ (768 มิติ) สำหรับสมองกลคัดกรอง AI
               </p>
            </div>
            <button onClick={loadKnowledgeBase} className="btn btn-outline-primary fw-bold uppercase tracking-widest py-2 px-4 shadow-sm d-flex align-items-center gap-2 rounded-pill" style={{ fontSize: "11px" }}>
               <RefreshCw size={14} className={loading ? "animate-spin" : ""} /> ซิงก์ข้อมูลคลังสมอง RAG
            </button>
         </div>

         {/* ==================== STATS ROW ==================== */}
         <div className="row g-3 mb-4">
            <div className="col-md-4">
               <div className="card p-4 border-0 shadow-sm bg-white rounded-4 h-100" style={{ background: 'linear-gradient(145deg, #ffffff, #f8f9fa)' }}>
                  <div className="d-flex justify-content-between align-items-center mb-3">
                     <p className="text-[10px] font-bold text-muted uppercase tracking-widest mb-0" style={{ fontSize: "10px" }}>บล็อกความรู้ที่ใช้งาน (Knowledge Nodes)</p>
                     <Database size={18} className="text-primary" />
                  </div>
                  <h3 className="fw-black mb-1 h3 text-dark">{loading ? "-" : knowledgeList.length}</h3>
                  <small className="text-[10px] text-muted font-bold uppercase tracking-tighter" style={{ fontSize: "9px" }}>จำนวนเวกเตอร์ที่จัดเก็บใน PostgreSQL</small>
               </div>
            </div>
            <div className="col-md-4">
               <div className="card p-4 border-0 shadow-sm bg-white rounded-4 h-100" style={{ background: 'linear-gradient(145deg, #ffffff, #f8f9fa)' }}>
                  <div className="d-flex justify-content-between align-items-center mb-3">
                     <p className="text-[10px] font-bold text-muted uppercase tracking-widest mb-0" style={{ fontSize: "10px" }}>ขอบเขตแกนชีววิทยาที่ครอบคลุม (Axes Mapped)</p>
                     <Layers size={18} className="text-success" />
                  </div>
                  <h3 className="fw-black mb-1 h3 text-dark">
                     {loading ? "-" : new Set(knowledgeList.map(item => item.axis_id).filter(a => a && a > 0)).size} / 39
                  </h3>
                  <small className="text-[10px] text-muted font-bold uppercase tracking-tighter" style={{ fontSize: "9px" }}>กลุ่มระบบชีววิทยาที่สร้างเวกเตอร์แล้ว</small>
               </div>
            </div>
            <div className="col-md-4">
               <div className="card p-4 border-0 shadow-sm bg-white rounded-4 h-100" style={{ background: 'linear-gradient(145deg, #ffffff, #f8f9fa)' }}>
                  <div className="d-flex justify-content-between align-items-center mb-3">
                     <p className="text-[10px] font-bold text-muted uppercase tracking-widest mb-0" style={{ fontSize: "10px" }}>สถานะการเชื่อมต่อ AI (LLM Engine)</p>
                     <Sliders size={18} className="text-info" />
                  </div>
                  <h3 className="fw-black mb-1 h3 text-dark">พร้อมใช้งาน</h3>
                  <small className="text-[10px] text-muted font-bold uppercase tracking-tighter" style={{ fontSize: "9px" }}>คลังความรู้ซิงก์ตรงกับสมองกลคัดกรอง TSPI</small>
               </div>
            </div>
         </div>

         <div className="row g-4 text-start">
            {/* ==================== LEFT COLUMN: KNOWLEDGE INGESTION FORM ==================== */}
            <div className="col-lg-5">
               <div className="card border-0 shadow-sm bg-white rounded-4 overflow-hidden mb-4">
                  <div className="card-header bg-primary bg-opacity-10 border-0 py-3 px-4 d-flex align-items-center gap-2">
                     <Plus size={16} className="text-primary" />
                     <h3 className="card-title text-sm font-bold uppercase text-primary tracking-widest mb-0" style={{ fontSize: "13.5px" }}>
                        นำเข้าเอกสารความรู้ใหม่ (RAG Source Ingestion)
                     </h3>
                  </div>
                  <div className="card-body p-4 bg-primary bg-opacity-5">
                     <form onSubmit={handleSubmit} className="d-grid gap-3">
                        <div>
                           <label className="text-[11px] font-bold text-dark mb-1 d-block uppercase tracking-wider" style={{ fontSize: "10px" }}>เอกสารอ้างอิง / แหล่งที่มาทางการแพทย์</label>
                           <input
                              type="text"
                              className="form-control bg-white border-0 shadow-sm py-2.5 px-3 rounded-3 text-sm"
                              placeholder="เช่น NIH PubMed PMC10928, คู่มือสรีรวิทยา TSPI v3"
                              value={source}
                              onChange={(e) => setSource(e.target.value)}
                              required
                           />
                        </div>

                        <div className="row g-3">
                           <div className="col-md-6">
                              <label className="text-[11px] font-bold text-dark mb-1 d-block uppercase tracking-wider" style={{ fontSize: "10px" }}>แกนชีววิทยาเป้าหมาย</label>
                              <select
                                 className="form-select bg-white border-0 shadow-sm py-2.5 px-3 rounded-3 text-sm"
                                 value={axis}
                                 onChange={(e) => setAxis(e.target.value)}
                              >
                                 <option value="General">โครงสร้างหลักทั่วไป (General)</option>
                                 {/* ✅ ใช้ AXES_OPTIONS ที่สร้างจาก JSON */}
                                 {AXES_OPTIONS.map((opt) => (
                                    <option key={opt.id} value={`Axis ${opt.id}: ${opt.name}`}>
                                       แกนที่ {opt.id}: {opt.name}
                                    </option>
                                 ))}
                              </select>
                           </div>
                           <div className="col-md-6">
                              <label className="text-[11px] font-bold text-dark mb-1 d-block uppercase tracking-wider" style={{ fontSize: "10px" }}>ประเภทเนื้อหาเอกสาร</label>
                              <select
                                 className="form-select bg-white border-0 shadow-sm py-2.5 px-3 rounded-3 text-sm"
                                 value={type}
                                 onChange={(e) => setType(e.target.value)}
                              >
                                 <option value="clinical_guideline">แนวทางปฏิบัติการรักษาคลินิก</option>
                                 <option value="research_paper">เอกสารงานวิจัยทางวิทยาศาสตร์</option>
                                 <option value="patient_case_study">กรณีศึกษาผู้ป่วยจริง (Case Study)</option>
                                 <option value="nutraceutical_synergy">สารสมุนไพร/พฤกษเคมีเสริมฤทธิ์</option>
                              </select>
                           </div>
                        </div>

                        <div>
                           <label className="text-[11px] font-bold text-dark mb-1 d-block uppercase tracking-wider" style={{ fontSize: "10px" }}>ข้อมูลความรู้และคำอธิบายสรีรวิทยา (Context Block)</label>
                           <textarea
                              className="form-control bg-white border-0 shadow-sm p-3 rounded-3 text-sm"
                              rows={6}
                              style={{ resize: "none" }}
                              placeholder="กรอกรายละเอียดสรีรวิทยา กลไกระดับเซลล์ การทำงานของสารอาหาร หรือโปรโตคอลการรักษาเพื่อแปลงเป็นเวกเตอร์ในการค้นหา..."
                              value={text}
                              onChange={(e) => setText(e.target.value)}
                              required
                           />
                        </div>

                        <button
                           type="submit"
                           disabled={isSubmitting}
                           className="btn btn-primary py-3 rounded-pill fw-bold uppercase tracking-widest d-flex align-items-center justify-content-center gap-2 mt-2 text-xs shadow-sm"
                        >
                           {isSubmitting ? (
                              <><Loader2 className="animate-spin" size={14} /> กำลังคำนวณและบันทึกเวกเตอร์ RAG...</>
                           ) : (
                              <><Send size={14} /> บันทึกเข้าฐานความรู้ (Index to RAG)</>
                           )}
                        </button>
                     </form>
                  </div>
               </div>
            </div>

            {/* ==================== RIGHT COLUMN: ACTIVE RAG DATABASE GRID ==================== */}
            <div className="col-lg-7">
               <div className="card border-0 shadow-sm bg-white rounded-4 overflow-hidden h-100 d-flex flex-column">
                  <div className="card-header bg-white border-bottom border-light py-4 px-4 d-flex justify-content-between align-items-center flex-wrap gap-3 flex-shrink-0">
                     <div className="d-flex align-items-center gap-2">
                        <Database size={18} className="text-primary" />
                        <h3 className="card-title text-sm font-bold uppercase text-dark tracking-widest mb-0" style={{ fontSize: "13.5px" }}>
                           รายการคลังสมอง RAG ในระบบ EMR (Active RAG Nodes)
                        </h3>
                     </div>

                     <div className="d-flex gap-2">
                        {/* Search Input */}
                        <div className="position-relative">
                           <Search size={14} className="position-absolute top-50 start-0 translate-middle-y ms-3 text-muted" />
                           <input
                              type="text"
                              className="form-control rounded-pill bg-light border-0 py-2 ps-5 pe-3 text-xs font-semibold"
                              placeholder="ค้นหาตามข้อความ..."
                              style={{ width: "200px" }}
                              value={searchTerm}
                              onChange={(e) => setSearchTerm(e.target.value)}
                           />
                        </div>

                        {/* Filter Axis */}
                        <select
                           className="form-select rounded-pill bg-light border-0 py-2 px-3 text-xs font-semibold"
                           style={{ width: "160px" }}
                           value={filterAxis}
                           onChange={(e) => setFilterAxis(e.target.value)}
                        >
                           <option value="All">ทุกแกนระบบ</option>
                           <option value="General">แกนทั่วไป (General)</option>
                           {/* ✅ ใช้ AXES_OPTIONS ที่สร้างจาก JSON */}
                           {AXES_OPTIONS.map((opt) => (
                              <option key={opt.id} value={`Axis ${opt.id}: ${opt.name}`}>
                                 แกนที่ {opt.id}
                              </option>
                           ))}
                        </select>
                     </div>
                  </div>

                  <div className="card-body p-4 bg-light flex-grow-1 overflow-auto" style={{ maxHeight: '650px' }}>
                     {loading ? (
                        <div className="text-center py-5 d-flex flex-column align-items-center justify-content-center h-100">
                           <Loader2 className="animate-spin text-primary mb-3" size={32} />
                           <p className="text-xs text-muted font-bold tracking-widest uppercase" style={{ fontSize: "11px" }}>กำลังโหลดข้อมูลความรู้...</p>
                        </div>
                     ) : filteredList.length === 0 ? (
                        <div className="text-center py-5 d-flex flex-column align-items-center justify-content-center h-100 opacity-50">
                           <BookOpen size={48} className="text-muted mb-3" />
                           <h5 className="text-sm font-bold text-dark uppercase tracking-widest mb-1">ไม่พบข้อมูล RAG</h5>
                           <p className="text-[11px] text-muted mx-auto" style={{ maxWidth: "250px", fontSize: "11px" }}>
                              ไม่มีข้อมูลบทความที่ตรงกับการค้นหา หรือยังไม่มีฐานความรู้บันทึกไว้ในระบบ
                           </p>
                        </div>
                     ) : (
                        <div className="d-flex flex-column gap-3">
                           {filteredList.map((item) => (
                              <div
                                 key={item.id}
                                 className="card border-0 shadow-sm rounded-4 overflow-hidden"
                              >
                                 <div className="card-body p-4 bg-white text-start">
                                    <div className="d-flex justify-content-between align-items-start gap-2 mb-2">
                                       <div>
                                          <div className="d-flex align-items-center gap-2 mb-2 flex-wrap">
                                             <span className="badge bg-primary bg-opacity-10 text-primary fw-bold px-2.5 py-1.5 rounded-pill uppercase tracking-wider" style={{ fontSize: "9px" }}>
                                                {TYPE_TRANSLATIONS[item.type] || item.type}
                                             </span>
                                             <span className="text-[10px] text-muted font-bold uppercase tracking-wider" style={{ fontSize: "10.5px" }}>
                                                <Sliders size={10} className="me-1 d-inline" />
                                                {item.axis?.split("(")[0] || "โครงสร้างหลักทั่วไป (General)"}
                                             </span>
                                          </div>
                                          <h5 className="text-sm font-bold text-dark m-0 d-flex align-items-center gap-2" style={{ fontSize: "13.5px" }}>
                                             <FileText size={14} className="text-muted" />
                                             {item.source}
                                          </h5>
                                       </div>
                                       <button
                                          onClick={() => handleDelete(item.id)}
                                          className="btn btn-light p-2 text-muted hover-text-danger rounded-circle shadow-sm"
                                       >
                                          <Trash2 size={14} />
                                       </button>
                                    </div>

                                    <div className="bg-light p-3 rounded-3 mt-3">
                                       <p className="text-xs text-dark mb-0 font-medium" style={{ lineHeight: 1.6, fontSize: "12px" }}>
                                          {item.text}
                                       </p>
                                    </div>

                                    <div className="mt-3 text-end">
                                       <span className="text-[10px] text-muted font-bold uppercase tracking-wider" style={{ fontSize: "9px" }}>
                                          <Clock size={10} className="me-1 d-inline" />
                                          สร้างเมื่อ: {parseDate(item.createdAt)}
                                       </span>
                                    </div>
                                 </div>
                              </div>
                           ))}
                        </div>
                     )}
                  </div>
               </div>
            </div>
         </div>
         <style jsx>{`
            .animate-spin { animation: spin 1s linear infinite; }
            @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
            @keyframes fadeInDown { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
            .hover-text-danger:hover { color: #dc3545 !important; background-color: #f8d7da !important; }
         `}</style>
      </div>
   );
}