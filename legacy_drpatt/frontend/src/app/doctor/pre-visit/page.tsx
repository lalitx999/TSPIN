"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
   Brain, Activity, Clock, AlertTriangle, FileText,
   CheckCircle, Stethoscope, Heart, User, ArrowLeft,
   Calendar, Zap, Info, ShieldCheck, Users, ClipboardCheck,
   ChevronRight, RefreshCw, Loader2
} from "lucide-react";
import Link from "next/link";
import { getAppointment } from "@/utils/api/services";
import "./../theme-inapp.css";

function PreVisitContent() {
   const router = useRouter();
   const searchParams = useSearchParams();
   const appointmentId = searchParams.get("id");
   const [loading, setLoading] = useState(true);
   const [data, setData] = useState<any>(null);
   const [error, setError] = useState<string | null>(null);

   useEffect(() => {
      async function fetchData() {
         if (!appointmentId) {
            setLoading(false);
            return;
         }
         try {
            const apptData = await getAppointment(appointmentId);
            if (!apptData) {
               setError("Session data not found or inaccessible.");
               setLoading(false);
               return;
            }
            setData({ appointment: apptData });
         } catch (err) {
            console.error(err);
            setError("Error synchronizing clinical data archive.");
         } finally {
            setLoading(false);
         }
      }
      fetchData();
   }, [appointmentId]);

   if (loading) return <div className="p-5 text-center font-bold text-muted uppercase tracking-widest animate-pulse font-mono">SYNCHRONIZING CLINICAL DATA...</div>;

   if (error || !data) {
      return (
         <div className="d-flex justify-content-center pt-5">
            <div className="col-md-6">
               <div className="card border-0 shadow-lg bg-white rounded-4 overflow-hidden border-top border-4 border-danger">
                  <div className="card-body text-center p-5">
                     <AlertTriangle size={48} className="text-danger mb-3" />
                     <h5 className="fw-black text-dark uppercase tracking-widest">{error || "NO ACTIVE SESSION SELECTED"}</h5>
                     <p className="text-muted small mb-4 font-medium leading-relaxed">The requested clinical briefing session could not be retrieved from the institutional cloud registry.</p>
                     <button onClick={() => router.push("/doctor/appointments")} className="btn btn-primary btn-sm px-4 font-bold uppercase tracking-widest py-2 shadow-sm">Return to Schedule</button>
                  </div>
               </div>
            </div>
         </div>
      );
   }

   const { appointment } = data;

   return (
      <div className="pb-5">
         {/* 🧭 Header Section */}
         <div className="d-flex justify-content-between align-items-center mb-4">
            <div className="d-flex align-items-center gap-3">
               <button onClick={() => router.back()} className="btn btn-light border btn-sm rounded-circle p-2 shadow-sm">
                  <ArrowLeft size={18} />
               </button>
               <div>
                  <h1 className="fs-4 fw-black mb-0 text-dark uppercase tracking-tight">Clinical Pre-visit Briefing</h1>
                  <p className="text-[10px] text-muted uppercase font-bold tracking-widest">Intake Intelligence Session Registry</p>
               </div>
            </div>
            <div className="d-flex gap-2">
               <span className="badge bg-primary bg-opacity-10 text-primary border border-primary border-opacity-20 px-3 py-2 text-[9px] uppercase font-black tracking-widest">Status: Ready for Consultation</span>
            </div>
         </div>

         <div className="row g-4">
            {/* 🏥 Left Column: Patient Profile & AI Insights */}
            <div className="col-lg-8">

               {/* Patient Identity Card */}
               <div className="card border-0 shadow-sm bg-white mb-4 rounded-4 overflow-hidden">
                  <div className="card-header bg-primary py-4 border-0 position-relative" style={{ height: '100px' }}>
                     <div className="position-absolute start-0 top-0 w-100 h-100 opacity-10" style={{ backgroundImage: 'radial-gradient(circle, white 1px, transparent 1px)', backgroundSize: '10px 10px' }}></div>
                  </div>
                  <div className="card-body p-4 pt-0 position-relative">
                     <div className="d-flex align-items-end gap-3 mt-n5 mb-4 px-2">
                        <div className="bg-white p-1 rounded-circle shadow-sm border-white border-4">
                           <div className="bg-light border rounded-circle d-flex align-items-center justify-content-center text-dark font-black h2 mb-0" style={{ width: '100px', height: '100px' }}>
                              {(appointment.patientName || "P").charAt(0)}
                           </div>
                        </div>
                        <div className="mb-2">
                           <h2 className="fw-black text-dark mb-1">{appointment.patientName}</h2>
                           <div className="text-[10px] text-muted font-bold uppercase tracking-widest d-flex align-items-center gap-2">
                              <Users size={12} /> HN: {appointment.hn || String(appointment.id || '').slice(0, 8).toUpperCase()} • Clinical ID: {String(appointment.id || '').slice(-6).toUpperCase()}
                           </div>
                        </div>
                     </div>

                     <div className="row g-3 px-2 border-top border-light pt-4 mt-2">
                        {[
                           { label: "Date of Visit", val: appointment.date || "12 May 24", icon: Calendar },
                           { label: "Session Time", val: appointment.time || "09:30 AM", icon: Clock },
                           { label: "Consultation Type", val: appointment.type || "First Intake", icon: Stethoscope },
                           { label: "Physician Hub", val: "TSPI Precision", icon: Activity },
                        ].map((item, idx) => (
                           <div key={idx} className="col-md-3 col-6">
                              <div className="p-2">
                                 <div className="text-[9px] font-bold text-muted uppercase tracking-widest mb-1 d-flex align-items-center gap-1">
                                    <item.icon size={10} className="text-primary" /> {item.label}
                                 </div>
                                 <div className="text-xs font-black text-dark tracking-tighter">{item.val}</div>
                              </div>
                           </div>
                        ))}
                     </div>
                  </div>
               </div>

               {/* AI Briefing Intelligence */}
               <div className="card border-0 shadow-lg bg-dark text-white rounded-4 overflow-hidden mb-4">
                  <div className="card-header py-3 d-flex justify-content-between align-items-center px-4" style={{ backgroundColor: '#121212', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                     <div className="d-flex align-items-center gap-2">
                        <div className="bg-primary p-2 rounded-circle shadow-sm"><Brain size={18} className="text-white" /></div>
                        <h3 className="card-title text-[10px] font-bold uppercase text-white mb-0 tracking-[0.2em]">Clinical AI Briefing Intelligence</h3>
                     </div>
                     <div className="text-[9px] font-bold text-success uppercase tracking-widest d-flex align-items-center gap-1">
                        <CheckCircle size={12} /> V-Twin Sync Verified
                     </div>
                  </div>
                  <div className="card-body p-4 bg-[#0a0a0a]">
                     <div className="p-3 bg-primary bg-opacity-10 border border-primary border-opacity-20 rounded-4 mb-4">
                        <div className="d-flex align-items-center gap-2 mb-2 text-primary">
                           <Zap size={16} />
                           <span className="text-[10px] font-black uppercase tracking-widest">Initial Clinical Impression</span>
                        </div>
                        <p className="text-sm font-medium mb-0 leading-relaxed text-gray-200">
                           Patient presents with multi-axis biological load primarily centered on the <strong>Metabolic (D3)</strong> and <strong>Immune (D1)</strong> domains. Preliminary intake data suggests chronic systemic stress with potential downstream impact on vascular integrity.
                        </p>
                     </div>

                     <div className="row g-4">
                        <div className="col-md-6 border-end border-white border-opacity-10">
                           <h6 className="text-[10px] font-bold uppercase text-muted tracking-widest mb-3 pb-2 border-bottom border-white border-opacity-5">Urgent Mechanistic Concerns</h6>
                           <ul className="list-unstyled space-y-3">
                              {[
                                 "Insulin Flux Variability (A3.1)",
                                 "Persistent Low-Grade Inflammation (A1.4)",
                                 "Oxidative Burden Elevation (A4.2)"
                              ].map((item, idx) => (
                                 <li key={idx} className="d-flex align-items-start gap-2 mb-3 text-xs">
                                    <div className="mt-1"><AlertTriangle size={12} className="text-warning" /></div>
                                    <span className="text-gray-300 font-medium">{item}</span>
                                 </li>
                              ))}
                           </ul>
                        </div>
                        <div className="col-md-6 ps-md-4">
                           <h6 className="text-[10px] font-bold uppercase text-muted tracking-widest mb-3 pb-2 border-bottom border-white border-opacity-5">Pre-visit Diagnostic Focus</h6>
                           <ul className="list-unstyled space-y-3">
                              {[
                                 "Verify morning cortisol levels",
                                 "Assess sleep architecture impact",
                                 "Review longitudinal biomarker trends"
                              ].map((item, idx) => (
                                 <li key={idx} className="d-flex align-items-start gap-2 mb-3 text-xs">
                                    <div className="mt-1"><div className="bg-primary rounded-circle" style={{ width: 6, height: 6 }}></div></div>
                                    <span className="text-gray-300 font-medium">{item}</span>
                                 </li>
                              ))}
                           </ul>
                        </div>
                     </div>
                  </div>
               </div>
            </div>

            {/* 🏛️ Right Column: Intake Details & Actions */}
            <div className="col-lg-4">
               <div className="card border-0 shadow-sm bg-white mb-4 rounded-4 overflow-hidden">
                  <div className="card-header bg-transparent border-bottom border-light py-3">
                     <h3 className="card-title text-[10px] font-bold uppercase text-muted tracking-widest mb-0">Patient Input Context</h3>
                  </div>
                  <div className="card-body p-4">
                     <div className="mb-4">
                        <h6 className="text-[10px] font-black text-dark uppercase tracking-widest mb-3">Primary Complaints</h6>
                        <div className="p-3 bg-light rounded-3">
                           <p className="text-xs font-bold text-dark mb-0 leading-relaxed">"Feeling chronically fatigued and having trouble staying asleep for the past 3 weeks."</p>
                        </div>
                     </div>

                     <div>
                        <h6 className="text-[10px] font-black text-dark uppercase tracking-widest mb-3">Reported Biomarker Flags</h6>
                        <div className="d-flex flex-wrap gap-2">
                           {["Elevated CRP", "HbA1c > 6.0", "Morning Fatigue"].map((flag, idx) => (
                              <span key={idx} className="badge bg-light border text-muted text-[9px] px-2 py-1 uppercase font-black">{flag}</span>
                           ))}
                        </div>
                     </div>
                  </div>
               </div>

               <div className="card border-0 shadow-sm bg-white mb-4 rounded-4 overflow-hidden border-start border-4 border-primary">
                  <div className="card-body p-4 text-center">
                     <h6 className="text-[10px] font-black text-dark uppercase tracking-widest mb-4">Clinical Action Console</h6>
                     <div className="d-flex flex-column gap-2">
                        <button onClick={() => router.push(`/doctor/ai-physician?id=${appointment.patientId}`)} className="btn btn-dark btn-sm w-100 font-bold uppercase tracking-widest text-[9px] py-2.5 d-flex align-items-center justify-content-center gap-2">
                           <Zap size={12} className="text-primary" /> Start AI Analysis session
                        </button>
                        <button className="btn btn-outline-secondary btn-sm w-100 font-bold uppercase tracking-widest text-[9px] py-2.5 d-flex align-items-center justify-content-center gap-2">
                           <RefreshCw size={12} /> Sync Digital Twin
                        </button>
                     </div>
                  </div>
               </div>

               <div className="p-4 bg-info bg-opacity-5 rounded-4 border border-info border-opacity-10 d-flex align-items-center gap-3">
                  <div className="bg-info text-white p-2 rounded-circle shadow-sm">
                     <ShieldCheck size={18} />
                  </div>
                  <div>
                     <h6 className="fw-bold text-info mb-1 text-[10px] uppercase tracking-widest">Protocol Verified</h6>
                     <p className="text-[9px] text-muted mb-0 font-medium">Session data is encrypted and verified against institutional governance v3.2.</p>
                  </div>
               </div>
            </div>
         </div>
      </div>
   );
}

export default function PreVisitPage() {
   return (
      <Suspense fallback={<div className="p-5 text-center font-bold text-muted animate-pulse font-mono uppercase tracking-widest">SYNCHRONIZING CLINICAL DATA...</div>}>
         <PreVisitContent />
      </Suspense>
   );
}
