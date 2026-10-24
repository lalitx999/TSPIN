"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
// Architecture: Django + PostgreSQL backend (no Firebase/Firestore) — all data via REST API
import {
  Brain, Users, Search, Send, Loader2, ShieldCheck,
  Mic, StopCircle, CheckCircle, Play, Pause, ChevronRight, RefreshCw,
  Image, Paperclip, Save, History, Share2, X, Zap, Eye, FileText, Download, Trash2
} from "lucide-react";
import Swal from "sweetalert2";

import BiologicalHUD from "@/components/intelligence/BiologicalHUD";
import ContextInspector from "@/components/intelligence/ContextInspector";
import QuickActionMenu from "@/components/intelligence/QuickActionMenu";
import ErrorBoundary from "@/components/ui/ErrorBoundary";
import { medicalDb } from "@/lib/medical-data";
import axesLocalData from "@/data/39_last_x.json";
import { saveGeneratedReport, getGeneratedReports, deleteGeneratedReport, updatePatient, getPatient, saveClinicalAnalysis, getClinicalAnalyses } from "@/utils/api/services";

// ── Style helpers ────────────────────────────────────────────────
const card: React.CSSProperties = {
  background: "#FFFFFF",
  border: "1px solid #E5E7EB",
  borderRadius: "8px",
  padding: "20px",
};

const sectionLabel: React.CSSProperties = {
  fontSize: "11px",
  fontWeight: 600,
  color: "#6B7280",
  letterSpacing: "0.5px",
  textTransform: "uppercase",
  marginBottom: "16px",
};

export default function AIPhysicianPage() {
  return (
    <Suspense fallback={
      <div style={{ minHeight: "40vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <p style={{ fontSize: "13px", color: "#9CA3AF" }}>กำลังโหลด Neural Engine…</p>
      </div>
    }>
      <ErrorBoundary>
        <AIPhysicianContent />
      </ErrorBoundary>
    </Suspense>
  );
}

function AIPhysicianContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const patientIdFromUrl = searchParams.get("id");

  const [patients, setPatients] = useState<any[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string | null>(patientIdFromUrl);
  const [showPatientSearch, setShowPatientSearch] = useState(false);
  const [patientSearch, setPatientSearch] = useState("");
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<any[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [activeMission, setActiveMission] = useState<string | null>(null);
  const [patientInfo, setPatientInfo] = useState<any>(null);
  const [axisData, setAxisData] = useState<any[]>([]);

  // ── Workflow States ──────────────────────────────────────────
  const [workflowPhase, setWorkflowPhase] = useState<"intake" | "analysis">("intake");
  const [isRecording, setIsRecording] = useState(false);
  const [transcription, setTranscription] = useState("");
  const [intakeSummary, setIntakeSummary] = useState<string | null>(null);
  const [structuredSoap, setStructuredSoap] = useState<any>(null);
  const [isProcessingIntake, setIsProcessingIntake] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [showSendModal, setShowSendModal] = useState(false);
  const [historyItems, setHistoryItems] = useState<any[]>([]);
  const [expandedHistoryId, setExpandedHistoryId] = useState<string | null>(null);
  // 🗂️ Multi-file queue: เก็บหลายไฟล์พร้อมกัน (เสียง + รูป + Lab PDF)
  const [intakeFiles, setIntakeFiles] = useState<File[]>([]);
  const [intakeFileProgress, setIntakeFileProgress] = useState<string>("");



  // Redirect to dedicated Precision Report generator page
  const handleOpenDeepReportModal = () => {
    if (!selectedPatientId) {
      Swal.fire({
        title: "กรุณาเลือกคนไข้",
        text: "กรุณาเลือกคนไข้ก่อนสร้างรายงานเชิงลึกครับ",
        icon: "warning",
        confirmButtonColor: "#0A5C8E"
      });
      return;
    }
    router.push(`/doctor/precision-report?patientId=${selectedPatientId}`);
  };

  // Systemic Biological Burden Animation hook
  const targetBurden = Math.round(
    axisData.reduce((acc, cur) => acc + (cur.severity || 0), 0) / (axisData.length || 1)
  ) || 0;
  const [burdenProgress, setBurdenProgress] = useState(0);

  useEffect(() => {
    if (isAnalyzing) {
      // Simulate search/scan processing animation while loading
      let current = 0;
      const interval = setInterval(() => {
        current += Math.random() * 8 + 2;
        if (current > 92) current = 92;
        setBurdenProgress(Math.round(current));
      }, 300);
      return () => clearInterval(interval);
    } else {
      // Smooth animation transition to final target calculated score
      let start = burdenProgress;
      const diff = targetBurden - start;
      if (diff === 0) return;

      const duration = 1000;
      const startTime = performance.now();

      let animationFrameId: number;
      const animate = (time: number) => {
        const elapsed = time - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const ease = progress * (2 - progress); // easeOutQuad
        setBurdenProgress(Math.round(start + diff * ease));

        if (progress < 1) {
          animationFrameId = requestAnimationFrame(animate);
        }
      };

      animationFrameId = requestAnimationFrame(animate);
      return () => cancelAnimationFrame(animationFrameId);
    }
  }, [isAnalyzing, targetBurden]);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const multiFileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // 🗂️ Add files to intake queue (ไม่ process ทันที รอกด "ประมวลผล")
  const handleAddFilesToQueue = (newFiles: FileList | null) => {
    if (!newFiles) return;
    if (!selectedPatientId) {
      Swal.fire({ title: "แจ้งเตือน", text: "กรุณาเลือกคนไข้ก่อนแนบไฟล์ครับ", icon: "warning", confirmButtonColor: "#0A5C8E" });
      return;
    }
    const fileArr = Array.from(newFiles);
    setIntakeFiles(prev => {
      const existingNames = new Set(prev.map(f => f.name));
      const unique = fileArr.filter(f => !existingNames.has(f.name));
      return [...prev, ...unique];
    });
  };

  // 🚀 Process all queued files sequentially then merge into SOAP Note
  const handleProcessAllFiles = async () => {
    if (!selectedPatientId) {
      Swal.fire({ title: "แจ้งเตือน", text: "กรุณาเลือกคนไข้ก่อนครับ", icon: "warning", confirmButtonColor: "#0A5C8E" });
      return;
    }
    const allFilesToProcess = [...intakeFiles];
    // If there's also typed text, we'll process that too via text endpoint
    const hasTextOnly = allFilesToProcess.length === 0 && transcription.trim();
    if (allFilesToProcess.length === 0 && !transcription.trim()) return;

    setIsProcessingIntake(true);
    setIntakeSummary(null);
    setStructuredSoap(null);

    const combinedTexts: string[] = [];
    let mergedStructured: any = null;

    try {
      // Process typed text first if present
      if (transcription.trim()) {
        setIntakeFileProgress(`📝 ประมวลผลข้อความ...`);
        try {
          const res = await fetch("/api/doctor/voice-to-form", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: transcription, patientId: selectedPatientId })
          });
          const d = await res.json();
          if (!d.error && d.text) combinedTexts.push(d.text);
          if (!d.error && d.structured && !mergedStructured) mergedStructured = d.structured;
        } catch (e) { console.warn("Text intake error:", e); }
      }

      // Process each file sequentially
      for (let i = 0; i < allFilesToProcess.length; i++) {
        const file = allFilesToProcess[i];
        setIntakeFileProgress(`📄 กำลังวิเคราะห์ [${i + 1}/${allFilesToProcess.length}]: ${file.name} ด้วย Gemini...`);
        try {
          const formData = new FormData();
          formData.append("file", file);
          formData.append("patientId", selectedPatientId);
          const res = await fetch("/api/doctor/voice-to-form", { method: "POST", body: formData });
          const d = await res.json();
          if (d.error) { console.warn(`⚠️ File [${file.name}] error:`, d.error); continue; }
          if (d.text) combinedTexts.push(`[${file.name}]: ${d.text}`);
          if (d.structured && !mergedStructured) mergedStructured = d.structured;
        } catch (e) { console.warn(`⚠️ File [${file.name}] failed:`, e); }
      }

      // Merge all text outputs
      const combinedRawText = combinedTexts.join("\n\n");
      setTranscription(combinedRawText);

      // If we have multiple sources, re-process combined text to get a unified SOAP
      if (combinedTexts.length > 1) {
        setIntakeFileProgress("🧠 กำลังรวมข้อมูลและสร้าง SOAP Note แบบรวม...");
        try {
          const mergeRes = await fetch("/api/doctor/voice-to-form", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: combinedRawText, patientId: selectedPatientId })
          });
          const mergeData = await mergeRes.json();
          if (!mergeData.error) {
            setIntakeSummary(mergeData.summary || combinedRawText);
            setStructuredSoap(mergeData.structured || mergedStructured);
          } else {
            setIntakeSummary(combinedRawText);
            setStructuredSoap(mergedStructured);
          }
        } catch (e) {
          setIntakeSummary(combinedRawText);
          setStructuredSoap(mergedStructured);
        }
      } else {
        // Single source - use result directly
        const singleRes = combinedRawText || transcription;
        if (mergedStructured) {
          setIntakeSummary(mergedStructured.summary_short || singleRes);
          setStructuredSoap(mergedStructured);
        } else {
          setIntakeSummary(singleRes);
          setStructuredSoap(null);
        }
      }

      setIntakeFileProgress("");
      setIntakeFiles([]);
    } catch (err: any) {
      console.error("🔥 Multi-file processing error:", err);
      setIntakeFileProgress(`⚠️ เกิดข้อผิดพลาด: ${err.message}`);
    } finally {
      setIsProcessingIntake(false);
    }
  };

  // Legacy single-file handler (kept for voice recording use)
  const handleFileUpload = async (file: File) => {
    if (!selectedPatientId) return;
    setIntakeFiles(prev => [...prev, file]);
  };

  const handleSaveIntake = async () => {
    if (!selectedPatientId || !intakeSummary) {
      Swal.fire({
        title: "แจ้งเตือน",
        text: "กรุณาเลือกคนไข้และประมวลผลอาการก่อนบันทึกครับ",
        icon: "warning",
        confirmButtonColor: "#0A5C8E"
      });
      return;
    }

    setIsSaving(true);
    try {
      const patient = await getPatient(selectedPatientId);
      const patientName = (patientInfo?.first_name || patientInfo?.fname || "") + " " + (patientInfo?.last_name || patientInfo?.lname || "");

      // 1. Build structured SOAP content for history entry
      let historyContent = intakeSummary;
      if (structuredSoap) {
        historyContent = `SOAP Note\n`;
        historyContent += `[S] Subjective: ${structuredSoap.subjective || "-"}\n`;
        historyContent += `[O] Objective: ${structuredSoap.objective || "-"}\n`;
        historyContent += `[A] Assessment: ${structuredSoap.assessment || "-"}\n`;
        historyContent += `[P] Plan: ${structuredSoap.plan || "-"}\n`;
        if (structuredSoap.key_symptoms?.length) {
          historyContent += `\nอาการสำคัญ: ${structuredSoap.key_symptoms.join(", ")}\n`;
        }
        historyContent += `\nสรุป: ${structuredSoap.summary_short || intakeSummary}`;
      }
      if (transcription) historyContent += `\n\nบันทึกเสียง/ข้อมูลดิบ:\n${transcription}`;

      // 2. Write to PatientHistory (Django REST) — shows in Treatment Timeline
      const token = typeof window !== "undefined"
        ? (localStorage.getItem("doctor_access_token") || "")
        : "";
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";
      await fetch(`${apiBase}/api/history/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { "Authorization": `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          patient: selectedPatientId,
          type: "Doctor Visit",
          title: `SOAP Note — ${new Date().toLocaleDateString("th-TH", { year: "numeric", month: "short", day: "numeric" })}`,
          content: historyContent
        })
      }).catch((e: any) => console.warn("⚠️ PatientHistory write failed (non-critical):", e));

      // 3. Update patient extra_data (clinical_intakes list)
      if (patient) {
        const clinicalIntakes = patient.extra_data?.clinical_intakes || [];
        const newIntake = {
           patientId: selectedPatientId,
           patientName,
           summary: intakeSummary,
           rawTranscription: transcription,
           structuredSoap: structuredSoap || null,
           timestamp: new Date().toISOString(),
        };
        await updatePatient(selectedPatientId, {
           symptoms: intakeSummary,
           lastIntakeDate: new Date().toISOString(),
           extra_data: {
              ...(patient.extra_data || {}),
              clinical_intakes: [newIntake, ...clinicalIntakes]
           }
        });
      }

      await loadPatientData(selectedPatientId);
      Swal.fire({
        title: "สำเร็จ",
        text: "บันทึกลง EMR และประวัติการรักษา (Treatment History) เรียบร้อยแล้วครับ!",
        icon: "success",
        confirmButtonColor: "#0A5C8E"
      });
    } catch (err: any) {
      console.error("🔥 EMR Save Error:", err);
      Swal.fire({
        title: "เกิดข้อผิดพลาด",
        text: `บันทึกไม่สำเร็จ: ${err.message}`,
        icon: "error",
        confirmButtonColor: "#0A5C8E"
      });
    } finally {
      setIsSaving(false);
    }
  };

  useEffect(() => {
    if (!isRecording && transcription === "" && workflowPhase === 'intake') {
      // Simulate transcription after recording stops
    }
  }, [isRecording]);

  const toggleRecording = async () => {
    if (isRecording) {
      // 🛑 Stop recording
      setIsRecording(false);
      const recorder = mediaRecorderRef.current;
      if (recorder && recorder.state !== "inactive") {
        recorder.stop();
        recorder.stream.getTracks().forEach(t => t.stop());
      }
    } else {
      try {
        // 🎙️ 1. Request Microphone Access + GPS
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        navigator.geolocation.getCurrentPosition(
          (pos) => console.log("Clinical Location Captured:", pos.coords.latitude, pos.coords.longitude),
          (err) => console.warn("GPS Access Denied:", err.message)
        );

        // 2. Setup MediaRecorder
        audioChunksRef.current = [];
        const recorder = new MediaRecorder(stream, {
          mimeType: MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "audio/mp4",
        });

        recorder.ondataavailable = (e) => {
          if (e.data.size > 0) audioChunksRef.current.push(e.data);
        };

        recorder.onstop = async () => {
          const audioBlob = new Blob(audioChunksRef.current, {
            type: recorder.mimeType,
          });

          if (audioBlob.size < 100) {
            console.warn("⚠️ Empty recording, skipping...");
            return;
          }

          // 3. Send to voice-to-form API
          setIsProcessingIntake(true);
          try {
            const formData = new FormData();
            formData.append("file", audioBlob, `recording_${Date.now()}.webm`);
            if (selectedPatientId) {
              formData.append("patientId", selectedPatientId);
            }

            const res = await fetch("/api/doctor/voice-to-form", {
              method: "POST",
              body: formData,
            });

            const data = await res.json();

            if (data.error) throw new Error(data.error);

            setTranscription(data.text || "");
            setIntakeSummary(data.summary || "");
            setStructuredSoap(data.structured || null);
            console.log("✅ Voice transcribed and structured SOAP set:", data.text?.slice(0, 100));
          } catch (err: any) {
            console.error("Voice processing error:", err);
            setTranscription(`⚠️ การถอดเสียงล้มเหลว: ${err.message}`);
          } finally {
            setIsProcessingIntake(false);
          }
        };

        mediaRecorderRef.current = recorder;
        recorder.start();
        setIsRecording(true);
        setTranscription("");
        setIntakeSummary(null);
        setStructuredSoap(null);
      } catch (err: any) {
        Swal.fire({
          title: "สิทธิ์การเข้าถึงไมโครโฟน",
          text: `ไม่สามารถเริ่มการซักถามได้: ${err.message}\nโปรดอนุญาตสิทธิ์การใช้ไมโครโฟนในเบราว์เซอร์ครับ`,
          icon: "error",
          confirmButtonColor: "#0A5C8E"
        });
      }
    }
  };
  const fetchHistory = async () => {
    console.log("Fetching history for:", selectedPatientId);
    if (!selectedPatientId) return;
    try {
      const items = await getClinicalAnalyses(selectedPatientId);

      // Sort manually in memory
      const sortedItems = [...items].sort((a: any, b: any) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      );

      setHistoryItems(sortedItems);
      setShowHistoryModal(true);
      console.log("✅ History loaded:", sortedItems.length, "items");
    } catch (err: any) {
      console.error("🔥 Fetch History Error:", err);
      Swal.fire({
        title: "เกิดข้อผิดพลาด",
        text: `ไม่สามารถดึงประวัติได้: ${err.message}`,
        icon: "error",
        confirmButtonColor: "#0A5C8E"
      });
    }
  };

  const handleSaveAnalysis = async (content: string) => {
    if (!selectedPatientId) return;
    try {
      await saveClinicalAnalysis(selectedPatientId, {
        content,
        mission: activeMission,
        visibleToPatient: true
      });
    } catch (err) {
      console.error("Error saving analysis:", err);
    }
  };

  useEffect(() => {
    const fetchPatients = async () => {
      try {
        const data = await medicalDb.getPatientList();
        setPatients(data);
      } catch (err) {
        console.error("Error fetching patients:", err);
      }
    };
    fetchPatients();

    if (patientIdFromUrl) {
      setSelectedPatientId(patientIdFromUrl);
      loadPatientData(patientIdFromUrl);
    }
  }, [patientIdFromUrl]);

  const loadPatientData = async (id: string) => {
    try {
      const data = await medicalDb.getPatient(id);

      if (data) {
        const pInfo = {
          ...data,
          name: data.name || `${data.fname || data.firstName || "Unknown"} ${data.lname || data.lastName || ""}`.trim(),
        };
        setPatientInfo(pInfo);

        // 🧠 Real-time Heuristic Reasoning for Digital Twin HUD
        let processedAxes: any[] = [];
        const patientAxes = data.axes || {}; // Scores saved from previous AI analysis

        try {
          // ✅ Fast, Offline-Resilient Axis Definitions from 39_last_x.json
          const domainsList = (axesLocalData as any).domains || [];
          processedAxes = domainsList.flatMap((d: any) => 
            (d.axes || []).map((ax: any) => {
              const axisKey = `D${d.domain_id}_${ax.axis_id}`; // e.g. "D1_1" — axis key format used in clinical records
              const savedScore = patientAxes[axisKey] || patientAxes[`AXIS_${ax.axis_id}`] || patientAxes[ax.axis_id] || {};
              return {
                axis_id: axisKey,
                axis_name: ax.name,
                domain_id: d.domain_id,
                domain_title: d.title,
                severity: savedScore.score || 0,   // 0 = ยังไม่ได้วิเคราะห์
                insight: savedScore.insight || "",
              };
            })
          ).sort((a: any, b: any) => (a.domain_id || 0) - (b.domain_id || 0));
        } catch (localErr) {
          console.error("Failed to map local axis definitions:", localErr);
        }

        setAxisData(processedAxes);
      }
    } catch (err) {
      console.error("Error loading patient info:", err);
    }
  };

  const handleSelectPatient = (id: string) => {
    setSelectedPatientId(id);
    loadPatientData(id);
    setShowPatientSearch(false);
    setMessages([]);
    setActiveMission(null);
    router.push(`/doctor/ai-physician?id=${id}`);
  };

  const handleQuickAction = (_actionId: string, label: string) => {
    if (!selectedPatientId) return;
    setActiveMission(label);
    setQuery(`[Mission: ${label}] โปรดวิเคราะห์ข้อมูลคนไข้รายนี้ในประเด็น "${label}" โดยละเอียด อ้างอิงจากประวัติการตรวจและแกนชีวภาพที่มีอยู่ครับ`);
  };

  const handleAnalyze = async () => {
    if (!query.trim() || !selectedPatientId) return;
    setIsAnalyzing(true);

    const userMessage = { role: "user", content: query };
    setMessages(prev => [...prev, userMessage]);
    setQuery("");

    try {
      console.log("🚀 Sending to AI Brain with Bio-Feedback loop...");
      // 🛡️ Only proceed if real axes are loaded from PostgreSQL
      if (axisData.length === 0) {
        setMessages(prev => [...prev, { role: "assistant", content: "⚠️ กรุณาเลือกคนไข้และรอให้ระบบโหลดข้อมูลแกนชีวภาพจากฐานข้อมูลก่อนครับ" }]);
        setIsAnalyzing(false);
        return;
      }
      const currentAxes = axisData;

      const res = await fetch("/api/ai/brain", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [...messages, userMessage],
          patientId: selectedPatientId,
          clinicalContext: {
            symptoms: intakeSummary || patientInfo?.symptoms,
            patientName: `${patientInfo?.fname} ${patientInfo?.lname}`,
            hn: patientInfo?.hn,
            axes: currentAxes
          },
          engine: "groq",
          // ✅ System instruction ที่ถูกต้อง — บังคับ AI ส่ง JSON เสมอ
          systemInstruction: `เมื่อวิเคราะห์เสร็จ ให้ปิดท้ายด้วย JSON block นี้เสมอ โดยประเมินค่า severity (0-100) ตามความรุนแรงทางคลินิกจริง:
:::BIO_UPDATE::: {"axes":[{"axis_id":"D1_1","severity":XX,"insight":"..."},{"axis_id":"D3_1","severity":XX,"insight":"..."},{"axis_id":"D5_1","severity":XX,"insight":"..."},{"axis_id":"D9_1","severity":XX,"insight":"..."}]} :::`,
        }),
      });

      const data = await res.json();
      if (data.error) throw new Error(data.error);

      // 🧠 Parse Bio-Feedback from AI response
      let mainContent = data.content;

      // Extract JSON block
      const bioMatch = mainContent.match(/:::BIO_UPDATE:::([\s\S]*?)(?::::|$)/);
      let updates: any[] = [];

      if (bioMatch) {
        try {
          const bioUpdate = JSON.parse(bioMatch[1].trim());
          if (bioUpdate.axes) updates = bioUpdate.axes;
          mainContent = mainContent.replace(/:::BIO_UPDATE:::[\s\S]*?(?::::|$)/, "").trim();
          console.log("✅ Bio-Feedback received:", updates);
        } catch (e) {
          console.warn("⚠️ Failed to parse bio-feedback JSON:", e);
        }
      }

      // Fallback: Regex extraction from Thai text
      if (updates.length === 0) {
        const patterns = [
          { axis_id: "D1_1", regex: /(?:Detox|ตับ|พิษ).*?(\d+)%/i },
          { axis_id: "D3_1", regex: /(?:Metabolic|น้ำตาล|เบาหวาน).*?(\d+)%/i },
          { axis_id: "D5_1", regex: /(?:Cardio|หัวใจ|หลอดเลือด).*?(\d+)%/i },
          { axis_id: "D9_1", regex: /(?:Neuro|ประสาท|นอน).*?(\d+)%/i },
        ];
        patterns.forEach(p => {
          const match = mainContent.match(p.regex);
          if (match && match[1]) {
            updates.push({ axis_id: p.axis_id, severity: parseInt(match[1]), insight: "สกัดจากบทวิเคราะห์ AI" });
          }
        });
      }

      // ✅ Update HUD State
      if (updates.length > 0) {
        const updatedAxes = currentAxes.map(ax => {
          const u = updates.find((u: any) => u.axis_id === ax.axis_id);
          return u ? { ...ax, severity: u.severity, insight: u.insight } : ax;
        });
        setAxisData(updatedAxes);
        console.log("🧬 HUD Updated:", updatedAxes);

        // 💾 Persist to Django PostgreSQL
        const scoresMap: Record<string, any> = {};
        updatedAxes.forEach((ax: any) => {
          const numericId = parseInt(String(ax.axis_id).replace(/[^\d]/g, ''));
          if (numericId >= 1 && numericId <= 39) {
            scoresMap[`AXIS_${numericId}`] = {
              score: ax.severity,
              insight: ax.insight,
              axisName: ax.axis_name
            };
          }
        });
        await medicalDb.updateBiologicalScores(selectedPatientId, scoresMap);
      }

      const assistantMessage = { role: "assistant", content: mainContent };
      setMessages(prev => [...prev, assistantMessage]);

      await handleSaveAnalysis(mainContent);
    } catch (err: any) {
      setMessages(prev => [...prev, { role: "assistant", content: `เกิดข้อผิดพลาด: ${err.message}` }]);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const filteredPatients = patients.filter(p =>
    (p.name || p.fname || "").toLowerCase().includes(patientSearch.toLowerCase()) ||
    (p.lname || "").toLowerCase().includes(patientSearch.toLowerCase()) ||
    (p.hn || "").toLowerCase().includes(patientSearch.toLowerCase())
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>

      {/* ── Header ───────────────────────────────────────────── */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "4px" }}>
            <div style={{ width: "40px", height: "40px", background: "#E8F0F5", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Brain size={22} style={{ color: "#0A5C8E" }} />
            </div>
            <h1 style={{ fontSize: "22px", fontWeight: 600, color: "#1F2937", margin: 0 }}>
              AI Physician Assistant
            </h1>
          </div>
          <p style={{ fontSize: "12px", color: "#6B7280", margin: "0 0 0 52px", letterSpacing: "0.3px" }}>
            Clinical Reasoning Engine · 39 Mechanistic Axes
          </p>
        </div>

        {/* Patient selector */}
        <div style={{ position: "relative" }}>
          <button
            onClick={() => setShowPatientSearch(v => !v)}
            className="btn btn-primary"
            style={{ fontSize: "13px", padding: "8px 16px", display: "flex", alignItems: "center", gap: "8px" }}
          >
            <Users size={15} />
            {selectedPatientId && patientInfo ? patientInfo.name : "เลือกคนไข้"}
          </button>

          {showPatientSearch && (
            <div style={{
              position: "absolute", right: 0, top: "calc(100% + 8px)",
              width: "300px", ...card, zIndex: 200,
              boxShadow: "0 8px 24px rgba(0,0,0,0.12)", padding: "16px",
            }}>
              {/* Search */}
              <div style={{
                display: "flex", alignItems: "center", gap: "8px",
                border: "1px solid #E5E7EB", borderRadius: "4px",
                padding: "7px 12px", background: "#F9FAFB", marginBottom: "12px",
              }}>
                <Search size={13} style={{ color: "#9CA3AF", flexShrink: 0 }} />
                <input
                  autoFocus
                  type="text"
                  placeholder="ค้นหาชื่อหรือ HN…"
                  value={patientSearch}
                  onChange={e => setPatientSearch(e.target.value)}
                  style={{ background: "transparent", border: "none", outline: "none", fontSize: "13px", flex: 1, color: "#1F2937" }}
                />
              </div>

              <div style={{ maxHeight: "280px", overflowY: "auto" }} className="custom-scrollbar">
                {filteredPatients.length === 0 ? (
                  <p style={{ textAlign: "center", padding: "24px 0", fontSize: "13px", color: "#9CA3AF", margin: 0 }}>
                    ไม่พบข้อมูลคนไข้
                  </p>
                ) : (
                  filteredPatients.map(p => (
                    <button
                      key={p.id}
                      onClick={() => handleSelectPatient(p.id)}
                      style={{
                        width: "100%", display: "flex", alignItems: "center", gap: "10px",
                        padding: "8px 10px", background: "transparent", border: "none",
                        borderRadius: "4px", cursor: "pointer", marginBottom: "2px", textAlign: "left",
                        transition: "background 0.1s",
                      }}
                      onMouseEnter={e => (e.currentTarget.style.background = "#F3F4F6")}
                      onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                    >
                      <div style={{
                        width: "32px", height: "32px", borderRadius: "50%",
                        background: "#0A5C8E", color: "white",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: "13px", fontWeight: 600, flexShrink: 0,
                      }}>
                        {(p.name || p.fname || "?").charAt(0)}
                      </div>
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontSize: "13px", fontWeight: 500, color: "#1F2937", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {p.name || `${p.fname} ${p.lname}`}
                        </div>
                        <div style={{ fontSize: "11px", color: "#9CA3AF" }}>HN: {p.hn || p.id}</div>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── No patient ──────────────────────────────────────── */}
      {!selectedPatientId ? (
        <div style={{ ...card, textAlign: "center", padding: "60px 40px" }}>
          <div style={{
            width: "64px", height: "64px", background: "#F3F4F6", borderRadius: "12px",
            display: "flex", alignItems: "center", justifyContent: "center",
            margin: "0 auto 20px",
          }}>
            <Brain size={36} style={{ color: "#D1D5DB" }} />
          </div>
          <h2 style={{ fontSize: "18px", fontWeight: 600, color: "#1F2937", marginBottom: "8px" }}>
            ยังไม่มีเซสชันการรักษา
          </h2>
          <p style={{ fontSize: "13px", color: "#6B7280", maxWidth: "360px", margin: "0 auto 24px", lineHeight: 1.6 }}>
            โปรดเลือกคนไข้เพื่อเริ่มการวิเคราะห์ด้วยระบบ AI Physician Assistant
          </p>
          <button onClick={() => setShowPatientSearch(true)} className="btn btn-primary" style={{ padding: "8px 24px" }}>
            เลือกคนไข้เพื่อเริ่มเซสชัน
          </button>
        </div>
      ) : (
        /* ── Main Workspace layout ─────────────────────────────── */
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>

          {/* 📋 Step 1: Clinical Intake & Tactical Reasoning (Full Width clinical card) */}
          <div style={{ ...card, background: "#FFFFFF", borderColor: "#E5E7EB", color: "#1F2937", padding: "20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: workflowPhase === 'intake' ? '#0A5C8E' : '#9CA3AF' }} />
                <span style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "0.5px", textTransform: "uppercase", color: "#4B5563" }}>
                  Phase 01: Clinical Intake Console
                </span>
              </div>
              {workflowPhase === 'analysis' && (
                <button
                  onClick={() => {
                    setWorkflowPhase('intake');
                    setIntakeSummary(null);
                    setTranscription("");
                  }}
                  style={{ background: "transparent", border: "none", color: "#0A5C8E", fontSize: "11px", display: "flex", alignItems: "center", gap: "4px", cursor: "pointer", fontWeight: 600 }}
                >
                  <RefreshCw size={12} /> New Patient Session
                </button>
              )}
            </div>

            {/* Main Display Area (Transcription or Summary) */}
            <div style={{
              background: "#F9FAFB",
              borderRadius: "12px",
              padding: "20px",
              minHeight: "120px",
              marginBottom: "16px",
              border: "1px solid #E5E7EB",
              display: "flex",
              flexDirection: "column",
              justifyContent: transcription || intakeSummary || isRecording || isProcessingIntake ? "flex-start" : "center",
              alignItems: transcription || intakeSummary || isRecording || isProcessingIntake ? "stretch" : "center"
            }}>
              {isProcessingIntake ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px", alignItems: "center", justifyContent: "center", padding: "24px 0" }}>
                  <div style={{ position: "relative", width: "52px", height: "52px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <div className="animate-spin" style={{
                      position: "absolute",
                      width: "100%",
                      height: "100%",
                      border: "3px solid rgba(10, 92, 142, 0.1)",
                      borderTop: "3px solid #0A5C8E",
                      borderRadius: "50%"
                    }} />
                    <Brain className="animate-pulse" size={22} style={{ color: "#0A5C8E" }} />
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <span style={{ fontSize: "13px", color: "#0A5C8E", fontWeight: 700, display: "block", letterSpacing: "0.5px" }}>
                      กำลังประมวลผลข้อมูล...
                    </span>
                    <span style={{ fontSize: "11px", color: "#6B7280", marginTop: "4px", display: "block" }}>
                      Gemini 2.5 Flash กำลังสแกนหาตัวชี้วัดและวิเคราะห์ SOAP Note
                    </span>
                  </div>
                </div>
              ) : isRecording ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "12px", alignItems: "center" }}>
                  <div style={{ display: "flex", gap: "6px", alignItems: "flex-end", height: "30px" }}>
                    {[1, 2, 3, 4, 5, 6, 7, 8].map(i => (
                      <div key={i} style={{ width: "4px", height: "12px", background: "#0A5C8E", animation: `wave 0.8s infinite ${i * 0.1}s`, borderRadius: "2px" }} />
                    ))}
                  </div>
                  <span style={{ fontSize: "12px", color: "#0A5C8E", fontWeight: 700, letterSpacing: "1px" }}>RECORDING ACTIVE...</span>
                </div>
              ) : intakeSummary ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "10px", paddingBottom: "12px", borderBottom: "1px solid #E5E7EB" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#0A5C8E" }}>
                      <CheckCircle size={18} style={{ color: "#059669" }} />
                      <span style={{ fontSize: "13px", fontWeight: 700, letterSpacing: "0.5px" }}>VERIFIED CLINICAL SOAP SUMMARY</span>
                    </div>
                    
                    {structuredSoap?.severity && (
                      <div style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                        padding: "4px 10px",
                        borderRadius: "12px",
                        fontSize: "11px",
                        fontWeight: 700,
                        textTransform: "uppercase",
                        letterSpacing: "0.5px",
                        background: structuredSoap.severity === "severe" ? "rgba(239, 68, 68, 0.08)" :
                                    structuredSoap.severity === "moderate" ? "rgba(245, 158, 11, 0.08)" : "rgba(16, 185, 129, 0.08)",
                        border: `1px solid ${structuredSoap.severity === "severe" ? "rgba(239, 68, 68, 0.2)" :
                                           structuredSoap.severity === "moderate" ? "rgba(245, 158, 11, 0.2)" : "rgba(16, 185, 129, 0.2)"}`,
                        color: structuredSoap.severity === "severe" ? "#DC2626" :
                               structuredSoap.severity === "moderate" ? "#D97706" : "#059669"
                      }}>
                        <span style={{
                          width: "6px",
                          height: "6px",
                          borderRadius: "50%",
                          background: structuredSoap.severity === "severe" ? "#EF4444" :
                                      structuredSoap.severity === "moderate" ? "#F59E0B" : "#10B981"
                        }} />
                        SEVERITY: {structuredSoap.severity}
                      </div>
                    )}
                  </div>

                  {/* Short Summary */}
                  <div style={{ background: "#EEF2F6", padding: "14px 18px", borderRadius: "8px", borderLeft: "4px solid #0A5C8E" }}>
                    <p style={{ fontSize: "13.5px", color: "#374151", margin: 0, lineHeight: 1.6, fontWeight: 500 }}>
                      {structuredSoap?.summary_short || intakeSummary}
                    </p>
                  </div>

                  {/* Key Symptoms */}
                  {structuredSoap?.key_symptoms && structuredSoap.key_symptoms.length > 0 && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                      {structuredSoap.key_symptoms.map((symptom: string, idx: number) => (
                        <span key={idx} style={{
                          fontSize: "11px",
                          background: "#EFF6FF",
                          color: "#1D4ED8",
                          border: "1px solid #BFDBFE",
                          padding: "3px 8px",
                          borderRadius: "6px",
                          fontWeight: 600
                        }}>
                          {symptom}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* SOAP Grid */}
                  {structuredSoap && (
                    <div style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                      gap: "14px",
                      marginTop: "8px"
                    }}>
                      {/* Subjective */}
                      <div style={{ background: "#EEF2FF", border: "1px solid #C7D2FE", borderRadius: "8px", padding: "12px" }}>
                        <span style={{ fontSize: "11px", fontWeight: 700, color: "#4338CA", display: "block", marginBottom: "6px", letterSpacing: "0.5px" }}>[S] SUBJECTIVE</span>
                        <p style={{ fontSize: "12.5px", color: "#374151", margin: 0, lineHeight: 1.5 }}>{structuredSoap.subjective || "-"}</p>
                      </div>

                      {/* Objective */}
                      <div style={{ background: "#ECFDF5", border: "1px solid #A7F3D0", borderRadius: "8px", padding: "12px" }}>
                        <span style={{ fontSize: "11px", fontWeight: 700, color: "#047857", display: "block", marginBottom: "6px", letterSpacing: "0.5px" }}>[O] OBJECTIVE</span>
                        <p style={{ fontSize: "12.5px", color: "#374151", margin: 0, lineHeight: 1.5 }}>{structuredSoap.objective || "-"}</p>
                      </div>

                      {/* Assessment */}
                      <div style={{ background: "#FFFBEB", border: "1px solid #FDE68A", borderRadius: "8px", padding: "12px" }}>
                        <span style={{ fontSize: "11px", fontWeight: 700, color: "#B45309", display: "block", marginBottom: "6px", letterSpacing: "0.5px" }}>[A] ASSESSMENT</span>
                        <p style={{ fontSize: "12.5px", color: "#374151", margin: 0, lineHeight: 1.5 }}>{structuredSoap.assessment || "-"}</p>
                      </div>

                      {/* Plan */}
                      <div style={{ background: "#FFF1F2", border: "1px solid #FECDD3", borderRadius: "8px", padding: "12px" }}>
                        <span style={{ fontSize: "11px", fontWeight: 700, color: "#BE123C", display: "block", marginBottom: "6px", letterSpacing: "0.5px" }}>[P] PLAN</span>
                        <p style={{ fontSize: "12.5px", color: "#374151", margin: 0, lineHeight: 1.5 }}>{structuredSoap.plan || "-"}</p>
                      </div>
                    </div>
                  )}
                </div>
              ) : transcription ? (
                <p style={{ fontSize: "14px", color: "#374151", margin: 0, lineHeight: 1.6, fontStyle: "italic" }}>"{transcription}"</p>
              ) : (
                <div style={{ textAlign: "center", color: "#6B7280" }}>
                  <Brain size={32} style={{ marginBottom: "12px", opacity: 0.5, color: "#0A5C8E" }} />
                  <p style={{ fontSize: "13px", margin: 0, fontWeight: 500 }}>พร้อมรับข้อมูลการซักประวัติ (เสียงซักถาม, ข้อความพิมพ์, หรือแนบไฟล์ผล Lab)</p>
                </div>
              )}
            </div>

            {/* File Queue chips - shown above bar when files are pending */}
            {intakeFiles.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "8px" }}>
                {intakeFiles.map((f, i) => (
                  <div key={i} style={{
                    display: "inline-flex", alignItems: "center", gap: "5px",
                    background: "#EEF2FF", border: "1px solid #C7D2FE",
                    borderRadius: "6px", padding: "3px 8px", fontSize: "11px", color: "#4338CA"
                  }}>
                    {f.type.startsWith("audio") ? "🎙️" : f.type.startsWith("image") ? "🖼️" : "📄"}
                    {f.name.length > 22 ? f.name.slice(0, 20) + "…" : f.name}
                    <button
                      onClick={() => setIntakeFiles(prev => prev.filter((_, idx) => idx !== i))}
                      style={{ background: "none", border: "none", cursor: "pointer", color: "#6366F1", fontSize: "13px", lineHeight: 1, padding: 0 }}
                    >×</button>
                  </div>
                ))}
                <span style={{ fontSize: "10.5px", color: "#6B7280", alignSelf: "center" }}>
                  {intakeFiles.length} ไฟล์พร้อมประมวลผล
                </span>
              </div>
            )}

            {/* Intake progress label */}
            {intakeFileProgress && (
              <div style={{ fontSize: "11.5px", color: "#0A5C8E", background: "#EEF2FF", borderRadius: "6px", padding: "5px 10px", marginBottom: "6px", fontWeight: 600 }}>
                {intakeFileProgress}
              </div>
            )}

            {/* Intake Tactical Command Bar */}
            <div style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              background: "#F3F4F6",
              padding: "8px 12px",
              borderRadius: "10px",
              border: "1px solid #E5E7EB"
            }}>
              {/* Actions */}
              <div style={{ display: "flex", gap: "4px" }}>
                {/* Multi-file input (ทุก type รวม): รูป + PDF + เสียง พร้อมกัน */}
                <input
                  type="file"
                  ref={multiFileInputRef}
                  multiple
                  accept="image/*,audio/*,.pdf,.doc,.docx,.txt"
                  style={{ display: "none" }}
                  onChange={(e) => handleAddFilesToQueue(e.target.files)}
                />
                {/* Legacy single file refs (kept for backward compat) */}
                <input type="file" ref={fileInputRef} style={{ display: "none" }}
                  onChange={(e) => handleAddFilesToQueue(e.target.files)} />
                <input type="file" accept="image/*" ref={imageInputRef} style={{ display: "none" }}
                  onChange={(e) => handleAddFilesToQueue(e.target.files)} />

                <button
                  onClick={toggleRecording}
                  style={{
                    width: "36px", height: "36px", borderRadius: "8px",
                    background: isRecording ? "#EF4444" : "transparent",
                    border: "none", color: isRecording ? "white" : "#4B5563",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    transition: "all 0.2s", cursor: "pointer"
                  }}
                  title="อัดเสียงซักประวัติ"
                >
                  {isRecording ? <StopCircle size={20} /> : <Mic size={20} />}
                </button>

                <button
                  onClick={() => multiFileInputRef.current?.click()}
                  style={{
                    width: "36px", height: "36px", borderRadius: "8px",
                    background: intakeFiles.length > 0 ? "#EEF2FF" : "transparent",
                    border: intakeFiles.length > 0 ? "1.5px solid #C7D2FE" : "none",
                    color: intakeFiles.length > 0 ? "#4338CA" : "#4B5563",
                    display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer",
                    position: "relative"
                  }}
                  title="แนบไฟล์ (รูป / PDF / เสียง)"
                >
                  <Paperclip size={20} />
                  {intakeFiles.length > 0 && (
                    <span style={{
                      position: "absolute", top: "-4px", right: "-4px",
                      background: "#4F46E5", color: "white",
                      borderRadius: "50%", fontSize: "9px", fontWeight: 700,
                      width: "14px", height: "14px",
                      display: "flex", alignItems: "center", justifyContent: "center"
                    }}>{intakeFiles.length}</span>
                  )}
                </button>
              </div>

              {/* Input */}
              <input
                type="text"
                placeholder={isRecording ? "กำลังรับเสียงคนไข้..." : "สรุปอาการ หรือพิมพ์คำสั่งซักประวัติที่นี่..."}
                disabled={isRecording || workflowPhase === 'analysis'}
                value={transcription}
                onChange={(e) => setTranscription(e.target.value)}
                style={{
                  flex: 1, background: "transparent", border: "none", color: "#1F2937",
                  fontSize: "13.5px", outline: "none", padding: "4px 8px"
                }}
              />

              {/* Submit/Next */}
              {!intakeSummary ? (
                <button
                  onClick={handleProcessAllFiles}
                  disabled={(!transcription.trim() && intakeFiles.length === 0) || isProcessingIntake}
                  className="btn btn-success"
                  style={{ borderRadius: "6px", padding: "6px 16px", fontSize: "12px", fontWeight: 600, whiteSpace: "nowrap" }}
                >
                  {isProcessingIntake
                    ? <Loader2 size={14} className="animate-spin" />
                    : (intakeFiles.length > 0 ? `ประมวลผล (${intakeFiles.length} ไฟล์${transcription.trim() ? "+ข้อความ" : ""})` : "ประมวลผล")
                  }
                </button>
              ) : (
                <div style={{ display: "flex", gap: "8px" }}>
                  <button
                    onClick={handleSaveIntake}
                    disabled={isSaving}
                    style={{ background: "#0A5C8E", border: "none", color: "white", fontSize: "12px", padding: "6px 12px", borderRadius: "6px", display: "flex", alignItems: "center", gap: "6px", cursor: "pointer" }}
                  >
                    {isSaving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                    บันทึกประวัติ
                  </button>
                  <button
                    onClick={() => setWorkflowPhase('analysis')}
                    className="btn btn-primary"
                    style={{ borderRadius: "6px", padding: "6px 16px", fontSize: "12px", fontWeight: 600, display: "flex", alignItems: "center", gap: "6px", cursor: "pointer" }}
                  >
                    ยืนยัน <ChevronRight size={14} />
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* ── Two-column layout for details ─────────────────────────────── */}
          <div style={{ display: "grid", gridTemplateColumns: "380px 1fr", gap: "24px", alignItems: "start" }}>

            {/* ══ LEFT: Patient info + HUD + Quick actions ═══ */}
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>

              {/* Patient info */}
              <div style={card}>
                <div style={{ display: "flex", alignItems: "center", gap: "14px", marginBottom: "20px" }}>
                  <div style={{
                    width: "52px", height: "52px", background: "#0A5C8E", color: "white",
                    borderRadius: "10px", display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: "22px", fontWeight: 600, flexShrink: 0,
                  }}>
                    {patientInfo?.name?.charAt(0)}
                  </div>
                  <div>
                    <div style={{ fontSize: "16px", fontWeight: 600, color: "#1F2937", marginBottom: "2px" }}>
                      {patientInfo?.name}
                    </div>
                    <div style={{ fontSize: "12px", color: "#6B7280" }}>HN: {patientInfo?.hn}</div>
                    <span style={{
                      display: "inline-block", marginTop: "6px",
                      background: "#ECFDF5", color: "#059669",
                      fontSize: "11px", fontWeight: 500,
                      padding: "2px 10px", borderRadius: "20px",
                    }}>
                      Intelligence Relay Active
                    </span>
                  </div>
                </div>

              </div>

              {/* Quick missions */}
              <div style={card}>
                <div style={sectionLabel}>Mission Control</div>
                <QuickActionMenu
                  patientId={selectedPatientId}
                  onActionSelect={handleQuickAction}
                />

                {/* 🆕 Advanced Actions */}
                <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "20px" }}>
                  <button
                    onClick={handleOpenDeepReportModal}
                    style={{
                      padding: "10px", borderRadius: "8px", border: "none", background: "#0A5C8E",
                      display: "flex", alignItems: "center", gap: "10px", fontSize: "13px", color: "white",
                      cursor: "pointer", transition: "all 0.2s", fontWeight: 600
                    }}
                    onMouseEnter={e => e.currentTarget.style.opacity = "0.9"}
                    onMouseLeave={e => e.currentTarget.style.opacity = "1"}
                  >
                    <FileText size={16} /> สร้างรายงานผู้ป่วยเชิงลึก
                  </button>
                  <button
                    onClick={fetchHistory}
                    style={{
                      padding: "10px", borderRadius: "8px", border: "1px solid #E5E7EB", background: "white",
                      display: "flex", alignItems: "center", gap: "10px", fontSize: "13px", color: "#4B5563",
                      cursor: "pointer", transition: "all 0.2s"
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = "#F9FAFB"}
                    onMouseLeave={e => e.currentTarget.style.background = "white"}
                  >
                    <History size={16} /> ประวัติการซักประวัติ
                  </button>
                  <button
                    onClick={() => setShowSendModal(true)}
                    style={{
                      padding: "10px", borderRadius: "8px", border: "none", background: "#059669",
                      display: "flex", alignItems: "center", gap: "10px", fontSize: "13px", color: "white",
                      cursor: "pointer", transition: "all 0.2s"
                    }}
                    onMouseEnter={e => e.currentTarget.style.opacity = "0.9"}
                    onMouseLeave={e => e.currentTarget.style.opacity = "1"}
                  >
                    <Share2 size={16} /> ส่งข้อมูลการรักษา
                  </button>
                </div>
              </div>
            </div>

            {/* ══ RIGHT: Multi-Step Clinical Flow ═══════════════════════ */}
            <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>

              {/* 🧠 Step 2: Neural Analysis Console */}
              <div style={{
              ...card,
              padding: 0,
              overflow: "hidden",
              display: "flex",
              flexDirection: "column",
              height: "500px",
              opacity: workflowPhase === 'analysis' ? 1 : 0.5,
              pointerEvents: workflowPhase === 'analysis' ? 'auto' : 'none',
              transition: "all 0.3s"
            }}>

              {/* Chat header */}
              <div style={{
                padding: "14px 20px", borderBottom: "1px solid #E5E7EB",
                display: "flex", alignItems: "center", justifyContent: "space-between",
                background: "#FFFFFF", flexShrink: 0,
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <div style={{ width: "10px", height: "10px", borderRadius: "50%", background: "#059669" }} />
                  <div>
                    <div style={{ fontSize: "14px", fontWeight: 500, color: "#1F2937" }}>Neural Analysis Console</div>
                    <div style={{ fontSize: "11px", color: "#6B7280" }}>Precision Reasoning Engine</div>
                  </div>
                </div>

                {activeMission && (
                  <span style={{
                    background: "#E8F0F5", color: "#0A5C8E",
                    fontSize: "11px", fontWeight: 600,
                    padding: "4px 12px", borderRadius: "20px", letterSpacing: "0.3px",
                  }}>
                    MISSION: {activeMission}
                  </span>
                )}
              </div>

              {/* Messages */}
              <div
                style={{ flex: 1, overflowY: "auto", padding: "20px", display: "flex", flexDirection: "column", gap: "16px", background: "#F9FAFB" }}
                className="custom-scrollbar"
              >
                {messages.length === 0 ? (
                  <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center" }}>
                    <Brain size={52} style={{ color: "#E5E7EB", marginBottom: "16px" }} />
                    <p style={{ fontSize: "13px", color: "#9CA3AF", margin: "0 0 6px" }}>รอคำสั่งวิเคราะห์จากคุณ</p>
                    <p style={{ fontSize: "12px", color: "#D1D5DB", margin: 0 }}>พิมพ์คำถาม หรือเลือก Mission จากด้านซ้าย</p>
                  </div>
                ) : (
                  messages.map((msg, idx) => {
                    const isUser = msg.role === "user";
                    // 🧹 Strip :::BIO_UPDATE::: JSON block before rendering to keep chat clean
                    const displayContent = !isUser
                      ? (msg.content || "").replace(/:::BIO_UPDATE:::[\s\S]*?(?::::|$)/g, "").trim()
                      : (msg.content || "");
                    const hasBioUpdate = !isUser && /:::BIO_UPDATE:::/.test(msg.content || "");
                    return (
                      <div key={idx} style={{ display: "flex", justifyContent: isUser ? "flex-end" : "flex-start" }}>
                        <div style={{
                          maxWidth: "78%",
                          padding: "12px 16px",
                          background: isUser ? "#0A5C8E" : "#FFFFFF",
                          color: isUser ? "#FFFFFF" : "#1F2937",
                          borderRadius: isUser ? "12px 12px 0 12px" : "12px 12px 12px 0",
                          border: isUser ? "none" : "1px solid #E5E7EB",
                          fontSize: "13px", lineHeight: 1.6,
                        }}>
                          <div style={{
                            fontSize: "10px", fontWeight: 600,
                            color: isUser ? "rgba(255,255,255,0.6)" : "#9CA3AF",
                            letterSpacing: "0.5px", textTransform: "uppercase", marginBottom: "6px",
                          }}>
                            {isUser ? "Clinical Inquiry" : "AI Analysis"}
                          </div>
                          <div style={{ whiteSpace: "pre-wrap" }}>{displayContent}</div>

                          {!isUser && hasBioUpdate && (
                            <div style={{ marginTop: "8px", display: "inline-flex", alignItems: "center", gap: "5px", background: "#ECFDF5", border: "1px solid #A7F3D0", borderRadius: "6px", padding: "3px 8px", fontSize: "10.5px", color: "#047857", fontWeight: 600 }}>
                              <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#10B981", display: "inline-block" }} />
                              อัปเดตกราฟชีวภาพ 39 แกนเรียบร้อยแล้ว
                            </div>
                          )}

                          {!isUser && (
                            <div style={{ marginTop: "12px", paddingTop: "8px", borderTop: "1px solid #F3F4F6", display: "flex", justifyContent: "flex-end" }}>
                              <button
                                onClick={() => handleSaveAnalysis(msg.content)}
                                style={{
                                  background: "transparent", border: "1px solid #E5E7EB", borderRadius: "4px",
                                  fontSize: "11px", color: "#6B7280", padding: "4px 10px", display: "flex", alignItems: "center", gap: "6px",
                                  cursor: "pointer"
                                }}
                              >
                                <Save size={12} /> บันทึกการรักษานี้
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <div style={{ padding: "16px 20px", borderTop: "1px solid #E5E7EB", background: "#FFFFFF", flexShrink: 0 }}>
                <div style={{ display: "flex", gap: "10px", marginBottom: "10px" }}>
                  <input
                    type="text"
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && handleAnalyze()}
                    disabled={isAnalyzing}
                    placeholder="พิมพ์คำถามทางคลินิก หรือพารามิเตอร์การวิเคราะห์…"
                    style={{
                      flex: 1, padding: "10px 16px",
                      border: "1px solid #E5E7EB", borderRadius: "6px",
                      background: "#F9FAFB", fontSize: "13px",
                      outline: "none", color: "#1F2937",
                      opacity: isAnalyzing ? 0.6 : 1,
                    }}
                  />
                  <button
                    onClick={handleAnalyze}
                    disabled={isAnalyzing || !query.trim()}
                    className="btn btn-primary"
                    style={{
                      padding: "10px 20px", display: "flex", alignItems: "center", justifyContent: "center",
                      opacity: isAnalyzing || !query.trim() ? 0.5 : 1,
                      cursor: isAnalyzing || !query.trim() ? "default" : "pointer",
                    }}
                  >
                    {isAnalyzing ? <Loader2 size={18} style={{ animation: "spin 0.8s linear infinite" }} /> : <Send size={18} />}
                  </button>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "11px", color: "#9CA3AF" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <ShieldCheck size={13} style={{ color: "#059669" }} />
                    End-to-End Encrypted
                  </div>
                  <div>Powered by V-Twin Engine</div>
                </div>
              </div>
            </div>

            {/* 🧬 SYSTEMIC BIOLOGICAL BURDEN Widget */}
            <div style={{ ...card, padding: 0, overflow: "hidden" }}>
              <div style={{
                padding: "14px 20px", borderBottom: "1px solid #E5E7EB",
                display: "flex", alignItems: "center", justifyContent: "space-between",
                background: "#FAFAFA"
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <Zap size={15} style={{ color: "#0A5C8E" }} />
                  <span style={{ fontSize: "11px", fontWeight: 700, color: "#4B5563", letterSpacing: "0.5px" }}>SYSTEMIC BIOLOGICAL BURDEN</span>
                </div>
                <button
                  onClick={() => {
                    setQuery("วิเคราะห์ภาระชีวภาพรวมของคนไข้รายนี้ตามกรอบ TSPI 39-Axis และประเมินระดับความรุนแรงของแต่ละแกนชีวภาพ");
                    setTimeout(() => handleAnalyze(), 100);
                  }}
                  disabled={isAnalyzing || !selectedPatientId}
                  className="btn btn-primary"
                  style={{
                    fontSize: "11px", padding: "5px 14px",
                    display: "flex", alignItems: "center", gap: "6px",
                    opacity: isAnalyzing || !selectedPatientId ? 0.5 : 1,
                  }}
                >
                  {isAnalyzing
                    ? <><Loader2 size={13} style={{ animation: "spin 0.8s linear infinite" }} /> กำลังประมวลผล…</>
                    : <><Zap size={13} /> ประมวลผลภาระชีวภาพ</>}
                </button>
              </div>

              <div style={{ padding: "20px" }}>
                {/* Score + Label */}
                <div style={{ display: "flex", alignItems: "baseline", gap: "10px", marginBottom: "12px" }}>
                  <span style={{ fontSize: "40px", fontWeight: 800, color: "#111827", lineHeight: 1 }}>
                    {burdenProgress}%
                  </span>
                  <span style={{
                    fontSize: "12px", fontWeight: 600,
                    color: burdenProgress > 70
                      ? "#EF4444"
                      : burdenProgress > 40
                        ? "#F59E0B" : "#10B981"
                  }}>
                    {burdenProgress > 70
                      ? "⚠️ CRITICAL RISK"
                      : burdenProgress > 40
                        ? "⚡ MODERATE BURDEN" : "✅ OPTIMAL STATE"}
                  </span>
                </div>

                {/* Progress Bar */}
                <div style={{ height: "10px", background: "#E5E7EB", borderRadius: "6px", overflow: "hidden", marginBottom: "12px" }}>
                  <div style={{
                    height: "100%",
                    width: `${burdenProgress}%`,
                    background: burdenProgress > 70
                      ? "linear-gradient(90deg, #EF4444, #DC2626)"
                      : burdenProgress > 40
                        ? "linear-gradient(90deg, #F59E0B, #D97706)"
                        : "linear-gradient(90deg, #10B981, #059669)",
                    borderRadius: "6px",
                    transition: "width 0.2s ease-out"
                  }} />
                </div>

                {/* Axis count info */}
                <div style={{ fontSize: "11px", color: "#9CA3AF", marginBottom: "20px" }}>
                  {axisData.length > 0
                    ? `คำนวณจาก ${axisData.filter(a => (a.severity || 0) > 0).length} แกนที่มีข้อมูล จากทั้งหมด ${axisData.length} แกน`
                    : "กดปุ่มประมวลผลเพื่อเริ่มการวิเคราะห์"}
                </div>

                {/* Biological Axes List (Detailed breakdown) */}
                <div style={{ borderTop: "1px solid #F3F4F6", paddingTop: "20px" }}>
                  <div style={{ fontSize: "12px", fontWeight: 700, color: "#1F2937", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
                    <Zap size={16} style={{ color: "#0A5C8E" }} />
                    DETAILED MECHANISTIC AXES (39-AXIS)
                  </div>
                  <div style={{ maxHeight: "500px", overflowY: "auto", paddingRight: "8px" }} className="custom-scrollbar">
                    <BiologicalHUD axes={axisData} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      )}

      {/* ── Context Inspector ───────────────────────────────── */}
      {selectedPatientId && (
        <div style={card}>
          <div style={sectionLabel}>Contextual Reasoning Inspector</div>
          <ContextInspector patientId={selectedPatientId} />
        </div>
      )}

      {/* ── Modals ────────────────────────────────────────── */}
      {showHistoryModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, backdropFilter: "blur(4px)" }}>
          <div style={{ ...card, width: "650px", maxHeight: "85vh", overflow: "hidden", position: "relative", display: "flex", flexDirection: "column", border: "1px solid #D1D5DB", boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px", borderBottom: "1px solid #E5E7EB", paddingBottom: "12px" }}>
              <h3 style={{ fontSize: "16px", fontWeight: 600, margin: 0, color: "#111827", display: "flex", alignItems: "center", gap: "8px" }}>
                <History size={18} style={{ color: "#0A5C8E" }} />
                ประวัติการซักประวัติและตรวจวิเคราะห์ทางชีวภาพ
              </h3>
              <button onClick={() => { setShowHistoryModal(false); setExpandedHistoryId(null); }} style={{ border: "none", background: "transparent", cursor: "pointer", color: "#9CA3AF" }}><X size={20} /></button>
            </div>
            <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: "14px", paddingRight: "4px" }} className="custom-scrollbar">
              {historyItems.length === 0 ? (
                <p style={{ textAlign: "center", color: "#9CA3AF", padding: "40px 0" }}>ไม่พบประวัติการซักประวัติ</p>
              ) : (
                historyItems.map((item, idx) => {
                  const isExpanded = expandedHistoryId === item.id;
                  return (
                    <div key={item.id || idx} style={{ padding: "16px", border: "1px solid #E5E7EB", borderRadius: "10px", background: "#FFFFFF", transition: "all 0.2s" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                        <div style={{ display: "flex", flexDirection: "column" }}>
                          <span style={{ fontSize: "13px", fontWeight: 600, color: "#111827" }}>{item.patientName || "ไม่ทราบชื่อคนไข้"}</span>
                          <span style={{ fontSize: "11px", color: "#6B7280" }}>{new Date(item.timestamp).toLocaleString("th-TH")}</span>
                        </div>
                        <button
                          onClick={() => setExpandedHistoryId(isExpanded ? null : item.id)}
                          style={{
                            display: "flex", alignItems: "center", gap: "6px",
                            background: isExpanded ? "#EFF6FF" : "#F3F4F6",
                            color: isExpanded ? "#0A5C8E" : "#4B5563",
                            border: "none", padding: "6px 12px", borderRadius: "6px",
                            fontSize: "12px", fontWeight: 500, cursor: "pointer",
                            transition: "all 0.2s"
                          }}
                        >
                          <Eye size={14} />
                          {isExpanded ? "ย่อข้อมูล" : "ดูแบบละเอียด"}
                        </button>
                      </div>

                      {/* Summary */}
                      <div style={{ fontSize: "13px", color: "#374151", lineHeight: 1.6 }}>{item.summary}</div>

                      {/* Expandable SOAP detailed grid */}
                      {isExpanded && (
                        <div style={{ borderTop: "1px dashed #E5E7EB", paddingTop: "14px", marginTop: "12px", display: "flex", flexDirection: "column", gap: "12px" }}>
                          {item.structuredSoap ? (
                            <>
                              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }} className="ai-grid">
                                <div style={{ background: "#F0F9FF", borderLeft: "4px solid #0EA5E9", padding: "10px 12px", borderRadius: "6px" }}>
                                  <div style={{ fontSize: "11px", fontWeight: 700, color: "#0369A1", textTransform: "uppercase", marginBottom: "4px" }}>Subjective (S)</div>
                                  <div style={{ fontSize: "12px", color: "#0C4A6E", lineHeight: 1.5 }}>{item.structuredSoap.subjective || "-"}</div>
                                </div>
                                <div style={{ background: "#F0FDF4", borderLeft: "4px solid #22C55E", padding: "10px 12px", borderRadius: "6px" }}>
                                  <div style={{ fontSize: "11px", fontWeight: 700, color: "#15803D", textTransform: "uppercase", marginBottom: "4px" }}>Objective (O)</div>
                                  <div style={{ fontSize: "12px", color: "#14532D", lineHeight: 1.5 }}>{item.structuredSoap.objective || "-"}</div>
                                </div>
                                <div style={{ background: "#FAF5FF", borderLeft: "4px solid #A855F7", padding: "10px 12px", borderRadius: "6px" }}>
                                  <div style={{ fontSize: "11px", fontWeight: 700, color: "#7E22CE", textTransform: "uppercase", marginBottom: "4px" }}>Assessment (A)</div>
                                  <div style={{ fontSize: "12px", color: "#581C87", lineHeight: 1.5 }}>{item.structuredSoap.assessment || "-"}</div>
                                </div>
                                <div style={{ background: "#F0FDFA", borderLeft: "4px solid #14B8A6", padding: "10px 12px", borderRadius: "6px" }}>
                                  <div style={{ fontSize: "11px", fontWeight: 700, color: "#0F766E", textTransform: "uppercase", marginBottom: "4px" }}>Plan (P)</div>
                                  <div style={{ fontSize: "12px", color: "#115E59", lineHeight: 1.5 }}>{item.structuredSoap.plan || "-"}</div>
                                </div>
                              </div>

                              {item.structuredSoap.key_symptoms && item.structuredSoap.key_symptoms.length > 0 && (
                                <div>
                                  <div style={{ fontSize: "11px", fontWeight: 600, color: "#4B5563", marginBottom: "6px" }}>อาการสำคัญ (Key Symptoms):</div>
                                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                                    {item.structuredSoap.key_symptoms.map((sym: string, sIdx: number) => (
                                      <span key={sIdx} style={{ fontSize: "11px", background: "#F3F4F6", color: "#374151", padding: "4px 8px", borderRadius: "12px", border: "1px solid #E5E7EB" }}>{sym}</span>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </>
                          ) : (
                            <div style={{ fontSize: "12px", color: "#6B7280", fontStyle: "italic" }}>ไม่มีข้อมูล SOAP Note แบบโครงสร้าง</div>
                          )}

                          {item.rawTranscription && (
                            <div style={{ background: "#F9FAFB", padding: "10px 12px", borderRadius: "6px", border: "1px solid #E5E7EB" }}>
                              <div style={{ fontSize: "11px", fontWeight: 600, color: "#4B5563", marginBottom: "4px" }}>บันทึกเสียงดิบ/ข้อความนำเข้า:</div>
                              <div style={{ fontSize: "12px", color: "#4B5563", lineHeight: 1.5, fontStyle: "italic" }}>{item.rawTranscription}</div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}

      {showSendModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, backdropFilter: "blur(4px)" }}>
          <div style={{ ...card, width: "420px", textAlign: "center", padding: "30px", border: "1px solid #E5E7EB", boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1)" }}>
            <div style={{ width: "50px", height: "50px", background: "#ECFDF5", color: "#059669", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 20px" }}>
              <Share2 size={24} />
            </div>
            <h3 style={{ fontSize: "18px", fontWeight: 600, marginBottom: "12px", color: "#111827" }}>ส่งแผนการรักษาเข้าระบบ</h3>
            <p style={{ fontSize: "14px", color: "#6B7280", marginBottom: "24px", lineHeight: 1.5 }}>
              คุณต้องการบันทึกแผนการรักษานี้ลงในฐานข้อมูลหลัก หรือส่งต่อให้คนไข้ผ่านทาง Patient Portal?
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <button
                onClick={async () => {
                  if (!selectedPatientId) return;
                  setIsSaving(true);
                  try {
                    const latestMsg = messages.filter(m => m.role === "assistant").pop();
                    const cleanContent = latestMsg?.content
                      ? latestMsg.content.replace(/:::BIO_UPDATE:::[\s\S]*?(?::::|$)/g, "").trim()
                      : "";
                    await saveClinicalAnalysis(selectedPatientId, {
                      patientName: (patientInfo?.fname && patientInfo?.lname) ? `${patientInfo.fname} ${patientInfo.lname}` : (patientInfo?.name || "ไม่ระบุชื่อ"),
                      content: cleanContent || intakeSummary || "",
                      summary: intakeSummary || "",
                      mission: activeMission,
                      type: "emr_record",
                      visibleToPatient: true,
                      source: "ai_physician",
                    });
                    
                    Swal.fire({
                      title: "บันทึกเวชระเบียนสำเร็จ",
                      text: "บันทึกข้อมูลและวิเคราะห์ SOAP ลงในเวชระเบียนกลางเรียบร้อยแล้ว",
                      icon: "success",
                      confirmButtonColor: "#0A5C8E"
                    });
                    setShowSendModal(false);
                  } catch (err: any) {
                    console.error("🔥 Save EMR error:", err);
                    Swal.fire({
                      title: "เกิดข้อผิดพลาด",
                      text: `บันทึกไม่สำเร็จ: ${err.message}`,
                      icon: "error",
                      confirmButtonColor: "#0A5C8E"
                    });
                  } finally {
                    setIsSaving(false);
                  }
                }}
                disabled={isSaving}
                style={{
                  padding: "12px", borderRadius: "8px", border: "1px solid #D1D5DB", background: "white",
                  fontSize: "14px", fontWeight: 500, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px",
                  opacity: isSaving ? 0.6 : 1, color: "#374151"
                }}
              >
                {isSaving ? <Loader2 size={16} style={{ animation: "spin 0.8s linear infinite" }} /> : <Save size={16} />}
                {isSaving ? "กำลังบันทึก..." : "บันทึกเก็บในเวชระเบียน"}
              </button>
              <button
                onClick={async () => {
                  if (!selectedPatientId) return;
                  setIsSaving(true);
                  try {
                    const latestMsg = messages.filter(m => m.role === "assistant").pop();
                    const cleanContent = latestMsg?.content
                      ? latestMsg.content.replace(/:::BIO_UPDATE:::[\s\S]*?(?::::|$)/g, "").trim()
                      : "";
                    await saveClinicalAnalysis(selectedPatientId, {
                      patientName: (patientInfo?.fname && patientInfo?.lname) ? `${patientInfo.fname} ${patientInfo.lname}` : (patientInfo?.name || "ไม่ระบุชื่อ"),
                      content: cleanContent || intakeSummary || "",
                      summary: intakeSummary || "",
                      mission: activeMission,
                      type: "portal_message",
                      visibleToPatient: true,
                      source: "ai_physician",
                      sentToPatient: true,
                    });

                    Swal.fire({
                      title: "ส่งข้อมูลสำเร็จ",
                      text: "แผนการรักษานี้ถูกส่งต่อไปยัง Patient Portal ของคนไข้แล้ว",
                      icon: "success",
                      confirmButtonColor: "#0A5C8E"
                    });
                    setShowSendModal(false);
                  } catch (err: any) {
                    console.error("🔥 Portal Send error:", err);
                    Swal.fire({
                      title: "เกิดข้อผิดพลาด",
                      text: `ส่งไม่สำเร็จ: ${err.message}`,
                      icon: "error",
                      confirmButtonColor: "#0A5C8E"
                    });
                  } finally {
                    setIsSaving(false);
                  }
                }}
                disabled={isSaving}
                style={{
                  padding: "12px", borderRadius: "8px", border: "none", background: isSaving ? "#6B7280" : "#0A5C8E", color: "white",
                  fontSize: "14px", fontWeight: 500, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px",
                  opacity: isSaving ? 0.6 : 1,
                }}
              >
                {isSaving ? <Loader2 size={16} style={{ animation: "spin 0.8s linear infinite" }} /> : <Send size={16} />}
                {isSaving ? "กำลังส่ง..." : "ส่งให้คนไข้ (Patient Portal)"}
              </button>
              <button onClick={() => setShowSendModal(false)} style={{ marginTop: "10px", color: "#9CA3AF", background: "transparent", border: "none", cursor: "pointer", fontSize: "13px" }}>ไว้ทีหลัง</button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @media (max-width: 1024px) {
          .ai-grid { grid-template-columns: 1fr !important; }
        }
        .custom-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #E5E7EB; border-radius: 10px; }
      `}</style>
    </div>
  );
}