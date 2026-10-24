"use client";

import { useState, useEffect, useMemo } from "react";
import {
   Sliders, Search, RefreshCw, Save,
   AlertTriangle, CheckCircle, ShieldAlert,
   Undo2, Info, Loader2, Database, ChevronDown, ChevronUp
} from "lucide-react";
import { getAxes, getAxesWeightConfig, updateAxesWeightConfig } from "@/utils/api/services";

interface AxisItem {
   id: string;
   numericId: number;
   name: string;
   domainTitle: string;
   subAxes: { name: string; description: string }[];
}

const DOMAIN_COLOR: Record<string, string> = {
   "Immune–Infection Governance": "#0A5C8E",
   "Metabolic–Energy Core": "#059669",
   "Genomic–Longevity Programming": "#D97706",
   "Neuro-Endocrine Governance": "#6B7280",
   "Circulatory-Vascular": "#DC2626",
   "Gut-Microbiome Axis": "#7C3AED",
   "Detoxification-Biotransformation": "#0D9488",
   "Structural-Matrix": "#CA8A04",
   "Hormonal Regulation Core": "#E11D48",
   "Cellular Quality & Autophagy": "#4F46E5",
   "Epigenetic & Chronological": "#0284C7",
   "Mitochondrial Bioenergetics": "#EA580C"
};

const DEFAULT_COLOR = "#9CA3AF";

export default function AxisWeightsPage() {
   const [search, setSearch] = useState("");
   const [selectedDomain, setSelectedDomain] = useState("all");
   
   const [allAxes, setAllAxes] = useState<AxisItem[]>([]);
   const [domains, setDomains] = useState<string[]>([]);
   
   const [weights, setWeights] = useState<Record<string, number>>({});
   
   const [isLoading, setIsLoading] = useState(true);
   const [isSaving, setIsSaving] = useState(false);
   const [message, setMessage] = useState<{ type: "success" | "error" | ""; text: string }>({ type: "", text: "" });

   useEffect(() => {
      loadData();
   }, []);

   const loadData = async () => {
      setIsLoading(true);
      try {
         // Fetch axes from Firestore
         const axesData = await getAxes();
         
         const formattedAxes: AxisItem[] = axesData.map((a: any) => {
            const numericId = parseInt(String(a.axis_id).replace(/\D/g, '')) || 0;
            const subAxesList = a.sub_axes ? Object.values(a.sub_axes).map((sa: any) => ({
               name: sa.name,
               description: sa.description
            })) : [];

            return {
               id: `AXIS_${numericId}`,
               numericId: numericId,
               name: a.name || `Axis ${numericId}`,
               domainTitle: a.domain_title || "Other",
               subAxes: subAxesList
            };
         });

         // Sort by numeric ID
         formattedAxes.sort((a, b) => a.numericId - b.numericId);
         setAllAxes(formattedAxes);

         // Extract unique domains
         const uniqueDomains = Array.from(new Set(formattedAxes.map(a => a.domainTitle))).filter(Boolean);
         setDomains(uniqueDomains);

         // Fetch weights
         const dbWeights = await getAxesWeightConfig();
         const initialWeights: Record<string, number> = {};
         
         // Initialize all axes to 1.0 default
         formattedAxes.forEach(ax => {
            initialWeights[ax.id] = 1.0;
         });

         if (dbWeights) {
            Object.keys(dbWeights).forEach(key => {
               if (initialWeights[key] !== undefined) {
                  initialWeights[key] = dbWeights[key];
               }
            });
         }
         setWeights(initialWeights);

      } catch (err: any) {
         console.error("Failed to load data:", err);
         setMessage({ type: "error", text: "ไม่สามารถโหลดข้อมูลจากระบบหลักได้" });
      } finally {
         setIsLoading(false);
      }
   };

   const handleWeightChange = (id: string, value: number) => {
      setWeights(prev => ({ ...prev, [id]: value }));
   };

   const handleResetDefaults = () => {
      const resetWeights: Record<string, number> = {};
      allAxes.forEach(ax => {
         resetWeights[ax.id] = 1.0;
      });
      setWeights(resetWeights);
      setMessage({ type: "success", text: "รีเซ็ตค่าน้ำหนักเริ่มต้น (100%) เรียบร้อยแล้ว กรุณากดปุ่มบันทึกเพื่อยืนยัน" });
   };

   const handleSave = async () => {
      setIsSaving(true);
      setMessage({ type: "", text: "" });
      try {
         await updateAxesWeightConfig(weights);
         setMessage({ type: "success", text: "บันทึกค่าน้ำหนักชีวภาพของอัลกอริทึม TSPI สำเร็จแล้ว" });
      } catch (err: any) {
         console.error("Save error:", err);
         setMessage({ type: "error", text: "เกิดข้อผิดพลาดในการบันทึกข้อมูล: " + err.message });
      } finally {
         setIsSaving(false);
      }
   };

   // Filter axes
   const filteredAxes = useMemo(() => {
      return allAxes.filter(ax => {
         const matchesSearch = ax.name.toLowerCase().includes(search.toLowerCase()) ||
            ax.id.toLowerCase().includes(search.toLowerCase()) ||
            ax.domainTitle.toLowerCase().includes(search.toLowerCase());
         const matchesDomain = selectedDomain === "all" || ax.domainTitle === selectedDomain;
         return matchesSearch && matchesDomain;
      });
   }, [allAxes, search, selectedDomain]);

   return (
      <div className="pb-5" style={{ backgroundColor: '#F8FAFC', minHeight: '100vh' }}>
         <div className="container-fluid py-4">
            
            {/* HEADER */}
            <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-4 gap-3 bg-white p-4 rounded-4 shadow-sm border" style={{ borderColor: '#E2E8F0' }}>
               <div>
                  <h1 className="fs-4 fw-bold mb-1 d-flex align-items-center gap-2" style={{ color: '#0F172A' }}>
                     <Sliders size={24} className="text-primary" />
                     TSPI Algorithm Calibration
                  </h1>
                  <p className="text-muted mb-0" style={{ fontSize: '14px' }}>
                     Adjust computational significance weights for the 39 Systemic Axes
                  </p>
               </div>
               <div className="d-flex gap-3">
                  <button
                     onClick={handleResetDefaults}
                     disabled={isLoading || isSaving}
                     className="btn btn-outline-secondary d-flex align-items-center gap-2 fw-semibold px-4"
                     style={{ borderRadius: '8px' }}
                  >
                     <Undo2 size={16} /> Reset Default
                  </button>
                  <button
                     onClick={handleSave}
                     disabled={isLoading || isSaving}
                     className="btn btn-primary d-flex align-items-center gap-2 fw-bold px-4"
                     style={{ borderRadius: '8px' }}
                  >
                     {isSaving ? <Loader2 size={16} className="spinner-border spinner-border-sm" /> : <Save size={16} />}
                     {isSaving ? "Saving..." : "Commit Weights"}
                  </button>
               </div>
            </div>

            {/* NOTIFICATIONS & ALERTS */}
            {message.text && (
               <div className={`alert ${message.type === 'success' ? 'alert-success border-success' : 'alert-danger border-danger'} d-flex align-items-center gap-2 rounded-4 shadow-sm mb-4 border`}>
                  {message.type === 'success' ? <CheckCircle size={18} /> : <AlertTriangle size={18} />}
                  <span className="fw-semibold">{message.text}</span>
               </div>
            )}

            <div className="card border-0 border-start border-warning border-4 shadow-sm rounded-4 mb-4" style={{ backgroundColor: '#FFFBEB' }}>
               <div className="card-body p-4 d-flex gap-3">
                  <ShieldAlert size={24} className="text-warning flex-shrink-0" />
                  <div>
                     <h6 className="fw-bold text-dark mb-1">Institutional Safety Warning</h6>
                     <p className="mb-0 text-muted" style={{ fontSize: '13px' }}>
                        Changing these coefficients directly impacts the calculated <strong>Burden Score</strong> and <strong>Diagnostic Priority</strong> of patients globally. Please ensure calibrations are reviewed by the medical board.
                     </p>
                  </div>
               </div>
            </div>

            {/* FILTERS */}
            <div className="row g-3 mb-4">
               <div className="col-md-8">
                  <div className="input-group bg-white rounded-3 shadow-sm border overflow-hidden">
                     <span className="input-group-text bg-white border-0 text-muted px-3">
                        <Search size={18} />
                     </span>
                     <input
                        type="text"
                        className="form-control border-0 shadow-none py-2"
                        placeholder="Search axes by name, ID, or domain..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                     />
                  </div>
               </div>
               <div className="col-md-4">
                  <select
                     className="form-select bg-white shadow-sm border py-2 fw-semibold text-dark"
                     value={selectedDomain}
                     onChange={(e) => setSelectedDomain(e.target.value)}
                  >
                     <option value="all">All Domains (12 Systems)</option>
                     {domains.map((d, i) => (
                        <option key={i} value={d}>{d}</option>
                     ))}
                  </select>
               </div>
            </div>

            {/* CONTENT */}
            {isLoading ? (
               <div className="d-flex flex-column align-items-center justify-content-center py-5">
                  <Loader2 size={40} className="spinner-border text-primary mb-3" />
                  <p className="text-muted fw-semibold">Loading TSPI Registry...</p>
               </div>
            ) : filteredAxes.length === 0 ? (
               <div className="card border-0 shadow-sm rounded-4 text-center py-5">
                  <Database size={48} className="text-muted opacity-50 mx-auto mb-3" />
                  <h5 className="fw-bold text-dark">No Axes Found</h5>
                  <p className="text-muted mb-0">Try adjusting your search or domain filter.</p>
               </div>
            ) : (
               <div className="row g-4">
                  {filteredAxes.map(ax => {
                     const currentWeight = weights[ax.id] !== undefined ? weights[ax.id] : 1.0;
                     const domainColor = DOMAIN_COLOR[ax.domainTitle] || DEFAULT_COLOR;
                     const weightPercentage = Math.round(currentWeight * 100);

                     return (
                        <div key={ax.id} className="col-md-6 col-xl-4">
                           <div className="card h-100 border-0 shadow-sm rounded-4 overflow-hidden" style={{ transition: 'all 0.2s ease' }}>
                              <div className="card-header border-0 bg-white p-4 pb-2 d-flex justify-content-between align-items-start gap-3">
                                 <div>
                                    <span className="badge mb-2 px-2 py-1" style={{ backgroundColor: `${domainColor}20`, color: domainColor, fontWeight: 700, fontSize: '10px' }}>
                                       {ax.domainTitle}
                                    </span>
                                    <h6 className="fw-bold text-dark mb-1 lh-sm" style={{ fontSize: '15px' }}>
                                       {ax.name}
                                    </h6>
                                    <span className="text-muted fw-semibold" style={{ fontSize: '11px' }}>AXIS {ax.numericId}</span>
                                 </div>
                                 <div className="text-end">
                                    <div className="fw-bold" style={{ fontSize: '24px', color: currentWeight > 1.2 ? '#DC2626' : currentWeight < 0.8 ? '#D97706' : '#0A5C8E' }}>
                                       {weightPercentage}%
                                    </div>
                                    <span className="text-muted d-block" style={{ fontSize: '10px', marginTop: '-4px' }}>IMPACT</span>
                                 </div>
                              </div>
                              
                              <div className="card-body px-4 pt-2 pb-4">
                                 <input
                                    type="range"
                                    className="form-range"
                                    min="0.0"
                                    max="2.0"
                                    step="0.05"
                                    value={currentWeight}
                                    onChange={(e) => handleWeightChange(ax.id, parseFloat(e.target.value))}
                                 />
                                 <div className="d-flex justify-content-between text-muted" style={{ fontSize: '10px', fontWeight: 600 }}>
                                    <span className={currentWeight === 0 ? "text-danger" : ""}>0x (Ignore)</span>
                                    <span className={currentWeight === 1 ? "text-primary" : ""}>1x (Standard)</span>
                                    <span className={currentWeight === 2 ? "text-warning" : ""}>2x (Double)</span>
                                 </div>

                                 {/* Sub-axes Preview */}
                                 {ax.subAxes.length > 0 && (
                                    <div className="mt-3 p-3 rounded-3" style={{ backgroundColor: '#F8FAFC', border: '1px solid #E2E8F0' }}>
                                       <div className="fw-bold text-dark mb-2" style={{ fontSize: '11px', textTransform: 'uppercase' }}>Includes:</div>
                                       <div className="d-flex flex-wrap gap-1">
                                          {ax.subAxes.map((sub, i) => (
                                             <span key={i} className="badge bg-white text-dark border px-2 py-1" style={{ fontSize: '10px', fontWeight: 500 }}>
                                                {sub.name}
                                             </span>
                                          ))}
                                       </div>
                                    </div>
                                 )}
                              </div>
                           </div>
                        </div>
                     );
                  })}
               </div>
            )}
         </div>
      </div>
   );
}