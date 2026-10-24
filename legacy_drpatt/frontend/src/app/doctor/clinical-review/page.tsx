"use client";

import { useState, useEffect } from "react";
import {
   Brain, Zap, Activity, AlertTriangle, Target,
   Package, Search, RefreshCw, FileText, CheckCircle,
   Info, Sparkles, Microscope, Users, ClipboardCheck,
   ShieldCheck, ArrowRightCircle, Loader2, Filter,
   FlaskConical, X, Calendar, User, ChevronRight, AlertCircle, History, Globe
} from "lucide-react";
import Link from "next/link";
import { getAllPatients, getLabResults, getPatient } from "@/utils/api/services";
import axesData from "@/data/39_last_x.json";

// 🇹🇭 Thai Localization Dictionaries for Clinical HUD
const domainThaiNames: Record<number, string> = {
   1: "การควบคุมระบบภูมิคุ้มกันและการติดเชื้อ (Immune-Infection Governance)",
   2: "แกนระบบเผาผลาญและพลังงาน (Metabolic-Energy Core)",
   3: "โปรแกรมรหัสพันธุกรรมและการยืดอายุขัย (Genomic-Longevity)",
   4: "การควบคุมระบบประสาทและต่อมไร้ท่อ (Neuro-Endocrine Governance)",
   5: "การควบคุมระบบหมุนเวียนโลหิตและหลอดเลือด (Circulatory-Vascular)",
   6: "แกนระบบทางเดินอาหารและจุลชีพในลำไส้ (Gut-Microbiome Axis)",
   7: "การกำจัดสารพิษและการเปลี่ยนรูปทางชีวภาพ (Detoxification-Biotransformation)",
   8: "การควบคุมโครงสร้างและเนื้อเยื่อพยุง (Structural-Matrix)",
   9: "แกนการควบคุมระบบฮอร์โมน (Hormonal Regulation Core)",
   10: "คุณภาพระดับเซลล์และการกลืนกินตัวเอง (Cellular Quality & Autophagy)",
   11: "การแสดงออกเหนือพันธุกรรมและอายุชีวภาพ (Epigenetic & Chronological)",
   12: "พลังงานชีวภาพระดับไมโทคอนเดรีย (Mitochondrial Bioenergetics)"
};

const axisThaiNames: Record<number, string> = {
   1: "ภาระการอักเสบทั่วร่างกาย (Systemic Inflammatory Load)",
   2: "สมดุลการตอบสนองทางภูมิคุ้มกัน (Immune Homeostasis)",
   3: "ระบบการป้องกันเชื้อโรค (Pathogen Defense)",
   4: "ภาวะการคงอยู่หลังติดเชื้อ (Post-Infectious Persistence)",
   5: "การควบคุมน้ำตาลและอินซูลิน (Glucose-Insulin)",
   6: "สมดุลไขมันและภาวะพิษจากไขมัน (Lipid-Liotoxicity)",
   7: "กลไกการรับรู้สารอาหาร (AMPK-mTOR)",
   8: "เครือข่ายไมโทคอนเดรีย (Mitochondrial Network)",
   9: "ภาวะเครียดจากออกซิเดชัน (Oxidative Stress)",
   10: "สมดุลโปรตีนและการกลืนกินตนเอง (Proteostasis-Autophagy)",
   11: "ระบบซ่อมแซม DNA และความมั่นคงของยีน (DNA Repair)",
   12: "การควบคุมระดับเหนือพันธุกรรม (Epigenetic Regulation)",
   13: "สัญญาณชะลอวัย (Longevity Signaling)",
   14: "ความชราภาพของเซลล์และสารหลั่งชรา (Senescence & SASP)",
   15: "สมดุลแกนความเครียด HPA (Cortisol/DHEA)",
   16: "สมดุลระบบประสาทอัตโนมัติ (Autonomic Balance)",
   17: "การรับส่งสารสื่อประสาท (Neurotransmitter Signaling)",
   18: "ภาวะอักเสบในระบบประสาทและแนวกั้นสมอง (Neuroinflammation)",
   19: "การทำงานของต่อมไทรอยด์ส่วนปลาย (Thyroid Peripheral)",
   20: "การสร้างฮอร์โมนจากต่อมหมวกไต (Adrenal Steroidogenesis)",
   21: "แกนควบคุมฮอร์โมนเพศ HPG (HPG Axis)",
   22: "ความแข็งแรงของผนังกั้นลำไส้ (Gut Barrier Integrity)",
   23: "ภาวะจุลชีพเสียสมดุลในลำไส้ (Dysbiosis & Ecology)",
   24: "กรดน้ำดีและการไหลเวียนรอบตับ (Bile Acid)",
   25: "กระบวนการขจัดสารพิษที่ตับ เฟส 1/2 (Hepatic Phase 1/2)",
   26: "การขับสารพิษออกนอกเซลล์ เฟส 3 (Cellular Efflux)",
   27: "ภาระโลหะหนักสะสม (Heavy Metal Burden)",
   28: "วิถีปฏิกิริยาเมทิลเลชัน (Methylation Pathway)",
   29: "สมดุลกลูตาไธโอนและวิถีกำมะถัน (Transsulfuration)",
   30: "การทำงานของเยื่อบุหลอดเลือด (Endothelial Function)",
   31: "สมดุลการแข็งตัวและการละลายลิ่มเลือด (Coagulation)",
   32: "ความสมบูรณ์ของหลอดเลือดฝอย (Microvascular Integrity)",
   33: "โครงสร้างเนื้อเยื่อภายนอกเซลล์ (ECM Remodeling)",
   34: "ขีดความสามารถการฟื้นฟูของสเต็มเซลล์ (Stem Cell)",
   35: "การไหลเวียนของระบบน้ำเหลือง (Lymphatic Drainage)",
   36: "นาฬิกาชีวิตและคุณภาพการนอนหลับ (Sleep & Circadian)",
   37: "การสื่อสารระหว่างเซลล์ (Cell-Cell Communication)",
   38: "เกลือแร่และศักย์ไฟฟ้าของเยื่อหุ้มเซลล์ (Electrolyte)",
   39: "ความสามารถในการปรับตัวต่อสภาพแวดล้อม (Microclimate)"
};

const getAxisDefinition = (axisKey: string) => {
   const match = axisKey.match(/\d+/);
   if (!match) return null;
   const numericId = parseInt(match[0], 10);
   
   for (const domain of (axesData as any).domains || []) {
      for (const axis of domain.axes || []) {
         if (axis.axis_id === numericId) {
            return {
               ...axis,
               domainTitle: domain.title,
               domainId: domain.domain_id
            };
         }
      }
   }
   return null;
};

interface Patient {
   id: string;
   fname: string;
   lname: string;
   hn?: string;
   age?: string | number;
   gender?: string;
   symptoms?: string | string[];
   allergies?: string | string[];
}

export default function ClinicalReviewPage() {
   // State
   const [patients, setPatients] = useState<Patient[]>([]);
   const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
   const [loadingPatients, setLoadingPatients] = useState(true);
   const [searchTerm, setSearchTerm] = useState("");
   const [clinicalNotes, setClinicalNotes] = useState("");
   const [labs, setLabs] = useState<any[]>([]);
   const [loadingLabs, setLoadingLabs] = useState(false);
   
   // AI Execution States
   const [isAnalyzing, setIsAnalyzing] = useState(false);
   const [analysisStep, setAnalysisStep] = useState(0);
   const [result, setResult] = useState<any>(null);
   const [activeTab, setActiveTab] = useState("roots");
   
   // Language Toggle
   const [displayLang, setDisplayLang] = useState<"th" | "en">("th");
   const [translatedTextCache, setTranslatedTextCache] = useState<Record<string, string>>({});
   const [isTranslating, setIsTranslating] = useState(false);
   
   // History states
   const [history, setHistory] = useState<any[]>([]);
   const [loadingHistory, setLoadingHistory] = useState(false);
   const [selectedHistoryId, setSelectedHistoryId] = useState<string | null>(null);
   
   // Toast Notification
   const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);

   // Load Patients
   useEffect(() => {
      const fetchPatients = async () => {
         try {
            setLoadingPatients(true);
            const data = await getAllPatients();
            setPatients(data as Patient[]);
         } catch (error) {
            console.error("Error loading patients:", error);
            showToast("ไม่สามารถโหลดรายชื่อผู้ป่วยได้", "error");
         } finally {
            setLoadingPatients(false);
         }
      };
      fetchPatients();
   }, []);

   // Load Patient Details & Labs & Snapshots History when patient changes
   useEffect(() => {
      if (!selectedPatient) {
         setLabs([]);
         setHistory([]);
         setResult(null);
         setSelectedHistoryId(null);
         return;
      }

      const fetchPatientDetails = async () => {
         try {
            // Fetch Labs
            setLoadingLabs(true);
            const labData = await getLabResults(selectedPatient.id);
            setLabs(labData);

            // Fetch Digital Twin History from EMR patient record
            setLoadingHistory(true);
            const patientData = await getPatient(selectedPatient.id);
            const historyList = patientData?.digitalTwinHistory || [];
            setHistory(historyList);

            // Auto-select latest snapshot if available
            if (historyList.length > 0) {
               setResult(historyList[0]);
               setSelectedHistoryId(historyList[0].id);
            } else {
               setResult(null);
               setSelectedHistoryId(null);
            }
            // Reset translation state
            setDisplayLang("th");
            setTranslatedTextCache({});
         } catch (error) {
            console.error("Error loading patient details:", error);
            showToast("ไม่สามารถโหลดประวัติเก่าได้", "error");
         } finally {
            setLoadingLabs(false);
            setLoadingHistory(false);
         }
      };

      fetchPatientDetails();
   }, [selectedPatient]);

   // Toast helper
   const showToast = (message: string, type: "success" | "error" | "info") => {
      setToast({ message, type });
      setTimeout(() => setToast(null), 4000);
   };

   // Change analysis steps to make the loading feel dynamic and clinical
   useEffect(() => {
      if (!isAnalyzing) return;
      
      const steps = [
         "กำลังเชื่อมโยงประวัติและวิเคราะห์ลักษณะทางคลินิก (Clinical Phenotype)...",
         "กำลังวิเคราะห์ค่าตัวบ่งชี้ทางชีวภาพ (Biomarker Integration)...",
         "กำลังประเมินกลไกและเวกเตอร์ระบบ 39 แกน (Systemic Pathway Mapping)...",
         "กำลังค้นหาปัจจัยต้นตอและความเชื่อมโยงของเซลล์ (Root Cause Analysis)...",
         "กำลังจำลองผลลัพธ์ผ่านโมเดลคู่แฝดดิจิทัล (Digital Twin Synchronization)...",
         "กำลังสรุปรายงานและแนะนำโมดูลบำบัดรักษาฟื้นฟู (Generating Precision Protocol)..."
      ];
      
      setAnalysisStep(0);
      const interval = setInterval(() => {
         setAnalysisStep(prev => {
            if (prev < steps.length - 1) {
               return prev + 1;
            }
            return prev;
         });
      }, 3500);

      return () => clearInterval(interval);
   }, [isAnalyzing]);

   // Helper: parse array-or-string arrays
   const getSymptoms = () => {
      if (!selectedPatient || !selectedPatient.symptoms) return [];
      if (Array.isArray(selectedPatient.symptoms)) return selectedPatient.symptoms;
      if (typeof selectedPatient.symptoms === 'string') return selectedPatient.symptoms.split(',').map(s => s.trim()).filter(Boolean);
      return [];
   };

   const getAllergies = () => {
      if (!selectedPatient || !selectedPatient.allergies) return [];
      if (Array.isArray(selectedPatient.allergies)) return selectedPatient.allergies;
      if (typeof selectedPatient.allergies === 'string') return selectedPatient.allergies.split(',').map(s => s.trim()).filter(Boolean);
      return [];
   };

   // Run the V-Twin Clinical Engine flow
   const handleRunEngine = async () => {
      if (!selectedPatient) {
         showToast("กรุณาเลือกผู้ป่วยก่อน", "info");
         return;
      }

      try {
         setIsAnalyzing(true);
         
         // Extract structured lab values if present
         const formattedLabData = labs.reduce((acc: any, lab: any) => {
            if (lab.markers) {
               Object.assign(acc, lab.markers);
            }
            return acc;
         }, {});

         const symptomsList = getSymptoms();
         const defaultNotes = symptomsList.length > 0 ? `พบอาการ: ${symptomsList.join(", ")}` : "ไม่พบอาการเบื้องต้น";

         const response = await fetch("/api/ai/precision", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
               patientId: String(selectedPatient.id),
               rawInput: clinicalNotes || defaultNotes,
               labData: formattedLabData
            })
         });

         if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.error || errData.message || "Failed to execute clinical engine");
         }

         const rawSnapshot = await response.json();
         
         // Reload History List from EMR patient record
         const patientData = await getPatient(selectedPatient.id);
         const historyList = patientData?.digitalTwinHistory || [];
         setHistory(historyList);

         // Display new result
         setResult(rawSnapshot);
         setSelectedHistoryId(rawSnapshot.snapshotId || historyList[0]?.id || "new");
         showToast("วิเคราะห์สำเร็จและบันทึกประวัติแล้ว", "success");
      } catch (error: any) {
         console.error("Clinical Engine Error:", error);
         showToast(error.message || "ระบบประมวลผลล้มเหลว", "error");
      } finally {
         setIsAnalyzing(false);
      }
   };

   // Select an older snapshot from the timeline
   const handleSelectHistoryItem = (item: any) => {
      setResult(item);
      setSelectedHistoryId(item.id);
   };

   // Handle Language Toggle
   const toggleLanguage = async (lang: "th" | "en") => {
      if (displayLang === lang) return;
      setDisplayLang(lang);

      if (!result || !result.mechanisticInsights) return;

      const cacheKey = `${selectedHistoryId}_${lang}`;
      if (translatedTextCache[cacheKey]) return; // Already translated

      // Assume original output is mostly English, so 'en' cache is just original if we haven't translated to TH yet?
      // Actually, Groq tends to reply in English. Let's just pass whatever it is to translator.
      try {
         setIsTranslating(true);
         const res = await fetch("/api/ai/translate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: result.mechanisticInsights, targetLang: lang })
         });
         
         if (res.ok) {
            const data = await res.json();
            setTranslatedTextCache(prev => ({
               ...prev,
               [cacheKey]: data.translatedText
            }));
         }
      } catch (err) {
         console.error("Translation Error", err);
         showToast("ไม่สามารถแปลภาษาได้ในขณะนี้", "error");
      } finally {
         setIsTranslating(false);
      }
   };

   const getDisplayMechanisticInsights = () => {
      if (!result) return "";
      const cacheKey = `${selectedHistoryId}_${displayLang}`;
      if (displayLang === 'th' && translatedTextCache[cacheKey]) return translatedTextCache[cacheKey];
      if (displayLang === 'en' && translatedTextCache[cacheKey]) return translatedTextCache[cacheKey];
      
      // If no translation exists in cache yet, show original, or if it's currently translating show a loader message
      if (isTranslating) return "กำลังแปลภาษา (Translating)...";
      return result.mechanisticInsights;
   };

   // Calculate Systemic Burden Score percentage based on axes State
   const getBurdenStats = () => {
      if (!result || !result.axesState) return { score: 0, criticalCount: 0 };
      const states = Object.values(result.axesState) as any[];
      const total = states.length;
      if (total === 0) return { score: 0, criticalCount: 0 };

      const sum = states.reduce((acc, curr) => acc + (curr.score || 0), 0);
      const criticalCount = states.filter(s => s.score > 60).length;
      return {
         score: Math.round(sum / total),
         criticalCount
      };
   };

   const burdenStats = getBurdenStats();

   // Filter patients by search term
   const filteredPatients = patients.filter(p => {
      const fullName = `${p.fname || ""} ${p.lname || ""}`.toLowerCase();
      const hn = (p.hn || "").toLowerCase();
      const q = searchTerm.toLowerCase();
      return fullName.includes(q) || hn.includes(q);
   });

   const loadingStepsText = [
      "กำลังเชื่อมโยงประวัติและวิเคราะห์ลักษณะทางคลินิก (Clinical Phenotype)...",
      "กำลังวิเคราะห์ค่าตัวบ่งชี้ทางชีวภาพ (Biomarker Integration)...",
      "กำลังประเมินกลไกและเวกเตอร์ระบบ 39 แกน (Systemic Pathway Mapping)...",
      "กำลังค้นหาปัจจัยต้นตอและความเชื่อมโยงของเซลล์ (Root Cause Analysis)...",
      "กำลังจำลองผลลัพธ์ผ่านโมเดลคู่แฝดดิจิทัล (Digital Twin Synchronization)...",
      "กำลังสรุปรายงานและแนะนำโมดูลบำบัดรักษาฟื้นฟู (Generating Precision Protocol)..."
   ];

   return (
      <div className="container-fluid py-4" style={{ backgroundColor: '#F8FAFC', minHeight: '100vh' }}>
         <Link href="/doctor/artifact-review" className="btn btn-outline-primary mb-3">ตรวจร่าง Agentic และประวัติความคิดเห็น (ไม่ใช่อนุมัติ)</Link>
         {/* Toast Notification */}
         {toast && (
            <div className="position-fixed top-0 start-50 translate-middle-x mt-4 z-3 shadow-lg" style={{
               background: toast.type === "success" ? "#10B981" : toast.type === "error" ? "#EF4444" : "#0A5C8E",
               color: "white",
               padding: "14px 24px",
               borderRadius: "8px",
               fontWeight: 600,
               fontSize: "14px",
               display: "flex",
               alignItems: "center",
               gap: "10px",
               animation: 'slideDown 0.3s ease-out'
            }}>
               {toast.type === "success" ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
               {toast.message}
            </div>
         )}

         {/* Header */}
         <div className="d-flex justify-content-between align-items-center mb-4 pb-3" style={{ borderBottom: '2px solid #E2E8F0' }}>
            <div>
               <h1 className="fs-4 fw-bold mb-1 text-dark d-flex align-items-center gap-2">
                  <Brain className="text-primary" size={26} />
                  ระบบวิเคราะห์และจำลองคู่แฝดดิจิทัล (V-Twin Clinical Review)
               </h1>
               <p className="text-muted mb-0" style={{ fontSize: '13px' }}>
                  ประเมินสุขภาพแบบองค์รวมด้วยระบบวิเคราะห์สรีรวิทยาระดับเซลล์ (39 Axes Systemic Analysis)
               </p>
            </div>
            
            {/* Language Toggle */}
            <div className="btn-group shadow-sm bg-white rounded-pill p-1 border">
               <button 
                  onClick={() => toggleLanguage('th')}
                  className={`btn btn-sm rounded-pill px-3 fw-bold ${displayLang === 'th' ? 'btn-primary' : 'btn-white text-muted border-0'}`}
                  style={{ fontSize: '12px' }}
               >
                  ไทย
               </button>
               <button 
                  onClick={() => toggleLanguage('en')}
                  className={`btn btn-sm rounded-pill px-3 fw-bold ${displayLang === 'en' ? 'btn-primary' : 'btn-white text-muted border-0'}`}
                  style={{ fontSize: '12px' }}
               >
                  EN
               </button>
            </div>
         </div>

         <div className="row g-4">
            {/* LEFT COLUMN: PATIENT SELECTION */}
            <div className="col-lg-4">
               <div className="card shadow-sm border-0 mb-4" style={{ borderRadius: '10px', backgroundColor: '#FFFFFF' }}>
                  <div className="card-header bg-white border-bottom py-3">
                     <h6 className="mb-0 fw-bold text-dark d-flex align-items-center">
                        <Users size={18} className="me-2 text-primary" /> เลือกประวัติผู้ป่วย
                     </h6>
                  </div>
                  <div className="card-body p-0">
                     <div className="p-3 bg-light border-bottom">
                        <div className="input-group">
                           <span className="input-group-text bg-white border-end-0 text-muted">
                              <Search size={16} />
                           </span>
                           <input
                              type="text"
                              className="form-control border-start-0 ps-0 shadow-none"
                              placeholder="ค้นหา HN, ชื่อ, นามสกุล..."
                              value={searchTerm}
                              onChange={(e) => setSearchTerm(e.target.value)}
                           />
                           {searchTerm && (
                              <button className="btn btn-white border border-start-0 text-muted" onClick={() => setSearchTerm("")}>
                                 <X size={16} />
                              </button>
                           )}
                        </div>
                     </div>
                     <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                        {loadingPatients ? (
                           <div className="text-center py-4">
                              <Loader2 size={24} className="spinner-border text-primary" />
                              <p className="text-muted mt-2" style={{ fontSize: '13px' }}>กำลังโหลดรายชื่อ...</p>
                           </div>
                        ) : filteredPatients.length === 0 ? (
                           <div className="text-center py-4 text-muted" style={{ fontSize: '13px' }}>ไม่พบรายชื่อผู้ป่วย</div>
                        ) : (
                           filteredPatients.map(p => {
                              const isSelected = selectedPatient?.id === p.id;
                              return (
                                 <div
                                    key={p.id}
                                    onClick={() => setSelectedPatient(p)}
                                    className="d-flex justify-content-between align-items-center px-4 py-3 border-bottom"
                                    style={{
                                       cursor: 'pointer',
                                       backgroundColor: isSelected ? '#EFF6FF' : '#FFFFFF',
                                       transition: 'background 0.2s ease',
                                    }}
                                 >
                                    <div>
                                       <div className={`fw-bold ${isSelected ? 'text-primary' : 'text-dark'}`} style={{ fontSize: '14px' }}>
                                          {p.fname} {p.lname}
                                       </div>
                                       <div className="text-muted mt-1" style={{ fontSize: '12px' }}>
                                          HN: {p.hn || 'N/A'} • {p.gender === 'male' ? 'ชาย' : p.gender === 'female' ? 'หญิง' : p.gender || 'ไม่ระบุ'}, {p.age || '-'} ปี
                                       </div>
                                    </div>
                                    <ChevronRight size={16} className={isSelected ? 'text-primary' : 'text-muted'} />
                                 </div>
                              );
                           })
                        )}
                     </div>
                  </div>
               </div>

               {/* PATIENT CONTEXT INFO */}
               {selectedPatient && (
                  <div className="card shadow-sm border-0" style={{ borderRadius: '10px', backgroundColor: '#FFFFFF' }}>
                     <div className="card-header bg-white border-bottom py-3">
                        <h6 className="mb-0 fw-bold text-dark d-flex align-items-center">
                           <ClipboardCheck size={18} className="me-2 text-primary" /> ข้อมูลทางคลินิก (Clinical Context)
                        </h6>
                     </div>
                     <div className="card-body">
                        {/* Allergies & Demographics */}
                        <div className="mb-3 p-3 rounded" style={{ backgroundColor: '#F8FAFC', border: '1px solid #E2E8F0' }}>
                           <div className="d-flex justify-content-between mb-2 pb-2 border-bottom">
                              <span className="text-muted" style={{ fontSize: '12px' }}>เพศ / อายุ</span>
                              <span className="fw-bold text-dark" style={{ fontSize: '12px' }}>{selectedPatient.gender === 'male' ? 'ชาย' : selectedPatient.gender === 'female' ? 'หญิง' : 'ไม่ระบุ'} / {selectedPatient.age || '-'} ปี</span>
                           </div>
                           <div className="d-flex justify-content-between">
                              <span className="text-muted" style={{ fontSize: '12px' }}>ประวัติการแพ้</span>
                              <span className="fw-bold text-danger text-end" style={{ fontSize: '12px', maxWidth: '60%' }}>
                                 {getAllergies().length > 0 ? getAllergies().join(", ") : "ไม่มีประวัติ"}
                              </span>
                           </div>
                        </div>

                        {/* Symptoms */}
                        <div className="mb-3">
                           <label className="form-label text-muted fw-bold" style={{ fontSize: '12px' }}>อาการทางคลินิกเบื้องต้น (Symptoms)</label>
                           <div className="d-flex flex-wrap gap-2">
                              {getSymptoms().length > 0 ? getSymptoms().map((s, i) => (
                                 <span key={i} className="badge bg-light text-dark border px-2 py-1" style={{ fontSize: '12px', fontWeight: 500 }}>
                                    {s}
                                 </span>
                              )) : <span className="text-muted" style={{ fontSize: '12px' }}>ไม่มีการบันทึกอาการ</span>}
                           </div>
                        </div>

                        {/* Labs Preview */}
                        <div className="mb-3">
                           <label className="form-label text-muted fw-bold" style={{ fontSize: '12px' }}>ผลแล็บล่าสุด</label>
                           {loadingLabs ? (
                              <div className="text-muted" style={{ fontSize: '12px' }}><Loader2 size={12} className="spinner-border me-1" /> กำลังโหลด...</div>
                           ) : labs.length === 0 ? (
                              <div className="text-muted p-2 bg-light rounded text-center" style={{ fontSize: '12px' }}>ไม่พบข้อมูลแล็บ</div>
                           ) : (
                              <div className="d-flex flex-wrap gap-1">
                                 {labs.slice(0, 1).map((lab: any) => {
                                    if (!lab.markers || Object.keys(lab.markers).length === 0) return <span key={lab.id} className="text-muted">ไม่พบข้อมูลตัวบ่งชี้</span>;
                                    return Object.entries(lab.markers).map(([marker, value]: any) => (
                                       <span key={marker} className="badge bg-primary text-white px-2 py-1" style={{ fontSize: '11px', fontWeight: 500 }}>
                                          {marker}: {value}
                                       </span>
                                    ));
                                 })}
                              </div>
                           )}
                        </div>

                        {/* Notes Input */}
                        <div className="mb-4">
                           <label className="form-label text-muted fw-bold" style={{ fontSize: '12px' }}>บันทึกข้อสังเกตแพทย์ (Clinical Notes)</label>
                           <textarea
                              className="form-control"
                              rows={3}
                              placeholder="เพิ่มข้อสังเกตหรืออาการเพื่อใช้วิเคราะห์ร่วมกับ AI..."
                              value={clinicalNotes}
                              onChange={(e) => setClinicalNotes(e.target.value)}
                              style={{ fontSize: '13px', resize: 'vertical' }}
                           />
                        </div>

                        <button
                           onClick={handleRunEngine}
                           disabled={isAnalyzing}
                           className="btn btn-primary w-100 d-flex align-items-center justify-content-center fw-bold"
                           style={{ padding: '12px', fontSize: '14px', borderRadius: '8px', backgroundColor: '#0A5C8E' }}
                        >
                           {isAnalyzing ? (
                              <><Loader2 size={18} className="spinner-border me-2" /> กำลังประมวลผล V-Twin...</>
                           ) : (
                              <><Brain size={18} className="me-2" /> เริ่มการวิเคราะห์สรีรวิทยาระบบ (Run Engine)</>
                           )}
                        </button>
                     </div>
                  </div>
               )}
            </div>

            {/* RIGHT COLUMN: ANALYSIS RESULTS */}
            <div className="col-lg-8">
               {isAnalyzing ? (
                  // Loader Mode
                  <div className="card shadow-sm border-0 d-flex flex-column align-items-center justify-content-center h-100" style={{ minHeight: '600px', backgroundColor: '#FFFFFF', borderRadius: '10px' }}>
                     <div className="spinner-grow text-primary mb-4" style={{ width: '4rem', height: '4rem' }} role="status">
                        <span className="visually-hidden">Loading...</span>
                     </div>
                     <h5 className="fw-bold text-dark mb-2">V-Twin AI Engine กำลังทำงาน</h5>
                     <p className="text-primary fw-bold text-center" style={{ fontSize: '14px', maxWidth: '80%' }}>
                        {loadingStepsText[analysisStep]}
                     </p>
                     <div className="progress mt-4 w-50" style={{ height: '8px', borderRadius: '10px' }}>
                        <div className="progress-bar progress-bar-striped progress-bar-animated bg-primary" 
                             style={{ width: `${((analysisStep + 1) / loadingStepsText.length) * 100}%` }} />
                     </div>
                  </div>
               ) : !result ? (
                  // Empty State
                  <div className="card shadow-sm border-0 d-flex flex-column align-items-center justify-content-center h-100 p-5 text-center" style={{ minHeight: '600px', backgroundColor: '#FFFFFF', borderRadius: '10px' }}>
                     <div className="bg-light rounded-circle p-4 mb-4">
                        <Activity size={48} className="text-muted" />
                     </div>
                     <h5 className="fw-bold text-dark">ระบบประเมินความสมดุลร่างกายด้วย V-Twin AI</h5>
                     <p className="text-muted mt-2" style={{ maxWidth: '500px', fontSize: '14px' }}>
                        โปรดเลือกประวัติผู้ป่วยจากแถบด้านซ้าย เพื่อดูผลการประเมินประวัติย้อนหลัง หรือกด "เริ่มการวิเคราะห์สรีรวิทยาระบบ" เพื่อวิเคราะห์ข้อมูลปัจจุบัน
                     </p>
                  </div>
               ) : (
                  // Results Dashboard
                  <div className="d-flex flex-column gap-4">
                     {/* Score Cards */}
                     <div className="row g-4">
                        <div className="col-md-4">
                           <div className="card shadow-sm border-0 h-100" style={{ borderRadius: '10px', backgroundColor: '#FFFFFF' }}>
                              <div className="card-body d-flex flex-column justify-content-between p-4">
                                 <h6 className="text-muted fw-bold mb-3" style={{ fontSize: '12px' }}>ภาพรวมความตึงเครียด (Systemic Burden)</h6>
                                 <div className="d-flex align-items-end gap-2">
                                    <h1 className="fw-bold mb-0" style={{ fontSize: '42px', color: burdenStats.score > 60 ? '#DC2626' : burdenStats.score > 40 ? '#F59E0B' : '#10B981' }}>
                                       {burdenStats.score}%
                                    </h1>
                                 </div>
                                 <p className="text-muted mt-3 mb-0" style={{ fontSize: '12px' }}>สะท้อนระดับภาระการทำงานหนักโดยรวมของระบบร่างกาย</p>
                              </div>
                           </div>
                        </div>

                        <div className="col-md-4">
                           <div className="card shadow-sm border-0 h-100" style={{ borderRadius: '10px', backgroundColor: '#FEF2F2' }}>
                              <div className="card-body d-flex flex-column justify-content-between p-4">
                                 <h6 className="text-danger fw-bold mb-3" style={{ fontSize: '12px' }}>แกนระบบที่เข้าขั้นวิกฤต (Critical Vectors)</h6>
                                 <h1 className="fw-bold text-danger mb-0" style={{ fontSize: '42px' }}>
                                    {burdenStats.criticalCount}
                                 </h1>
                                 <p className="text-danger mt-3 mb-0" style={{ fontSize: '12px', opacity: 0.8 }}>จำนวนระบบทางชีววิทยาที่ต้องได้รับการดูแลเร่งด่วน</p>
                              </div>
                           </div>
                        </div>

                        <div className="col-md-4">
                           <div className="card shadow-sm border-0 h-100" style={{ borderRadius: '10px', backgroundColor: '#FFFFFF' }}>
                              <div className="card-body p-3">
                                 <h6 className="text-muted fw-bold mb-2 pb-2 border-bottom d-flex align-items-center gap-2" style={{ fontSize: '12px' }}>
                                    <History size={14} /> ประวัติการวิเคราะห์ (History)
                                 </h6>
                                 <div className="d-flex flex-column gap-2" style={{ maxHeight: '110px', overflowY: 'auto' }}>
                                    {history.map((h) => (
                                       <button
                                          key={h.id}
                                          onClick={() => handleSelectHistoryItem(h)}
                                          className="btn btn-sm d-flex justify-content-between align-items-center text-start border-0 rounded"
                                          style={{
                                             backgroundColor: selectedHistoryId === h.id ? '#EFF6FF' : 'transparent',
                                             color: selectedHistoryId === h.id ? '#0A5C8E' : '#475569',
                                             fontWeight: selectedHistoryId === h.id ? '600' : '400',
                                             fontSize: '12px',
                                             padding: '6px 10px'
                                          }}
                                       >
                                          <span>{new Date(h.timestamp).toLocaleDateString("th-TH")}</span>
                                          <span className="badge bg-light text-dark border">วิกฤต {Object.values(h.axesState || {}).filter((a: any) => a.score > 60).length}</span>
                                       </button>
                                    ))}
                                 </div>
                              </div>
                           </div>
                        </div>
                     </div>

                     {/* Tabs section */}
                     <div className="card shadow-sm border-0" style={{ borderRadius: '10px', backgroundColor: '#FFFFFF' }}>
                        <div className="card-header bg-white border-bottom p-0">
                           <div className="d-flex">
                              <button
                                 onClick={() => setActiveTab("roots")}
                                 className="btn btn-link text-decoration-none rounded-0 px-4 py-3 border-0 fw-bold"
                                 style={{
                                    fontSize: '13px',
                                    color: activeTab === 'roots' ? '#0A5C8E' : '#64748B',
                                    borderBottom: activeTab === 'roots' ? '3px solid #0A5C8E' : '3px solid transparent'
                                 }}
                              >
                                 ผลการวิเคราะห์ภาพรวม (Analysis)
                              </button>
                              <button
                                 onClick={() => setActiveTab("axes")}
                                 className="btn btn-link text-decoration-none rounded-0 px-4 py-3 border-0 fw-bold"
                                 style={{
                                    fontSize: '13px',
                                    color: activeTab === 'axes' ? '#0A5C8E' : '#64748B',
                                    borderBottom: activeTab === 'axes' ? '3px solid #0A5C8E' : '3px solid transparent'
                                 }}
                              >
                                 ตารางคะแนน 39 แกน (39-Axes Burden Map)
                              </button>
                              <button
                                 onClick={() => setActiveTab("modules")}
                                 className="btn btn-link text-decoration-none rounded-0 px-4 py-3 border-0 fw-bold"
                                 style={{
                                    fontSize: '13px',
                                    color: activeTab === 'modules' ? '#0A5C8E' : '#64748B',
                                    borderBottom: activeTab === 'modules' ? '3px solid #0A5C8E' : '3px solid transparent'
                                 }}
                              >
                                 เป้าหมายการรักษา (Protocol)
                              </button>
                           </div>
                        </div>

                        <div className="card-body p-4" style={{ minHeight: '400px' }}>
                           {/* TAB: Analysis */}
                           {activeTab === 'roots' && (
                              <div>
                                 <div className="alert alert-success d-flex align-items-start gap-3 border-0" style={{ backgroundColor: '#F0FDF4', color: '#166534' }}>
                                    <ShieldCheck size={24} className="flex-shrink-0 mt-1" />
                                    <div>
                                       <h6 className="fw-bold mb-1">สถานะความปลอดภัยทางคลินิก</h6>
                                       <p className="mb-0" style={{ fontSize: '13px' }}>
                                          ไม่พบระดับอันตรายเฉียบพลัน ข้อมูลแสดงสภาวะความเครียดสะสมเรื้อรัง ระบบแนะนำให้ฟื้นฟูเสถียรภาพระดับเซลล์
                                       </p>
                                    </div>
                                 </div>
                                 <h6 className="fw-bold mt-4 mb-3 text-dark d-flex align-items-center gap-2">
                                    <Sparkles size={18} className="text-primary" /> 
                                    {displayLang === 'th' ? 'สรุปผลวิเคราะห์เชิงกลไก (Mechanistic Summary)' : 'Mechanistic Summary'}
                                    {isTranslating && <Loader2 size={14} className="spinner-border text-primary ms-2" />}
                                 </h6>
                                 <div className="p-4 bg-light rounded border text-dark" style={{ whiteSpace: 'pre-line', fontSize: '14px', lineHeight: '1.8' }}>
                                    {getDisplayMechanisticInsights() || "ไม่พบรายละเอียดเชิงลึก โปรดรันวิเคราะห์ข้อมูลใหม่"}
                                 </div>
                              </div>
                           )}

                           {/* TAB: Axes Map */}
                           {activeTab === 'axes' && (
                              <div>
                                 <div className="d-flex justify-content-between align-items-center mb-4">
                                    <h6 className="fw-bold text-dark mb-0">ระดับภาระความเครียดแยกตามแกนระบบ</h6>
                                    <div className="d-flex gap-2">
                                       <span className="badge bg-danger-subtle text-danger px-2 py-1">วิกฤต (&gt;60)</span>
                                       <span className="badge bg-warning-subtle text-dark px-2 py-1">ปานกลาง (40-60)</span>
                                       <span className="badge bg-success-subtle text-success px-2 py-1">ปกติ (&lt;40)</span>
                                    </div>
                                 </div>
                                 <div className="row g-3" style={{ maxHeight: '450px', overflowY: 'auto' }}>
                                    {(() => {
                                       if (!result.axesState) return <div className="text-muted text-center py-4 w-100">ไม่มีข้อมูลเวกเตอร์ชีววิทยา</div>;
                                       
                                       const sortedAxes = Object.entries(result.axesState).sort((a: any, b: any) => {
                                          const aNum = parseInt(a[0].replace(/\D/g, ""), 10) || 0;
                                          const bNum = parseInt(b[0].replace(/\D/g, ""), 10) || 0;
                                          return aNum - bNum;
                                       });

                                       return sortedAxes.map(([axisId, data]: any) => {
                                           const isNotAssessed = data.score === null || data.score === undefined;
                                           const isCritical = !isNotAssessed && data.score > 60;
                                           const isModerate = !isNotAssessed && data.score >= 40 && data.score <= 60;
                                          const numericId = parseInt(axisId.replace(/\D/g, ""), 10) || 0;
                                          const thaiName = axisThaiNames[numericId] || axisId;
                                          
                                          return (
                                             <div key={axisId} className="col-md-6 col-lg-4">
                                                <div className="card h-100 border p-3 shadow-sm" style={{ backgroundColor: isNotAssessed ? '#F1F5F9' : isCritical ? '#FEF2F2' : isModerate ? '#FFFBEB' : '#F8FAFC' }}>
                                                   <div className="d-flex justify-content-between mb-2">
                                                      <span className="badge bg-dark">แกนที่ {numericId}</span>
                                                      <span className="fw-bold" style={{ color: isNotAssessed ? '#64748B' : isCritical ? '#DC2626' : isModerate ? '#D97706' : '#10B981', fontSize: '13px' }}>{isNotAssessed ? 'ไม่ได้ประเมิน' : `${data.score}%`}</span>
                                                   </div>
                                                   <div className="fw-bold text-dark lh-sm" style={{ fontSize: '13px', opacity: isNotAssessed ? 0.6 : 1 }}>{thaiName}</div>
                                                    {!isNotAssessed && <div className="progress mt-auto pt-2" style={{ height: '4px', backgroundColor: 'transparent' }}>
                                                      <div className="progress-bar" style={{ width: `${data.score}%`, backgroundColor: isCritical ? '#EF4444' : isModerate ? '#F59E0B' : '#10B981' }}></div>
                                                   </div>}
                                                </div>
                                             </div>
                                          );
                                       });
                                    })()}
                                 </div>
                              </div>
                           )}

                           {/* TAB: Protocol */}
                           {activeTab === 'modules' && (
                              <div className="table-responsive">
                                 <table className="table table-hover align-middle">
                                    <thead className="table-light">
                                       <tr>
                                          <th className="text-center" style={{ width: '60px' }}>ลำดับ</th>
                                          <th>โมดูลทางคลินิก (Therapeutic Module)</th>
                                          <th>เหตุผลความสอดคล้องทางชีววิทยา</th>
                                          <th className="text-end" style={{ width: '120px' }}>สถานะ</th>
                                       </tr>
                                    </thead>
                                    <tbody>
                                       {result.recommendedProtocol && result.recommendedProtocol.map((module: any, idx: number) => (
                                          <tr key={idx}>
                                             <td className="text-center">
                                                <span className="badge rounded-circle p-2" style={{ backgroundColor: idx < 2 ? '#FEE2E2' : '#F1F5F9', color: idx < 2 ? '#DC2626' : '#475569' }}>
                                                   {idx + 1}
                                                </span>
                                             </td>
                                             <td>
                                                <div className="fw-bold text-dark">{module.name}</div>
                                                <div className="text-muted" style={{ fontSize: '12px' }}>รหัส: {module.moduleId}</div>
                                             </td>
                                             <td style={{ fontSize: '13px', color: '#475569' }}>{module.rationale}</td>
                                             <td className="text-end">
                                                <button className="btn btn-outline-primary btn-sm rounded-pill px-3" onClick={() => showToast(`เพิ่ม ${module.name} ในแผนรักษาสำเร็จ`, "success")}>เลือก</button>
                                             </td>
                                          </tr>
                                       ))}
                                    </tbody>
                                 </table>
                              </div>
                           )}
                        </div>
                     </div>
                  </div>
               )}
            </div>
         </div>
      </div>
   );
}
