"use client";

import { useState } from "react";
import {
   Database, CheckCircle, Loader2, AlertCircle, TrendingUp,
   Package, Link as LinkIcon, Zap, X, RefreshCw, Terminal,
   ArrowRight, Info, AlertTriangle, Layers, Activity
} from "lucide-react";
import Link from "next/link";
import "./../theme-inapp.css";

export default function ImportAxesPage() {
   const [isRunning, setIsRunning] = useState(false);
   const [progress, setProgress] = useState(0);
   const [showLogs, setShowLogs] = useState(true);

   const steps = [
      { name: "Clinical Domains (11)", status: progress > 20 ? "success" : progress > 0 ? "loading" : "pending" },
      { name: "Mechanistic Axes (36)", status: progress > 40 ? "success" : progress > 20 ? "loading" : "pending" },
      { name: "Sub-Axes Architecture", status: progress > 60 ? "success" : progress > 40 ? "loading" : "pending" },
      { name: "Treatment Modules", status: progress > 80 ? "success" : progress > 60 ? "loading" : "pending" },
      { name: "Module-Axis Mapping", status: progress >= 100 ? "success" : progress > 80 ? "loading" : "pending" },
   ];

   const handleStart = () => {
      setIsRunning(true);
      setProgress(0);
      const interval = setInterval(() => {
         setProgress(prev => {
            if (prev >= 100) {
               clearInterval(interval);
               setIsRunning(false);
               return 100;
            }
            return prev + 5;
         });
      }, 200);
   };

   return (
      <div className="pb-5">
         {/* 🧭 Header Section */}
         <div className="d-flex justify-content-between align-items-center mb-4">
            <div>
               <h1 className="fs-3 fw-bold mb-1 text-dark d-flex align-items-center gap-2">
                  <div className="bg-primary bg-opacity-10 p-2 rounded-3 text-primary">
                     <Database size={24} />
                  </div>
                  Import Clinical Framework
               </h1>
               <p className="text-muted text-xs uppercase font-bold tracking-widest ms-5">Database Migration Hub</p>
            </div>
         </div>

         <div className="row g-4">
            {/* 🚀 Progress & Control Hub */}
            <div className="col-md-7">
               <div className="card border-0 shadow-sm bg-white rounded-4 overflow-hidden">
                  <div className="card-header bg-transparent border-bottom border-light py-3 d-flex justify-content-between align-items-center">
                     <h3 className="card-title text-[10px] font-bold uppercase text-muted tracking-widest mb-0 d-flex align-items-center gap-2">
                        <Activity size={14} className="text-primary" /> Migration Status
                     </h3>
                     <span className="badge bg-primary text-white px-2 text-[9px] font-bold">{progress}% COMPLETED</span>
                  </div>
                  <div className="card-body p-0">
                     <div className="p-3 bg-light border-bottom">
                        <div className="progress rounded-pill shadow-none mb-0" style={{ height: '8px' }}>
                           <div className="progress-bar bg-primary progress-bar-striped progress-bar-animated" style={{ width: `${progress}%` }}></div>
                        </div>
                     </div>
                     <div className="list-group list-group-flush">
                        {steps.map((step, i) => (
                           <div key={i} className={`list-group-item px-4 py-3 d-flex align-items-center justify-content-between border-bottom border-light ${step.status === 'success' ? 'bg-success bg-opacity-5' : ''}`}>
                              <div className="d-flex align-items-center gap-3">
                                 <span className={`badge ${step.status === 'success' ? 'bg-success text-white' : 'bg-light border text-muted'} rounded-circle d-flex align-items-center justify-content-center font-bold`} style={{ width: '28px', height: '28px' }}>{i + 1}</span>
                                 <span className={`font-bold text-sm ${step.status === 'success' ? 'text-success' : 'text-dark'}`}>{step.name}</span>
                              </div>
                              {step.status === 'success' && <CheckCircle size={16} className="text-success" />}
                              {step.status === 'loading' && <RefreshCw size={14} className="text-primary animate-spin" />}
                           </div>
                        ))}
                     </div>
                  </div>
                  <div className="card-footer bg-white py-3 d-flex gap-2 border-top border-light">
                     <button
                        onClick={handleStart}
                        disabled={isRunning}
                        className="btn btn-primary font-bold flex-grow-1 shadow-sm py-2 d-flex align-items-center justify-content-center gap-2"
                     >
                        {isRunning ? <><RefreshCw size={14} className="animate-spin" /> PROCESSING...</> : <><Database size={14} /> RUN FRAMEWORK IMPORT</>}
                     </button>
                     <button
                        onClick={() => setShowLogs(!showLogs)}
                        className="btn btn-light border font-bold px-4 d-flex align-items-center gap-1"
                     >
                        <Terminal size={14} /> LOGS
                     </button>
                  </div>
               </div>
            </div>

            {/* 🖥️ Console & Metrics Hub */}
            <div className="col-md-5">
               {/* System Summary */}
               <div className="card bg-dark text-white border-0 shadow-sm rounded-4 overflow-hidden mb-4">
                  <div className="card-header bg-dark border-bottom border-secondary py-3">
                     <h3 className="card-title text-[10px] font-bold uppercase text-primary mb-0 d-flex align-items-center gap-2">
                        <Info size={14} /> System Summary
                     </h3>
                  </div>
                  <div className="card-body p-3">
                     <div className="row g-2">
                        {[
                           { label: 'Domains', val: '11', icon: Layers },
                           { label: 'Axes', val: '36', icon: Activity },
                           { label: 'Sub-Axes', val: '108', icon: Layers },
                           { label: 'Modules', val: '200+', icon: Package },
                        ].map(s => (
                           <div key={s.label} className="col-6 mb-2">
                              <div className="p-2 border border-secondary rounded-3 bg-white bg-opacity-5 d-flex align-items-center gap-3">
                                 <s.icon size={20} className="text-primary opacity-50" />
                                 <div>
                                    <small className="text-[9px] text-muted uppercase font-bold d-block">{s.label}</small>
                                    <span className="text-sm font-bold text-white">{s.val}</span>
                                 </div>
                              </div>
                           </div>
                        ))}
                     </div>
                  </div>
               </div>

               {/* Console Logs */}
               <div className={`card bg-black text-white border-0 shadow-sm rounded-4 overflow-hidden mb-4 ${showLogs ? '' : 'opacity-30'}`}>
                  <div className="card-header bg-black border-bottom border-secondary py-2 d-flex justify-content-between align-items-center">
                     <h3 className="card-title text-[10px] font-bold uppercase text-success mb-0 d-flex align-items-center gap-2">
                        <Terminal size={12} /> Console Output
                     </h3>
                     <span className="badge bg-secondary text-white text-[8px] font-bold">LIVE</span>
                  </div>
                  <div className="card-body p-3 font-monospace text-[10px] text-success opacity-80" style={{ maxHeight: '180px', overflowY: 'auto' }}>
                     <div className="mb-1">{isRunning ? "> Initializing migration engine..." : "> System idle. Ready for command."}</div>
                     {progress > 10 && <div className="mb-1 text-muted">[{new Date().toLocaleTimeString()}] Fetching source manifest...</div>}
                     {progress > 50 && <div className="mb-1">✅ Axes structure successfully migrated to Firestore.</div>}
                     {progress >= 100 && <div className="mb-1 text-primary">🎉 ARCHITECTURE SYNC COMPLETED SUCCESSFULLY.</div>}
                  </div>
               </div>

               {/* Warning Callout */}
               <div className="p-4 bg-danger bg-opacity-5 rounded-4 border border-danger border-opacity-20 d-flex align-items-start gap-3">
                  <div className="bg-danger text-white p-2 rounded-circle shadow-sm mt-1">
                     <AlertTriangle size={16} />
                  </div>
                  <div>
                     <h6 className="fw-bold text-danger mb-1 text-[10px] uppercase tracking-widest">Data Integrity Warning</h6>
                     <p className="text-[10px] text-muted mb-0">
                        <strong>ระวัง:</strong> การดำเนินการนี้จะเขียนทับโครงสร้างความสัมพันธ์ (Mapping) เดิมทั้งหมด กรุณาสำรองข้อมูล (Backup) และตรวจสอบความถูกต้องของไฟล์ต้นฉบับก่อนรันระบบ
                     </p>
                  </div>
               </div>
            </div>
         </div>
      </div>
   );
}
