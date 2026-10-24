"use client";

import { useState, useEffect, useMemo } from "react";
import {
   BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip,
   ReferenceLine, ResponsiveContainer, Radar, RadarChart, PolarGrid,
   PolarAngleAxis, PolarRadiusAxis
} from "recharts";
import {
   Activity, AlertTriangle, Search, Settings2,
   Database, User, ChevronRight, Zap, Loader2,
   RefreshCw, FileText
} from "lucide-react";
import { getAllPatients, getAxes, getPatient } from "@/utils/api/services";
import Link from "next/link";

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

export default function AxisGraphPage() {
   const [isClient, setIsClient] = useState(false);
   const [patients, setPatients] = useState<any[]>([]);
   const [selectedPatientId, setSelectedPatientId] = useState<string>("");
   const [allAxes, setAllAxes] = useState<any[]>([]);
   
   const [loading, setLoading] = useState(true);
   const [loadingTwin, setLoadingTwin] = useState(false);
   const [isAnalyzing, setIsAnalyzing] = useState(false);
   
   const [snapshot, setSnapshot] = useState<any>(null);
   const [graphData, setGraphData] = useState<any[]>([]);
   const [domainData, setDomainData] = useState<any[]>([]);

   useEffect(() => {
      setIsClient(true);
      const initData = async () => {
         try {
            setLoading(true);
            const [pats, axes] = await Promise.all([
               getAllPatients(),
               getAxes()
            ]);
            setPatients(pats);
            // Sort axes by ID
            const sortedAxes = axes.sort((a: any, b: any) => {
               const idA = parseInt(String(a.axis_id).replace(/\D/g, '')) || 0;
               const idB = parseInt(String(b.axis_id).replace(/\D/g, '')) || 0;
               return idA - idB;
            });
            setAllAxes(sortedAxes);
         } catch (error) {
            console.error("Error loading init data", error);
         } finally {
            setLoading(false);
         }
      };
      initData();
   }, []);

   useEffect(() => {
      if (!selectedPatientId) {
         setSnapshot(null);
         setGraphData([]);
         setDomainData([]);
         return;
      }

      const fetchPatientTwin = async () => {
         try {
            setLoadingTwin(true);
            const patData = await getPatient(selectedPatientId);
            if (patData && patData.axes) {
               setSnapshot({ axesState: patData.axes });
               processGraphData(patData.axes);
            } else {
               setSnapshot(null);
               setGraphData([]);
               setDomainData([]);
            }
         } catch (error) {
            console.error("Error fetching twin", error);
         } finally {
            setLoadingTwin(false);
         }
      };

      fetchPatientTwin();
   }, [selectedPatientId]);

   const processGraphData = (axesState: Record<string, any>) => {
      const newGraphData: any[] = [];
      const domainScores: Record<string, { total: number; count: number }> = {};

      allAxes.forEach(axis => {
         const key = `AXIS_${axis.axis_id}`;
         const state = axesState[key];
         const hasScore = state?.score !== null && state?.score !== undefined;
         const score = hasScore ? state.score : 0;
         const domain = axis.domain_title || "Other";
         const color = DOMAIN_COLOR[domain] || DEFAULT_COLOR;

         newGraphData.push({
            axis: key.replace('AXIS_', 'A'),
            name: axis.name,
            domain: domain,
            score: score,
            color: color,
            isCritical: hasScore && score > 75,
            isElevated: hasScore && score > 50 && score <= 75,
            isNotAssessed: !hasScore
         });

         if (hasScore) {
            if (!domainScores[domain]) {
               domainScores[domain] = { total: 0, count: 0 };
            }
            domainScores[domain].total += score;
            domainScores[domain].count += 1;
         }
      });

      setGraphData(newGraphData);

      const radarData = Object.keys(domainScores).map(domain => {
         const avg = Math.round(domainScores[domain].total / domainScores[domain].count);
         return {
            subject: domain.split(' ')[0], // Shorten name for radar
            fullDomain: domain,
            score: avg,
            fullMark: 100
         };
      });
      setDomainData(radarData);
   };

   const handleRunEngine = async () => {
      if (!selectedPatientId) return;
      const patient = patients.find(p => p.id === selectedPatientId);
      if (!patient) return;
      
      try {
         setIsAnalyzing(true);
         
         const symptomsList = patient.symptoms 
            ? (Array.isArray(patient.symptoms) ? patient.symptoms : patient.symptoms.split(',').map((s:any) => s.trim()).filter(Boolean)) 
            : [];
         const defaultNotes = symptomsList.length > 0 ? `พบอาการ: ${symptomsList.join(", ")}` : "ไม่พบอาการเบื้องต้น";
         
         const response = await fetch("/api/ai/precision", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
               patientId: selectedPatientId,
               rawInput: defaultNotes,
               labData: {}
            })
         });
         
         if (!response.ok) throw new Error("Failed to execute clinical engine");
         const rawSnapshot = await response.json();
         setSnapshot(rawSnapshot);
         processGraphData(rawSnapshot.axesState || {});
      } catch (error) {
         console.error("Clinical Engine Error:", error);
         alert("ระบบประมวลผลล้มเหลว");
      } finally {
         setIsAnalyzing(false);
      }
   };

   const CustomTooltip = ({ active, payload }: any) => {
      if (active && payload && payload.length) {
         const data = payload[0].payload;
         return (
            <div className="card shadow-sm border-0" style={{ minWidth: '220px', background: '#fff' }}>
               <div className="card-header border-0" style={{ padding: '12px 16px', background: '#F8FAFC' }}>
                  <div className="d-flex align-items-center gap-2">
                     <div style={{ width: '12px', height: '12px', borderRadius: '3px', backgroundColor: data.color }} />
                     <span style={{ fontSize: '11px', fontWeight: 600, color: '#6B7280', textTransform: 'uppercase' }}>
                        {data.axis} • {data.domain}
                     </span>
                  </div>
               </div>
               <div className="p-3">
                  <p style={{ fontSize: '13px', fontWeight: 600, color: '#1F2937', marginBottom: '8px', lineHeight: 1.4 }}>
                     {data.name}
                  </p>
                  <div className="d-flex align-items-center justify-content-between">
                     <span style={{ fontWeight: 800, fontSize: '24px', color: data.color }}>
                        {data.score}%
                     </span>
                     {data.isCritical && (
                        <span className="badge" style={{ background: '#FEF2F2', color: '#DC2626', fontSize: '10px', fontWeight: 700, padding: '4px 8px' }}>
                           CRITICAL
                        </span>
                     )}
                     {data.isElevated && (
                        <span className="badge" style={{ background: '#FFF7ED', color: '#D97706', fontSize: '10px', fontWeight: 700, padding: '4px 8px' }}>
                           ELEVATED
                        </span>
                     )}
                  </div>
               </div>
            </div>
         );
      }
      return null;
   };

   if (!isClient) return null;

   return (
      <div className="pb-8" style={{ backgroundColor: '#F8FAFC', minHeight: '100vh' }}>
         <div className="container-fluid py-4">
            
            {/* HEADER */}
            <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-4 gap-3 bg-white p-4 rounded-4 shadow-sm border" style={{ borderColor: '#E2E8F0' }}>
               <div>
                  <h1 className="fs-4 fw-bold mb-1" style={{ color: '#0F172A' }}>Biological Network Graph</h1>
                  <p className="text-muted mb-0" style={{ fontSize: '14px' }}>Systemic Load Visualization & AI Mechanistic Insights</p>
               </div>
               <div className="d-flex align-items-center gap-3">
                  <div className="bg-light px-3 py-2 rounded-3 border">
                     <div className="d-flex align-items-center gap-2">
                        <User size={16} className="text-muted" />
                        <select 
                           className="form-select form-select-sm border-0 bg-transparent fw-semibold shadow-none p-0 text-truncate" 
                           style={{ width: '100%', maxWidth: '250px', color: '#1F2937', cursor: 'pointer' }}
                           value={selectedPatientId}
                           onChange={(e) => setSelectedPatientId(e.target.value)}
                        >
                           <option value="">-- Select Patient --</option>
                           {patients.map(p => {
                              const fullName = `${p.fname} ${p.lname} ${p.hn ? `(${p.hn})` : ''}`;
                              const displayName = fullName.length > 35 ? fullName.substring(0, 35) + '...' : fullName;
                              return (
                                 <option key={p.id} value={p.id}>
                                    {displayName}
                                 </option>
                              );
                           })}
                        </select>
                     </div>
                  </div>
                  {selectedPatientId && snapshot && (
                     <button 
                        onClick={handleRunEngine} 
                        disabled={isAnalyzing}
                        className="btn btn-primary d-inline-flex align-items-center"
                        style={{ fontWeight: 600, borderRadius: '8px', padding: '8px 16px' }}
                     >
                        {isAnalyzing ? <Loader2 size={16} className="spinner-border spinner-border-sm me-2" /> : <RefreshCw size={16} className="me-2" />}
                        {isAnalyzing ? "Processing..." : "Re-Analyze"}
                     </button>
                  )}
               </div>
            </div>

            {loading ? (
               <div className="d-flex align-items-center justify-content-center py-5">
                  <Loader2 className="spinner-border text-primary" style={{ width: '32px', height: '32px', animationDuration: '1s' }} />
               </div>
            ) : selectedPatientId && loadingTwin ? (
               <div className="d-flex align-items-center justify-content-center py-5">
                  <Loader2 className="spinner-border text-primary" style={{ width: '32px', height: '32px', animationDuration: '1s' }} />
                  <span className="ms-3 fw-semibold text-muted">Loading Graph Data...</span>
               </div>
            ) : selectedPatientId && !snapshot ? (
               <div className="card border-0 shadow-sm text-center py-5 rounded-4">
                  <Database size={48} style={{ color: '#CBD5E1', margin: '0 auto 16px auto' }} />
                  <h4 className="fw-bold text-dark">No Graph Data</h4>
                  <p className="text-muted mb-4">Run the AI Engine to generate the biological network and insights.</p>
                  <button 
                     onClick={handleRunEngine} 
                     disabled={isAnalyzing}
                     className="btn btn-primary d-inline-flex align-items-center" 
                     style={{ margin: '0 auto', padding: '12px 28px', borderRadius: '50px', fontWeight: 600 }}
                  >
                     {isAnalyzing ? (
                        <><Loader2 size={18} className="me-2 spinner-border spinner-border-sm" /> Processing...</>
                     ) : (
                        <><Zap size={18} className="me-2" /> Generate Graph Data</>
                     )}
                  </button>
               </div>
            ) : selectedPatientId && snapshot ? (
               <>
                  <div className="row g-4 mb-4">
                     {/* RADAR CHART (SYSTEMIC OVERVIEW) */}
                     <div className="col-xl-5">
                        <div className="card border-0 shadow-sm h-100 rounded-4">
                           <div className="card-header bg-white border-0 pt-4 pb-0 px-4 d-flex justify-content-between align-items-center">
                              <h5 className="fw-bold mb-0 text-dark d-flex align-items-center gap-2">
                                 <Activity size={20} color="#0A5C8E" /> Systemic Domain Load
                              </h5>
                           </div>
                           <div className="card-body p-0 d-flex align-items-center justify-content-center" style={{ minHeight: '350px' }}>
                              <ResponsiveContainer width="100%" height={320}>
                                 <RadarChart cx="50%" cy="50%" outerRadius="65%" data={domainData}>
                                    <PolarGrid stroke="#E2E8F0" />
                                    <PolarAngleAxis 
                                       dataKey="subject" 
                                       tick={{ fill: '#475569', fontSize: 11, fontWeight: 600 }}
                                    />
                                    <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                                    <Radar name="Severity Score" dataKey="score" stroke="#0A5C8E" strokeWidth={2} fill="#0A5C8E" fillOpacity={0.3} />
                                    <RechartsTooltip />
                                 </RadarChart>
                              </ResponsiveContainer>
                           </div>
                        </div>
                     </div>

                     {/* AI MECHANISTIC INSIGHTS (DETAILED TEXT) */}
                     <div className="col-xl-7">
                        <div className="card border-0 shadow-sm h-100 rounded-4" style={{ overflow: 'hidden' }}>
                           <div className="card-header border-0 px-4 py-3 d-flex justify-content-between align-items-center" style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)' }}>
                              <h5 className="fw-bold mb-0 text-white d-flex align-items-center gap-2">
                                 <FileText size={18} color="#38BDF8" /> Mechanistic Insights
                              </h5>
                              <span className="badge bg-white text-dark rounded-pill px-3 py-1 fw-bold" style={{ fontSize: '11px' }}>
                                 AI Generated
                              </span>
                           </div>
                           <div className="card-body p-4" style={{ backgroundColor: '#F8FAFC', maxHeight: '400px', overflowY: 'auto' }}>
                              <div className="prose prose-sm max-w-none text-dark" style={{ fontSize: '14px', lineHeight: '1.7' }}>
                                 {snapshot.mechanisticInsights ? (
                                    <div style={{ whiteSpace: 'pre-line' }}>{snapshot.mechanisticInsights}</div>
                                 ) : (
                                    <p className="text-muted font-italic">No detailed insights available for this snapshot.</p>
                                 )}
                              </div>
                           </div>
                           <div className="card-footer bg-white border-top px-4 py-3">
                              <Link href="/doctor/therapeutic-matrix" className="btn btn-dark w-100 fw-bold d-flex align-items-center justify-content-center gap-2 rounded-3 py-2">
                                 View Recommended Therapeutics <ChevronRight size={16} />
                              </Link>
                           </div>
                        </div>
                     </div>
                  </div>

                  {/* 39-AXIS BAR CHART */}
                  <div className="card border-0 shadow-sm rounded-4 mb-4">
                     <div className="card-header bg-white border-0 pt-4 pb-2 px-4 d-flex justify-content-between align-items-center">
                        <h5 className="fw-bold mb-0 text-dark d-flex align-items-center gap-2">
                           <Activity size={20} color="#DC2626" /> 39-Axis Detailed Propagation
                        </h5>
                        <div className="d-flex gap-3">
                           <div className="d-flex align-items-center gap-2">
                              <div style={{ width: '12px', height: '12px', background: '#DC2626', borderRadius: '50%' }}></div>
                              <span style={{ fontSize: '12px', fontWeight: 600, color: '#64748B' }}>Critical ({'>'}75%)</span>
                           </div>
                           <div className="d-flex align-items-center gap-2">
                              <div style={{ width: '12px', height: '12px', background: '#D97706', borderRadius: '50%' }}></div>
                              <span style={{ fontSize: '12px', fontWeight: 600, color: '#64748B' }}>Elevated ({'>'}50%)</span>
                           </div>
                        </div>
                     </div>
                     <div className="card-body px-2 pb-4">
                        <ResponsiveContainer width="100%" height={400}>
                           <BarChart data={graphData} margin={{ top: 20, right: 20, left: -20, bottom: 60 }}>
                              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                              <XAxis
                                 dataKey="axis"
                                 axisLine={{ stroke: '#CBD5E1' }}
                                 tickLine={false}
                                 tick={{ fontSize: 10, fontWeight: 700, fill: '#475569' }}
                                 interval={0}
                                 angle={-45}
                                 textAnchor="end"
                              />
                              <YAxis
                                 axisLine={false}
                                 tickLine={false}
                                 tick={{ fontSize: 11, fontWeight: 600, fill: '#64748B' }}
                                 domain={[0, 100]}
                              />
                              <RechartsTooltip content={<CustomTooltip />} cursor={{ fill: '#F1F5F9' }} />
                              <ReferenceLine y={75} stroke="#DC2626" strokeDasharray="4 4" />
                              <ReferenceLine y={50} stroke="#D97706" strokeDasharray="4 4" />
                              <Bar dataKey="score" radius={[4, 4, 0, 0]} maxBarSize={30}>
                                 {graphData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.color} opacity={0.9} />
                                 ))}
                              </Bar>
                           </BarChart>
                        </ResponsiveContainer>
                     </div>
                  </div>
               </>
            ) : (
               <div className="card border-0 shadow-sm text-center py-5 rounded-4">
                  <User size={48} style={{ color: '#CBD5E1', margin: '0 auto 16px auto' }} />
                  <h4 className="fw-bold text-dark">Welcome to Axis Graph</h4>
                  <p className="text-muted mb-0">Please select a patient to continue.</p>
               </div>
            )}
         </div>
      </div>
   );
}
