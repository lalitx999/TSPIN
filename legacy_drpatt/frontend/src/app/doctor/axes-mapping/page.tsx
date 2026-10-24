"use client";

import { useState } from "react";
import {
   Search, Filter, ChevronRight, ChevronDown, Microscope,
   Activity, Shield, Droplet, Brain, Heart, TrendingUp,
   Eye, X, Target, Layers, Sparkles, Info, AlertCircle,
   Crosshair, Dna, GitBranch, Beaker, Lock
} from "lucide-react";
import Link from "next/link";
import "./../theme-inapp.css";

export default function AxesMappingPage() {
   const [expandedDomain, setExpandedDomain] = useState<string | null>("D3");
   const [selectedAxis, setSelectedAxis] = useState<any>(null);

   const domains = [
      { id: "D1", name: "Immune & Inflammation", icon: Shield, color: "danger", count: 4 },
      { id: "D3", name: "Metabolic & Glucose", icon: TrendingUp, color: "primary", count: 5 },
      { id: "D12", name: "Neurological Health", icon: Brain, color: "info", count: 3 },
   ];

   const axes = [
      { id: "Ax3.1", name: "Insulin Sensitivity", domain: "D3", scope: "การตอบสนองของเซลล์ต่อฮอร์โมนอินซูลิน", sub: ["A", "B"], biomarkers: ["Glucose", "HbA1c", "Insulin"] },
      { id: "Ax3.2", name: "Lipid Metabolism", domain: "D3", scope: "การสลายและสะสมไขมันในร่างกาย", sub: ["A", "B", "C"], biomarkers: ["LDL", "Triglycerides"] },
   ];

   return (
      <div className="pb-5">
         {/* 🧭 Header Section */}
         <div className="d-flex justify-content-between align-items-center mb-4">
            <div>
               <h1 className="fs-3 fw-bold mb-1 text-dark d-flex align-items-center gap-2">
                  <div className="bg-primary bg-opacity-10 p-2 rounded-3 text-primary">
                     <Layers size={24} />
                  </div>
                  Mechanistic Axes Mapping
               </h1>
               <p className="text-muted text-xs uppercase font-bold tracking-widest ms-5">Clinical Framework</p>
            </div>
         </div>

         {/* 📊 Global Framework Stats */}
         <div className="row g-3 mb-4">
            <div className="col-md-3 col-6">
               <div className="card border-0 shadow-sm bg-white p-3 d-flex align-items-center gap-3">
                  <div className="bg-primary text-white p-3 rounded-3 shadow-sm">
                     <Layers size={20} />
                  </div>
                  <div>
                     <span className="text-[10px] uppercase font-bold text-muted d-block">Total Axes</span>
                     <span className="h5 mb-0 fw-bold text-dark">38</span>
                  </div>
               </div>
            </div>
            <div className="col-md-3 col-6">
               <div className="card border-0 shadow-sm bg-white p-3 d-flex align-items-center gap-3">
                  <div className="bg-info text-white p-3 rounded-3 shadow-sm">
                     <GitBranch size={20} />
                  </div>
                  <div>
                     <span className="text-[10px] uppercase font-bold text-muted d-block">Sub-Mechanisms</span>
                     <span className="h5 mb-0 fw-bold text-dark">114</span>
                  </div>
               </div>
            </div>
            <div className="col-md-3 col-6">
               <div className="card border-0 shadow-sm bg-white p-3 d-flex align-items-center gap-3">
                  <div className="bg-success text-white p-3 rounded-3 shadow-sm">
                     <Activity size={20} />
                  </div>
                  <div>
                     <span className="text-[10px] uppercase font-bold text-muted d-block">Domains</span>
                     <span className="h5 mb-0 fw-bold text-dark">12</span>
                  </div>
               </div>
            </div>
            <div className="col-md-3 col-6">
               <div className="card border-0 shadow-sm bg-white p-3 d-flex align-items-center gap-3">
                  <div className="bg-warning text-white p-3 rounded-3 shadow-sm">
                     <Beaker size={20} />
                  </div>
                  <div>
                     <span className="text-[10px] uppercase font-bold text-muted d-block">Active Markers</span>
                     <span className="h5 mb-0 fw-bold text-dark">240</span>
                  </div>
               </div>
            </div>
         </div>

         {/* 🔍 Search & Filter */}
         <div className="card shadow-sm border-0 bg-white mb-4 rounded-4 overflow-hidden">
            <div className="card-body p-2">
               <div className="row g-2 align-items-center">
                  <div className="col-md-10">
                     <div className="input-group input-group-sm">
                        <span className="input-group-text bg-light border-0"><Search size={16} className="text-muted" /></span>
                        <input type="text" className="form-control bg-light border-0 font-bold text-sm" placeholder="Filter biological domains, axes, or biomarkers..." />
                     </div>
                  </div>
                  <div className="col-md-2">
                     <button className="btn btn-light border btn-sm font-bold px-3 w-100 d-flex align-items-center justify-content-center gap-1">
                        <Filter size={14} /> ADVANCED
                     </button>
                  </div>
               </div>
            </div>
         </div>

         {/* 📂 Biological Domains List */}
         <div className="d-flex flex-column gap-3">
            {domains.map((d) => (
               <div key={d.id} className="card border-0 shadow-sm bg-white rounded-4 overflow-hidden">
                  <div
                     className="card-header bg-transparent py-3 d-flex align-items-center gap-3 cursor-pointer border-0"
                     onClick={() => setExpandedDomain(expandedDomain === d.id ? null : d.id)}
                  >
                     <div className={`bg-${d.color} text-white p-2 rounded-3 shadow-sm d-flex align-items-center justify-content-center`} style={{ width: '42px', height: '42px' }}>
                        <d.icon size={20} />
                     </div>
                     <div className="flex-grow-1">
                        <h6 className="font-bold text-dark m-0">{d.name}</h6>
                        <small className="text-[10px] text-muted font-bold uppercase tracking-tighter">{d.count} MECHANISMS MAPPED</small>
                     </div>
                     <div className="text-muted">
                        {expandedDomain === d.id ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                     </div>
                  </div>

                  {expandedDomain === d.id && (
                     <div className="card-body p-4 pt-0 border-top border-light animate-in fade-in slide-in-from-top-1">
                        <div className="row g-3 mt-1">
                           {axes.map((ax) => (
                              <div key={ax.id} className="col-md-6 col-lg-4">
                                 <div
                                    className="card border shadow-sm mb-0 cursor-pointer transition-all hover:border-primary"
                                    onClick={() => setSelectedAxis(ax)}
                                 >
                                    <div className="card-body p-3">
                                       <div className="d-flex justify-content-between align-items-start mb-2">
                                          <span className="badge bg-primary text-white text-[8px] uppercase px-2 font-bold">{ax.id}</span>
                                          <Eye size={12} className="text-muted opacity-30" />
                                       </div>
                                       <h6 className="font-bold text-dark text-xs mb-1">{ax.name}</h6>
                                       <p className="text-[10px] text-muted mb-3">{ax.scope}</p>
                                       <div className="d-flex flex-wrap gap-1">
                                          {ax.biomarkers.map(b => (
                                             <span key={b} className="text-[8px] font-bold text-muted bg-white border px-2 py-0.5 rounded">{b}</span>
                                          ))}
                                       </div>
                                    </div>
                                 </div>
                              </div>
                           ))}
                        </div>
                     </div>
                  )}
               </div>
            ))}
         </div>

         {/* 🔍 Axis Detail Modal (Overlay) */}
         {selectedAxis && (
            <div className="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center" style={{ zIndex: 1050, backgroundColor: 'rgba(0,0,0,0.5)' }}>
               <div className="bg-white rounded-4 shadow-xl overflow-hidden" style={{ maxWidth: '600px', width: '90%' }}>
                  <div className="card border-0 mb-0">
                     <div className="card-header bg-transparent py-3 d-flex justify-content-between align-items-center border-bottom border-light">
                        <h3 className="card-title text-sm font-bold uppercase d-flex align-items-center gap-2 mb-0">
                           <Crosshair size={16} className="text-primary" /> Mechanistic Detail: {selectedAxis.id}
                        </h3>
                        <button onClick={() => setSelectedAxis(null)} className="btn-close" aria-label="Close"></button>
                     </div>
                     <div className="card-body p-4">
                        <div className="d-flex align-items-center gap-3 mb-4">
                           <div className="bg-primary text-white p-3 rounded-3 shadow-sm">
                              <Dna size={32} />
                           </div>
                           <div>
                              <h4 className="font-bold text-dark mb-0">{selectedAxis.name}</h4>
                              <small className="text-muted font-bold uppercase text-[10px]">{selectedAxis.domain} Framework</small>
                           </div>
                        </div>

                        <div className="p-3 bg-info bg-opacity-5 rounded-3 border-start border-4 border-info mb-4">
                           <p className="text-[10px] font-bold text-info uppercase mb-1">Functional Scope</p>
                           <p className="text-xs text-dark font-medium mb-0">{selectedAxis.scope} และวิเคราะห์ผลกระทบต่อเซลล์เป้าหมายผ่านกระบวนการส่งสัญญาณทางเคมี...</p>
                        </div>

                        <div className="row g-4">
                           <div className="col-md-6">
                              <p className="text-[10px] font-bold text-muted uppercase mb-2 border-bottom pb-1 d-flex align-items-center gap-1">
                                 <GitBranch size={12} className="text-primary" /> Sub-Mechanisms
                              </p>
                              <div className="d-flex flex-column gap-2">
                                 {selectedAxis.sub.map((s: string) => (
                                    <div key={s} className="p-2 border rounded-3 bg-light d-flex align-items-center gap-2">
                                       <span className="badge bg-primary text-white rounded-circle d-flex align-items-center justify-content-center font-bold" style={{ width: '22px', height: '22px' }}>{s}</span>
                                       <span className="text-xs font-bold text-dark">Mechanism Tier {s}</span>
                                    </div>
                                 ))}
                              </div>
                           </div>
                           <div className="col-md-6">
                              <p className="text-[10px] font-bold text-muted uppercase mb-2 border-bottom pb-1 d-flex align-items-center gap-1">
                                 <Beaker size={12} className="text-info" /> Triggering Markers
                              </p>
                              <div className="d-flex flex-wrap gap-2">
                                 {selectedAxis.biomarkers.map((b: string) => (
                                    <span key={b} className="badge bg-info text-white text-[9px] px-3 py-1.5 font-bold">{b}</span>
                                 ))}
                              </div>
                           </div>
                        </div>
                     </div>
                     <div className="card-footer bg-light py-2 text-center border-top">
                        <small className="text-muted d-flex align-items-center justify-content-center gap-1">
                           <Lock size={10} /> ข้อมูลนี้ถูกเข้ารหัสเป็น Clinical Framework สำหรับสมองกล V-Twin Engine
                        </small>
                     </div>
                  </div>
               </div>
            </div>
         )}
      </div>
   );
}
