"use client";

import { useState } from "react";
import {
   Layers,
   ChevronRight,
   Search,
   Shield,
   Droplet,
   TrendingUp,
   Leaf,
   Heart,
   Wrench,
   Bone,
   Activity,
   Brain,
   Eye,
   FlaskConical,
   Zap,
   Info,
   Edit3,
   Plus
} from "lucide-react";

const DOMAINS = [
   { id: "D1", name: "Immune / Shield", icon: Shield, color: "text-primary", bg: "bg-light" },
   { id: "D2", name: "Blood / Droplet", icon: Droplet, color: "text-primary", bg: "bg-light" },
   { id: "D3", name: "Metabolic / Energy", icon: TrendingUp, color: "text-primary", bg: "bg-light" },
   { id: "D4", name: "Detox / Cleanse", icon: Leaf, color: "text-primary", bg: "bg-light" },
   { id: "D5", name: "Cardiovascular / Heart", icon: Heart, color: "text-primary", bg: "bg-light" },
   { id: "D6", name: "Structural / Repair", icon: Wrench, color: "text-primary", bg: "bg-light" },
   { id: "D7", name: "Bone / Matrix", icon: Bone, color: "text-primary", bg: "bg-light" },
   { id: "D8", name: "Endocrine / Signal", icon: Activity, color: "text-primary", bg: "bg-light" },
   { id: "D9", name: "Neurological / Mind", icon: Brain, color: "text-primary", bg: "bg-light" },
   { id: "D10", name: "Sensory / Perception", icon: Eye, color: "text-primary", bg: "bg-light" },
   { id: "D11", name: "Cellular / Vitality", icon: Zap, color: "text-primary", bg: "bg-light" },
   { id: "D12", name: "Regulatory / Flow", icon: Layers, color: "text-primary", bg: "bg-light" },
];

export default function MechanisticAxesPage() {
   const [selectedDomain, setSelectedDomain] = useState("D1");
   const [searchTerm, setSearchTerm] = useState("");

   const axes = [
      { code: "D1_IMMUNE_RESP", name: "Immune Response Status", status: "Active", weight: 0.8 },
      { code: "D1_INFLAM_MARK", name: "Inflammatory Markers", status: "Active", weight: 1.2 },
      { code: "D1_AUTOIMM_TEN", name: "Autoimmune Tendency", status: "Inactive", weight: 0.5 },
   ];

   return (
      <div className="p-4" style={{ fontFamily: 'Kanit, sans-serif' }}>
         {/* Header Area */}
         <div className="mb-4 text-start">
            <div className="d-flex align-items-center gap-2 mb-2">
               <div className="bg-primary-custom bg-opacity-10 p-2 rounded-3">
                  <Layers size={20} className="text-primary-custom" />
               </div>
               <span className="tiny fw-bold text-primary-custom text-uppercase tracking-widest">Clinical Core</span>
            </div>
            <div className="d-flex align-items-center justify-content-between flex-wrap gap-3">
               <div>
                  <h3 className="fw-bold text-dark mb-1">38 Mechanistic Axes</h3>
                  <p className="small text-muted mb-0">จัดการแกนชีววิทยาที่เป็นรากฐานของระบบ V-Twin Clinical Engine</p>
               </div>
               <button className="btn btn-drpat-primary rounded-pill px-4 py-2 fw-bold shadow-sm d-flex align-items-center gap-2">
                  <Plus size={18} /> เพิ่มแกนใหม่
               </button>
            </div>
         </div>

         <div className="row g-4">
            {/* Left: Domain Selector */}
            <div className="col-lg-4">
               <div className="bg-white rounded-5 shadow-sm border border-light p-3">
                  <div className="mb-3 px-2">
                     <div className="position-relative">
                        <Search className="position-absolute top-50 start-0 translate-middle-y ms-3 text-muted" size={16} />
                        <input
                           type="text"
                           className="form-control form-control-sm rounded-pill ps-5 bg-light border-0 py-2 tiny"
                           placeholder="ค้นหา Domain หรือแกน..."
                           value={searchTerm}
                           onChange={(e) => setSearchTerm(e.target.value)}
                        />
                     </div>
                  </div>

                  <div className="d-grid gap-1 overflow-auto max-h-75vh pe-2 custom-scrollbar">
                     {DOMAINS.map((domain) => {
                        const isActive = selectedDomain === domain.id;
                        const Icon = domain.icon;
                        return (
                           <button
                              key={domain.id}
                              onClick={() => setSelectedDomain(domain.id)}
                              className={`btn border-0 text-start p-3 rounded-4 d-flex align-items-center justify-content-between transition-all ${isActive ? "bg-primary-custom text-white shadow" : "text-dark hover-bg-light"}`}
                           >
                              <div className="d-flex align-items-center gap-3">
                                 <div className={`${isActive ? "bg-white text-primary-custom" : `${domain.bg} ${domain.color}`} p-2 rounded-3`}>
                                    <Icon size={18} />
                                 </div>
                                 <div>
                                    <p className={`tiny fw-bold mb-0 ${isActive ? "text-white" : "text-muted"}`}>{domain.id}</p>
                                    <p className="small fw-bold mb-0 text-truncate" style={{ maxWidth: '150px' }}>{domain.name}</p>
                                 </div>
                              </div>
                              {isActive && <ChevronRight size={14} className="opacity-50" />}
                           </button>
                        );
                     })}
                  </div>
               </div>
            </div>

            {/* Right: Axis List */}
            <div className="col-lg-8">
               <div className="bg-white rounded-5 shadow-sm border border-light p-4 h-100">
                  <div className="d-flex align-items-center justify-content-between mb-4">
                     <h6 className="fw-bold text-dark mb-0">รายการแกนภายใต้ {selectedDomain}</h6>
                     <div className="badge-pill-custom bg-light text-muted border-0 small">3 Axes Found</div>
                  </div>

                  <div className="table-responsive">
                     <table className="table align-middle">
                        <thead>
                           <tr>
                              <th className="tiny fw-bold text-muted uppercase">รหัสแกน (Code)</th>
                              <th className="tiny fw-bold text-muted uppercase">ชื่อแกน (Name)</th>
                              <th className="tiny fw-bold text-muted uppercase text-center">ค่าน้ำหนัก (Weight)</th>
                              <th className="tiny fw-bold text-muted uppercase text-center">สถานะ</th>
                              <th className="tiny fw-bold text-muted uppercase text-end">จัดการ</th>
                           </tr>
                        </thead>
                        <tbody>
                           {axes.map((ax, i) => (
                              <tr key={i}>
                                 <td><code className="tiny fw-bold text-primary-custom bg-primary-custom bg-opacity-5 px-2 py-1 rounded">{ax.code}</code></td>
                                 <td><span className="small fw-medium text-dark">{ax.name}</span></td>
                                 <td className="text-center"><span className="small fw-bold text-dark">{ax.weight}x</span></td>
                                 <td className="text-center">
                                    <span className={`tiny fw-bold px-2 py-1 rounded-pill ${ax.status === "Active" ? "bg-success bg-opacity-10 text-success" : "bg-light text-muted"}`}>
                                       {ax.status}
                                    </span>
                                 </td>
                                 <td className="text-end">
                                    <button className="btn btn-light rounded-circle p-2"><Edit3 size={14} className="text-muted" /></button>
                                 </td>
                              </tr>
                           ))}
                        </tbody>
                     </table>
                  </div>

                  <div className="bg-secondary-custom rounded-4 p-4 mt-4 border border-light">
                     <div className="d-flex align-items-start gap-3">
                        <div className="bg-white rounded-circle p-2 shadow-sm text-primary-custom">
                           <Info size={16} />
                        </div>
                        <div>
                           <p className="small fw-bold text-dark mb-1">Clinical Logic Tip</p>
                           <p className="tiny text-muted mb-0 leading-relaxed">
                              แกนชีววิทยาใน Domain **{DOMAINS.find(d => d.id === selectedDomain)?.name}** จะส่งผลต่อการคำนวณความเสี่ยงของคนไข้ในส่วนของ AI Intake และ AI Physician Consultation โปรดตรวจสอบค่าน้ำหนัก (Weight) ให้สอดคล้องกับแนวทางเวชปฏิบัติ
                           </p>
                        </div>
                     </div>
                  </div>
               </div>
            </div>
         </div>

         <style jsx>{`
        .hover-bg-light:hover { background-color: #f8f9fa; }
        .max-h-75vh { max-height: 75vh; }
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #eee; border-radius: 10px; }
        .leading-relaxed { line-height: 1.6; }
      `}</style>
      </div>
   );
}
