"use client";

import { useState } from "react";
import {
   FileText,
   Upload,
   Layers,
   Thermometer,
   Activity,
   ChevronRight,
   Info,
   CheckCircle2,
   Trash2,
   Database,
   Microscope,
   Zap,
   ArrowRight,
   ArrowLeft,
   Send,
   RefreshCw,
   Sparkles,
   Search
} from "lucide-react";

export default function LabOCRReviewPage() {
   const [input, setInput] = useState("Glucose: 160 mg/dL, HbA1c: 7.5%, LDL: 195 mg/dL, CRP: 12.4 mg/L");
   const [isProcessing, setIsProcessing] = useState(false);
   const [extractedData, setExtractedData] = useState<any>(null);
   const [patientId, setPatientId] = useState("");

   const handleProcess = () => {
      setIsProcessing(true);
      setTimeout(() => {
         setExtractedData({
            markers: [
               { name: "Glucose", value: "160", unit: "mg/dL", flag: "HIGH", key: "fasting_glucose" },
               { name: "HbA1c", value: "7.5", unit: "%", flag: "HIGH", key: "HbA1c" },
               { name: "LDL", value: "195", unit: "mg/dL", flag: "HIGH", key: "LDL" },
               { name: "CRP", value: "12.4", unit: "mg/L", flag: "HIGH", key: "CRP" },
            ],
            axes: ["D3 (Metabolic)", "D1 (Inflammation)", "D8 (Circulation)"]
         });
         setIsProcessing(false);
      }, 1500);
   };

   return (
      <div className="p-4" style={{ fontFamily: 'Kanit, sans-serif' }}>
         {/* Header Area */}
         <div className="mb-4 text-start">
            <div className="d-flex align-items-center gap-2 mb-2">
               <div className="bg-primary-custom bg-opacity-10 p-2 rounded-3">
                  <Microscope size={20} className="text-primary-custom" />
               </div>
               <span className="tiny fw-bold text-primary-custom text-uppercase tracking-widest">Quality Assurance</span>
            </div>
            <div className="d-flex align-items-center justify-content-between flex-wrap gap-3">
               <div>
                  <h3 className="fw-bold text-dark mb-1">Lab OCR Data Verification</h3>
                  <p className="small text-muted mb-0">ตรวจสอบและยืนยันความถูกต้องของข้อมูล Biomarkers ก่อนเข้าสู่ระบบประมวลผล</p>
               </div>
            </div>
         </div>

         <div className="row g-4 text-start">
            {/* Input Card */}
            <div className="col-lg-12">
               <div className="bg-white rounded-5 shadow-sm border border-light p-4">
                  <div className="row g-4">
                     <div className="col-md-8">
                        <label className="tiny fw-bold text-muted uppercase mb-2 d-flex align-items-center gap-2">
                           <FileText size={14} className="text-primary-custom" /> Raw OCR Text / Uploaded Data
                        </label>
                        <textarea
                           className="form-control rounded-4 bg-light border-0 p-4 small"
                           rows={5}
                           style={{ resize: 'none' }}
                           value={input}
                           onChange={(e) => setInput(e.target.value)}
                           placeholder="ตรวจสอบข้อความที่สกัดได้จากรูปภาพที่นี่..."
                        />
                     </div>
                     <div className="col-md-4 d-flex flex-column justify-content-center gap-2">
                        <button
                           onClick={handleProcess}
                           className="btn btn-drpat-primary rounded-pill py-3 fw-bold shadow-sm d-flex align-items-center justify-content-center gap-2"
                        >
                           <Layers size={18} /> Verify & Extract Markers
                        </button>
                        <button className="btn btn-light rounded-pill py-2.5 small fw-bold text-muted border d-flex align-items-center justify-content-center gap-2">
                           <Upload size={18} /> Re-upload Document
                        </button>
                     </div>
                  </div>
               </div>
            </div>

            {/* Verification Results */}
            {extractedData && (
               <div className="col-lg-12 animate-fade-in">
                  <div className="row g-4">
                     {/* Biomarker Verification List */}
                     <div className="col-lg-7">
                        <div className="bg-white rounded-5 shadow-sm border border-light p-4 h-100">
                           <h6 className="tiny fw-bold text-muted uppercase tracking-widest mb-4 d-flex align-items-center gap-2">
                              <Activity size={16} className="text-primary-custom" /> Structured Biomarker Data
                           </h6>
                           <div className="d-grid gap-2">
                              {extractedData.markers.map((m: any, i: number) => (
                                 <div key={i} className="p-3 bg-light rounded-4 d-flex align-items-center gap-3 border border-white shadow-xs">
                                    <div className="bg-white p-2 rounded-3 text-primary-custom shadow-xs"><Database size={16} /></div>
                                    <div className="flex-grow-1">
                                       <p className="tiny fw-bold text-dark mb-0">{m.name}</p>
                                       <p className="tiny text-muted mb-0">Mapped Key: {m.key}</p>
                                    </div>
                                    <div className="text-end">
                                       <p className={`small fw-bold mb-0 ${m.flag === 'HIGH' ? 'text-danger' : 'text-dark'}`}>{m.value} {m.unit}</p>
                                       <span className={`tiny fw-bold px-2 py-0.5 rounded-pill ${m.flag === 'HIGH' ? 'bg-danger bg-opacity-10 text-danger' : 'bg-success bg-opacity-10 text-success'}`}>
                                          {m.flag}
                                       </span>
                                    </div>
                                    <button className="btn btn-link p-0 text-muted hover-text-danger"><Trash2 size={14} /></button>
                                 </div>
                              ))}
                           </div>
                        </div>
                     </div>

                     {/* Send to Engine & Quick Result */}
                     <div className="col-lg-5">
                        <div className="d-grid gap-4">
                           {/* Patient Linking */}
                           <div className="bg-white rounded-5 shadow-sm border border-light p-4">
                              <h6 className="tiny fw-bold text-muted uppercase tracking-widest mb-4 d-flex align-items-center gap-2">
                                 <Zap size={16} className="text-warning" /> Link & Analyze
                              </h6>
                              <div className="d-grid gap-3">
                                 <div className="position-relative">
                                    <Search className="position-absolute top-50 start-0 translate-middle-y ms-3 text-muted" size={16} />
                                    <input
                                       type="text"
                                       className="form-control rounded-pill ps-5 bg-light border-0 py-2.5 small"
                                       placeholder="Patient ID (เช่น 67-00001)"
                                       value={patientId}
                                       onChange={(e) => setPatientId(e.target.value)}
                                    />
                                 </div>
                                 <button className="btn btn-dark rounded-pill py-3 fw-bold shadow-sm d-flex align-items-center justify-content-center gap-2">
                                    <Send size={18} /> Send to Clinical Engine
                                 </button>
                              </div>
                           </div>

                           {/* Associated Mechanisms */}
                           <div className="bg-dark rounded-5 p-4 text-white shadow-lg">
                              <p className="tiny fw-bold text-primary-custom uppercase mb-3 d-flex align-items-center gap-2"><Sparkles size={14} /> Associated Mechanisms</p>
                              <div className="d-flex flex-wrap gap-2">
                                 {extractedData.axes.map((ax: string) => (
                                    <span key={ax} className="tiny fw-bold bg-white bg-opacity-10 border border-white border-opacity-10 px-3 py-1.5 rounded-pill">{ax}</span>
                                 ))}
                              </div>
                              <hr className="opacity-10 my-4" />
                              <button className="btn btn-link btn-sm text-white text-decoration-none p-0 d-flex align-items-center gap-2 tiny fw-bold hover-text-primary">
                                 VIEW DETAILED CLINICAL REVIEW <ArrowRight size={14} />
                              </button>
                           </div>
                        </div>
                     </div>
                  </div>
               </div>
            )}
         </div>

         <style jsx>{`
        .animate-fade-in { animation: fadeIn 0.4s ease-out; }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
      </div>
   );
}
