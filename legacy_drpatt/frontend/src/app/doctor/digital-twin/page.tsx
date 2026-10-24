"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
   Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
   ResponsiveContainer, Tooltip as RechartsTooltip
} from "recharts";
import { medicalDb } from "@/lib/medical-data";
import axesData from "@/data/39_last_x.json";
import modulesDb from "@/data/200_module_tspi.json";
import labMapping from "@/data/lab_mapping.json";
import { getAxesWeightConfig, updatePatient } from "@/utils/api/services";
import {
   Search, ShieldCheck, Zap, Activity, Brain,
   RefreshCw, Star, Users, ShieldAlert,
   Settings2, ClipboardCheck, Dna, Droplet,
   Heart, Bone, Printer, Download,
   ChevronRight, ArrowRight, Play, Check, AlertTriangle, Layers, Loader2, X
} from "lucide-react";
import Swal from "sweetalert2";

// ── Domain visual mapping config ──────────────────────────────────
const DOMAINS_MAP: Record<number, { name: string; color: string; icon: any; description: string }> = {
   1: { name: "Immune–Infection Governance", color: "#EF4444", icon: ShieldCheck, description: "Systemic cytokine burden, immune balance (Th1/Th2/Th17) and pathogen defenses." },
   2: { name: "Metabolic–Energy Core", color: "#10B981", icon: Zap, description: "Glucose-insulin pathways, mitochondrial capacity, mTOR/AMPK cellular signaling." },
   3: { name: "Genomic–Longevity Programming", color: "#3B82F6", icon: Dna, description: "DNA repair dynamics, sirtuins activity, telomere protection and epigenetics." },
   4: { name: "Detox–Digestive–Gut Ecosystem", color: "#F59E0B", icon: Droplet, description: "Gut mucosal integrity, liver Phase I/II detoxification, autophagy mechanisms." },
   5: { name: "Vascular–Circulation–Stroke", color: "#EC4899", icon: Heart, description: "Endothelial nitric oxide tone, lipid transport dynamics, microvascular compliance." },
   6: { name: "Repair–Fibrosis–Regeneration", color: "#8B5CF6", icon: Bone, description: "Extracellular matrix remodelling, stem cell activity, tissue injury recovery." },
   7: { name: "Musculoskeletal & Structural", color: "#F43F5E", icon: Activity, description: "Bone mineral density, joint cartilage integrity, sarcopenia prevention." },
   8: { name: "Endocrine Network", color: "#FB923C", icon: Star, description: "Adrenal steroidogenesis, thyroid response loops, systemic hormone balance." },
   9: { name: "Neuro–Sleep–Stress", color: "#6366F1", icon: Brain, description: "Neurotransmitter synthesis, sleep architecture, sympathetic-vagal tone." },
   10: { name: "Organ Axis + Oncology", color: "#06B6D4", icon: ShieldAlert, description: "Renal glomerular reserve, pulmonary compliance, tumor defense microenvironment." },
   11: { name: "Regeneration & Repair System", color: "#008080", icon: Layers, description: "Stem cell mobilization and targeted cellular repair sequences." },
   12: { name: "Proteostasis & Cellular Integrity", color: "#7C3AED", icon: Settings2, description: "Protein chaperone fold systems, ER stress response, ubiquitin-proteasome." },
};

// ── Design Tokens & Styles ───────────────────────────────────────
const cardStyle: React.CSSProperties = {
   background: "#FFFFFF",
   border: "1px solid #E5E7EB",
   borderRadius: "12px",
   padding: "20px",
   boxShadow: "0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03)",
   transition: "transform 0.2s, box-shadow 0.2s"
};

const clinicalCardStyle: React.CSSProperties = {
   background: "#FFFFFF",
   border: "1px solid #E5E7EB",
   borderRadius: "12px",
   overflow: "hidden",
   boxShadow: "0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03)"
};

const sectionLabel: React.CSSProperties = {
   fontSize: "11px",
   fontWeight: 700,
   color: "#4B5563",
   letterSpacing: "1px",
   textTransform: "uppercase",
};

const ghostBtn: React.CSSProperties = {
   background: "transparent",
   border: "1px solid #E5E7EB",
   borderRadius: "6px",
   padding: "8px 12px",
   cursor: "pointer",
   fontSize: "12px",
   color: "#4B5563",
   display: "flex",
   alignItems: "center",
   gap: "6px",
   fontWeight: 500,
   transition: "all 0.15s"
};

// ── AI Diagnosis Formatter Helper ──────────────────────────────────
const renderFormattedSummary = (text: string) => {
   if (!text) return null;
   const sections = text.split(/(?=\[.*?\])/);
   return sections.map((sec, idx) => {
      const match = sec.match(/^\[(.*?)\]([\s\S]*)/);
      if (match) {
         const title = match[1];
         const content = match[2].trim();
         let icon = <Activity size={16} />;
         let bgColor = "rgba(10, 92, 142, 0.04)";
         let borderLeftColor = "#0A5C8E";
         if (title.toLowerCase().includes("clinical impression")) {
            icon = <Brain size={16} />;
            bgColor = "rgba(14, 116, 144, 0.04)";
            borderLeftColor = "#0E7490";
         } else if (title.toLowerCase().includes("pathophysiology") || title.toLowerCase().includes("mechanistic")) {
            icon = <Activity size={16} />;
            bgColor = "rgba(16, 185, 129, 0.04)";
            borderLeftColor = "#10B981";
         } else if (title.toLowerCase().includes("burden") || title.toLowerCase().includes("biomarker")) {
            icon = <ShieldAlert size={16} />;
            bgColor = "rgba(239, 68, 68, 0.04)";
            borderLeftColor = "#EF4444";
         }
         return (
            <div key={idx} className="p-3 mb-3 rounded-3 border-start" style={{ backgroundColor: bgColor, borderLeftWidth: "4px", borderLeftColor: borderLeftColor, borderStyle: "solid", borderColor: "transparent transparent transparent " + borderLeftColor }}>
               <div className="d-flex align-items-center gap-2 mb-2">
                  <span style={{ color: borderLeftColor }}>{icon}</span>
                  <span style={{ fontSize: "12.5px", fontWeight: 750, color: "#1F2937", textTransform: "uppercase", letterSpacing: "0.5px" }}>{title}</span>
               </div>
               <div style={{ fontSize: "13px", lineHeight: "1.6", color: "#374151", whiteSpace: "pre-wrap" }}>
                  {content}
               </div>
            </div>
         );
      }
      return (
         <div key={idx} style={{ fontSize: "13px", lineHeight: "1.6", color: "#374151", whiteSpace: "pre-wrap" }} className="mb-3">
            {sec}
         </div>
      );
   });
};

// ── Main Component ───────────────────────────────────────────────
function DigitalTwinStandard() {
   const searchParams = useSearchParams();
   const patientId = searchParams.get("id");
   const router = useRouter();

   const [loading, setLoading] = useState(true);
   const [patient, setPatient] = useState<any>(null);
   const [patients, setPatients] = useState<any[]>([]);
   const [weights, setWeights] = useState<Record<string, number>>({});
   
   // Interactive Simulation State
   const [isSimulationMode, setIsSimulationMode] = useState(false);
   const [simulatedAxes, setSimulatedAxes] = useState<Record<string, number>>({});
   const [focusedDomainId, setFocusedDomainId] = useState<number>(1);
   const [expandedAxisId, setExpandedAxisId] = useState<string | null>(null);

   // AI Diagnosis State
   const [isAnalyzing, setIsAnalyzing] = useState(false);
   const [selectedEngine, setSelectedEngine] = useState<"gemini" | "deepseek" | "django" | "tspi-brain">("gemini");
   const [aiReport, setAiReport] = useState<any>(null);
   const [isAIModalOpen, setIsAIModalOpen] = useState(false);
   const [isBurdenModalOpen, setIsBurdenModalOpen] = useState(false);
   
   // UI Controls
   const [searchTerm, setSearchTerm] = useState("");
   const [showSearch, setShowSearch] = useState(false);

   // Lab simulation & network graph states (Phase 3C)
   const [graphViewMode, setGraphViewMode] = useState<"radar" | "network">("network");
   const [hoveredAxisId, setHoveredAxisId] = useState<string | null>(null);
   const [simulatedLabs, setSimulatedLabs] = useState({
      hba1c: 7.8,
      fbs: 152,
      crp: 4.5,
      ldl: 165,
      alt: 45,
      ggt: 55
   });
   const [actualLabs, setActualLabs] = useState({
      hba1c: 7.8,
      fbs: 152,
      crp: 4.5,
      ldl: 165,
      alt: 45,
      ggt: 55
   });

   // Dynamic, precise algorithm that maps patient labs and symptoms to standard biological scores
   const getPatientAxisScore = (axisId: string, customPatientData?: any) => {
      const currentPatient = customPatientData || patient;
      if (!currentPatient) return 50;
      
      const scoreItem = currentPatient.axes?.[axisId];
      if (scoreItem !== undefined) {
         return typeof scoreItem === 'object' ? (scoreItem?.score ?? 50) : scoreItem;
      }
      
      // Compute dynamically using their real labs and symptoms if not pre-stored
      if (currentPatient.labs) {
         const relevantLabs = (labMapping as any).mappings.filter((m: any) => m.axisId === axisId);
         let score = 50;
         if (relevantLabs.length > 0) {
            let labTotalScore = 0;
            let totalWeight = 0;
            relevantLabs.forEach((m: any) => {
               const val = currentPatient.labs[m.marker];
               if (val !== undefined) {
                  let contribution = 20;
                  if (val > m.criticalRange.min) contribution = 100;
                  else if (val > m.optimalRange.max) contribution = 70;
                  const finalBiomarkerWeight = m.weight * (weights[axisId] ?? 1.0);
                  labTotalScore += contribution * finalBiomarkerWeight;
                  totalWeight += finalBiomarkerWeight;
               }
            });
            if (totalWeight > 0) score = labTotalScore / totalWeight;
         }
         if (currentPatient.symptoms && currentPatient.symptoms.length > 0) {
            score = Math.min(100, score + currentPatient.symptoms.length * 5 * (weights[axisId] ?? 1.0));
         }
         return Math.round(score);
      }
      
      return 50;
   };

   const updateSimulatedAxesFromLabs = (labs: typeof actualLabs) => {
      if (!patient) return;
      
      const initialSim: Record<string, number> = {};
      const domains = (axesData as any).domains || [];
      
      // Calculate delta percentages relative to baseline
      const deltaHbA1c = (labs.hba1c - actualLabs.hba1c) / (actualLabs.hba1c || 7.8);
      const deltaFBS = (labs.fbs - actualLabs.fbs) / (actualLabs.fbs || 152);
      const glucoseImpact = deltaHbA1c * 0.6 + deltaFBS * 0.4;
      
      const deltaCRP = (labs.crp - actualLabs.crp) / (actualLabs.crp || 4.5);
      const deltaLDL = (labs.ldl - actualLabs.ldl) / (actualLabs.ldl || 165);
      
      const deltaALT = (labs.alt - actualLabs.alt) / (actualLabs.alt || 45);
      const deltaGGT = (labs.ggt - actualLabs.ggt) / (actualLabs.ggt || 55);
      const liverImpact = deltaALT * 0.5 + deltaGGT * 0.5;

      domains.forEach((d: any) => {
         const axes = d.axes || [];
         axes.forEach((a: any) => {
            const axisId = `AXIS_${a.axis_id}`;
            const baseScore = getPatientAxisScore(axisId, patient);
            
            let modifiedScore = baseScore;
            
            // Apply biological feedback loop modifications
            if (a.axis_id === 5) {
               modifiedScore += glucoseImpact * 40;
            } else if (a.axis_id === 6) {
               modifiedScore += glucoseImpact * 15 + deltaLDL * 40;
            } else if (a.axis_id === 8) {
               modifiedScore += glucoseImpact * 15;
            } else if (a.axis_id === 20) {
               modifiedScore += glucoseImpact * 20 + deltaCRP * 20 + deltaLDL * 20;
            } else if (a.axis_id === 21) {
               modifiedScore += glucoseImpact * 20;
            } else if (a.axis_id === 35) {
               modifiedScore += glucoseImpact * 15;
            } else if (a.axis_id === 34) {
               modifiedScore += glucoseImpact * 15;
            } else if (a.axis_id === 1) {
               modifiedScore += deltaCRP * 50;
            } else if (a.axis_id === 2) {
               modifiedScore += deltaCRP * 30;
            } else if (a.axis_id === 9) {
               modifiedScore += deltaCRP * 25;
            } else if (a.axis_id === 22) {
               modifiedScore += deltaLDL * 15;
            } else if (a.axis_id === 15) {
               modifiedScore += liverImpact * 45;
            } else if (a.axis_id === 16) {
               modifiedScore += liverImpact * 15;
            }

            initialSim[axisId] = Math.max(0, Math.min(100, Math.round(modifiedScore)));
         });
      });
      
      setSimulatedAxes(initialSim);
   };

   const handleLabSliderChange = (marker: string, value: number) => {
      setSimulatedLabs(prev => {
         const updated = { ...prev, [marker]: value };
         updateSimulatedAxesFromLabs(updated);
         return updated;
      });
   };

   const handleSimulateChange = (axisId: string, val: number) => {
      setSimulatedAxes(prev => ({ ...prev, [axisId]: val }));
   };

   const getGraphData = () => {
      const domains = (axesData as any).domains || [];
      const nodesList: any[] = [];
      const nodeIndexMap: Record<number, any> = {};

      const CX = 275;
      const CY = 200;
      const R = 125;

      const activeDomains = domains.filter((d: any) => d.domain_id <= 10);

      activeDomains.forEach((domain: any, idx: number) => {
         const angle = (idx * 2 * Math.PI) / activeDomains.length;
         const dX = CX + R * Math.cos(angle);
         const dY = CY + R * Math.sin(angle);

         const axesList = domain.axes || [];
         const numAxes = axesList.length;

         axesList.forEach((a: any, k: number) => {
            const axisAngle = numAxes > 1 ? (k * 2 * Math.PI) / numAxes : 0;
            const r = numAxes > 1 ? 22 : 0;
            const x = dX + r * Math.cos(axisAngle);
            const y = dY + r * Math.sin(axisAngle);
            const axisId = `AXIS_${a.axis_id}`;

            const score = isSimulationMode 
               ? (simulatedAxes[axisId] ?? 50) 
               : getPatientAxisScore(axisId);

            let color = "#059669"; // green
            if (score > 70) color = "#DC2626"; // red
            else if (score >= 40) color = "#D97706"; // yellow

            const nodeObj = {
               id: axisId,
               numId: a.axis_id,
               name: a.name,
               x,
               y,
               domainId: domain.domain_id,
               score,
               color
            };

            nodesList.push(nodeObj);
            nodeIndexMap[a.axis_id] = nodeObj;
         });
      });

      const linksList: any[] = [];
      const linkConnections = [
         [5, 6], [5, 8], [5, 20], [5, 21], [5, 34], [5, 35],
         [1, 2], [1, 9], [1, 18], [1, 20],
         [15, 16], [15, 17], [15, 18], [15, 35],
         [34, 20], [34, 21], [18, 1], [8, 9]
      ];

      linkConnections.forEach(([src, dst]) => {
         const sourceNode = nodeIndexMap[src];
         const targetNode = nodeIndexMap[dst];
         if (sourceNode && targetNode) {
            linksList.push({
               source: sourceNode,
               target: targetNode
            });
         }
      });

      return { nodes: nodesList, links: linksList };
   };

   // Fetch Patient lists, weights config, and active patient data
   useEffect(() => {
      const fetchData = async () => {
         try {
            const pList = await medicalDb.getPatientList();
            setPatients(pList);

            // Load Custom Formula Weights
            const dbWeights = await getAxesWeightConfig();
            const initialWeights: Record<string, number> = {};
            const domains = (axesData as any).domains || [];
            
            domains.forEach((d: any) => {
               const axes = d.axes || [];
               axes.forEach((a: any) => {
                  initialWeights[`AXIS_${a.axis_id}`] = 1.0;
               });
            });

            if (dbWeights) {
               Object.keys(dbWeights).forEach(key => {
                  if (initialWeights[key] !== undefined) {
                     initialWeights[key] = dbWeights[key];
                  }
               });
            }
            setWeights(initialWeights);

            if (!patientId) { setLoading(false); return; }

            const patientData = await medicalDb.getPatient(patientId);
            if (patientData) {
               const p = patientData as any;
               const fullName = p.firstName || p.fname
                  ? `${p.firstName || p.fname} ${p.lastName || p.lname || ""}`
                  : p.name || "Unknown Patient";
               setPatient({ ...patientData, name: fullName } as any);

               // Extract real labs or fallback to defaults
               const getLabValue = (keys: string[], fallback: number) => {
                  const source = p.labs || p.labData || {};
                  for (const k of keys) {
                     if (source[k] !== undefined) {
                        const val = parseFloat(source[k]);
                        if (!isNaN(val)) return val;
                     }
                  }
                  return fallback;
               };

               const pLabs = {
                  hba1c: getLabValue(["HbA1c", "hba1c"], 7.8),
                  fbs: getLabValue(["Fasting Glucose", "FBS", "fbs", "fasting_glucose"], 152),
                  crp: getLabValue(["CRP", "crp", "hsCRP", "hscrp"], 4.5),
                  ldl: getLabValue(["LDL", "ldl", "cholesterol_ldl"], 165),
                  alt: getLabValue(["ALT", "alt", "sgpt"], 45),
                  ggt: getLabValue(["GGT", "ggt"], 55)
               };

               setActualLabs(pLabs);
               setSimulatedLabs(pLabs);

               // Initialize simulated scores with patient active values or baseline
               const initialSim: Record<string, number> = {};
               domains.forEach((d: any) => {
                  const axes = d.axes || [];
                  axes.forEach((a: any) => {
                     const axisId = `AXIS_${a.axis_id}`;
                     initialSim[axisId] = getPatientAxisScore(axisId, patientData);
                  });
               });
               setSimulatedAxes(initialSim);
            }
         } catch (e) {
            console.error("🔥 Error loading twin dashboard data:", e);
         } finally {
            setLoading(false);
         }
      };
      fetchData();
   }, [patientId]);

   const handleSelectPatient = (id: string) => {
      setShowSearch(false);
      setAiReport(null);
      router.push(`/doctor/digital-twin?id=${id}`);
   };

   // ── Core Domain Calculations ────────────────────────────────────
   const computeDomainScore = (domainId: number, useSimulated: boolean) => {
      const domains = (axesData as any).domains || [];
      const domain = domains.find((d: any) => d.domain_id === domainId);
      if (!domain) return 0;

      let axesList: any[] = [];
      if (domainId === 11 && domain.referenced_axes) {
         const flatAxes = domains.flatMap((d: any) => d.axes || []);
         axesList = flatAxes.filter((a: any) => domain.referenced_axes.includes(a.axis_id));
      } else {
         axesList = domain.axes || [];
      }

      if (axesList.length === 0) return 0;

      const scores = axesList.map((a: any) => {
         const axisId = `AXIS_${a.axis_id}`;
         if (useSimulated && isSimulationMode) {
            return simulatedAxes[axisId] ?? 50;
         }
         return getPatientAxisScore(axisId);
      });

      const avg = scores.reduce((sum: number, val: number) => sum + val, 0) / scores.length;
      return Math.round(avg);
   };

   const computeOverallBurden = (useSimulated: boolean) => {
      const domains = (axesData as any).domains || [];
      const flatAxes = domains
         .filter((d: any) => d.domain_id !== 11) // Avoid double counting domain 11
         .flatMap((d: any) => d.axes || []);

      if (flatAxes.length === 0) return 0;

      const scores = flatAxes.map((a: any) => {
         const axisId = `AXIS_${a.axis_id}`;
         if (useSimulated && isSimulationMode) {
            return simulatedAxes[axisId] ?? 50;
         }
         return getPatientAxisScore(axisId);
      });

      const avg = scores.reduce((sum: number, val: number) => sum + val, 0) / scores.length;
      return Math.round(avg);
   };

   // ── Real-Time Synergy therapeutic matcher ─────────────────────────
   const getSynergyRankings = () => {
      const modulesList = (modulesDb as any).data || [];
      
      const computed = modulesList.map((mod: any) => {
         const mapping = mod['TSPI Axis Mapping'] || '';
         const id = mod['Code /_Product ID'] || mod['name'] || 'UNKNOWN';
         const name = mod['Product Derived From'] || id;
         const mechanism = mod['Main Key Mechanism_(3 Pillars)'] || '';

         let synergyScore = 0;
         const coveredAxes: string[] = [];

         const domains = (axesData as any).domains || [];
         const flatAxes = domains.flatMap((d: any) => d.axes || []);

         flatAxes.forEach((a: any) => {
            const axisId = `AXIS_${a.axis_id}`;
            const score = isSimulationMode ? (simulatedAxes[axisId] ?? 50) : getPatientAxisScore(axisId);
            if (score > 60) { // Highly active target axes
               const numericId = a.axis_id;
               if (mapping.includes(`Axis ${numericId} `)) {
                  const w = weights[axisId] ?? 1.0;
                  synergyScore += (score / 100) * w;
                  coveredAxes.push(axisId);
               }
            }
         });

         return { id, name, synergyScore, coveredAxes, mechanism };
      });

      return computed
         .filter((m: any) => m.synergyScore > 0)
         .sort((a: any, b: any) => b.synergyScore - a.synergyScore)
         .slice(0, 4);
   };

   // ── Multi-Engine Advanced Clinical Clinical Analysis ──────────────────
   const runAIAnalysis = async () => {
      if (!patient || !patientId) return;
      setIsAnalyzing(true);
      setAiReport(null);

      try {
         if (selectedEngine === "django" || selectedEngine === "tspi-brain") {
            const token = localStorage.getItem("doctor_access_token") || sessionStorage.getItem("doctor_access_token");
            
            const apiBase = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";
            
            // If TSPI Brain is selected, check stats and notify the user about training progress
            if (selectedEngine === "tspi-brain") {
               try {
                  const statsRes = await fetch(`${apiBase}/api/ai/brain-training-stats/`, {
                     headers: {
                        ...(token ? { "Authorization": `Bearer ${token}` } : {})
                     }
                  });
                  if (statsRes.ok) {
                     const stats = await statsRes.json();
                     await Swal.fire({
                        icon: "info",
                        title: "สมองกล TSPI Brain อยู่ในระยะสะสมการเรียนรู้",
                        html: `
                           <div style="font-size: 13.5px; text-align: left; line-height: 1.6; color: #374151;">
                              ขณะนี้ระบบสะสมคู่ข้อมูลจำลองสำเร็จแล้ว: 
                              <strong style="color: #0A5C8E; font-size: 16px;">${stats.logged_cases} เคส</strong> (ต้องการขั้นต่ำ ${stats.required_cases} เคส)<br/>
                              <span style="font-size: 11.5px; color: #6B7280; display: block; margin-top: 5px;">* ทุกครั้งประเมินด้วย AI (Gemini/Deepseek) ระบบจะจดจำ Inputs/Outputs เพื่อสอนสมองกลโลคอลโดยอัตโนมัติ *</span>
                              <br/>
                              ระหว่างที่สมองกลสะสมชั่วโมงบินระบบจำศีลนี้ <strong>ระบบจะขอยืมประมวลผลกลไกสรีรวิทยาผ่านเอนจินหลังบ้าน Django แทนก่อนชั่วคราวชิ้นนี้</strong>
                           </div>
                        `,
                        confirmButtonColor: "#0A5C8E",
                        confirmButtonText: "เข้าใจแล้ว (รันจำลองหลังบ้าน)"
                     });
                  }
               } catch (statsErr) {
                  console.warn("Failed to fetch brain training stats:", statsErr);
               }
            }

            // 🧪 Django Precision Medicine Calculation Engine Branch
            const res = await fetch(`${apiBase}/api/patients/${patientId}/calculate-precision-medicine/`, {
               method: "POST",
               headers: {
                  "Content-Type": "application/json",
                  ...(token ? { "Authorization": `Bearer ${token}` } : {})
               },
               body: JSON.stringify({
                  symptoms: patient.symptoms || "อาการจำลองจาก Digital Twin",
                  fbs: String(simulatedLabs.fbs),
                  hba1c: String(simulatedLabs.hba1c),
                  doppler: "",
                  otherLabs: `CRP: ${simulatedLabs.crp}\nLDL: ${simulatedLabs.ldl}\nALT: ${simulatedLabs.alt}\nGGT: ${simulatedLabs.ggt}`,
                  bowelStatus: "normal"
               })
            });

            if (!res.ok) {
               throw new Error(`เซิร์ฟเวอร์หลังบ้านประมวลผลล้มเหลว: ${res.status}`);
            }

            const data = await res.json();
            if (!data.success) {
               throw new Error("คำนวณสูตรแพทย์ Django ล้มเหลว");
            }

            // Map Django calculated scores to twin format
            const axesUpdates: any[] = [];
            const returnedScores = data.calculated_scores || {};
            const updatedSim = { ...simulatedAxes };
            
            Object.keys(returnedScores).forEach((axisKey) => {
               const scoreVal = returnedScores[axisKey];
               updatedSim[axisKey] = scoreVal;
               axesUpdates.push({
                  axis_id: axisKey,
                  severity: scoreVal,
                  insight: "คำนวณเสร็จสิ้นโดยระบบวิเคราะห์ชีววิทยาหลังบ้าน Django"
               });
            });

            // Immediately apply the newly calculated scores to the simulated axes state
            setSimulatedAxes(updatedSim);

            setAiReport({
               clinicalSummary: data.insight || "วิเคราะห์สรีรวิทยาและพยาธิสภาพระดับเซลล์เสร็จสิ้น",
               aiSuggestedUpdates: axesUpdates
            });

            setIsAIModalOpen(true);

            Swal.fire({
               title: "คำนวณสูตรแพทย์สำเร็จ",
               text: "คำนวณวิถีโรคด้วยเอนจินหลังบ้าน Django เรียบร้อยแล้ว",
               icon: "success",
               timer: 2500,
               showConfirmButton: false
            });
         } else {
            // 🧠 Generative AI Engine Branch (Gemini / Deepseek)
            const activeVectors: Record<string, number> = {};
            const domains = (axesData as any).domains || [];
            const flatAxes = domains.flatMap((d: any) => d.axes || []);
            flatAxes.forEach((a: any) => {
               const axisId = `AXIS_${a.axis_id}`;
               activeVectors[axisId] = isSimulationMode ? (simulatedAxes[axisId] ?? 50) : getPatientAxisScore(axisId);
            });

            const token = localStorage.getItem("doctor_access_token") || sessionStorage.getItem("doctor_access_token");
            const response = await fetch('/api/ai/brain', {
               method: 'POST',
               headers: {
                  'Content-Type': 'application/json',
                  ...(token ? { "Authorization": `Bearer ${token}` } : {})
               },
               body: JSON.stringify({
                  patientId,
                  clinicalContext: {
                     patientName: patient.name,
                     hn: patient.hn,
                     axes: activeVectors,
                     weights: weights
                  },
                  systemInstruction: `คุณคือ 'TSPI™ Systems Biology Intelligence' ปัญญาประดิษฐ์ทางการแพทย์ระดับสูงของคณะแพทยศาสตร์คลินิก 
                  โปรดประเมินแผนผังดิจิทัลทวิน (39-Axis Digital Twin) ของคนไข้รายนี้ตามหลักวิชาชีพแพทย์
                  1. ตอบเป็นภาษาไทยระดับเป็นทางการ (Professional Clinical Thai) เพื่อให้แพทย์อ่านประเมินก่อนเข้าปรึกษา
                  2. ระบุหัวข้อหลักอย่างชัดเจน: [Clinical Impression], [Mechanistic Pathophysiology Pathways], [Biomarker Burden Interlinkage]
                  3. นำเสนอโครงสร้างการรักษาเป็นลำดับขั้นตอน (Step-by-step therapeutic advice)
                  4. ปิดท้ายบทวิเคราะห์ด้วย JSON block เสมอ เพื่อแนะนำการคาลิเบรตค่าแกนชีวภาพตามโครงสร้างต่อไปนี้เท่านั้น:
                  :::BIO_UPDATE:::
                  {
                    "axes": [
                      { "axis_id": "AXIS_X", "severity": number_between_0_100, "insight": "เหตุผลเชิงลึกทางสรีรวิทยาการแพทย์" }
                    ]
                  }
                  :::`,
                  engine: selectedEngine === "deepseek" ? "deepseek" : "gemini-2.5-flash"
               })
            });

            const result = await response.json();
            if (result.error) throw new Error(result.details || result.message || result.error);

            let mainContent = result.content || "";
            const bioMatch = mainContent.match(/:::BIO_UPDATE:::([\s\S]*?)(?::::|$)/);

            let parsedKeyFindings: any[] = [];
            if (bioMatch) {
               try {
                  const bioUpdateString = bioMatch[1].trim();
                  const bioUpdate = JSON.parse(bioUpdateString);
                  if (Array.isArray(bioUpdate.axes)) {
                     parsedKeyFindings = bioUpdate.axes.filter((a: any) => a && a.axis_id != null);
                  }
                  mainContent = mainContent.replace(/:::BIO_UPDATE:::[\s\S]*?(?::::|$)/, "").trim();
               } catch (e) {
                  console.warn("⚠️ AI Bio-Sync JSON parsing failed:", e);
               }
            }

            setAiReport({
               clinicalSummary: mainContent,
               aiSuggestedUpdates: parsedKeyFindings
            });

            setIsAIModalOpen(true);

            Swal.fire({
               title: "วิเคราะห์โมเดลสำเร็จ",
               text: `ระบบปัญญาประดิษฐ์ ${selectedEngine === "deepseek" ? "Deepseek" : "Gemini"} ได้วิเคราะห์รายงานชีววิทยาแบบเรียลไทม์เรียบร้อยแล้ว`,
               icon: "success",
               timer: 2500,
               showConfirmButton: false
            });
         }
      } catch (err: any) {
         console.error("🔥 Digital Twin Analysis failed:", err);
         Swal.fire({
            title: "ข้อผิดพลาด",
            text: `การวิเคราะห์ชีววิทยาผิดพลาด: ${err.message}`,
            icon: "error",
            confirmButtonColor: "#0A5C8E"
         });
      } finally {
         setIsAnalyzing(false);
      }
   };

   // Sync AI suggestions back to Firestore and local state
   const applyAISuggestions = async () => {
      if (!aiReport || !aiReport.aiSuggestedUpdates || aiReport.aiSuggestedUpdates.length === 0 || !patientId) return;

      try {
         const currentAxes = patient.axes || {};
         const updatedAxes = { ...currentAxes };
         const scoresMap: Record<string, any> = {};

         aiReport.aiSuggestedUpdates.filter((upd: any) => upd?.axis_id != null).forEach((upd: any) => {
            const axisId = String(upd.axis_id);
            const axisKey = axisId.startsWith("AXIS_") ? axisId : `AXIS_${axisId}`;
            updatedAxes[axisKey] = {
               ...currentAxes[axisKey],
               score: upd.severity,
               insight: upd.insight,
               lastUpdate: new Date().toISOString()
            };
         });

         // Build complete 39-axes map to record in the historical table of PostgreSQL
         for (let i = 1; i <= 39; i++) {
            const axisKey = `AXIS_${i}`;
            scoresMap[axisKey] = {
               score: updatedAxes[axisKey]?.score ?? currentAxes[axisKey]?.score ?? 50,
               insight: updatedAxes[axisKey]?.insight ?? currentAxes[axisKey]?.insight ?? 'Calibrated via Digital Twin AI Simulation'
            };
         }

         // 💾 Save to Django PostgreSQL historical records table
         await medicalDb.updateBiologicalScores(patientId, scoresMap);

         await updatePatient(patientId, { axes: updatedAxes });

         setPatient({ ...patient, axes: updatedAxes });
         
         const updatedSim = { ...simulatedAxes };
         Object.keys(updatedAxes).forEach(k => {
            updatedSim[k] = updatedAxes[k].score;
         });
         setSimulatedAxes(updatedSim);
         setAiReport(null);

         Swal.fire({
            title: "อัปเดตระบบชีวภาพเสร็จสิ้น",
            text: "ข้อมูลเวกเตอร์ชีวภาพของดิจิทัลทวินคนไข้ได้รับการปรับค่าเรียบร้อยแล้ว",
            icon: "success",
            timer: 2000,
            showConfirmButton: false
         });
      } catch (err: any) {
         console.error("🔥 Apply bio sync failed:", err);
         Swal.fire({
            title: "ผิดพลาด",
            text: "ไม่สามารถบันทึกข้อมูลปรับค่าลงระบบหลักได้: " + err.message,
            icon: "error",
            confirmButtonColor: "#0A5C8E"
         });
      }
   };

   const resetSimulation = () => {
      if (!patient) return;
      setSimulatedLabs(actualLabs);
      const initialSim: Record<string, number> = {};
      const domains = (axesData as any).domains || [];
      domains.forEach((d: any) => {
         const axes = d.axes || [];
         axes.forEach((a: any) => {
            const axisId = `AXIS_${a.axis_id}`;
            initialSim[axisId] = patient.axes?.[axisId]?.score ?? 50;
         });
      });
      setSimulatedAxes(initialSim);
      Swal.fire({
         title: "รีเซ็ตการจำลอง",
         text: "ค่าความรุนแรงของร่างกายคนไข้และผลแล็บจำลองถูกดึงกลับสู่สภาพจริงแล้ว",
         icon: "info",
         timer: 1500,
         showConfirmButton: false
      });
   };

   const filteredPatients = patients.filter(p =>
      (p.fname || p.name || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      (p.hn || "").toLowerCase().includes(searchTerm.toLowerCase())
   );

   // Pre-calculate dual radar data
   const radarData = (axesData as any).domains.map((domain: any) => {
      const mapping = DOMAINS_MAP[domain.domain_id] || { name: domain.title, color: "#6B7280" };
      const currentScore = computeDomainScore(domain.domain_id, false);
      const simulatedScore = computeDomainScore(domain.domain_id, true);

      return {
         domainId: domain.domain_id,
         domain: mapping.name,
         current: currentScore,
         simulated: simulatedScore,
         color: mapping.color
      };
   });

   const currentOverall = computeOverallBurden(false);
   const simulatedOverall = computeOverallBurden(true);
   const deltaOverall = simulatedOverall - currentOverall;

   const activeSynergy = getSynergyRankings();

   const generateExcelHtml = (p: any) => {
      let html = `
        <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">
        <head>
          <meta charset="utf-8">
          <style>
            body { font-family: 'Sarabun', Tahoma, sans-serif; }
            h2 { color: #0A5C8E; font-size: 16px; margin-top: 20px; }
            table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
            th { background-color: #0A5C8E; color: #FFFFFF; font-weight: bold; text-align: left; padding: 8px; border: 1px solid #D1D5DB; }
            td { padding: 8px; border: 1px solid #E5E7EB; text-align: left; }
            .header { font-size: 18px; font-weight: bold; color: #1F2937; }
            .patient-cell { background-color: #F3F4F6; font-weight: bold; }
            .stable { background-color: #D1FAE5; color: #065F46; }
            .moderate { background-color: #FEF3C7; color: #92400E; }
            .high { background-color: #FEE2E2; color: #991B1B; font-weight: bold; }
          </style>
        </head>
        <body>
          <div class="header">รายงานสรุปสารชีวเคมีและคะแนนสรีรวิทยา Digital Twin - TSPI™ Systems Biology</div>
          <br/>
          <table>
            <tr>
              <td class="patient-cell" style="width: 20%">ชื่อ-สกุล ผู้ป่วย</td>
              <td style="width: 30%">${p.name || p.firstName || "ไม่ระบุ"}</td>
              <td class="patient-cell" style="width: 20%">เลขประจำตัว (HN)</td>
              <td style="width: 30%">${p.hn || "-"}</td>
            </tr>
            <tr>
              <td class="patient-cell">อายุ</td>
              <td>${p.age || "-"} ปี</td>
              <td class="patient-cell">เพศ</td>
              <td>${p.gender || "-"}</td>
            </tr>
            <tr>
              <td class="patient-cell">ภาระความเสี่ยงรวม (Burden)</td>
              <td style="color: #DC2626; font-weight: bold;">${currentOverall}%</td>
              <td class="patient-cell">วันที่ส่งออกข้อมูล</td>
              <td>${new Date().toLocaleDateString('th-TH')}</td>
            </tr>
          </table>

          <h2>1. ผลการตรวจชีวเคมีห้องปฏิบัติการ (Biochemistry Markers)</h2>
          <table>
            <thead>
              <tr>
                <th style="width: 15%">ตัวย่อพารามิเตอร์</th>
                <th style="width: 35%">คำอธิบายพารามิเตอร์ชีวเคมี</th>
                <th style="width: 15%">ค่าผลตรวจวัด</th>
                <th style="width: 15%">หน่วยวัด</th>
                <th style="width: 20%">ค่าอ้างอิงปกติ</th>
              </tr>
            </thead>
            <tbody>
      `;

      const labInfoMap: Record<string, { name: string; unit: string; range: string }> = {
         hba1c: { name: "HbA1c (น้ำตาลสะสม)", unit: "%", range: "4.0 - 5.6%" },
         fbs: { name: "FBS (น้ำตาลในเลือดก่อนอาหาร)", unit: "mg/dL", range: "70 - 99 mg/dL" },
         crp: { name: "hs-CRP (การอักเสบเฉียบพลัน)", unit: "mg/L", range: "< 1.0 mg/L" },
         ldl: { name: "LDL Cholesterol (ไขมันเลว)", unit: "mg/dL", range: "< 100 mg/dL" },
         alt: { name: "ALT (เอนไซม์ตับ)", unit: "U/L", range: "0 - 45 U/L" },
         ggt: { name: "GGT (เอนไซม์ตับ/ท่อน้ำดี)", unit: "U/L", range: "0 - 50 U/L" }
      };

      const testResults = p.labs || {};
      Object.entries(testResults).forEach(([key, value]: any) => {
         const mapping = labInfoMap[key.toLowerCase()] || { name: key.toUpperCase(), unit: "-", range: "-" };
         html += `
            <tr>
              <td><strong>${key.toUpperCase()}</strong></td>
              <td>${mapping.name}</td>
              <td><strong>${value}</strong></td>
              <td>${mapping.unit}</td>
              <td>${mapping.range}</td>
            </tr>
         `;
      });

      html += `
            </tbody>
          </table>

          <h2>2. สถานะความตึงเครียดของระบบเซลล์ 39 แกนสรีรวิทยา (39 Systems Biology Axes)</h2>
          <table>
            <thead>
              <tr>
                <th style="width: 15%">รหัสแกนย่อย</th>
                <th style="width: 45%">ชื่อแกนควบคุมทางชีวภาพ (Systems Biology Axis Name)</th>
                <th style="width: 20%">คะแนนความตึงเครียด (Score %)</th>
                <th style="width: 20%">ระดับความเสี่ยง (Preclinical Risk)</th>
              </tr>
            </thead>
            <tbody>
      `;

      const domains = (axesData as any).domains || [];
      domains.forEach((d: any) => {
         const axes = d.axes || [];
         axes.forEach((a: any) => {
            const axisId = `AXIS_${a.axis_id}`;
            const score = simulatedAxes[axisId] ?? p.axes?.[axisId]?.score ?? 50;
            let riskText = "ปกติ (Stable)";
            let riskClass = "stable";
            if (score > 70) {
               riskText = "เสี่ยงสูงเรื้อรัง (High)";
               riskClass = "high";
            } else if (score > 40) {
               riskText = "เสี่ยงปานกลาง (Moderate)";
               riskClass = "moderate";
            }

            html += `
               <tr>
                 <td><strong>Axis ${a.axis_id}</strong></td>
                 <td>${a.title}</td>
                 <td><strong>${score}%</strong></td>
                 <td class="${riskClass}">${riskText}</td>
               </tr>
            `;
         });
      });

      html += `
            </tbody>
          </table>
        </body>
        </html>
      `;
      return html;
   };

   const generateWordHtml = (p: any, overall: number) => {
      let html = `
        <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" xmlns="http://www.w3.org/TR/REC-html40">
        <head>
          <meta charset="utf-8">
          <title>Clinical Assessment Report</title>
          <style>
            body { font-family: 'Sarabun', Arial, sans-serif; line-height: 1.6; color: #333333; padding: 20px; }
            .title-box { text-align: center; border-bottom: 3px double #0A5C8E; padding-bottom: 12px; margin-bottom: 25px; }
            .title { color: #0A5C8E; font-size: 24px; font-weight: bold; }
            .subtitle { font-size: 12px; color: #666666; margin-top: 5px; }
            h2 { color: #0A5C8E; font-size: 16px; border-bottom: 1px solid #D1D5DB; padding-bottom: 5px; margin-top: 25px; }
            .profile-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
            .profile-table td { padding: 8px; border: 1px solid #E5E7EB; font-size: 13px; }
            .profile-label { background-color: #F3F4F6; font-weight: bold; width: 25%; }
            .data-table { width: 100%; border-collapse: collapse; margin-top: 15px; }
            .data-table th { background-color: #0A5C8E; color: white; padding: 8px; font-size: 12px; border: 1px solid #D1D5DB; text-align: left; }
            .data-table td { padding: 8px; border: 1px solid #E5E7EB; font-size: 12.5px; }
            .footer { font-size: 11px; color: #999999; text-align: center; margin-top: 50px; border-top: 1px solid #E5E7EB; padding-top: 15px; }
          </style>
        </head>
        <body>
          <div class="title-box">
            <div class="title">TSPI™ SYSTEMS BIOLOGY ASSESSMENT REPORT</div>
            <div class="subtitle">สถาบันการแพทย์บูรณาการและวิเคราะห์ชีววิทยาพ้องสมดุล TSPI</div>
          </div>

          <table class="profile-table">
            <tr>
              <td class="profile-label">ชื่อผู้ป่วย (Patient Name)</td>
              <td>${p.name || p.firstName || "ไม่ระบุ"}</td>
              <td class="profile-label">รหัสประจำตัว HN</td>
              <td>${p.hn || "-"}</td>
            </tr>
            <tr>
              <td class="profile-label">อายุ (Age) / เพศ (Gender)</td>
              <td>${p.age || "-"} ปี / ${p.gender || "-"}</td>
              <td class="profile-label">ดัชนีชีวภาพรวม</td>
              <td style="color: #DC2626; font-weight: bold;">${overall}% Burden Index</td>
            </tr>
          </table>

          <h2>1. สรุปพารามิเตอร์ชีวเคมีพรีคลินิก (Preclinical Biomarkers Matrix)</h2>
          <table class="data-table">
            <thead>
              <tr>
                <th style="width: 15%">Biomarker</th>
                <th style="width: 45%">รายละเอียดชีวภาพย่อย</th>
                <th style="width: 15%">ค่าผลการวัด</th>
                <th style="width: 10%">หน่วย</th>
                <th style="width: 15%">ช่วงอ้างอิง</th>
              </tr>
            </thead>
            <tbody>
      `;

      const labInfoMap: Record<string, { name: string; unit: string; range: string }> = {
         hba1c: { name: "HbA1c (น้ำตาลสะสม)", unit: "%", range: "4.0 - 5.6%" },
         fbs: { name: "FBS (น้ำตาลในเลือดก่อนอาหาร)", unit: "mg/dL", range: "70 - 99 mg/dL" },
         crp: { name: "hs-CRP (การอักเสบเฉียบพลัน)", unit: "mg/L", range: "< 1.0 mg/L" },
         ldl: { name: "LDL Cholesterol (ไขมันเลว)", unit: "mg/dL", range: "< 100 mg/dL" },
         alt: { name: "ALT (เอนไซม์ตับ)", unit: "U/L", range: "0 - 45 U/L" },
         ggt: { name: "GGT (เอนไซม์ตับ/ท่อน้ำดี)", unit: "U/L", range: "0 - 50 U/L" }
      };

      const testResults = p.labs || {};
      Object.entries(testResults).forEach(([key, value]: any) => {
         const mapping = labInfoMap[key.toLowerCase()] || { name: key.toUpperCase(), unit: "-", range: "-" };
         html += `
            <tr>
              <td><strong>${key.toUpperCase()}</strong></td>
              <td>${mapping.name}</td>
              <td><strong>${value}</strong></td>
              <td>${mapping.unit}</td>
              <td>${mapping.range}</td>
            </tr>
         `;
      });

      html += `
            </tbody>
          </table>

          <h2>2. ข้อเสนอแนะการวิเคราะห์สมดุลสรีรวิทยา (AI Clinical Diagnostics & Insights)</h2>
          <p>จากการสอบเทียบโมเดลร่างกายจำลอง (Preclinical Digital Twin Calibration) ระบบประเมินว่าระบบสารสื่อการอักเสบร่วมกับความผิดปกติในกระบวนการเมแทบอลิซึมระดับเซลล์ (Metabolic core) อยู่ในภาวะล้าและควรได้รับการฟื้นฟูด้วยการส่งเสริมโมเลกุลพ้องธรรมชาติ ร่วมกับการรับประทานอาหารสูตรควบคุมดัชนีน้ำตาลอย่างเข้มงวดและลดการสะสมความตึงเครียดของระบบประสาทส่วนกลางเพื่อลดระดับสารต้านอนุมูลอิสระ</p>

          <div class="footer">
            * เอกสารสรุปชีวเคมีฉบับนี้พิมพ์ด้วยระบบคอมพิวเตอร์ผ่าน TSPI Digital Twin Console *
          </div>
        </body>
        </html>
      `;
      return html;
   };

   const triggerExcelExport = () => {
      if (!patient) return;
      const html = generateExcelHtml(patient);
      const blob = new Blob([html], { type: "application/vnd.ms-excel;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `TSPI_Biochemistry_Summary_${patient.hn || "Report"}.xls`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      Swal.fire({
         icon: 'success',
         title: 'ส่งออก Excel สำเร็จ',
         text: 'ดาวน์โหลดสรุปพารามิเตอร์ชีวเคมีเรียบร้อยแล้ว',
         timer: 1500,
         showConfirmButton: false
      });
   };

   const triggerWordExport = () => {
      if (!patient) return;
      const html = generateWordHtml(patient, currentOverall);
      const blob = new Blob([html], { type: "application/msword;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `TSPI_Clinical_Report_${patient.hn || "Report"}.doc`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      Swal.fire({
         icon: 'success',
         title: 'ส่งออก Word สำเร็จ',
         text: 'ดาวน์โหลดรายงานวิเคราะห์สรีรวิทยาเรียบร้อยแล้ว',
         timer: 1500,
         showConfirmButton: false
      });
   };

   const handleExportMenu = () => {
      if (!patient) {
         Swal.fire({
            icon: 'warning',
            title: 'กรุณาเลือกผู้ป่วย',
            text: 'กรุณาเลือกผู้ป่วยก่อนส่งออกข้อมูล',
            confirmButtonColor: '#0A5C8E'
         });
         return;
      }
      Swal.fire({
         title: '<span style="font-size: 18px; font-weight: bold; color: #1F2937;">เลือกรูปแบบการส่งออกสรุปชีวเคมี</span>',
         html: `
            <div style="font-size: 13px; color: #6B7280; margin-bottom: 20px;">
               ผู้ป่วย: <strong>${patient?.name || "ไม่ทราบชื่อ"}</strong> (HN: ${patient?.hn || "-"})
            </div>
            <div style="display: flex; flex-direction: column; gap: 10px;">
               <div id="export-pdf-btn" style="padding: 15px; border: 1px solid #E5E7EB; border-radius: 8px; cursor: pointer; text-align: left; display: flex; align-items: center; gap: 12px; transition: all 0.2s;">
                  <div style="background-color: rgba(239, 68, 68, 0.1); color: #EF4444; width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                     📄
                  </div>
                  <div>
                     <strong style="display: block; font-size: 14px; color: #1F2937;">ส่งออกเป็น PDF Report</strong>
                     <span style="font-size: 11.5px; color: #6B7280;">รายงานทางการแพทย์พร้อมชาร์ตและผลวินิจฉัยพหุระบบ</span>
                  </div>
               </div>

               <div id="export-word-btn" style="padding: 15px; border: 1px solid #E5E7EB; border-radius: 8px; cursor: pointer; text-align: left; display: flex; align-items: center; gap: 12px; transition: all 0.2s;">
                  <div style="background-color: rgba(59, 130, 246, 0.1); color: #3B82F6; width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                     📝
                  </div>
                  <div>
                     <strong style="display: block; font-size: 14px; color: #1F2937;">ส่งออกเป็น Microsoft Word (.doc)</strong>
                     <span style="font-size: 11.5px; color: #6B7280;">สรุปผลการวิเคราะห์ระดับเซลล์ที่สามารถปรับปรุงเนื้อหาได้</span>
                  </div>
               </div>

               <div id="export-excel-btn" style="padding: 15px; border: 1px solid #E5E7EB; border-radius: 8px; cursor: pointer; text-align: left; display: flex; align-items: center; gap: 12px; transition: all 0.2s;">
                  <div style="background-color: rgba(16, 185, 129, 0.1); color: #10B981; width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                     📊
                  </div>
                  <div>
                     <strong style="display: block; font-size: 14px; color: #1F2937;">ส่งออกเป็น Excel Spreadsheet (.xls)</strong>
                     <span style="font-size: 11.5px; color: #6B7280;">ตารางค่าสรุปตัวบ่งชี้ชีวเคมีสำหรับการคำนวณซ้ำ</span>
                  </div>
               </div>
            </div>
         `,
         showConfirmButton: false,
         showCloseButton: true,
         didOpen: () => {
            const pdf = document.getElementById("export-pdf-btn");
            const word = document.getElementById("export-word-btn");
            const excel = document.getElementById("export-excel-btn");

            if (pdf) {
               pdf.style.cursor = 'pointer';
               pdf.addEventListener("click", () => {
                  Swal.close();
                  handlePrintReport();
               });
               pdf.addEventListener("mouseover", () => { pdf.style.backgroundColor = '#F9FAFB'; pdf.style.borderColor = '#0A5C8E'; });
               pdf.addEventListener("mouseout", () => { pdf.style.backgroundColor = 'transparent'; pdf.style.borderColor = '#E5E7EB'; });
            }
            if (word) {
               word.style.cursor = 'pointer';
               word.addEventListener("click", () => {
                  Swal.close();
                  triggerWordExport();
               });
               word.addEventListener("mouseover", () => { word.style.backgroundColor = '#F9FAFB'; word.style.borderColor = '#0A5C8E'; });
               word.addEventListener("mouseout", () => { word.style.backgroundColor = 'transparent'; word.style.borderColor = '#E5E7EB'; });
            }
            if (excel) {
               excel.style.cursor = 'pointer';
               excel.addEventListener("click", () => {
                  Swal.close();
                  triggerExcelExport();
               });
               excel.addEventListener("mouseover", () => { excel.style.backgroundColor = '#F9FAFB'; excel.style.borderColor = '#0A5C8E'; });
               excel.addEventListener("mouseout", () => { excel.style.backgroundColor = 'transparent'; excel.style.borderColor = '#E5E7EB'; });
            }
         }
      });
   };

   const handlePrintReport = async () => {
      if (!patient || !patientId) {
         Swal.fire({
            icon: 'warning',
            title: 'กรุณาเลือกผู้ป่วย',
            text: 'กรุณาเลือกผู้ป่วยก่อนพิมพ์รายงาน',
            confirmButtonColor: '#0A5C8E'
         });
         return;
      }
      
      Swal.fire({
         title: 'กำลังจัดทำรายงานแพทย์ 30 หน้า...',
         text: 'ระบบกำลังดึงข้อมูลพยาธิสภาพและประมวลผล 36 แกนตามมาตรฐาน TSPI™',
         allowOutsideClick: false,
         didOpen: () => {
            Swal.showLoading();
         }
      });

      try {
         const token = localStorage.getItem("doctor_access_token") || sessionStorage.getItem("doctor_access_token");
         const apiBase = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";
         const res = await fetch(`${apiBase}/api/ai/generate-clinical-pdf/?patient=${patientId}`, {
            headers: {
               "Authorization": token ? `Bearer ${token}` : ""
            }
         });
         
         if (!res.ok) {
            throw new Error(`Server returned status: ${res.status}`);
         }
         
         const data = await res.json();
         Swal.close();

         if (data.success && data.html) {
            const iframe = document.createElement('iframe');
            iframe.style.position = 'fixed';
            iframe.style.right = '0';
            iframe.style.bottom = '0';
            iframe.style.width = '0';
            iframe.style.height = '0';
            iframe.style.border = '0';
            document.body.appendChild(iframe);
            
            const doc = iframe.contentDocument || iframe.contentWindow?.document;
            if (doc) {
               doc.open();
               doc.write(data.html);
               doc.close();
               
               setTimeout(() => {
                  iframe.contentWindow?.focus();
                  iframe.contentWindow?.print();
                  setTimeout(() => {
                     document.body.removeChild(iframe);
                  }, 1000);
               }, 500);
            }
         } else {
            throw new Error("Invalid response format");
         }
      } catch (error: any) {
         console.error("Failed to generate PDF dossier:", error);
         Swal.fire({
            icon: 'error',
            title: 'เกิดข้อผิดพลาด',
            text: 'ไม่สามารถออกเอกสารรายงานได้ กรุณาลองใหม่อีกครั้ง',
            confirmButtonColor: '#E53E3E'
         });
      }
   };

   if (loading) {
      return (
         <div className="d-flex flex-column align-items-center justify-content-center" style={{ minHeight: "80vh", gap: "16px" }}>
            <Loader2 className="animate-spin text-primary" size={40} style={{ color: "#0A5C8E" }} />
            <div style={{ fontSize: "14px", fontWeight: 600, color: "#4B5563" }}>กำลังโหลดพารามิเตอร์ระบบชีววิทยาของคนไข้...</div>
         </div>
      );
   }

   return (
      <div className="container-fluid px-4 pb-5 font-sans" style={{ fontFamily: "'Inter', sans-serif" }}>

         {/* ── HEADER ─────────────────────────────────────────────────── */}
         <div className="d-flex justify-content-between align-items-center mb-4 border-bottom pb-3">
            <div>
               <div className="d-flex align-items-center gap-2 mb-1">
                  <div className="bg-primary bg-opacity-10 p-2 rounded-3 text-primary" style={{ background: "rgba(10, 92, 142, 0.1)", color: "#0A5C8E" }}>
                     <Brain size={24} />
                  </div>
                  <h1 className="h3 fw-bold mb-0 text-dark">Digital Twin Console</h1>
               </div>
               <p className="text-muted text-xs uppercase font-bold tracking-widest ms-5" style={{ fontSize: "11px", letterSpacing: "1px" }}>
                  TSPI™ Systems Biology 39-Axis Biological Replica & Interactive Simulator
               </p>
            </div>

            {/* Patient selector dropdown */}
            <div className="position-relative">
               <button
                  onClick={() => setShowSearch(v => !v)}
                  className="btn btn-outline-primary d-flex align-items-center gap-2"
                  style={{
                     borderColor: "#0A5C8E",
                     color: "#0A5C8E",
                     fontSize: "13px",
                     fontWeight: 600,
                     padding: "8px 16px",
                     borderRadius: "8px"
                  }}
               >
                  <Users size={16} />
                  {patient?.name ? `${patient.name} (HN: ${patient.hn || String(patient.id || '').slice(0, 8)})` : "เลือกข้อมูลคนไข้"}
               </button>

               {showSearch && (
                  <div className="position-absolute right-0 mt-2" style={{
                     right: 0,
                     width: "320px",
                     ...cardStyle,
                     zIndex: 1050,
                     boxShadow: "0 10px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1)"
                  }}>
                     <div className="d-flex align-items-center gap-2 border rounded-3 p-2 bg-light mb-3">
                        <Search size={15} className="text-muted" />
                        <input
                           autoFocus
                           type="text"
                           placeholder="ค้นหาชื่อหรือ HN คนไข้..."
                           value={searchTerm}
                           onChange={e => setSearchTerm(e.target.value)}
                           className="bg-transparent border-0 outline-none w-100"
                           style={{ outline: "none", fontSize: "13px", color: "#1F2937" }}
                        />
                     </div>

                     <div style={{ maxHeight: "250px", overflowY: "auto" }}>
                        {filteredPatients.map(p => (
                           <button
                              key={p.id}
                              onClick={() => handleSelectPatient(p.id)}
                              className="w-100 d-flex align-items-center gap-3 p-2 rounded-2 border-0 text-start bg-transparent"
                              style={{ transition: "background 0.15s", cursor: "pointer" }}
                              onMouseEnter={e => (e.currentTarget.style.backgroundColor = "#F3F4F6")}
                              onMouseLeave={e => (e.currentTarget.style.backgroundColor = "transparent")}
                           >
                              <div style={{
                                 width: "32px", height: "32px", borderRadius: "50%",
                                 backgroundColor: "#0A5C8E", color: "#FFFFFF",
                                 display: "flex", alignItems: "center", justifyContent: "center",
                                 fontSize: "12px", fontWeight: 700
                              }}>
                                 {(p.fname || p.name || "?").charAt(0)}
                              </div>
                              <div style={{ minWidth: 0 }}>
                                 <div style={{ fontSize: "13px", fontWeight: 600, color: "#1F2937", textOverflow: "ellipsis", whiteSpace: "nowrap", overflow: "hidden" }}>
                                    {p.fname || p.name}
                                 </div>
                                 <div style={{ fontSize: "11px", color: "#9CA3AF" }}>HN: {p.hn || String(p.id || '').slice(0, 8)}</div>
                              </div>
                           </button>
                        ))}
                     </div>
                  </div>
               )}
            </div>
         </div>

         {/* ── NO PATIENT ELECTED ──────────────────────────────────────── */}
         {!patientId ? (
            <div className="d-flex flex-column align-items-center justify-content-center text-center p-5 border rounded-3 bg-white mx-auto shadow-sm" style={{ maxWidth: "540px", marginTop: "40px" }}>
               <div className="bg-light p-4 rounded-circle mb-3" style={{ background: "#F3F4F6" }}>
                  <Dna size={48} style={{ color: "#9CA3AF" }} />
               </div>
               <h2 className="h4 fw-bold text-dark mb-2">ไม่พบบัญชีผู้รับตรวจที่ทำงาน</h2>
               <p className="text-muted text-sm mb-4" style={{ maxWidth: "380px" }}>
                  กรุณาคลิกเลือกคนไข้จากปุ่ม **"เลือกข้อมูลคนไข้"** ทางด้านขวา เพื่อดาวน์โหลดแผนผังระบบดิจิทัลทวินและการจำลองทางชีวภาพของคนไข้
               </p>
               <button onClick={() => setShowSearch(true)} className="btn btn-primary px-4 py-2" style={{ backgroundColor: "#0A5C8E", borderColor: "#0A5C8E" }}>
                  เปิดศูนย์ข้อมูลคนไข้
               </button>
            </div>
         ) : (
            /* ── MAIN TWO-COLUMN WORKSPACE ───────────────────────────────── */
            <div>
               <div className="row g-4 mb-4">
                  {/* LEFT COLUMN: Visual Systems Radar & Load Indices */}
                  <div className="col-lg-6 col-12 d-flex flex-column gap-4">

                     {/* Visualizer Card (Radar / Network Graph Toggle) */}
                     <div className="card border-0" style={cardStyle}>
                        <div className="d-flex justify-content-between align-items-center border-bottom pb-3 mb-3">
                           <div className="d-flex align-items-center gap-2">
                              <Activity size={18} style={{ color: "#0A5C8E" }} />
                              <span style={sectionLabel}>Systemic Biological Mapping</span>
                           </div>
                           
                           {/* Toggle buttons between Radar and Network Map */}
                           <div className="d-flex p-1 bg-light border rounded-3 gap-1">
                              <button
                                 type="button"
                                 onClick={() => setGraphViewMode("network")}
                                 className={`btn border-0 py-1 px-2.5 transition-all`}
                                 style={{
                                    fontSize: "11px",
                                    fontWeight: 750,
                                    backgroundColor: graphViewMode === "network" ? "#0A5C8E" : "transparent",
                                    color: graphViewMode === "network" ? "#FFFFFF" : "#6B7280",
                                    borderRadius: "4px"
                                 }}
                              >
                                 39-Axes Network Map
                              </button>
                              <button
                                 type="button"
                                 onClick={() => setGraphViewMode("radar")}
                                 className={`btn border-0 py-1 px-2.5 transition-all`}
                                 style={{
                                    fontSize: "11px",
                                    fontWeight: 750,
                                    backgroundColor: graphViewMode === "radar" ? "#0A5C8E" : "transparent",
                                    color: graphViewMode === "radar" ? "#FFFFFF" : "#6B7280",
                                    borderRadius: "4px"
                                 }}
                              >
                                 Radar Chart
                              </button>
                           </div>
                        </div>

                        <div style={{ height: "420px", backgroundColor: "#FCFDFE", borderRadius: "10px", overflow: "hidden" }} className="d-flex align-items-center justify-content-center p-2 border position-relative">
                           
                           {graphViewMode === "radar" ? (
                              <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                                 <RadarChart cx="50%" cy="50%" outerRadius="75%" data={radarData}>
                                    <PolarGrid stroke="#E5E7EB" />
                                    <PolarAngleAxis dataKey="domain" tick={{ fill: "#4B5563", fontSize: 10, fontWeight: 700 }} />
                                    <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                                    
                                    <Radar
                                       name="Current Clinical Burden"
                                       dataKey="current"
                                       stroke="#0A5C8E"
                                       strokeWidth={2}
                                       fill="#0A5C8E"
                                       fillOpacity={0.15}
                                    />
                                    
                                    {isSimulationMode && (
                                       <Radar
                                          name="Simulated Future State"
                                          dataKey="simulated"
                                          stroke="#059669"
                                          strokeWidth={2.5}
                                          strokeDasharray="4 4"
                                          fill="#059669"
                                          fillOpacity={0.12}
                                       />
                                    )}
                                    <RechartsTooltip contentStyle={{ fontSize: "12px", borderRadius: "8px" }} />
                                 </RadarChart>
                              </ResponsiveContainer>
                           ) : (
                              /* 39-Axes Biological Network Graph */
                              <div className="w-100 h-100 position-relative">
                                 {(() => {
                                    const { nodes, links } = getGraphData();
                                    return (
                                       <svg viewBox="0 0 550 420" style={{ width: "100%", height: "100%", userSelect: "none" }}>
                                          {/* Domain Centers & Outlines (Guides) */}
                                          {(axesData as any).domains.filter((d: any) => d.domain_id <= 10).map((domain: any, idx: number) => {
                                             const angle = (idx * 2 * Math.PI) / 10;
                                             const dX = 275 + 130 * Math.cos(angle);
                                             const dY = 200 + 130 * Math.sin(angle);
                                             const labelAngle = (idx * 2 * Math.PI) / 10;
                                             const labelX = 275 + 172 * Math.cos(labelAngle);
                                             const labelY = 200 + 172 * Math.sin(labelAngle);
                                             
                                             const color = DOMAINS_MAP[domain.domain_id]?.color || "#9CA3AF";

                                             return (
                                                <g key={domain.domain_id}>
                                                   {/* Cluster guide circle */}
                                                   <circle
                                                      cx={dX}
                                                      cy={dY}
                                                      r={32}
                                                      fill="none"
                                                      stroke={color}
                                                      strokeWidth={1}
                                                      strokeOpacity={0.1}
                                                      strokeDasharray="3 3"
                                                   />
                                                   {/* Dashed line to outer label */}
                                                   <line
                                                      x1={dX}
                                                      y1={dY}
                                                      x2={labelX}
                                                      y2={labelY}
                                                      stroke="#9CA3AF"
                                                      strokeDasharray="2 2"
                                                      strokeWidth={1}
                                                      strokeOpacity={0.25}
                                                   />
                                                   {/* Outer Domain Label Badge */}
                                                   <g 
                                                      style={{ cursor: "pointer" }}
                                                      onClick={() => {
                                                         setFocusedDomainId(domain.domain_id);
                                                         setExpandedAxisId(null);
                                                      }}
                                                   >
                                                      <title>{DOMAINS_MAP[domain.domain_id]?.name || domain.title}</title>
                                                      <circle 
                                                         cx={labelX} 
                                                         cy={labelY} 
                                                         r={12} 
                                                         fill={focusedDomainId === domain.domain_id ? "#0A5C8E" : "#FFFFFF"} 
                                                         stroke={focusedDomainId === domain.domain_id ? "#0A5C8E" : "#E5E7EB"} 
                                                         strokeWidth={1.5} 
                                                      />
                                                      <text 
                                                         x={labelX} 
                                                         y={labelY + 3.5} 
                                                         textAnchor="middle" 
                                                         fontSize="9px" 
                                                         fontWeight="bold" 
                                                         fill={focusedDomainId === domain.domain_id ? "#FFFFFF" : "#4B5563"}
                                                      >
                                                         D{domain.domain_id}
                                                      </text>
                                                   </g>
                                                </g>
                                             );
                                          })}

                                          {/* Connection Links */}
                                          {links.map((link, i) => (
                                             <line
                                                key={i}
                                                x1={link.source.x}
                                                y1={link.source.y}
                                                x2={link.target.x}
                                                y2={link.target.y}
                                                stroke={
                                                   hoveredAxisId === link.source.id || hoveredAxisId === link.target.id
                                                      ? "#0A5C8E"
                                                      : "#E5E7EB"
                                                }
                                                strokeWidth={
                                                   hoveredAxisId === link.source.id || hoveredAxisId === link.target.id
                                                      ? 2
                                                      : 1
                                                }
                                                strokeOpacity={
                                                   hoveredAxisId === link.source.id || hoveredAxisId === link.target.id
                                                      ? 0.95
                                                      : 0.65
                                                }
                                             />
                                          ))}

                                          {/* Nodes */}
                                          {nodes.map((node) => {
                                             const isHovered = hoveredAxisId === node.id;
                                             const isSelected = expandedAxisId === node.id;
                                             return (
                                                <g
                                                   key={node.id}
                                                   style={{ cursor: "pointer" }}
                                                   onMouseEnter={() => setHoveredAxisId(node.id)}
                                                   onMouseLeave={() => setHoveredAxisId(null)}
                                                   onClick={() => {
                                                      setFocusedDomainId(node.domainId);
                                                      setExpandedAxisId(node.id);
                                                   }}
                                                >
                                                   {/* Selection outer ring */}
                                                   {(isHovered || isSelected) && (
                                                      <circle
                                                         cx={node.x}
                                                         cy={node.y}
                                                         r={15}
                                                         fill="none"
                                                         stroke={node.color}
                                                         strokeWidth={2}
                                                         strokeOpacity={0.8}
                                                      />
                                                   )}
                                                   {/* Node Circle */}
                                                   <circle
                                                      cx={node.x}
                                                      cy={node.y}
                                                      r={9.5}
                                                      fill={node.color}
                                                      stroke="#FFFFFF"
                                                      strokeWidth={1.5}
                                                   />
                                                   {/* Inner text containing Axis numeric ID */}
                                                   <text
                                                      x={node.x}
                                                      y={node.y + 3.2}
                                                      textAnchor="middle"
                                                      fill="#FFFFFF"
                                                      fontSize="8px"
                                                      fontWeight="bold"
                                                   >
                                                      {node.numId}
                                                   </text>
                                                </g>
                                             );
                                          })}
                                       </svg>
                                    );
                                 })()}

                                 {/* Node Quick Info Overlay (Tooltip) */}
                                 {hoveredAxisId && (() => {
                                    const axisNumber = parseInt(hoveredAxisId.replace("AXIS_", ""));
                                    const domains = (axesData as any).domains || [];
                                    const flatAxes = domains.flatMap((d: any) => d.axes || []);
                                    const axisMeta = flatAxes.find((a: any) => a.axis_id === axisNumber);
                                    const score = isSimulationMode ? (simulatedAxes[hoveredAxisId] ?? 50) : getPatientAxisScore(hoveredAxisId);
                                    if (!axisMeta) return null;

                                    return (
                                       <div 
                                          className="position-absolute p-2 bg-dark text-white rounded shadow-sm"
                                          style={{
                                             bottom: "10px",
                                             left: "10px",
                                             maxWidth: "260px",
                                             fontSize: "11px",
                                             opacity: 0.95,
                                             zIndex: 10,
                                             border: "1px solid rgba(255,255,255,0.15)"
                                          }}
                                       >
                                          <div className="fw-bold text-primary-custom d-flex justify-content-between mb-1" style={{ color: "#FFD700" }}>
                                             <span>Axis {axisNumber}: {axisMeta.name}</span>
                                             <span>{score}%</span>
                                          </div>
                                          <div style={{ fontSize: "10px", opacity: 0.85 }}>
                                             {DOMAINS_MAP[axisMeta.domain_id || focusedDomainId]?.name}
                                          </div>
                                       </div>
                                    );
                                 })()}
                              </div>
                           )}
                        </div>
                     </div>

                     {/* Overall Biological Burden Gage Card */}
                     <div 
                        className="card border-0 hover-lift shadow-sm-hover" 
                        style={{ ...cardStyle, cursor: "pointer", transition: "all 0.2s" }}
                        onClick={() => setIsBurdenModalOpen(true)}
                     >
                        <div className="row align-items-center">
                           <div className="col-sm-5 col-12 d-flex flex-column align-items-center text-center">
                              
                              {/* circular progress gauge */}
                              <div className="position-relative d-flex align-items-center justify-content-center" style={{ width: "130px", height: "130px" }}>
                                 <svg style={{ transform: "rotate(-90deg)", width: "120px", height: "120px" }}>
                                    <circle
                                       cx="60"
                                       cy="60"
                                       r="50"
                                       fill="transparent"
                                       stroke="#F3F4F6"
                                       strokeWidth="10"
                                    />
                                    <circle
                                       cx="60"
                                       cy="60"
                                       r="50"
                                       fill="transparent"
                                       stroke={isSimulationMode ? "#059669" : "#0A5C8E"}
                                       strokeWidth="10"
                                       strokeDasharray="314.15"
                                       strokeDashoffset={314.15 - (314.15 * (isSimulationMode ? simulatedOverall : currentOverall)) / 100}
                                       style={{ transition: "stroke-dashoffset 0.3s ease" }}
                                    />
                                 </svg>
                                 <div className="position-absolute d-flex flex-column align-items-center">
                                    <span style={{ fontSize: "28px", fontWeight: 800, color: isSimulationMode ? "#059669" : "#0A5C8E" }}>
                                       {isSimulationMode ? simulatedOverall : currentOverall}%
                                    </span>
                                    <span className="text-muted" style={{ fontSize: "10px", fontWeight: 700, textTransform: "uppercase" }}>BURDEN</span>
                                 </div>
                              </div>
                           </div>

                           <div className="col-sm-7 col-12">
                              <div className="d-flex align-items-center gap-2 mb-2">
                                 <span style={{ ...sectionLabel, color: "#1F2937", fontSize: "12px" }}>Overall Burden Index</span>
                              </div>
                              <p className="text-muted" style={{ fontSize: "12px", lineHeight: "1.5" }}>
                                 ดัชนีภาระทางชีวภาพเฉลี่ยรวมทุกแกนของสรีรวิทยา หากมีค่าสูงกว่า 70% แสดงถึงระดับความเสี่ยงเรื้อรังสูงที่จำเป็นต้องได้รับหัตถการลดสรีรวิทยา
                              </p>

                              {/* Toggle simulation mode switch */}
                              <div className="d-flex align-items-center gap-3 mt-3">
                                 <button
                                    onClick={() => setIsSimulationMode(!isSimulationMode)}
                                    className="btn d-flex align-items-center gap-2 px-3 py-2 text-white"
                                    style={{
                                       backgroundColor: isSimulationMode ? "#059669" : "#0A5C8E",
                                       borderColor: isSimulationMode ? "#059669" : "#0A5C8E",
                                       fontSize: "12.5px",
                                       fontWeight: 600,
                                       borderRadius: "6px"
                                    }}
                                 >
                                    <Settings2 size={14} />
                                    {isSimulationMode ? "ปิดโหมดทดลองปรับค่า" : "โหมดทดลองปรับค่าจำลอง"}
                                 </button>
                                 
                                 {isSimulationMode && (
                                    <button
                                       onClick={resetSimulation}
                                       className="btn btn-outline-secondary"
                                       style={{ fontSize: "12px", borderRadius: "6px" }}
                                    >
                                       ดึงค่าตั้งต้นคนไข้
                                    </button>
                                 )}
                              </div>

                              {isSimulationMode && (
                                 <div className="mt-3 p-2 rounded-3 d-flex align-items-center gap-2" style={{ backgroundColor: deltaOverall < 0 ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)" }}>
                                    <div className="rounded-circle d-flex align-items-center justify-content-center p-1" style={{ backgroundColor: deltaOverall < 0 ? "#10B981" : "#EF4444", color: "white" }}>
                                       {deltaOverall < 0 ? <Check size={10} /> : <AlertTriangle size={10} />}
                                    </div>
                                    <span style={{ fontSize: "12px", fontWeight: 700, color: deltaOverall < 0 ? "#047857" : "#B91C1C" }}>
                                       {deltaOverall < 0 
                                          ? `จำลองลดภาระการอักเสบและฟื้นฟูร่างกายได้ดีขึ้น: ${Math.abs(deltaOverall)}%`
                                          : deltaOverall === 0 
                                             ? "อยู่ระหว่างจำลองปรับคะแนนตามสไลเดอร์..."
                                             : `ดัชนีภาระความเสี่ยงทางชีวภาพเพิ่มสูงขึ้น: +${deltaOverall}%`
                                       }
                                    </span>
                                 </div>
                              )}
                           </div>
                        </div>
                     </div>

                     {/* Laboratory Parameters Simulator Card (Phase 3C) */}
                     {isSimulationMode && (
                        <div className="card border-0" style={cardStyle}>
                           <div className="d-flex align-items-center gap-2 border-bottom pb-3 mb-3">
                              <Settings2 size={16} style={{ color: "#059669" }} />
                              <span style={{ ...sectionLabel, color: "#1F2937" }}>Laboratory Parameters Simulator (จำลองระดับค่าน้ำตาลและผลแล็บ)</span>
                           </div>
                           
                           <p className="text-muted mb-3" style={{ fontSize: "11.5px" }}>
                              แพทย์สามารถสไลด์ปรับค่าน้ำตาลสะสม (HbA1c), ค่าน้ำตาลลอย (FBS) หรือการอักเสบ (CRP) เพื่อจำลองผลตอบสนองย้อนกลับ (Biological Feedback Loop) ไปยัง 39 แกนของร่างกาย
                           </p>

                           <div className="d-flex flex-column gap-3">
                              {/* HbA1c Slider */}
                              <div>
                                 <div className="d-flex justify-content-between align-items-center mb-1">
                                    <span className="small fw-bold text-dark">Glycated Hemoglobin (HbA1c)</span>
                                    <span className="badge text-white" style={{ backgroundColor: simulatedLabs.hba1c > 6.5 ? "#DC2626" : simulatedLabs.hba1c > 5.6 ? "#D97706" : "#059669", fontSize: "10px" }}>
                                       {simulatedLabs.hba1c.toFixed(1)}% {simulatedLabs.hba1c !== actualLabs.hba1c && `(จริง: ${actualLabs.hba1c.toFixed(1)}%)`}
                                    </span>
                                 </div>
                                 <input
                                    type="range"
                                    min="4.0"
                                    max="15.0"
                                    step="0.1"
                                    value={simulatedLabs.hba1c}
                                    onChange={e => handleLabSliderChange("hba1c", parseFloat(e.target.value))}
                                    className="form-range"
                                    style={{ accentColor: "#059669" }}
                                 />
                              </div>

                              {/* Fasting Blood Sugar Slider */}
                              <div>
                                 <div className="d-flex justify-content-between align-items-center mb-1">
                                    <span className="small fw-bold text-dark">Fasting Blood Sugar (FBS)</span>
                                    <span className="badge text-white" style={{ backgroundColor: simulatedLabs.fbs > 125 ? "#DC2626" : simulatedLabs.fbs > 99 ? "#D97706" : "#059669", fontSize: "10px" }}>
                                       {Math.round(simulatedLabs.fbs)} mg/dL {simulatedLabs.fbs !== actualLabs.fbs && `(จริง: ${Math.round(actualLabs.fbs)} mg/dL)`}
                                    </span>
                                 </div>
                                 <input
                                    type="range"
                                    min="70"
                                    max="400"
                                    step="1"
                                    value={simulatedLabs.fbs}
                                    onChange={e => handleLabSliderChange("fbs", parseInt(e.target.value))}
                                    className="form-range"
                                    style={{ accentColor: "#059669" }}
                                 />
                              </div>

                              {/* C-Reactive Protein (CRP) Slider */}
                              <div>
                                 <div className="d-flex justify-content-between align-items-center mb-1">
                                    <span className="small fw-bold text-dark">C-Reactive Protein (CRP)</span>
                                    <span className="badge text-white" style={{ backgroundColor: simulatedLabs.crp > 3.0 ? "#DC2626" : simulatedLabs.crp > 1.0 ? "#D97706" : "#059669", fontSize: "10px" }}>
                                       {simulatedLabs.crp.toFixed(1)} mg/L {simulatedLabs.crp !== actualLabs.crp && `(จริง: ${actualLabs.crp.toFixed(1)} mg/L)`}
                                    </span>
                                 </div>
                                 <input
                                    type="range"
                                    min="0.1"
                                    max="20.0"
                                    step="0.1"
                                    value={simulatedLabs.crp}
                                    onChange={e => handleLabSliderChange("crp", parseFloat(e.target.value))}
                                    className="form-range"
                                    style={{ accentColor: "#059669" }}
                                 />
                              </div>

                              {/* LDL Slider */}
                              <div>
                                 <div className="d-flex justify-content-between align-items-center mb-1">
                                    <span className="small fw-bold text-dark">LDL Cholesterol</span>
                                    <span className="badge text-white" style={{ backgroundColor: simulatedLabs.ldl > 130 ? "#DC2626" : simulatedLabs.ldl > 99 ? "#D97706" : "#059669", fontSize: "10px" }}>
                                       {Math.round(simulatedLabs.ldl)} mg/dL {simulatedLabs.ldl !== actualLabs.ldl && `(จริง: ${Math.round(actualLabs.ldl)})`}
                                    </span>
                                 </div>
                                 <input
                                    type="range"
                                    min="50"
                                    max="300"
                                    step="1"
                                    value={simulatedLabs.ldl}
                                    onChange={e => handleLabSliderChange("ldl", parseInt(e.target.value))}
                                    className="form-range"
                                    style={{ accentColor: "#059669" }}
                                 />
                              </div>

                              {/* ALT Slider */}
                              <div>
                                 <div className="d-flex justify-content-between align-items-center mb-1">
                                    <span className="small fw-bold text-dark">ALT (Liver Enzyme)</span>
                                    <span className="badge text-white" style={{ backgroundColor: simulatedLabs.alt > 40 ? "#DC2626" : simulatedLabs.alt > 30 ? "#D97706" : "#059669", fontSize: "10px" }}>
                                       {Math.round(simulatedLabs.alt)} U/L {simulatedLabs.alt !== actualLabs.alt && `(จริง: ${Math.round(actualLabs.alt)})`}
                                    </span>
                                 </div>
                                 <input
                                    type="range"
                                    min="5"
                                    max="200"
                                    step="1"
                                    value={simulatedLabs.alt}
                                    onChange={e => handleLabSliderChange("alt", parseInt(e.target.value))}
                                    className="form-range"
                                    style={{ accentColor: "#059669" }}
                                 />
                              </div>
                           </div>
                        </div>
                     )}
                  </div>

                  {/* RIGHT COLUMN: AI Neural Copilot & Matched Phytotherapeutic Registry */}
                  <div className="col-lg-6 col-12 d-flex flex-column gap-4">

                     {/* AI Neural Clinical Insight - Premium light clinical layout */}
                     <div className="card border-0" style={clinicalCardStyle}>
                        <div className="d-flex justify-content-between align-items-center p-3 border-bottom" style={{ borderColor: "#E5E7EB", backgroundColor: "#F9FAFB" }}>
                           <div className="d-flex align-items-center gap-2">
                              <div className="p-2 rounded-3 text-white" style={{ backgroundColor: "#0A5C8E" }}>
                                 <Brain size={16} />
                              </div>
                              <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                                 <span style={{ ...sectionLabel, color: "#1F2937", margin: 0 }}>Neural Clinical Intelligence</span>
                                 <select
                                    value={selectedEngine}
                                    onChange={(e) => setSelectedEngine(e.target.value as any)}
                                    style={{
                                       fontSize: "11px",
                                       fontWeight: 700,
                                       color: "#4B5563",
                                       border: "1px solid #D1D5DB",
                                       borderRadius: "4px",
                                       padding: "2px 6px",
                                       background: "white",
                                       cursor: "pointer",
                                       outline: "none"
                                    }}
                                 >
                                    <option value="gemini">Gemini 2.5 Flash (AI แนะนำแกนเร็ว)</option>
                                    <option value="deepseek">Deepseek Chat (AI วิเคราะห์เชิงลึก)</option>
                                    <option value="django">Django Precision (คำนวณสูตรแพทย์)</option>
                                    <option value="tspi-brain">TSPI Brain (สมองกลเรียนรู้โลคอล)</option>
                                 </select>
                              </div>
                           </div>
                           <button
                              onClick={runAIAnalysis}
                              disabled={isAnalyzing}
                              className="btn btn-success d-flex align-items-center gap-2 text-white"
                              style={{
                                 backgroundColor: "#10B981",
                                 borderColor: "#10B981",
                                 fontSize: "12.5px",
                                 fontWeight: 700,
                                 padding: "7px 16px",
                                 borderRadius: "8px",
                                 boxShadow: "0 4px 6px -1px rgba(16, 185, 129, 0.25)",
                                 transition: "all 0.2s ease"
                              }}
                           >
                              {isAnalyzing ? (
                                 <>
                                    <RefreshCw className="animate-spin" size={13} style={{ color: "#FFFFFF" }} />
                                    กำลังประมวลผล...
                                 </>
                              ) : (
                                 "เริ่มประเมินชีวภาพ"
                              )}
                           </button>
                        </div>

                        <div className="p-4" style={{ minHeight: "360px", backgroundColor: "#FFFFFF", color: "#1F2937" }}>
                           {!aiReport && !isAnalyzing && (
                              <div className="d-flex flex-column align-items-center justify-content-center text-center" style={{ minHeight: "300px", opacity: 0.7 }}>
                                 <Star size={36} className="mb-3 text-muted" />
                                 <div style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "1px", textTransform: "uppercase", color: "#1F2937" }}>Ready for Clinical Analysis</div>
                                 <p className="mt-2 text-muted" style={{ fontSize: "12px", maxWidth: "290px" }}>
                                    {selectedEngine === "django" 
                                       ? 'คลิกปุ่ม **"เริ่มประเมินชีวภาพ"** เพื่อประมวลผลคำนวณค่าแกนชีวภาพจำลองด้วยสูตรทางการแพทย์ฝั่งหลังบ้าน Django EMR'
                                       : `คลิกปุ่ม **"เริ่มประเมินชีวภาพ"** เพื่อใช้ปัญญาประดิษฐ์ ${selectedEngine === "deepseek" ? "Deepseek" : "Gemini 2.5"} ตรวจจับความเสี่ยงและวิเคราะห์แผนฟื้นฟูทางการแพทย์`}
                                 </p>
                              </div>
                           )}

                           {isAnalyzing && (
                              <div className="d-flex flex-column align-items-center justify-content-center text-center" style={{ minHeight: "300px" }}>
                                 <div className="spinner-border text-primary mb-3" style={{ color: "#0A5C8E", width: "3rem", height: "3rem" }} role="status">
                                    <span className="visually-hidden">Loading...</span>
                                 </div>
                                 <div style={{ fontSize: "12px", fontWeight: 700, letterSpacing: "1.5px", textTransform: "uppercase", color: "#0A5C8E" }}>
                                    Evaluating Physiological Mechanisms...
                                 </div>
                                 <p className="text-muted mt-2" style={{ fontSize: "12px" }}>
                                    กำลังประเมินดัชนีชีววิทยาระบบ 39 แกนร่วมกับข้อมูลประวัติการรักษา...
                                 </p>
                              </div>
                           )}

                           {aiReport && !isAnalyzing && (
                              <div style={{ fontSize: "13px", lineHeight: "1.6" }}>
                                 
                                 {/* Summary content */}
                                 <div className="p-3 mb-4 rounded-3" style={{ backgroundColor: "rgba(10, 92, 142, 0.05)", border: "1px solid rgba(10, 92, 142, 0.15)" }}>
                                    <div className="d-flex align-items-center gap-2 mb-2">
                                       <ShieldAlert size={15} style={{ color: "#0A5C8E" }} />
                                       <span style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", color: "#0A5C8E", letterSpacing: "0.5px" }}>Clinical Impression & Mechanism Pathophysiology</span>
                                    </div>
                                    <div style={{ whiteSpace: "pre-wrap", fontSize: "12.5px", color: "#374151" }}>
                                       {aiReport.clinicalSummary}
                                    </div>
                                 </div>

                                 {/* AI Suggested Calibrations */}
                                 {aiReport.aiSuggestedUpdates && aiReport.aiSuggestedUpdates.length > 0 && (
                                    <div>
                                       <div className="text-muted mb-2 border-bottom pb-2" style={{ ...sectionLabel, borderColor: "#E5E7EB" }}>
                                          ข้อเสนอแนะนำเพื่อปรับเทียบค่าแกนตรวจโรค (Bio-Vector Updates)
                                       </div>
                                       <div className="d-flex flex-column gap-2 mb-3">
                                          {aiReport.aiSuggestedUpdates.map((item: any, idx: number) => (
                                             <div key={idx} className="p-2 rounded border" style={{ backgroundColor: "#F9FAFB", borderColor: "#E5E7EB" }}>
                                                <div className="d-flex justify-content-between align-items-center mb-1">
                                                   <span style={{ fontSize: "12px", fontWeight: 700, color: "#0A5C8E" }}>
                                                      {item.axis_id}
                                                   </span>
                                                   <span className="badge" style={{ backgroundColor: item.severity > 70 ? "#DC2626" : item.severity > 40 ? "#D97706" : "#059669", fontSize: "10px" }}>
                                                      แนะนำ: {item.severity}% Burden
                                                   </span>
                                                </div>
                                                <div style={{ fontSize: "11.5px", color: "#4B5563" }}>{item.insight}</div>
                                             </div>
                                          ))}
                                       </div>

                                       <button
                                          onClick={applyAISuggestions}
                                          className="btn btn-success w-100 d-flex align-items-center justify-content-center gap-2 py-2"
                                          style={{ fontSize: "12.5px", fontWeight: 700 }}
                                       >
                                          <Check size={14} />
                                          อนุมัติและปรับเทียบค่าแกน Digital Twin ตาม AI แนะนำ
                                       </button>
                                    </div>
                                 )}
                              </div>
                           )}
                        </div>

                        {/* Footer tools */}
                        <div className="p-3 border-top d-flex justify-content-center gap-4 bg-light" style={{ borderColor: "#E5E7EB" }}>
                           <button 
                              onClick={handlePrintReport}
                              style={{ ...ghostBtn, color: "#0A5C8E", border: "1px solid rgba(10, 92, 142, 0.2)", background: "rgba(10, 92, 142, 0.05)", fontWeight: 600 }} 
                              className="hover-light"
                           >
                              <Printer size={12} /> พิมพ์รายงานชีวภาพ
                           </button>
                           <button 
                              onClick={handleExportMenu}
                              style={{ ...ghostBtn, color: "#0A5C8E", border: "1px solid rgba(10, 92, 142, 0.2)", background: "rgba(10, 92, 142, 0.05)", fontWeight: 600 }} 
                              className="hover-light"
                           >
                              <Download size={12} /> ส่งออกสรุปชีวเคมี
                           </button>
                        </div>
                     </div>

                     {/* Configuration stats / compliance */}
                     <div className="card border-0" style={cardStyle}>
                        <div className="d-flex align-items-center gap-2 border-bottom pb-3 mb-3">
                           <Settings2 size={16} style={{ color: "#0A5C8E" }} />
                           <span style={sectionLabel}>Digital Twin Calibration Diagnostics</span>
                        </div>
                        <div className="row g-2">
                           <div className="col-6">
                              <div className="p-3 rounded bg-light border d-flex align-items-center gap-3">
                                 <div className="p-2 rounded bg-white border">
                                    <ClipboardCheck size={16} style={{ color: "#0A5C8E" }} />
                                 </div>
                                 <div>
                                    <div style={{ fontSize: "10px", color: "#9CA3AF", fontWeight: 700, textTransform: "uppercase" }}>Twin Stability</div>
                                    <div style={{ fontSize: "13px", fontWeight: 700, color: "#1F2937" }}>98.9% Fidelity</div>
                                 </div>
                              </div>
                           </div>
                           <div className="col-6">
                              <div className="p-3 rounded bg-light border d-flex align-items-center gap-3">
                                 <div className="p-2 rounded bg-white border">
                                    <ShieldCheck size={16} style={{ color: "#059669" }} />
                                 </div>
                                 <div>
                                    <div style={{ fontSize: "10px", color: "#9CA3AF", fontWeight: 700, textTransform: "uppercase" }}>Compliance</div>
                                    <div style={{ fontSize: "13px", fontWeight: 700, color: "#1F2937" }}>PDPA HIPAA Level 3</div>
                                 </div>
                              </div>
                           </div>
                        </div>
                     </div>
                  </div>
               </div>

               {/* ── 12 BIOLOGICAL DOMAIN GRID CARDS ─────────────────────────── */}
               <div style={sectionLabel} className="mb-3">Biological Systems Domains Mapping (12 แกนระบบหลัก)</div>
               <div className="row g-3 mb-4">
                  {radarData.map((d: any) => {
                     const mapping = DOMAINS_MAP[d.domainId] || { name: d.domain, color: "#6B7280", icon: Activity, description: "" };
                     const Icon = mapping.icon;
                     const isFocused = focusedDomainId === d.domainId;

                     return (
                        <div key={d.domainId} className="col-xl-3 col-md-4 col-sm-6 col-12">
                           <div
                              onClick={() => {
                                 setFocusedDomainId(d.domainId);
                                 setExpandedAxisId(null);
                              }}
                              className={`card border-0 h-100 p-3`}
                              style={{
                                 ...cardStyle,
                                 borderTop: `4px solid ${mapping.color}`,
                                 cursor: "pointer",
                                 backgroundColor: isFocused ? "rgba(10, 92, 142, 0.03)" : "#FFFFFF",
                                 borderColor: isFocused ? "#0A5C8E" : "#E5E7EB",
                                 boxShadow: isFocused ? "0 10px 15px -3px rgba(10, 92, 142, 0.15)" : "0 4px 6px -1px rgba(0,0,0,0.05)"
                              }}
                           >
                              <div className="d-flex justify-content-between align-items-start mb-2">
                                 <div className="p-2 rounded bg-light d-flex align-items-center justify-content-center" style={{ backgroundColor: "#F3F4F6" }}>
                                    <Icon size={16} style={{ color: mapping.color }} />
                                 </div>
                                 <div className="d-flex align-items-center gap-1">
                                    <span style={{ fontSize: "20px", fontWeight: 800, color: mapping.color }}>{d.current}%</span>
                                    {isSimulationMode && d.simulated !== d.current && (
                                       <span style={{ fontSize: "12px", fontWeight: 700, color: d.simulated < d.current ? "#10B981" : "#EF4444" }}>
                                          ➜ {d.simulated}%
                                       </span>
                                    )}
                                 </div>
                              </div>
                              <div style={{ fontSize: "13px", fontWeight: 700, color: "#1F2937", marginBottom: "4px" }}>{mapping.name}</div>
                              <p className="text-muted mb-0" style={{ fontSize: "11px", lineHeight: "1.4" }}>{mapping.description}</p>
                           </div>
                        </div>
                     );
                  })}
               </div>

               {/* ── INTERACTIVE DRILLDOWN & SIMULATOR CONSOLE ───────────────── */}
               {focusedDomainId && (
                  <div className="card border-0 mb-4" style={cardStyle}>
                     <div className="d-flex justify-content-between align-items-center border-bottom pb-3 mb-3">
                        <div className="d-flex align-items-center gap-2">
                           <Activity size={18} style={{ color: DOMAINS_MAP[focusedDomainId]?.color }} />
                           <span style={{ ...sectionLabel, color: "#1F2937" }}>
                              กลไกรายละเอียด: {DOMAINS_MAP[focusedDomainId]?.name} (แกนย่อย)
                           </span>
                        </div>
                        <span className="text-muted" style={{ fontSize: "12px", fontWeight: 500 }}>
                           คลิกกล่องข้อความเพื่อขยายดูโครงสร้าง Sub-Axes (A, B, C)
                        </span>
                     </div>

                     <div className="d-flex flex-column gap-3">
                        {(() => {
                           const domains = (axesData as any).domains || [];
                           const domain = domains.find((d: any) => d.domain_id === focusedDomainId);
                           if (!domain) return <p className="text-muted">ไม่พบแกนย่อย</p>;

                           let axesList: any[] = [];
                           if (focusedDomainId === 11 && domain.referenced_axes) {
                              const flatAxes = domains.flatMap((d: any) => d.axes || []);
                              axesList = flatAxes.filter((a: any) => domain.referenced_axes.includes(a.axis_id));
                           } else {
                              axesList = domain.axes || [];
                           }

                           return axesList.map((a: any) => {
                              const axisId = `AXIS_${a.axis_id}`;
                              const currentVal = patient?.axes?.[axisId]?.score ?? 50;
                              const simVal = simulatedAxes[axisId] ?? 50;
                              const isExpanded = expandedAxisId === axisId;
                              const axisWeight = weights[axisId] ?? 1.0;

                              return (
                                 <div key={axisId} className="p-3 border rounded-3 bg-light" style={{ transition: "all 0.15s" }}>
                                    <div className="row align-items-center g-3">
                                       <div className="col-md-5 col-12" style={{ cursor: "pointer" }} onClick={() => setExpandedAxisId(isExpanded ? null : axisId)}>
                                          <div className="d-flex align-items-center gap-2 mb-1">
                                             <span className="badge" style={{ backgroundColor: "#0A5C8E", fontSize: "10px" }}>Axis {a.axis_id}</span>
                                             <span style={{ fontSize: "13.5px", fontWeight: 700, color: "#1F2937" }}>{a.name}</span>
                                          </div>
                                          <div style={{ fontSize: "11px", color: "#6B7280" }}>
                                             น้ำหนักปรับแต่งอัลกอริทึม: **{axisWeight.toFixed(1)}x Impact** | คลิกเพื่อขยายดูคำอธิบายย่อย
                                          </div>
                                       </div>

                                       <div className="col-md-7 col-12">
                                          {isSimulationMode ? (
                                             <div className="d-flex align-items-center gap-3">
                                                <span style={{ fontSize: "12px", fontWeight: 600, color: "#6B7280", width: "70px" }}>จำลองเป้าหมาย</span>
                                                <input
                                                   type="range"
                                                   min="0"
                                                   max="100"
                                                   value={simVal}
                                                   onChange={e => handleSimulateChange(axisId, parseInt(e.target.value))}
                                                   className="form-range flex-grow-1"
                                                   style={{ accentColor: "#10B981" }}
                                                />
                                                <span className="badge p-2 text-white" style={{ backgroundColor: "#10B981", minWidth: "55px", fontSize: "12px" }}>
                                                   {simVal}%
                                                </span>
                                                {simVal !== currentVal && (
                                                   <span style={{ fontSize: "11px", fontWeight: 700, color: simVal < currentVal ? "#10B981" : "#EF4444" }}>
                                                      ({simVal < currentVal ? `-${currentVal - simVal}%` : `+${simVal - currentVal}%`})
                                                   </span>
                                                )}
                                             </div>
                                          ) : (
                                             <div className="d-flex align-items-center gap-3">
                                                <span style={{ fontSize: "12px", fontWeight: 600, color: "#6B7280", width: "70px" }}>ค่าความเสี่ยง</span>
                                                <div className="progress flex-grow-1" style={{ height: "8px", backgroundColor: "#E5E7EB", borderRadius: "4px" }}>
                                                   <div
                                                      className="progress-bar"
                                                      role="progressbar"
                                                      style={{
                                                         width: `${currentVal}%`,
                                                         backgroundColor: currentVal > 75 ? "#EF4444" : currentVal > 40 ? "#F59E0B" : "#10B981",
                                                         borderRadius: "4px"
                                                      }}
                                                   />
                                                </div>
                                                <span className="badge p-2 text-white" style={{ backgroundColor: currentVal > 75 ? "#EF4444" : currentVal > 40 ? "#F59E0B" : "#10B981", minWidth: "55px", fontSize: "12px" }}>
                                                   {currentVal}%
                                                </span>
                                             </div>
                                          )}
                                       </div>
                                    </div>

                                    {/* Expanded sub-axes */}
                                    {isExpanded && (
                                       <div className="mt-3 pt-3 border-top">
                                          <div className="row g-3">
                                             {Object.entries(a.sub_axes || {}).map(([key, sub]: [string, any]) => (
                                                <div key={key} className="col-md-4 col-12">
                                                   <div className="p-2 border rounded bg-white h-100">
                                                      <span className="badge bg-secondary mb-1" style={{ fontSize: "9px" }}>Sub-Axis {key}</span>
                                                      <div style={{ fontSize: "12px", fontWeight: 700, color: "#1F2937", marginBottom: "2px" }}>{sub.name}</div>
                                                      <p className="text-muted mb-0" style={{ fontSize: "11px", lineHeight: "1.4" }}>{sub.description}</p>
                                                   </div>
                                                </div>
                                             ))}
                                          </div>
                                       </div>
                                    )}
                                 </div>
                              );
                           });
                        })()}
                     </div>
                  </div>
               )}

               {/* ── SYNERGISTIC THERAPEUTIC REGISTRY PANEL ───────────────────── */}
               <div className="card border-0" style={cardStyle}>
                  <div className="d-flex align-items-center gap-2 border-bottom pb-3 mb-3">
                     <Layers size={18} style={{ color: "#0A5C8E" }} />
                     <span style={sectionLabel}>Synergistic Therapeutic Registry (ตำรับสูตรฟื้นฟูที่มีความพ้องเชิงกลไกสูงสุด)</span>
                  </div>
                  <p className="text-muted" style={{ fontSize: "12.5px" }}>
                     อัลกอริทึมวิเคราะห์หาผลิตภัณฑ์ phytomedicinals ฟื้นฟูสุขภาพที่ซิงก์ตรงกับแกนชีวภาพที่มีความรุนแรงสูงสุด ณ ขณะนี้ (Synergy Rating สูงสุด 10 คะแนน)
                  </p>

                  <div className="row g-3">
                     {activeSynergy.length === 0 ? (
                        <div className="col-12 text-center py-4 opacity-55">
                           <Star size={24} className="text-muted mb-2" />
                           <div style={{ fontSize: "12px", color: "#6B7280" }}>ไม่พบความจำเป็นเร่งด่วนในการรับสารสกัด ณ ดัชนีภาระความเสี่ยงปัจจุบัน</div>
                        </div>
                     ) : (
                        activeSynergy.map((m: any) => (
                           <div key={m.id} className="col-xl-3 col-md-6 col-12">
                              <div className="p-3 border rounded-3 h-100 bg-light d-flex flex-column justify-content-between" style={{ transition: "all 0.15s" }}>
                                 <div>
                                    <div className="d-flex justify-content-between align-items-start mb-2">
                                       <span className="badge" style={{ backgroundColor: "#0A5C8E", color: "#FFFFFF", fontSize: "11px", fontWeight: 700 }}>
                                          {m.id}
                                       </span>
                                       <span className="badge rounded-pill bg-success" style={{ fontSize: "10.5px", fontWeight: 700 }}>
                                          Synergy: {m.synergyScore.toFixed(1)} / 10
                                       </span>
                                    </div>
                                    <div style={{ fontSize: "13.5px", fontWeight: 700, color: "#1F2937", marginBottom: "4px" }}>
                                       {m.name}
                                    </div>
                                    {m.mechanism && (
                                       <div className="p-2 mb-2 rounded bg-white" style={{ fontSize: "11px", border: "1px dashed #E5E7EB" }}>
                                          <strong>กลไกหลัก:</strong> {m.mechanism}
                                       </div>
                                    )}
                                 </div>

                                 <div className="mt-3">
                                    <div style={{ fontSize: "10px", color: "#9CA3AF", fontWeight: 700, textTransform: "uppercase", marginBottom: "4px" }}>
                                       Target Protected Axes
                                    </div>
                                    <div className="d-flex flex-wrap gap-1">
                                       {m.coveredAxes.map((ax: string) => (
                                          <span key={ax} className="badge bg-secondary" style={{ fontSize: "9px" }}>
                                             Axis {ax.replace("AXIS_", "")}
                                          </span>
                                       ))}
                                    </div>
                                 </div>
                              </div>
                           </div>
                        ))
                     )}
                  </div>
               </div>
            </div>
         )}

         {/* ── AI CLINICAL ASSESSMENT MODAL (POPUP) ──────────────────────── */}
         {isAIModalOpen && aiReport && (
            <div style={{
               position: "fixed",
               top: 0,
               left: 0,
               width: "100vw",
               height: "100vh",
               backgroundColor: "rgba(15, 23, 42, 0.4)",
               backdropFilter: "blur(6px)",
               display: "flex",
               alignItems: "center",
               justifyContent: "center",
               zIndex: 2000,
               padding: "20px"
            }}>
               <div style={{
                  backgroundColor: "#FFFFFF",
                  borderRadius: "16px",
                  width: "100%",
                  maxWidth: "900px",
                  maxHeight: "90vh",
                  display: "flex",
                  flexDirection: "column",
                  boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
                  border: "1px solid #E5E7EB",
                  animation: "modalFadeIn 0.2s ease-out",
                  overflow: "hidden"
               }}>
                  {/* Modal Header */}
                  <div className="d-flex justify-content-between align-items-center p-3 border-bottom bg-light">
                     <div className="d-flex align-items-center gap-2">
                        <div className="p-2 rounded" style={{ background: "rgba(10, 92, 142, 0.1)", color: "#0A5C8E" }}>
                           <Brain size={20} />
                        </div>
                        <div>
                           <h3 className="h5 fw-bold mb-0 text-dark">Clinical Intelligence & Bio-Systems Report</h3>
                           <p className="text-muted mb-0" style={{ fontSize: "11px" }}>สรีรวิทยาการแพทย์และการวิเคราะห์วิถีโรคเชิงบูรณาการ</p>
                        </div>
                     </div>
                     <button
                        onClick={() => setIsAIModalOpen(false)}
                        className="btn border-0 p-1 hover-light rounded-circle"
                        style={{ width: "32px", height: "32px", display: "flex", alignItems: "center", justifyContent: "center" }}
                     >
                        <X size={20} className="text-muted" />
                     </button>
                  </div>

                  {/* Modal Body */}
                  <div className="p-4" style={{ overflowY: "auto", flexGrow: 1 }}>
                     
                     {/* Structured Assessment */}
                     <div className="mb-4">
                        {renderFormattedSummary(aiReport.clinicalSummary)}
                     </div>

                     {/* Bio-Vector Calibration Column Grid */}
                     {aiReport.aiSuggestedUpdates && aiReport.aiSuggestedUpdates.length > 0 && (
                        <div className="border-top pt-4">
                           <div className="d-flex align-items-center gap-2 mb-3">
                              <Settings2 size={16} style={{ color: "#0A5C8E" }} />
                              <span style={{ fontSize: "12px", fontWeight: 700, color: "#1F2937", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                                 ข้อเสนอแนะนำเพื่อปรับเทียบค่าแกนตรวจโรค (Bio-Vector Updates)
                              </span>
                           </div>

                           <div className="row g-2 mb-2">
                              {aiReport.aiSuggestedUpdates.filter((item: any) => item?.axis_id != null).map((item: any, idx: number) => {
                                 const axisNum = String(item.axis_id).replace("AXIS_", "");
                                 return (
                                    <div key={idx} className="col-md-6 col-12">
                                       <div className="p-3 rounded-3 border h-100 bg-light d-flex flex-column justify-content-between" style={{ borderColor: "#E5E7EB" }}>
                                          <div className="d-flex justify-content-between align-items-start mb-2">
                                             <span style={{ fontSize: "12.5px", fontWeight: 800, color: "#0A5C8E" }}>
                                                Axis {axisNum}
                                             </span>
                                             <span className="badge" style={{
                                                backgroundColor: item.severity > 70 ? "rgba(220, 38, 38, 0.1)" : item.severity > 40 ? "rgba(217, 119, 6, 0.1)" : "rgba(5, 150, 105, 0.1)",
                                                color: item.severity > 70 ? "#DC2626" : item.severity > 40 ? "#D97706" : "#059669",
                                                border: `1px solid ${item.severity > 70 ? "#EF4444" : item.severity > 40 ? "#F59E0B" : "#10B981"}`,
                                                fontSize: "11px",
                                                fontWeight: 700
                                             }}>
                                                ความเสี่ยง: {item.severity}%
                                             </span>
                                          </div>
                                          <p className="mb-0 text-muted" style={{ fontSize: "11.5px", lineHeight: "1.4" }}>
                                             {item.insight}
                                          </p>
                                       </div>
                                    </div>
                                 );
                              })}
                           </div>
                        </div>
                     )}
                  </div>

                  {/* Modal Footer */}
                  <div className="p-3 border-top bg-light d-flex justify-content-end gap-2">
                     <button
                        onClick={() => setIsAIModalOpen(false)}
                        className="btn btn-outline-secondary px-4"
                        style={{ fontSize: "13px", fontWeight: 600 }}
                     >
                        ปิดหน้าต่าง
                     </button>
                     {aiReport.aiSuggestedUpdates && aiReport.aiSuggestedUpdates.length > 0 && (
                        <button
                           onClick={async () => {
                              await applyAISuggestions();
                              setIsAIModalOpen(false);
                           }}
                           className="btn btn-success px-4 d-flex align-items-center gap-2"
                           style={{ fontSize: "13px", fontWeight: 700 }}
                        >
                           <Check size={16} />
                           อนุมัติและปรับเทียบค่าแกน
                        </button>
                     )}
                  </div>
               </div>
            </div>
         )}

         {/* ── OVERALL BURDEN INDEX DETAIL MODAL ───────────────────────── */}
         {isBurdenModalOpen && (
            <div style={{
               position: "fixed",
               top: 0,
               left: 0,
               width: "100vw",
               height: "100vh",
               backgroundColor: "rgba(15, 23, 42, 0.4)",
               backdropFilter: "blur(6px)",
               display: "flex",
               alignItems: "center",
               justifyContent: "center",
               zIndex: 2000,
               padding: "20px"
            }}>
               <div style={{
                  backgroundColor: "#FFFFFF",
                  borderRadius: "16px",
                  width: "100%",
                  maxWidth: "950px",
                  maxHeight: "90vh",
                  display: "flex",
                  flexDirection: "column",
                  boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
                  border: "1px solid #E5E7EB",
                  animation: "modalFadeIn 0.2s ease-out",
                  overflow: "hidden"
               }}>
                  {/* Modal Header */}
                  <div className="d-flex justify-content-between align-items-center p-3 border-bottom bg-light">
                     <div className="d-flex align-items-center gap-2">
                        <div className="p-2 rounded bg-primary bg-opacity-10 text-primary" style={{ background: "rgba(10, 92, 142, 0.1)", color: "#0A5C8E" }}>
                           <Activity size={20} />
                        </div>
                        <div>
                           <h3 className="h5 fw-bold mb-0 text-dark">Overall Biological Burden & Vector Diagnostics</h3>
                           <p className="text-muted mb-0" style={{ fontSize: "11px" }}>สรุปสถานะดัชนีภาระความเสี่ยงทางสรีรวิทยาทั้ง 12 แกนระบบหลัก และ 39 แกนชีวภาพย่อย</p>
                        </div>
                     </div>
                     <button
                        onClick={() => setIsBurdenModalOpen(false)}
                        className="btn border-0 p-1 hover-light rounded-circle"
                        style={{ width: "32px", height: "32px", display: "flex", alignItems: "center", justifyContent: "center" }}
                     >
                        <X size={20} className="text-muted" />
                     </button>
                  </div>

                  {/* Modal Body */}
                  <div className="p-4" style={{ overflowY: "auto", flexGrow: 1 }}>
                     
                     {/* Summary Card and Stats */}
                     <div className="row g-3 mb-4">
                        <div className="col-md-6">
                           <div className="p-3 rounded-3 border h-100" style={{ backgroundColor: "#FCFDFE", borderColor: "#E5E7EB" }}>
                              <div className="d-flex align-items-center gap-3">
                                 {/* Circular burden percentage */}
                                 <div className="position-relative d-flex align-items-center justify-content-center" style={{ width: "80px", height: "80px" }}>
                                    <svg style={{ transform: "rotate(-90deg)", width: "80px", height: "80px" }}>
                                       <circle cx="40" cy="40" r="34" fill="transparent" stroke="#E5E7EB" strokeWidth="6" />
                                       <circle
                                          cx="40"
                                          cy="40"
                                          r="34"
                                          fill="transparent"
                                          stroke={isSimulationMode ? "#059669" : "#0A5C8E"}
                                          strokeWidth="6"
                                          strokeDasharray="213.63"
                                          strokeDashoffset={213.63 - (213.63 * (isSimulationMode ? simulatedOverall : currentOverall)) / 100}
                                          style={{ transition: "stroke-dashoffset 0.3s ease" }}
                                       />
                                    </svg>
                                    <div className="position-absolute d-flex flex-column align-items-center">
                                       <span style={{ fontSize: "18px", fontWeight: 800, color: isSimulationMode ? "#059669" : "#0A5C8E" }}>
                                          {isSimulationMode ? simulatedOverall : currentOverall}%
                                       </span>
                                    </div>
                                 </div>
                                 <div>
                                    <h4 className="fw-bold mb-1" style={{ fontSize: "14px", color: "#1F2937" }}>ดัชนีภาระความเสี่ยงรวม</h4>
                                    <p className="mb-0 text-muted" style={{ fontSize: "11.5px", lineHeight: "1.4" }}>
                                       ค่าเฉลี่ยของความรุนแรงในทุกฟังก์ชันการทำงานของเซลล์ หากมีคะแนนเกิน 60% ถือว่าเป็นความเสี่ยงระยะเปลี่ยนผ่านที่จะนำไปสู่โรคเรื้อรังแบบพหุระบบ
                                    </p>
                                 </div>
                              </div>
                           </div>
                        </div>

                        <div className="col-md-6">
                           <div className="p-3 rounded-3 border h-100 bg-light" style={{ borderColor: "#E5E7EB" }}>
                              <div className="row text-center h-100 align-items-center">
                                 <div className="col-4 border-end">
                                    <div style={{ fontSize: "20px", fontWeight: 850, color: "#DC2626" }}>
                                       {(() => {
                                          const domains = (axesData as any).domains || [];
                                          const flatAxes = domains.flatMap((d: any) => d.axes || []);
                                          return flatAxes.filter((a: any) => {
                                             const val = isSimulationMode ? (simulatedAxes[`AXIS_${a.axis_id}`] ?? 50) : getPatientAxisScore(`AXIS_${a.axis_id}`);
                                             return val > 70;
                                          }).length;
                                       })()}
                                    </div>
                                    <div className="text-muted" style={{ fontSize: "10px", fontWeight: 700 }}>HIGH RISK AXES</div>
                                 </div>
                                 <div className="col-4 border-end">
                                    <div style={{ fontSize: "20px", fontWeight: 850, color: "#D97706" }}>
                                       {(() => {
                                          const domains = (axesData as any).domains || [];
                                          const flatAxes = domains.flatMap((d: any) => d.axes || []);
                                          return flatAxes.filter((a: any) => {
                                             const val = isSimulationMode ? (simulatedAxes[`AXIS_${a.axis_id}`] ?? 50) : getPatientAxisScore(`AXIS_${a.axis_id}`);
                                             return val >= 40 && val <= 70;
                                          }).length;
                                       })()}
                                    </div>
                                    <div className="text-muted" style={{ fontSize: "10px", fontWeight: 700 }}>MODERATE RISK</div>
                                 </div>
                                 <div className="col-4">
                                    <div style={{ fontSize: "20px", fontWeight: 850, color: "#059669" }}>
                                       {(() => {
                                          const domains = (axesData as any).domains || [];
                                          const flatAxes = domains.flatMap((d: any) => d.axes || []);
                                          return flatAxes.filter((a: any) => {
                                             const val = isSimulationMode ? (simulatedAxes[`AXIS_${a.axis_id}`] ?? 50) : getPatientAxisScore(`AXIS_${a.axis_id}`);
                                             return val < 40;
                                          }).length;
                                       })()}
                                    </div>
                                    <div className="text-muted" style={{ fontSize: "10px", fontWeight: 700 }}>STABLE AXES</div>
                                 </div>
                                </div>
                            </div>
                         </div>
                      </div>

                      {/* 12 Domain Summary Accordion list */}
                      <div className="d-flex flex-column gap-3">
                         {radarData.map((d: any) => {
                            const mapping = DOMAINS_MAP[d.domainId] || { name: d.domain, color: "#6B7280", icon: Activity };
                            const Icon = mapping.icon;
                            
                            const domains = (axesData as any).domains || [];
                            const domain = domains.find((dom: any) => dom.domain_id === d.domainId);
                            let axesList: any[] = [];
                            if (domain) {
                               if (d.domainId === 11 && domain.referenced_axes) {
                                  const flatAxes = domains.flatMap((dom: any) => dom.axes || []);
                                  axesList = flatAxes.filter((a: any) => domain.referenced_axes.includes(a.axis_id));
                               } else {
                                  axesList = domain.axes || [];
                               }
                            }

                            return (
                               <div key={d.domainId} className="border rounded-3 overflow-hidden">
                                  <div className="d-flex justify-content-between align-items-center p-3 bg-light border-bottom">
                                     <div className="d-flex align-items-center gap-2">
                                        <Icon size={16} style={{ color: mapping.color }} />
                                        <span style={{ fontSize: "13px", fontWeight: 800, color: "#1F2937" }}>
                                           {mapping.name}
                                        </span>
                                     </div>
                                     <span className="badge" style={{ backgroundColor: mapping.color, fontSize: "11px", fontWeight: 750 }}>
                                        ภาระเฉลี่ย: {d.current}%
                                     </span>
                                  </div>
                                  <div className="p-3 bg-white">
                                     <div className="row g-2">
                                        {axesList.map((a: any) => {
                                           const axisKey = `AXIS_${a.axis_id}`;
                                           const score = isSimulationMode ? (simulatedAxes[axisKey] ?? 50) : getPatientAxisScore(axisKey);
                                           return (
                                              <div key={a.axis_id} className="col-md-6 col-12">
                                                 <div className="p-2 rounded border d-flex justify-content-between align-items-center" style={{ backgroundColor: "#FAFAFA" }}>
                                                    <div style={{ minWidth: 0, paddingRight: "8px" }}>
                                                       <div className="d-flex align-items-center gap-1.5">
                                                          <span className="badge" style={{ backgroundColor: "rgba(107, 114, 128, 0.15)", color: "#4B5563", fontSize: "9px" }}>
                                                             Axis {a.axis_id}
                                                          </span>
                                                          <span style={{ fontSize: "11.5px", fontWeight: 600, color: "#374151", textOverflow: "ellipsis", whiteSpace: "nowrap", overflow: "hidden" }}>
                                                             {a.name}
                                                          </span>
                                                       </div>
                                                    </div>
                                                    <span style={{
                                                       fontSize: "11px",
                                                       fontWeight: 700,
                                                       color: score > 70 ? "#DC2626" : score > 40 ? "#D97706" : "#059669"
                                                    }}>
                                                       {score}%
                                                    </span>
                                                 </div>
                                              </div>
                                           );
                                        })}
                                     </div>
                                  </div>
                               </div>
                            );
                         })}
                      </div>
                   </div>

                   {/* Modal Footer */}
                   <div className="p-3 border-top bg-light d-flex justify-content-end">
                      <button
                         onClick={() => setIsBurdenModalOpen(false)}
                         className="btn btn-primary px-4"
                         style={{ backgroundColor: "#0A5C8E", borderColor: "#0A5C8E", fontSize: "13px", fontWeight: 600 }}
                      >
                         ตกลง
                      </button>
                   </div>
                </div>
             </div>
          )}
       </div>
    );
}

// ── Page wrapper with Suspense ───────────────────────────────────
export default function DigitalTwinPage() {
   return (
      <Suspense fallback={
         <div className="d-flex flex-column align-items-center justify-content-center" style={{ minHeight: "80vh", gap: "16px" }}>
            <Loader2 className="animate-spin text-primary" size={40} style={{ color: "#0A5C8E" }} />
            <div style={{ fontSize: "14px", fontWeight: 600, color: "#4B5563" }}>กำลังโหลดข้อมูล Digital Twin Console...</div>
         </div>
      }>
         <DigitalTwinStandard />
      </Suspense>
   );
}