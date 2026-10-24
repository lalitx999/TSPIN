"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  Brain, Users, Loader2, FileText, Download, Trash2,
  History, ArrowLeft, Sparkles, ChevronRight, Copy, Check
} from "lucide-react";
import Swal from "sweetalert2";

import {
  saveGeneratedReport,
  getGeneratedReports,
  deleteGeneratedReport,
  approveGeneratedReport,
  getDoctorProfile,
  getPatient,
  getAllPatients
} from "@/utils/api/services";

// ── Style helpers ────────────────────────────────────────────────
const card: React.CSSProperties = {
  background: "#FFFFFF",
  border: "1px solid #E5E7EB",
  borderRadius: "12px",
  padding: "24px",
  boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.02)",
};

const sectionLabel: React.CSSProperties = {
  fontSize: "11px",
  fontWeight: 600,
  color: "#4F46E5",
  letterSpacing: "0.5px",
  textTransform: "uppercase",
  marginBottom: "12px",
};

export default function PrecisionReportPage() {
  return (
    <Suspense fallback={
      <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ textAlign: "center" }}>
          <Loader2 size={40} className="animate-spin" style={{ color: "#0A5C8E", margin: "0 auto 16px" }} />
          <p style={{ fontSize: "14px", color: "#6B7280" }}>กำลังดาวน์โหลดข้อมูลระบบจัดทำรายงาน…</p>
        </div>
      </div>
    }>
      <PrecisionReportContent />
    </Suspense>
  );
}

function PrecisionReportContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const urlPatientId = searchParams.get("patientId");

  const [patients, setPatients] = useState<any[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string>("");
  const [patientInfo, setPatientInfo] = useState<any>(null);

  // ── Config Inputs ───────────────────────────────────────────
  const [reportInputs, setReportInputs] = useState({
    symptoms: "",
    history: "",
    reportType: "physician" as "physician" | "patient" | "multi-omics",
    fbs: "",
    hba1c: "",
    doppler: "",
    otherLabs: ""
  });

  // ── Engine / Progress States ────────────────────────────────
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [generationStepText, setGenerationStepText] = useState("");
  const [activeGeneratedReport, setActiveGeneratedReport] = useState<any>(null);
  const [generatedReportHistory, setGeneratedReportHistory] = useState<any[]>([]);
  const [selectedHistoryReport, setSelectedHistoryReport] = useState<any>(null);
  const [activeReportChapterIdx, setActiveReportChapterIdx] = useState<number>(0);
  const [isCopied, setIsCopied] = useState(false);

  // ── Load Patient list ───────────────────────────────────────
  useEffect(() => {
    const loadData = async () => {
      try {
        const list = await getAllPatients();
        setPatients(list || []);

        // If patient ID is in URL, auto-select it
        if (urlPatientId) {
          setSelectedPatientId(urlPatientId);
        } else if (list && list.length > 0) {
          setSelectedPatientId(list[0].id);
        }
      } catch (err) {
        console.error("Failed to load patients for report page:", err);
      }
    };
    loadData();
  }, [urlPatientId]);

  // ── Load patient data when selected patient changes ─────────
  useEffect(() => {
    if (!selectedPatientId) return;

    const fetchPatientData = async () => {
      try {
        const info = await getPatient(selectedPatientId);
        setPatientInfo(info);

        // Prepopulate form
        const symptoms = info.symptoms || "";
        const history = info.history || info.medicalHistory || info.caseSummary || "";
        const rawLabs = info.labs || info.lab_results || [];

        let fbs = "";
        let hba1c = "";
        let doppler = "";
        let otherLabsParts: string[] = [];

        if (Array.isArray(rawLabs)) {
          rawLabs.forEach((l: any) => {
            const name = (l.test_name || l.name || l.parameter || "").toLowerCase();
            const val = l.result_value ?? l.value ?? l.result ?? "";
            const unit = l.unit || "";

            if (name.includes("fbs") || name.includes("fasting blood sugar")) {
              fbs = String(val);
            } else if (name.includes("hba1c") || name.includes("hemoglobin")) {
              hba1c = String(val);
            } else if (name.includes("doppler")) {
              doppler = String(val);
            } else if (name) {
              otherLabsParts.push(`${l.test_name || l.name}: ${val} ${unit}`);
            }
          });
        } else if (rawLabs && typeof rawLabs === "object") {
          fbs = rawLabs.fbs || rawLabs.FBS || "";
          hba1c = rawLabs.hba1c || rawLabs.HbA1c || "";
          doppler = rawLabs.doppler || rawLabs.Doppler || "";
          Object.entries(rawLabs).forEach(([k, v]) => {
            if (!["fbs", "FBS", "hba1c", "HbA1c", "doppler", "Doppler"].includes(k)) {
              otherLabsParts.push(`${k}: ${v}`);
            }
          });
        }

        setReportInputs({
          symptoms,
          history,
          reportType: "physician",
          fbs,
          hba1c,
          doppler,
          otherLabs: otherLabsParts.join("\n")
        });

        // Load report history
        const reports = await getGeneratedReports(selectedPatientId);
        setGeneratedReportHistory(reports || []);
        setActiveGeneratedReport(null);
        setSelectedHistoryReport(null);
      } catch (err) {
        console.error("Failed to load patient detail for report generator:", err);
      }
    };

    fetchPatientData();
  }, [selectedPatientId]);

  // ── Simulator progress hook ─────────────────────────────────
  const startProgressSimulation = (type: "physician" | "patient" | "multi-omics") => {
    setGenerationProgress(0);
    const steps = {
      physician: [
        "กำลังดึงข้อมูลแกนชีวภาพ (39 Mechanistic Axes) จากฐานข้อมูล EMR...",
        "ดึงข้อมูลเวชระเบียนประวัติการรักษาและอาการสำคัญเสร็จสิ้น...",
        "กำลังสังเคราะห์ข้อมูลร่วมกับ Knowledge Base ของหน่วยงาน TSPI...",
        "ประมวลผลบทที่ 1: ประเมินโครงข่ายระบบควบคุมความดันและแกนเมตาบอลิซึม...",
        "ประมวลผลบทที่ 2: วิเคราะห์การทำงานและการล้างสารพิษในตับ/ไต...",
        "ประมวลผลบทที่ 3: ตรวจสอบความยืดหยุ่นของระบบทางเดินอาหารและจุลชีพ...",
        "ประมวลผลบทที่ 4: วิเคราะห์ดัชนีชี้วัด Genomic Stability...",
        "ประมวลผลบทที่ 5: จัดลำดับการคืนสภาพตามระบบ 9-Step Ladder...",
        "ประมวลผลบทที่ 6: สร้างคำแนะนำการรักษาและสารต้านอนุมูลอิสระ...",
        "กำลังประกอบร่างเล่มรายงานแพทย์ (Physician Edition) ภาษาการแพทย์...",
        "กำลังเขียนตาราง 10 โดเมนและสรุปอาการลง EMR...",
        "ขั้นตอนสุดท้าย: ตรวจสอบและลงลายมือชื่อระบบรักษาความปลอดภัยดิจิทัล..."
      ],
      patient: [
        "กำลังดึงข้อมูลเวชระเบียนและผลแล็บคนไข้...",
        "ถอดความหมายทางการแพทย์เป็นภาษาที่คนไข้เข้าใจง่าย...",
        "ประมวลผลบทที่ 1: สุขภาพระบบพลังงานและการใช้น้ำตาลในร่างกาย...",
        "ประมวลผลบทที่ 2: ระบบล้างสารพิษและสุขภาพลำไส้องค์รวม...",
        "ประมวลผลบทที่ 3: สุขภาพหัวใจและระบบการไหลเวียนเลือด...",
        "ประมวลผลบทที่ 4: ระบบประสาทและการจัดการความเครียด/การนอนหลับ...",
        "ประมวลผลบทที่ 5: โครงข่ายกล้ามเนื้อและระบบกระดูก...",
        "กำลังร่างตารางประเมินสุขภาพ 6 มิติ (0-100)...",
        "จัดเตรียมข้อปฏิบัติการปรับรูปแบบการดำเนินชีวิต (Lifestyle Modification)...",
        "ขั้นตอนสุดท้าย: สรุปรายงานสำหรับคนไข้ (Patient Edition) พร้อมพิมพ์..."
      ],
      "multi-omics": [
        "ค้นหาชุดข้อมูล Omics ของผู้ป่วย: Genomics, Transcriptomics, Proteomics...",
        "กำลังเชื่อมต่อข้อมูลหลายชั้นเพื่อการวิเคราะห์บูรณาการระดับโครงข่าย...",
        "ประมวลผลบทที่ 1: วิเคราะห์ Single Nucleotide Polymorphism (SNPs) เสริมภูมิต้านทาน...",
        "ประมวลผลบทที่ 2: ประเมินความหลากหลายของจุลชีพ (Microbiome Alpha Diversity)...",
        "ประมวลผลบทที่ 3: แปลผลสารเมตาบอไลต์และเส้นทางพลังงานของไมโตคอนเดรีย...",
        "วิเคราะห์การสะสมทางระบบและภาระสารพิษชีวภาพ (Systemic Toxic Burden)...",
        "ประมวลผลบทที่ 4: สร้างสัดส่วนสารต้านอนุมูลอิสระและการกำจัดอนุมูลอิสระ...",
        "จับคู่ความจำเพาะของโมดูลสมุนไพร TSPI เข้ากับยีนและสารพฤกษเคมี...",
        "จัดลำดับความมั่นใจทางคลินิก (Evidence Confidence Matrix)...",
        "ขั้นตอนสุดท้าย: เรียบเรียงรายงาน Multi-Omics แบบสมบูรณ์..."
      ]
    }[type] || ["กำลังดำเนินการวิเคราะห์ชีววิทยาเชิงระบบ..."];

    let currentStep = 0;
    setGenerationStepText(steps[0]);

    const interval = setInterval(() => {
      currentStep++;
      if (currentStep < steps.length) {
        setGenerationStepText(steps[currentStep]);
        setGenerationProgress(Math.floor((currentStep / steps.length) * 95));
      } else {
        setGenerationProgress(prev => Math.min(prev + 1, 98));
      }
    }, 4500);

    return interval;
  };

  // ── Action: Generate ────────────────────────────────────────
  // ── Action: Generate ────────────────────────────────────────
  const handleGenerateReport = async () => {
    if (!selectedPatientId || !patientInfo) {
      Swal.fire({
        title: "ข้อผิดพลาด",
        text: "กรุณาเลือกคนไข้ก่อนสร้างรายงานครับ",
        icon: "warning",
        confirmButtonColor: "#0A5C8E"
      });
      return;
    }

    setIsGeneratingReport(true);
    setGenerationProgress(0);
    setGenerationStepText("กำลังเชื่อมต่อระบบ AI...");
    setActiveGeneratedReport(null);

    try {
      const labsPayload: Record<string, any> = {};
      if (reportInputs.fbs) labsPayload.fbs = reportInputs.fbs;
      if (reportInputs.hba1c) labsPayload.hba1c = reportInputs.hba1c;
      if (reportInputs.doppler) labsPayload.doppler = reportInputs.doppler;

      if (reportInputs.otherLabs.trim()) {
        reportInputs.otherLabs.split("\n").forEach(line => {
          const parts = line.split(":");
          if (parts.length >= 2) {
            labsPayload[parts[0].trim()] = parts.slice(1).join(":").trim();
          } else {
            labsPayload[line.trim()] = true;
          }
        });
      }

      const token = localStorage.getItem("doctor_access_token") || localStorage.getItem("patient_access_token");
      const response = await fetch("/api/ai/report", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { "Authorization": `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          patientId: selectedPatientId,
          patientData: {
            profile: patientInfo,
            labs: labsPayload,
            symptoms: reportInputs.symptoms,
            history: reportInputs.history,
            medications: null,
            genomics: patientInfo.genomics || {},
            microbiome: patientInfo.microbiome || {},
            proteomics: patientInfo.proteomics || {},
            biologicalScores: patientInfo.axes || {}
          },
          reportType: reportInputs.reportType
        })
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      const fullReport: Array<{ chapterTitle: string; content: string }> = [];

      let buffer = "";

      const processLine = async (line: string) => {
        if (!line.trim()) return;
        let data: any;
        try {
          data = JSON.parse(line);
        } catch (parseErr) {
          console.warn("Skipped unparsable stream line:", line);
          return;
        }

        if (data.type === "start") {
            setGenerationStepText(`กำลังเริ่มวิเคราะห์ระบบชีวภาพและสร้างรายงาน...`);
            setGenerationProgress(5);
          }

          if (data.type === "chapter_start") {
            setGenerationStepText(`กำลังวิเคราะห์: ${data.title}`);
            const progressPercentage = Math.min(10 + (fullReport.length * 15), 90);
            setGenerationProgress(progressPercentage);

            setActiveGeneratedReport((prev: { report: Array<{ chapterTitle: string; content: string }> } | null) => {
              const baseReport = prev || {
                id: "temp_generation",
                patientId: selectedPatientId,
                patientName: patientInfo.name || `${patientInfo.first_name || ""} ${patientInfo.last_name || ""}`.trim() || "Unknown Patient",
                patientHn: patientInfo.hn || selectedPatientId,
                reportType: reportInputs.reportType,
                inputsUsed: {
                  symptoms: reportInputs.symptoms,
                  history: reportInputs.history,
                  labResults: labsPayload
                },
                report: [],
                createdAt: new Date().toISOString()
              };
              return {
                ...baseReport,
                report: [...baseReport.report, { chapterTitle: data.title, content: "" }]
              };
            });

            setActiveReportChapterIdx(fullReport.length);
          }

          if (data.type === "content_chunk") {
            setActiveGeneratedReport((prev: { report: Array<{ chapterTitle: string; content: string }> } | null) => {
              if (!prev) return null;
              return {
                ...prev,
                report: prev.report.map((ch, idx) => {
                  if (idx === prev.report.length - 1) {
                    return { ...ch, content: ch.content + data.chunk };
                  }
                  return ch;
                })
              };
            });
          }

          if (data.type === "chapter_complete") {
            fullReport.push({
              chapterTitle: data.title,
              content: data.content
            });
          }

          if (data.type === "complete") {
            setGenerationProgress(100);
            setGenerationStepText("สร้างรายงานเสร็จสมบูรณ์!");

            const savedReportId = await saveGeneratedReport(
              selectedPatientId,
              patientInfo.name || `${patientInfo.first_name || ""} ${patientInfo.last_name || ""}`.trim() || "Unknown Patient",
              patientInfo.hn || selectedPatientId,
              reportInputs.reportType,
              {
                symptoms: reportInputs.symptoms,
                history: reportInputs.history,
                labResults: labsPayload
              },
              data.chapters || fullReport,
              data.reasoningLedger?.analysis_record_id ?? null
            );

            const finalizedReport = {
              id: savedReportId,
              patientId: selectedPatientId,
              patientName: patientInfo.name || `${patientInfo.first_name || ""} ${patientInfo.last_name || ""}`.trim(),
              patientHn: patientInfo.hn || selectedPatientId,
              reportType: reportInputs.reportType,
              inputsUsed: {
                symptoms: reportInputs.symptoms,
                history: reportInputs.history,
                labResults: labsPayload
              },
              report: data.chapters || fullReport,
              createdAt: new Date().toISOString()
            };

            setActiveGeneratedReport(finalizedReport);
            setActiveReportChapterIdx(0);

            const reports = await getGeneratedReports(selectedPatientId);
            setGeneratedReportHistory(reports || []);

            Swal.fire({
              title: "สร้างรายงานสำเร็จ!",
              text: `รายงาน ${fullReport.length} บท ถูกวิเคราะห์และบันทึกเรียบร้อย`,
              icon: "success",
              confirmButtonColor: "#0A5C8E"
            });
          }

        if (data.type === "error") {
          throw new Error(data.message || "เอนจิ้น AI ขัดข้องระหว่างประมวลผล");
        }
      };

      while (reader) {
        const { done, value } = await reader.read();

        if (value) {
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            await processLine(line);
          }
        }

        if (done) {
          buffer += decoder.decode();
          if (buffer.trim()) {
            await processLine(buffer);
          }
          break;
        }
      }
    } catch (err: any) {
      console.error("🔥 Error generating report:", err);
      Swal.fire({
        title: "เกิดข้อผิดพลาดในการวิเคราะห์",
        text: `ไม่สามารถออกรายงานได้: ${err.message || err}`,
        icon: "error",
        confirmButtonColor: "#0A5C8E"
      });
    } finally {
      setIsGeneratingReport(false);
    }
  };

  // ── Action: Delete ──────────────────────────────────────────
  const handleDeleteReport = async (reportId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const result = await Swal.fire({
      title: "ยืนยันการลบ",
      text: "คุณต้องการลบประวัติการสร้างรายงานนี้ออกจาก EMR หรือไม่? (การดำเนินการนี้ไม่สามารถย้อนกลับได้)",
      icon: "warning",
      showCancelButton: true,
      confirmButtonColor: "#DC2626",
      cancelButtonColor: "#6B7280",
      confirmButtonText: "ลบข้อมูล",
      cancelButtonText: "ยกเลิก"
    });

    if (result.isConfirmed) {
      try {
        await deleteGeneratedReport(reportId, selectedPatientId);

        // Reload report list
        const reports = await getGeneratedReports(selectedPatientId);
        setGeneratedReportHistory(reports || []);

        if (activeGeneratedReport?.id === reportId) {
          setActiveGeneratedReport(null);
        }
        if (selectedHistoryReport?.id === reportId) {
          setSelectedHistoryReport(null);
        }

        Swal.fire("ลบสำเร็จ", "ลบรายงานออกจากระบบแล้วครับ", "success");
      } catch (err: any) {
        Swal.fire("เกิดข้อผิดพลาด", `ไม่สามารถลบรายงานได้: ${err.message}`, "error");
      }
    }
  };

  // ─── Standard Medical Report Formatting & JSON Sanitizer ────────
  const cleanMarkdownContent = (content: string): string => {
    if (!content) return "";
    let trimmed = content.trim();

    // Remove markdown code blocks if the LLM wrapped the JSON in it
    if (trimmed.startsWith("```json")) {
      trimmed = trimmed.replace(/^```json\s*/, "").replace(/\s*```$/, "").trim();
    } else if (trimmed.startsWith("```")) {
      trimmed = trimmed.replace(/^```\s*/, "").replace(/\s*```$/, "").trim();
    }

    let finalContent = trimmed;

    // Check if it's a JSON string
    if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
      try {
        const parsed = JSON.parse(trimmed);

        // Case 1: Array of objects or strings
        if (Array.isArray(parsed)) {
          finalContent = parsed.map((item: any) => {
            if (typeof item === 'string') return item;
            if (typeof item === 'object' && item !== null) {
              return item.content || item.clinical_baseline_content || item.analysis_summary || JSON.stringify(item);
            }
            return String(item);
          }).join("\n\n");
        }
        // Case 2: Object
        else if (typeof parsed === 'object' && parsed !== null) {
          if (parsed.content && typeof parsed.content === 'string') {
            finalContent = parsed.content;
          } else {
            const keys = Object.keys(parsed);
            if (keys.length === 1 && Array.isArray(parsed[keys[0]])) {
              finalContent = parsed[keys[0]].join("\n\n");
            } else {
              let md = "";
              for (const [key, value] of Object.entries(parsed)) {
                if (key.toLowerCase() === 'title' || key.toLowerCase() === 'chapter') {
                  continue;
                }
                const formatKey = key
                  .split('_')
                  .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                  .join(' ');

                md += `**${formatKey.toUpperCase()}**\n\n`;
                if (Array.isArray(value)) {
                  md += value.map((val: any) => `- ${val}`).join('\n') + '\n\n';
                } else if (typeof value === 'object' && value !== null) {
                  md += JSON.stringify(value, null, 2) + '\n\n';
                } else {
                  md += `${value}\n\n`;
                }
              }
              finalContent = md.trim();
            }
          }
        }
      } catch (e) {
        console.warn("Graceful JSON parsing fallback in page.tsx:", e);
      }
    }

    // Double check if the nested content is still stringified JSON (recursive parse)
    if (finalContent !== trimmed && (finalContent.trim().startsWith("{") || finalContent.trim().startsWith("["))) {
      finalContent = cleanMarkdownContent(finalContent);
    }

    // Clean literal "\n" strings instead of actual newlines
    if (finalContent.includes("\\n")) {
      finalContent = finalContent.replace(/\\n/g, "\n");
    }
    if (finalContent.includes("\\\"")) {
      finalContent = finalContent.replace(/\\"/g, '"');
    }

    // 🩺 STANDARD MEDICAL FORMATTING: Strip '#' characters and convert to bold text headings
    const lines = finalContent.split("\n");
    const processedLines = lines.map(line => {
      const trimmedLine = line.trim();
      if (trimmedLine.startsWith("#")) {
        const match = trimmedLine.match(/^(#+)\s*(.*)$/);
        if (match) {
          const titleText = match[2].trim();
          return `**${titleText.toUpperCase()}**`;
        }
      }
      return line;
    });

    return processedLines.join("\n").trim();
  };

  // ── Action: Downloads ───────────────────────────────────────
  // ── Action: Exports & Printing ──────────────────────────────
  const handleDownloadPdf = async (reportObj: any) => {
    if (!reportObj) return;
    try {
      const token = localStorage.getItem("doctor_access_token") || localStorage.getItem("patient_access_token");
      const headers: Record<string, string> = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const url = `${apiBase}/api/ai/patients/${reportObj.patientId}/reports/${reportObj.id}/pdf/`;
      
      Swal.fire({
        title: "กำลังจัดเตรียมรายงาน PDF...",
        html: "ระบบกำลังจัดหน้าเล่มรายงานด้วย Weasyprint กรุณารอสักครู่...",
        allowOutsideClick: false,
        didOpen: () => {
          Swal.showLoading();
        }
      });
      
      const response = await fetch(url, { headers });
      if (!response.ok) {
        const errorText = await response.text();
        if (response.status === 403) {
          throw new Error("รายงานสำหรับผู้ป่วยยังไม่ได้รับการอนุมัติและเผยแพร่โดยแพทย์");
        }
        if (response.status === 409) {
          throw new Error("รายงานนี้ยังไม่มี Analysis Record ที่ผ่านเกณฑ์สำหรับสร้าง PDF");
        }
        throw new Error(errorText || `ไม่สามารถติดต่อเซิร์ฟเวอร์เพื่อเจน PDF ได้ (สถานะ ${response.status})`);
      }
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.setAttribute("download", `TSPI_Report_${reportObj.patientHn || reportObj.patientId}_${reportObj.id}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      
      Swal.close();
    } catch (error: any) {
      console.error("PDF generation failed:", error);
      Swal.fire({
        icon: "error",
        title: "ดาวน์โหลดไม่สำเร็จ",
        text: `ไม่สามารถเปิดรายงาน PDF: ${error.message || error}`
      });
    }
  };

  const handleOpenHTMLReport = (reportObj: any) => {
    if (!reportObj) return;
    const printWindow = window.open("", "_blank");
    if (!printWindow) {
      Swal.fire("แจ้งเตือน", "กรุณาเปิดสิทธิ์การเปิดหน้าต่างป๊อปอัปในเบราว์เซอร์ของคุณ", "warning");
      return;
    }

    const title = `TSPI Precision Report - ${reportObj.patientName} (${reportObj.patientHn})`;

    // Convert report chapters to HTML
    // NOTE (page-break fix): chapters now flow continuously instead of each
    // forcing a new page. Only the heading itself is protected from being
    // split across a page boundary (print-no-split), so a chapter title
    // never ends up alone at the bottom of a page.
    let chaptersHtml = "";
    reportObj.report.forEach((ch: any) => {
      // Basic markdown replacements to simple HTML elements
      let contentHtml = cleanMarkdownContent(ch.content)
        .replace(/\n\n/g, "<p style='margin-bottom: 16px; line-height: 1.8;'></p>")
        .replace(/\n/g, "<br/>")
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.*?)\*/g, "<em>$1</em>");

      chaptersHtml += `
        <div style="padding: 12mm 0; border-bottom: 1px solid #E5E7EB;">
          <h2 class="print-no-split" style="font-size: 22px; font-weight: 700; color: #0A5C8E; margin-bottom: 20px; border-bottom: 2px solid #0A5C8E; padding-bottom: 10px; text-transform: uppercase;">
            ${ch.chapterTitle.toUpperCase()}
          </h2>
          <div style="font-size: 14.5px; color: #374151; line-height: 1.8;">
            ${contentHtml}
          </div>
        </div>
      `;
    });

    let tocHtml = "";
    reportObj.report.forEach((ch: any, idx: number) => {
      tocHtml += `
        <div style="display: flex; justify-content: space-between; border-bottom: 1px dotted #D1D5DB; padding-bottom: 6px; margin-bottom: 12px; font-size: 14.5px;">
          <span style="color: #1F2937; font-weight: 500;">${ch.chapterTitle}</span>
          <span style="color: #6B7280;">บทที่ ${idx + 1}</span>
        </div>
      `;
    });

    const reportTypeLabel = reportObj.reportType === "physician" ? "Physician Edition" :
      reportObj.reportType === "patient" ? "Patient Edition" : "Multi-Omics Edition";

    const dateStr = new Date(reportObj.createdAt).toLocaleDateString("th-TH", { year: "numeric", month: "long", day: "numeric" });

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>${title}</title>
        <meta charset="utf-8">
        <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
          body {
            font-family: 'Sarabun', sans-serif;
            background-color: #F3F4F6;
            margin: 0;
            padding: 0;
          }
          .no-print-bar {
            background-color: #0A5C8E;
            color: white;
            padding: 16px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            z-index: 1000;
          }
          .print-btn {
            background-color: #10B981;
            color: white;
            border: none;
            padding: 10px 24px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s;
          }
          .print-btn:hover {
            background-color: #059669;
          }
          .report-container {
            max-width: 800px;
            margin: 40px auto;
            background-color: white;
            padding: 40px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.05);
            border-radius: 12px;
          }
          .print-page-break {
            page-break-before: always;
          }
          .print-no-split {
            page-break-inside: avoid;
            break-inside: avoid;
          }
          @media print {
            .no-print-bar {
              display: none !important;
            }
            html, body {
              height: auto !important;
              overflow: visible !important;
              background-color: white !important;
            }
            .report-container {
              box-shadow: none !important;
              margin: 0 !important;
              padding: 0 !important;
              max-width: 100% !important;
            }
            .print-page-break {
              page-break-before: always !important;
              break-before: page !important;
              padding-top: 15mm !important;
            }
            .print-no-split {
              page-break-inside: avoid !important;
              break-inside: avoid !important;
            }
          }
        </style>
      </head>
      <body>
        <div class="no-print-bar">
          <div style="font-weight: 700; font-size: 16px;">TSPI Clinic | Precision Medicine Report</div>
          <button class="print-btn" onclick="window.print()">พิมพ์รายงาน / Save PDF</button>
        </div>
        <div class="report-container">
          <!-- Cover Page -->
          <div style="min-height: 240mm; display: flex; flex-direction: column; justify-content: space-between; padding: 40mm 0 20mm 0; box-sizing: border-box;">
            <div style="text-align: center;">
              <div style="color: #0A5C8E; font-size: 42px; font-weight: 800; letter-spacing: 2px; margin-bottom: 8px;">TSPI CLINIC</div>
              <div style="color: #4B5563; font-size: 14px; font-weight: 600; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 50mm;">
                Systems Biology AI Expert
              </div>

              <h1 style="font-size: 30px; font-weight: 800; color: #111827; line-height: 1.4; margin: 0 0 16px 0;">
                Precision Biological Network Intelligence Report™
              </h1>
              <h3 style="font-size: 18px; font-weight: 700; color: #0A5C8E; text-transform: uppercase; letter-spacing: 1.5px; margin: 0;">
                ${reportTypeLabel}
              </h3>
            </div>

            <div style="border: 2px solid #0A5C8E; padding: 24px; border-radius: 8px; background: #FFFFFF; width: 100%; box-sizing: border-box; margin-top: auto;">
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; font-size: 15px;">
                <div>
                  <span style="color: #6B7280; display: block; margin-bottom: 4px; font-size: 13px;">Patient Name / ชื่อคนไข้</span>
                  <strong style="color: #111827; font-size: 17px;">${reportObj.patientName}</strong>
                </div>
                <div>
                  <span style="color: #6B7280; display: block; margin-bottom: 4px; font-size: 13px;">Hospital Number / HN</span>
                  <strong style="color: #111827; font-size: 17px;">${reportObj.patientHn}</strong>
                </div>
                <div>
                  <span style="color: #6B7280; display: block; margin-bottom: 4px; font-size: 13px;">Issue Date / วันที่ออกรายงาน</span>
                  <strong style="color: #111827;">${dateStr}</strong>
                </div>
                <div>
                  <span style="color: #6B7280; display: block; margin-bottom: 4px; font-size: 13px;">Physician / แพทย์ผู้ดูแล</span>
                  <strong style="color: ${reportObj.approvalStatus === "APPROVED" ? "#111827" : "#DC2626"};">${reportObj.approvalStatus === "APPROVED" ? `Reviewed & Certified by ${reportObj.approvedBy || "Physician"}` : "AI-GENERATED DRAFT — PENDING PHYSICIAN REVIEW"}</strong>
                </div>
              </div>
            </div>

            <div style="text-align: center; border-top: 1px solid #E5E7EB; padding-top: 24px; margin-top: 40px;">
              <p style="font-size: 11px; color: #9CA3AF; margin: 0; text-transform: uppercase; letter-spacing: 1px;">
                Strictly Confidential &middot; Medical Grade Data System
              </p>
            </div>
          </div>

          <!-- TOC Page -->
          <div class="print-page-break" style="padding: 20mm 0; min-height: 240mm; box-sizing: border-box;">
            <h2 style="font-size: 22px; font-weight: 800; color: #111827; margin-bottom: 30px; border-bottom: 2px solid #0A5C8E; padding-bottom: 12px;">
              สารบัญ (Table of Contents)
            </h2>
            <div style="margin-top: 20px;">
              ${tocHtml}
            </div>
          </div>

          <!-- Chapters: flow continuously, only the first chapter starts a new page after the TOC -->
          <div class="print-page-break">
            ${chaptersHtml}
          </div>
        </div>
      </body>
      </html>
    `);
    printWindow.document.close();
  };

  const handleCopyReportSummary = (reportObj: any) => {
    if (!reportObj) return;

    const reportTypeLabel = reportObj.reportType === "physician" ? "Physician Edition" :
      reportObj.reportType === "patient" ? "Patient Edition" : "Multi-Omics Edition";
    const dateStr = new Date(reportObj.createdAt).toLocaleString("th-TH");

    let text = `สรุปรายงานการรักษา TSPI Precision Medicine\n`;
    text += `คนไข้: ${reportObj.patientName} (HN: ${reportObj.patientHn})\n`;
    text += `ประเภทรายงาน: ${reportTypeLabel}\n`;
    text += `วันที่ออกรายงาน: ${dateStr}\n`;
    text += `===================================\n\n`;

    reportObj.report.slice(0, 3).forEach((ch: any, idx: number) => {
      // Get clean version of text
      const cleanContent = cleanMarkdownContent(ch.content)
        .replace(/[*#`_\-]/g, "") // remove formatting markdown
        .substring(0, 200); // Take first 200 characters of each chapter

      text += `บทที่ ${idx + 1}: ${ch.chapterTitle}\n`;
      text += `${cleanContent.trim()}...\n\n`;
    });

    text += `สามารถเข้าสู่ระบบผ่าน PWA App เพื่อดูรายงานการรักษาแบบสมบูรณ์และดาวน์โหลดผลวิเคราะห์เต็มรูปแบบได้ตลอดเวลา`;

    navigator.clipboard.writeText(text).then(() => {
      Swal.fire({
        toast: true,
        position: 'top-end',
        icon: 'success',
        title: 'คัดลอกสรุปรายงานลง Clipboard เรียบร้อยแล้วครับ',
        showConfirmButton: false,
        timer: 3000,
        timerProgressBar: true,
      });
    }).catch(err => {
      console.error("Failed to copy text: ", err);
      Swal.fire("ข้อผิดพลาด", "ไม่สามารถคัดลอกข้อความได้", "error");
    });
  };

  const handleApproveReport = async (reportObj: any) => {
    if (!reportObj || reportObj.approvalStatus === "APPROVED") return;

    const confirm = await Swal.fire({
      title: "ยืนยันการอนุมัติรายงาน",
      text: "รายงานฉบับนี้จะถูกทำเครื่องหมายว่าแพทย์ได้ตรวจสอบและรับรองแล้ว ยืนยันหรือไม่?",
      icon: "question",
      showCancelButton: true,
      confirmButtonText: "อนุมัติ",
      cancelButtonText: "ยกเลิก",
      confirmButtonColor: "#0A5C8E"
    });
    if (!confirm.isConfirmed) return;

    try {
      const profile = await getDoctorProfile();
      const approvedBy = profile ? `${profile.first_name || ""} ${profile.last_name || ""}`.trim() || "Physician" : "Physician";

      const updatedReport = await approveGeneratedReport(reportObj.patientId, reportObj.id, approvedBy);

      if (activeGeneratedReport?.id === reportObj.id) {
        setActiveGeneratedReport(updatedReport);
      }
      if (selectedHistoryReport?.id === reportObj.id) {
        setSelectedHistoryReport(updatedReport);
      }
      const refreshed = await getGeneratedReports(reportObj.patientId);
      setGeneratedReportHistory(refreshed || []);

      Swal.fire({
        title: "อนุมัติรายงานสำเร็จ",
        icon: "success",
        timer: 2000,
        showConfirmButton: false
      });
    } catch (e: any) {
      console.error("Failed to approve report:", e);
      Swal.fire("ข้อผิดพลาด", `ไม่สามารถอนุมัติรายงานได้: ${e.message || e}`, "error");
    }
  };

  // ── Simple Markdown Parser ──────────────────────────────────
  const parseMarkdownToReact = (mdContent: string) => {
    if (!mdContent) return null;
    const md = cleanMarkdownContent(mdContent);
    const lines = md.split("\n");
    const elements: React.ReactNode[] = [];

    let inList = false;
    let listItems: string[] = [];
    let inTable = false;
    let tableHeaders: string[] = [];
    let tableRows: string[][] = [];

    const flushList = (key: string) => {
      if (listItems.length > 0) {
        elements.push(
          <ul key={key} style={{ margin: "10px 0 16px 20px", paddingLeft: "10px", listStyleType: "disc" }}>
            {listItems.map((item, idx) => (
              <li key={idx} style={{ fontSize: "13px", lineHeight: "1.6", color: "#374151", marginBottom: "6px" }}>
                {parseInlineMarkdown(item)}
              </li>
            ))}
          </ul>
        );
        listItems = [];
      }
      inList = false;
    };

    const flushTable = (key: string) => {
      if (tableHeaders.length > 0 || tableRows.length > 0) {
        elements.push(
          <div key={key} style={{ overflowX: "auto", margin: "16px 0", border: "1px solid #E5E7EB", borderRadius: "8px" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12.5px", textAlign: "left" }}>
              <thead>
                <tr style={{ background: "#F3F4F6", borderBottom: "2px solid #E5E7EB" }}>
                  {tableHeaders.map((h, idx) => (
                    <th key={idx} style={{ padding: "10px 14px", fontWeight: 600, color: "#374151" }}>
                      {parseInlineMarkdown(h)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {tableRows.map((row, rIdx) => (
                  <tr key={rIdx} style={{ borderBottom: "1px solid #E5E7EB", background: rIdx % 2 === 0 ? "#FFFFFF" : "#F9FAFB" }}>
                    {row.map((cell, cIdx) => (
                      <td key={cIdx} style={{ padding: "10px 14px", color: "#4B5563" }}>
                        {parseInlineMarkdown(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        tableHeaders = [];
        tableRows = [];
      }
      inTable = false;
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      const uniqueKey = `md-${i}`;

      if (line.startsWith("|")) {
        flushList(uniqueKey + "-list-flush");

        const parts = line.split("|").map(p => p.trim()).filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);

        if (!inTable) {
          inTable = true;
          tableHeaders = parts;
        } else {
          const isSeparator = parts.every(p => p.replace(/[-:\s]/g, "") === "");
          if (!isSeparator) {
            tableRows.push(parts);
          }
        }
        continue;
      } else if (inTable) {
        flushTable(uniqueKey + "-table-flush");
      }

      if (line.startsWith("- ") || line.startsWith("* ")) {
        inList = true;
        listItems.push(line.substring(2));
        continue;
      } else if (inList) {
        flushList(uniqueKey + "-list-flush");
      }

      if (line.startsWith("### ")) {
        elements.push(
          <h4 key={uniqueKey} style={{ fontSize: "14px", fontWeight: 600, color: "#1F2937", margin: "20px 0 10px 0" }}>
            {parseInlineMarkdown(line.substring(4))}
          </h4>
        );
      } else if (line.startsWith("## ")) {
        elements.push(
          <h3 key={uniqueKey} style={{ fontSize: "16px", fontWeight: 600, color: "#0A5C8E", margin: "24px 0 12px 0", borderBottom: "1px solid #E5E7EB", paddingBottom: "6px" }}>
            {parseInlineMarkdown(line.substring(3))}
          </h3>
        );
      } else if (line.startsWith("# ")) {
        elements.push(
          <h2 key={uniqueKey} style={{ fontSize: "20px", fontWeight: 700, color: "#111827", margin: "28px 0 16px 0" }}>
            {parseInlineMarkdown(line.substring(2))}
          </h2>
        );
      } else if (line === "") {
        // empty line
      } else {
        elements.push(
          <p key={uniqueKey} style={{ fontSize: "13px", lineHeight: "1.6", color: "#374151", margin: "0 0 12px 0", textAlign: "justify" }}>
            {parseInlineMarkdown(line)}
          </p>
        );
      }
    }

    flushList("final-list-flush");
    flushTable("final-table-flush");

    return <div style={{ fontFamily: "'Inter', 'Sarabun', sans-serif" }}>{elements}</div>;
  };

  const parseInlineMarkdown = (text: string): React.ReactNode => {
    const boldRegex = /\*\*(.*?)\*\*/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = boldRegex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push(text.substring(lastIndex, match.index));
      }
      parts.push(<strong key={match.index} style={{ fontWeight: 600, color: "#111827" }}>{match[1]}</strong>);
      lastIndex = boldRegex.lastIndex;
    }

    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }

    return parts.length > 0 ? parts : text;
  };

  return (
    <div style={{ padding: "24px", maxWidth: "1600px", margin: "0 auto", height: "calc(100vh - 70px)", display: "flex", flexDirection: "column", overflow: "hidden" }}>

      {/* ── Page Header ── */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <button
            onClick={() => router.push(`/doctor/ai-physician?id=${selectedPatientId}`)}
            style={{ display: "flex", alignItems: "center", gap: "6px", background: "none", border: "none", color: "#6B7280", fontSize: "13px", cursor: "pointer", padding: 0, marginBottom: "8px" }}
          >
            <ArrowLeft size={14} /> กลับไปหน้าระบบซักประวัติ AI Physician
          </button>
          <h1 style={{ fontSize: "24px", fontWeight: 800, color: "#111827", margin: 0, display: "flex", alignItems: "center", gap: "10px" }}>
            <Brain size={28} style={{ color: "#0A5C8E" }} />
            TSPI Precision Clinical Report Engine
          </h1>
        </div>

        {/* Patient Selection Dropdown */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", background: "white", padding: "8px 16px", borderRadius: "8px", border: "1px solid #E5E7EB" }}>
          <Users size={16} style={{ color: "#6B7280" }} />
          <span style={{ fontSize: "13px", fontWeight: 600, color: "#374151" }}>เลือกคนไข้:</span>
          <select
            value={selectedPatientId}
            onChange={(e) => setSelectedPatientId(e.target.value)}
            style={{ border: "none", outline: "none", fontSize: "13.5px", fontWeight: 600, color: "#0A5C8E", cursor: "pointer", background: "transparent" }}
          >
            {patients.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name || `${p.first_name || ""} ${p.last_name || ""}`.trim()} ({p.hn || "No HN"})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* ── Main Content Area ── */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>

        {isGeneratingReport ? (
          /* ── Case 1: Processing screen ── */
          <div style={{ ...card, flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", background: "#FFFFFF", minHeight: "500px" }}>
            <div style={{ width: "80px", height: "80px", background: "#EEF2FF", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: "24px" }}>
              <Loader2 size={40} className="animate-spin" style={{ color: "#0A5C8E" }} />
            </div>
            <h4 style={{ fontSize: "20px", fontWeight: 700, color: "#1F2937", marginBottom: "8px" }}>
              กำลังคำนวณและจัดทำรายงานเครือข่ายชีวภาพ...
            </h4>
            <p style={{ fontSize: "14px", color: "#6B7280", marginBottom: "24px", textAlign: "center", maxWidth: "600px" }}>
              {generationStepText}
            </p>

            {/* Progress Bar */}
            <div style={{ width: "100%", maxWidth: "500px", height: "12px", background: "#E5E7EB", borderRadius: "6px", overflow: "hidden", marginBottom: "12px" }}>
              <div style={{ width: `${generationProgress}%`, height: "100%", background: "#0A5C8E", transition: "width 0.3s ease" }} />
            </div>
            <span style={{ fontSize: "15px", fontWeight: 700, color: "#0A5C8E" }}>
              {generationProgress}% สำเร็จ
            </span>
          </div>
        ) : (activeGeneratedReport || selectedHistoryReport) ? (
          /* ── Case 2: Report Output Viewer Screen ── */
          (() => {
            const currentReport = activeGeneratedReport || selectedHistoryReport;
            const activeChapter = currentReport.report[activeReportChapterIdx] || currentReport.report[0] || { chapterTitle: "บทนำ", content: "" };
            return (
              <div style={{ ...card, flex: 1, display: "flex", flexDirection: "column", padding: 0, overflow: "hidden" }}>

                {/* Top Action Bar */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 24px", borderBottom: "1px solid #E5E7EB", background: "#F3F4F6", flexShrink: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <span style={{ fontSize: "12px", fontWeight: 700, background: "#0A5C8E", color: "white", padding: "4px 10px", borderRadius: "4px" }}>
                      {currentReport.reportType.toUpperCase()} EDITION
                    </span>
                    <span style={{ fontSize: "13.5px", color: "#374151" }}>
                      คนไข้: <strong>{currentReport.patientName}</strong> (HN: {currentReport.patientHn})
                    </span>
                  </div>
                  <div style={{ display: "flex", gap: "8px" }}>
                    {currentReport.approvalStatus === "APPROVED" ? (
                      <span style={{ display: "flex", alignItems: "center", gap: "6px", padding: "8px 14px", borderRadius: "6px", fontSize: "12.5px", fontWeight: 600, color: "#059669", background: "#ECFDF5", border: "1px solid #A7F3D0" }}>
                        <Check size={14} /> อนุมัติแล้วโดย {currentReport.approvedBy}
                      </span>
                    ) : (
                      <button
                        onClick={() => handleApproveReport(currentReport)}
                        className="btn"
                        style={{ padding: "8px 16px", borderRadius: "6px", fontSize: "12.5px", fontWeight: 600, display: "flex", alignItems: "center", gap: "6px", cursor: "pointer", background: "#0A5C8E", color: "white", border: "none" }}
                      >
                        <Check size={14} /> อนุมัติรายงาน
                      </button>
                    )}
                    <button
                      onClick={() => handleDownloadPdf(currentReport)}
                      className="btn btn-success"
                      style={{ padding: "8px 16px", borderRadius: "6px", fontSize: "12.5px", fontWeight: 600, display: "flex", alignItems: "center", gap: "6px", cursor: "pointer" }}
                    >
                      <Download size={14} /> พิมพ์ / บันทึก PDF
                    </button>
                    <button
                      onClick={() => handleOpenHTMLReport(currentReport)}
                      style={{ background: "white", border: "1px solid #0A5C8E", color: "#0A5C8E", padding: "8px 14px", borderRadius: "6px", fontSize: "12.5px", fontWeight: 600, display: "flex", alignItems: "center", gap: "6px", cursor: "pointer" }}
                    >
                      <FileText size={14} /> เปิดตัวอย่าง HTML
                    </button>
                    <button
                      onClick={() => handleCopyReportSummary(currentReport)}
                      style={{ background: "white", border: "1px solid #6B7280", color: "#4B5563", padding: "8px 14px", borderRadius: "6px", fontSize: "12.5px", fontWeight: 600, display: "flex", alignItems: "center", gap: "6px", cursor: "pointer" }}
                    >
                      <Copy size={14} /> คัดลอกสรุป
                    </button>
                    <button
                      onClick={() => {
                        setActiveGeneratedReport(null);
                        setSelectedHistoryReport(null);
                        setActiveReportChapterIdx(0);
                      }}
                      style={{ background: "#6B7280", border: "none", color: "white", padding: "8px 14px", borderRadius: "6px", fontSize: "12.5px", fontWeight: 500, cursor: "pointer" }}
                    >
                      ย้อนกลับเครื่องมือสร้าง
                    </button>
                  </div>
                </div>

                {/* Main split display: left chapter menu, right content */}
                <div style={{ flex: 1, display: "flex", overflow: "hidden", height: "calc(100% - 60px)" }}>
                  {/* Chapters list (left) */}
                  <div style={{ width: "280px", borderRight: "1px solid #E5E7EB", background: "#F9FAFB", overflowY: "auto", padding: "16px" }} className="custom-scrollbar">
                    <span style={{ fontSize: "11px", fontWeight: 700, color: "#6B7280", display: "block", marginBottom: "12px", letterSpacing: "0.5px" }}>สารบัญรายงาน</span>
                    <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                      {currentReport.report.map((ch: any, idx: number) => {
                        const isActive = activeReportChapterIdx === idx;
                        return (
                          <button
                            key={idx}
                            onClick={() => setActiveReportChapterIdx(idx)}
                            style={{
                              width: "100%", textAlign: "left", padding: "10px 12px", borderRadius: "6px",
                              border: "none", background: isActive ? "#E8F0F5" : "transparent",
                              color: isActive ? "#0A5C8E" : "#374151", fontSize: "12.5px", fontWeight: isActive ? 600 : 500,
                              cursor: "pointer", transition: "all 0.15s", display: "flex", alignItems: "center", justifyContent: "space-between"
                            }}
                          >
                            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>
                              {ch.chapterTitle}
                            </span>
                            <ChevronRight size={14} style={{ opacity: isActive ? 1 : 0, color: "#0A5C8E" }} />
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Chapter Content display (right) */}
                  <div style={{ flex: 1, overflowY: "auto", padding: "32px 40px", background: "#FFFFFF" }} className="custom-scrollbar">
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px", borderBottom: "2px solid #E5E7EB", paddingBottom: "12px" }}>
                      <h2 style={{ fontSize: "20px", fontWeight: 700, color: "#111827", margin: 0 }}>
                        {activeChapter.chapterTitle}
                      </h2>
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(activeChapter.content);
                          setIsCopied(true);
                          setTimeout(() => setIsCopied(false), 2000);
                        }}
                        style={{ background: "#E8F0F5", border: "none", color: "#0A5C8E", padding: "6px 12px", borderRadius: "4px", fontSize: "12px", fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", gap: "6px" }}
                      >
                        {isCopied ? <Check size={13} /> : <Copy size={13} />}
                        {isCopied ? "คัดลอกแล้ว!" : "คัดลอกมาร์กดาวน์บทนี้"}
                      </button>
                    </div>

                    <div style={{ fontSize: "14px", lineHeight: "1.7", color: "#374151" }}>
                      {parseMarkdownToReact(activeChapter.content)}
                    </div>
                  </div>
                </div>

              </div>
            );
          })()
        ) : (
          /* ── Case 3: Config Form & History List Screen ── */
          <div style={{ flex: 1, display: "flex", gap: "24px" }}>

            <div style={{ ...card, flex: 1, display: "flex", flexDirection: "column", gap: "20px", minWidth: 0, overflowY: "auto" }} className="custom-scrollbar">
              <div>
                <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#111827", margin: "0 0 4px 0" }}>
                  ระบุพารามิเตอร์ของคนไข้ก่อนวิเคราะห์
                </h3>
                <p style={{ fontSize: "12px", color: "#6B7280", margin: 0 }}>
                  ข้อมูลจะถูกดึงจากเวชระเบียนของคนไข้ที่เลือก สามารถตรวจสอบและแก้ไขก่อนกดเจนรายงาน
                </p>
              </div>

              {/* Symptoms */}
              <div>
                <label style={{ fontSize: "12.5px", fontWeight: 600, color: "#374151", display: "block", marginBottom: "6px" }}>
                  อาการสำคัญและผลการซักประวัติ (Symptoms / SOAP Note)
                </label>
                <textarea
                  value={reportInputs.symptoms}
                  onChange={e => setReportInputs(prev => ({ ...prev, symptoms: e.target.value }))}
                  rows={4}
                  placeholder="รายละเอียดอาการสำคัญ..."
                  style={{ width: "100%", border: "1px solid #D1D5DB", borderRadius: "8px", padding: "12px", fontSize: "13px", outline: "none", color: "#1F2937", resize: "vertical", boxSizing: "border-box" }}
                />
              </div>

              {/* History */}
              <div>
                <label style={{ fontSize: "12.5px", fontWeight: 600, color: "#374151", display: "block", marginBottom: "6px" }}>
                  ประวัติทางการแพทย์และข้อมูลเชิงลึก (Clinical History)
                </label>
                <textarea
                  value={reportInputs.history}
                  onChange={e => setReportInputs(prev => ({ ...prev, history: e.target.value }))}
                  rows={3}
                  placeholder="ยาที่ใช้ โรคประจำตัว ประวัติครอบครัว..."
                  style={{ width: "100%", border: "1px solid #D1D5DB", borderRadius: "8px", padding: "12px", fontSize: "13px", outline: "none", color: "#1F2937", resize: "vertical", boxSizing: "border-box" }}
                />
              </div>

              {/* Labs Inputs */}
              <div>
                <span style={{ fontSize: "12.5px", fontWeight: 700, color: "#1F2937", display: "block", marginBottom: "12px" }}>
                  ข้อมูลผลการตรวจทางห้องปฏิบัติการ (Lab Results)
                </span>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "16px", marginBottom: "16px" }}>
                  <div>
                    <label style={{ fontSize: "11.5px", fontWeight: 600, color: "#4B5563", display: "block", marginBottom: "6px" }}>
                      FBS (mg/dL)
                    </label>
                    <input
                      type="text"
                      value={reportInputs.fbs}
                      onChange={e => setReportInputs(prev => ({ ...prev, fbs: e.target.value }))}
                      placeholder="เช่น 110"
                      style={{ width: "100%", border: "1px solid #D1D5DB", borderRadius: "8px", padding: "10px", fontSize: "13px", outline: "none", color: "#1F2937", boxSizing: "border-box" }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: "11.5px", fontWeight: 600, color: "#4B5563", display: "block", marginBottom: "6px" }}>
                      HbA1c (%)
                    </label>
                    <input
                      type="text"
                      value={reportInputs.hba1c}
                      onChange={e => setReportInputs(prev => ({ ...prev, hba1c: e.target.value }))}
                      placeholder="เช่น 6.2"
                      style={{ width: "100%", border: "1px solid #D1D5DB", borderRadius: "8px", padding: "10px", fontSize: "13px", outline: "none", color: "#1F2937", boxSizing: "border-box" }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: "11.5px", fontWeight: 600, color: "#4B5563", display: "block", marginBottom: "6px" }}>
                      Doppler Result
                    </label>
                    <input
                      type="text"
                      value={reportInputs.doppler}
                      onChange={e => setReportInputs(prev => ({ ...prev, doppler: e.target.value }))}
                      placeholder="เช่น normal, mild plaque"
                      style={{ width: "100%", border: "1px solid #D1D5DB", borderRadius: "8px", padding: "10px", fontSize: "13px", outline: "none", color: "#1F2937", boxSizing: "border-box" }}
                    />
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: "11.5px", fontWeight: 600, color: "#4B5563", display: "block", marginBottom: "6px" }}>
                    ผลแล็บอื่นๆ เพิ่มเติม (เขียนรูปแบบ Test: Value ทีละบรรทัด)
                  </label>
                  <textarea
                    value={reportInputs.otherLabs}
                    onChange={e => setReportInputs(prev => ({ ...prev, otherLabs: e.target.value }))}
                    rows={3}
                    placeholder="เช่น&#10;Cholesterol: 210 mg/dL&#10;Triglycerides: 150 mg/dL"
                    style={{ width: "100%", border: "1px solid #D1D5DB", borderRadius: "8px", padding: "12px", fontSize: "12px", fontFamily: "monospace", outline: "none", color: "#1F2937", resize: "vertical", boxSizing: "border-box" }}
                  />
                </div>
              </div>

              {/* Action area: selector and submit */}
              <div style={{ borderTop: "1px solid #E5E7EB", paddingTop: "20px", marginTop: "10px", display: "flex", flexDirection: "column", gap: "16px" }}>
                <div>
                  <span style={sectionLabel}>รูปแบบเล่มรายงาน Precision Medicine</span>
                  <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
                    {([
                      { val: "physician", label: "ฉบับแพทย์ (Physician)", sub: "10 บท + 5 Appendices" },
                      { val: "patient", label: "ฉบับคนไข้ (Patient)", sub: "10 บทเขียนอ่านเข้าใจง่าย" },
                      { val: "multi-omics", label: "Multi-Omics Edition", sub: "15 บทวิเคราะห์ยีน/สารพลังงาน" }
                    ] as const).map(({ val, label, sub }) => (
                      <button
                        key={val}
                        onClick={() => setReportInputs(prev => ({ ...prev, reportType: val }))}
                        style={{
                          flex: 1,
                          border: reportInputs.reportType === val ? "2px solid #0A5C8E" : "1px solid #D1D5DB",
                          padding: "12px 16px",
                          borderRadius: "10px",
                          fontSize: "12.5px",
                          fontWeight: 600,
                          background: reportInputs.reportType === val ? "#F0F7FB" : "white",
                          color: reportInputs.reportType === val ? "#0A5C8E" : "#4B5563",
                          cursor: "pointer",
                          display: "flex",
                          flexDirection: "column",
                          alignItems: "flex-start",
                          gap: "2px",
                          textAlign: "left",
                          transition: "all 0.15s"
                        }}
                      >
                        {label}
                        <span style={{ fontSize: "10px", fontWeight: 400, color: reportInputs.reportType === val ? "#3B82F6" : "#6B7280" }}>{sub}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <button
                  onClick={handleGenerateReport}
                  style={{
                    background: "#0A5C8E", color: "white", border: "none",
                    padding: "14px 28px", borderRadius: "8px", fontSize: "14px", fontWeight: 700,
                    cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "10px"
                  }}
                >
                  <Sparkles size={16} />
                  ประมวลผลระบบเพื่อสร้างรายงาน (ใช้เวลาวิเคราะห์ประมาณ 3-5 นาที)
                </button>
              </div>
            </div>

            {/* Right: Previous Reports History list */}
            <div style={{ ...card, width: "320px", display: "flex", flexDirection: "column", gap: "16px", flexShrink: 0 }}>
              <div>
                <span style={sectionLabel}>ประวัติรายงานใน EMR</span>
                <h4 style={{ fontSize: "14px", fontWeight: 700, color: "#111827", margin: "4px 0 0 0" }}>
                  เล่มรายงานคนไข้ก่อนหน้า
                </h4>
              </div>

              <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: "10px" }} className="custom-scrollbar">
                {generatedReportHistory.length === 0 ? (
                  <div style={{ textAlign: "center", padding: "40px 10px", color: "#9CA3AF", border: "1px dashed #E5E7EB", borderRadius: "8px" }}>
                    <History size={24} style={{ margin: "0 auto 10px", opacity: 0.5 }} />
                    <p style={{ fontSize: "12px", margin: 0 }}>ไม่มีประวัติการเจนรายงานสำหรับคนไข้รายนี้</p>
                  </div>
                ) : (
                  generatedReportHistory.map((hist) => (
                    <div
                      key={hist.id}
                      onClick={() => setSelectedHistoryReport(hist)}
                      style={{
                        padding: "14px", border: "1px solid #E5E7EB", borderRadius: "8px", background: "#F9FAFB",
                        cursor: "pointer", transition: "all 0.2s", position: "relative"
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = "#F3F4F6"}
                      onMouseLeave={e => e.currentTarget.style.background = "#F9FAFB"}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "4px" }}>
                        <span style={{ fontSize: "10.5px", fontWeight: 700, background: "#E8F0F5", color: "#0A5C8E", padding: "2px 6px", borderRadius: "4px" }}>
                          {hist.reportType?.toUpperCase() || "PHYSICIAN"}
                        </span>
                        <button
                          onClick={(e) => handleDeleteReport(hist.id, e)}
                          style={{ border: "none", background: "transparent", color: "#EF4444", cursor: "pointer", padding: "2px", display: "flex", alignItems: "center" }}
                          title="ลบรายงาน"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                      <div style={{ fontSize: "12.5px", fontWeight: 600, color: "#1F2937" }}>
                        รายงาน {hist.report?.length || 0} บทวิเคราะห์เชิงลึก
                      </div>
                      <div style={{ fontSize: "10.5px", color: "#9CA3AF", marginTop: "4px" }}>
                        {new Date(hist.createdAt).toLocaleString("th-TH")}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

          </div>
        )}

        {/* HIDDEN PRINT WRAPPER FOR PDF PRINT */}
        {(activeGeneratedReport || selectedHistoryReport) && (
          (() => {
            const currentReport = activeGeneratedReport || selectedHistoryReport;
            return (
              <div id="tspi-print-area" className="tspi-print-report" style={{ display: "none" }}>
                {/* Cover Page */}
                <div style={{ minHeight: "270mm", display: "flex", flexDirection: "column", justifyContent: "space-between", padding: "40mm 0 20mm 0", boxSizing: "border-box" }}>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ color: "#0A5C8E", fontSize: "36px", fontWeight: 800, letterSpacing: "2px", marginBottom: "8px" }}>TSPI</div>
                    <div style={{ color: "#4B5563", fontSize: "14px", fontWeight: 600, letterSpacing: "1px", textTransform: "uppercase", marginBottom: "60mm" }}>
                      Thai Systems Pharmacology Intelligence
                    </div>

                    <h1 style={{ fontSize: "28px", fontWeight: 700, color: "#111827", lineHeight: 1.4, margin: "0 0 10px 0" }}>
                      Precision Biological Network Intelligence Report™
                    </h1>
                    <h3 style={{ fontSize: "16px", fontWeight: 600, color: "#0A5C8E", textTransform: "uppercase", letterSpacing: "1px" }}>
                      {currentReport.reportType === "physician" ? "Physician Edition" :
                        currentReport.reportType === "patient" ? "Patient Edition" : "Multi-Omics Edition"}
                    </h3>
                  </div>

                  <div style={{ border: "2px solid #0A5C8E", padding: "20px 24px", borderRadius: "8px", background: "#FFFFFF", width: "100%", boxSizing: "border-box" }}>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", fontSize: "14px" }}>
                      <div>
                        <span style={{ color: "#6B7280", display: "block", marginBottom: "2px" }}>Patient Name / ชื่อคนไข้</span>
                        <strong style={{ color: "#111827", fontSize: "16px" }}>{currentReport.patientName}</strong>
                      </div>
                      <div>
                        <span style={{ color: "#6B7280", display: "block", marginBottom: "2px" }}>Hospital Number / HN</span>
                        <strong style={{ color: "#111827", fontSize: "16px" }}>{currentReport.patientHn}</strong>
                      </div>
                      <div>
                        <span style={{ color: "#6B7280", display: "block", marginBottom: "2px" }}>Issue Date / วันที่ออกรายงาน</span>
                        <strong style={{ color: "#111827" }}>
                          {new Date(currentReport.createdAt).toLocaleDateString("th-TH", { year: "numeric", month: "long", day: "numeric" })}
                        </strong>
                      </div>
                      <div>
                        <span style={{ color: "#6B7280", display: "block", marginBottom: "2px" }}>Physician / แพทย์ผู้ดูแล</span>
                        <strong style={{ color: currentReport.approvalStatus === "APPROVED" ? "#111827" : "#DC2626" }}>
                          {currentReport.approvalStatus === "APPROVED" ? `Reviewed & Certified by ${currentReport.approvedBy || "Physician"}` : "AI-GENERATED DRAFT — PENDING PHYSICIAN REVIEW"}
                        </strong>
                      </div>
                    </div>
                  </div>

                  <div style={{ textAlign: "center", borderTop: "1px solid #E5E7EB", paddingTop: "16px" }}>
                    <p style={{ fontSize: "11px", color: "#9CA3AF", margin: 0, textTransform: "uppercase", letterSpacing: "0.5px" }}>
                      Strictly Confidential · Medical Grade Data System
                    </p>
                  </div>
                </div>

                {/* Table of Contents Page */}
                <div className="print-page-break" style={{ padding: "20mm 0" }}>
                  <h2 style={{ fontSize: "20px", fontWeight: 700, color: "#111827", marginBottom: "24px", borderBottom: "2px solid #0A5C8E", paddingBottom: "10px" }}>
                    สารบัญ (Table of Contents)
                  </h2>
                  <div style={{ display: "flex", flexDirection: "column", gap: "12px", fontSize: "14px" }}>
                    {currentReport.report.map((ch: any, idx: number) => (
                      <div key={idx} style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px dotted #D1D5DB", paddingBottom: "4px" }}>
                        <span style={{ color: "#1F2937", fontWeight: 500 }}>{ch.chapterTitle}</span>
                        <span style={{ color: "#6B7280" }}>บทที่ {idx + 1}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/*
                  Chapters: only the FIRST chapter forces a fresh page (right after
                  the TOC). Every subsequent chapter flows directly on from the one
                  before it — the browser will only break to a new page when the
                  current page actually runs out of room. This is what prevents
                  short chapters from leaving large blank areas at the bottom of a
                  page. Each chapter heading is still protected with
                  print-no-split so a title never gets orphaned alone at the
                  bottom of a page, separated from its own content.
                */}
                <div className="print-page-break">
                  {currentReport.report.map((ch: any, idx: number) => (
                    <div key={idx} style={{ padding: "12mm 0" }}>
                      <h2 className="print-no-split" style={{ fontSize: "22px", fontWeight: 700, color: "#0A5C8E", marginBottom: "20px", borderBottom: "2px solid #0A5C8E", paddingBottom: "10px" }}>
                        {ch.chapterTitle.toUpperCase()}
                      </h2>
                      <div style={{ fontSize: "14px", lineHeight: "1.8", color: "#374151" }}>
                        {parseMarkdownToReact(ch.content)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })()
        )}

        <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        .custom-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #E5E7EB; border-radius: 10px; }

        @media print {
          html, body {
            height: auto !important;
            overflow: visible !important;
            background: #FFFFFF !important;
          }
          /* Reset parent layouts to block/static to prevent clipping and splitting issues */
          div, main, section, article {
            overflow: visible !important;
            height: auto !important;
            max-height: none !important;
            display: block !important;
          }
          body * {
            visibility: hidden;
          }
          #tspi-print-area, #tspi-print-area * {
            visibility: visible;
          }
          #tspi-print-area {
            position: static !important;
            width: 100% !important;
            display: block !important;
            background: white !important;
            padding: 0 !important;
            margin: 0 !important;
            overflow: visible !important;
            height: auto !important;
          }
          .print-page-break {
            page-break-before: always !important;
            break-before: page !important;
            padding-top: 15mm !important;
          }
          .print-no-split {
            page-break-inside: avoid !important;
            break-inside: avoid !important;
          }
          table {
            page-break-inside: avoid !important;
          }
          tr {
            page-break-inside: avoid !important;
            page-break-after: auto !important;
          }
        }
      `}</style>

      </div>
    </div>
  );
}
