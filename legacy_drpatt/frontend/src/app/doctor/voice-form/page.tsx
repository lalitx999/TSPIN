"use client";

import { useState, useRef, useEffect } from "react";
import {
  Mic, MicOff, Upload, Play, Pause, Loader2, Save,
  Volume2, Sparkles, CheckCircle, Info, FileText,
  StopCircle, History, MessageSquare, Brain,
  ChevronRight, ClipboardCheck, Activity, ShieldCheck,
  AlertTriangle, RefreshCw
} from "lucide-react";
import Link from "next/link";
import { getAllPatients } from "@/utils/api/services";
import Swal from "sweetalert2";

interface SoapResult {
  S: string;
  O: string;
  A: string;
  P: string;
  axes: string[];
}

export default function VoiceFormPage() {
  const [patients, setPatients] = useState<any[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string>("");
  const [recording, setRecording] = useState(false);
  const [duration, setDuration] = useState(0);
  const [processing, setProcessing] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [interimTranscript, setInterimTranscript] = useState("");
  const [result, setResult] = useState<SoapResult | null>(null);
  const [error, setError] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isSaved, setIsSaved] = useState(false);

  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const recognitionRef = useRef<any>(null);

  // Load patients on mount
  useEffect(() => {
    const loadPatients = async () => {
      try {
        const list = await getAllPatients();
        setPatients(list || []);
        if (list && list.length > 0) {
          setSelectedPatientId(list[0].id);
        }
      } catch (err) {
        console.error("Failed to load patients for voice form:", err);
      }
    };
    loadPatients();
  }, []);

  // Initialize Web Speech API
  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = "th-TH"; // Supports Thai and English seamlessly on most modern engines

        recognition.onresult = (event: any) => {
          let currentInterim = "";
          let finalTranscripts = "";

          for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
              finalTranscripts += event.results[i][0].transcript + " ";
            } else {
              currentInterim += event.results[i][0].transcript;
            }
          }
          
          if (finalTranscripts) {
             setTranscript(prev => prev + finalTranscripts);
          }
          setInterimTranscript(currentInterim);
        };

        recognition.onerror = (event: any) => {
          console.error("Speech recognition error", event.error);
          if (event.error !== 'no-speech') {
             setError("Microphone Error: " + event.error);
             stopRecording();
          }
        };
        
        recognitionRef.current = recognition;
      } else {
        setError("Your browser does not support Speech Recognition. Please use Chrome or Edge.");
      }
    }
  }, []);

  // Timer logic
  useEffect(() => {
    if (recording) {
      timerRef.current = setInterval(() => setDuration(d => d + 1), 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [recording]);

  const startRecording = () => {
    setError("");
    setResult(null);
    setTranscript("");
    setInterimTranscript("");
    setIsSaved(false);
    
    if (recognitionRef.current) {
      try {
        recognitionRef.current.start();
        setRecording(true);
        setDuration(0);
      } catch (e) {
        console.error(e);
        setError("Could not start recording. Check microphone permissions.");
      }
    } else {
       setError("Speech recognition not initialized.");
    }
  };

  const stopRecording = () => {
    if (recognitionRef.current && recording) {
      recognitionRef.current.stop();
      setRecording(false);
      processTranscript();
    }
  };

  const processTranscript = async () => {
    const fullText = transcript + interimTranscript;
    setInterimTranscript("");
    
    if (!fullText.trim()) {
      setError("No voice detected. Please try again.");
      return;
    }

    setProcessing(true);
    try {
      const res = await fetch("/api/ai/voice-soap", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: fullText }),
      });
      
      if (!res.ok) throw new Error("Failed to process SOAP note.");
      
      const data = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || "An error occurred during AI processing.");
    } finally {
      setProcessing(false);
    }
  };

  const handleSave = async () => {
    if (!selectedPatientId) {
      Swal.fire({
        title: "กรุณาเลือกคนไข้",
        text: "โปรดระบุคนไข้ก่อนกดบันทึกบันทึกการรักษา",
        icon: "warning",
        confirmButtonColor: "#0A5C8E"
      });
      return;
    }
    
    setIsSaving(true);
    try {
      const token = localStorage.getItem("doctor_access_token");
      const DJANGO_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      
      const contentText = `**Subjective (S):**\n${result?.S || "N/A"}\n\n**Objective (O):**\n${result?.O || "N/A"}\n\n**Assessment (A):**\n${result?.A || "N/A"}\n\n**Plan (P):**\n${result?.P || "N/A"}\n\n**Impacted Axes:**\n${result?.axes?.join(", ") || "None"}\n\n**Original Voice Transcript:**\n${transcript}`;
      
      const res = await fetch(`${DJANGO_BASE}/api/history/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          patient: selectedPatientId,
          type: "Doctor Visit",
          title: "บันทึกสรุปการตรวจรักษารายครั้ง (AI Voice SOAP)",
          content: contentText
        })
      });

      if (!res.ok) {
        throw new Error("Failed to save SOAP note to Django history.");
      }

      setIsSaved(true);
      Swal.fire({
        title: "บันทึกสำเร็จ! 🎉",
        text: "สรุปบันทึกการตรวจโรค (SOAP) ถูกบันทึกลงในเวชระเบียนคนไข้แล้ว",
        icon: "success",
        confirmButtonColor: "#0A5C8E"
      });
    } catch (err: any) {
      console.error("Save voice SOAP error:", err);
      Swal.fire({
        title: "เกิดข้อผิดพลาด",
        text: err.message || "ไม่สามารถเชื่อมต่อระบบ EMR เพื่อบันทึกข้อมูลได้",
        icon: "error",
        confirmButtonColor: "#0A5C8E"
      });
    } finally {
      setIsSaving(false);
    }
  };

  const formatDuration = (seconds: number) =>
    `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;

  return (
    <div className="pb-5" style={{ backgroundColor: '#F8FAFC', minHeight: '100vh' }}>
      <div className="container-fluid py-4">
        
        {/* ==================== HEADER ==================== */}
        <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-4 gap-3 bg-white p-4 rounded-4 shadow-sm border" style={{ borderColor: '#E2E8F0' }}>
          <div>
            <h1 className="fs-4 fw-bold mb-1 d-flex align-items-center gap-2" style={{ color: '#0F172A' }}>
              <Mic size={24} className="text-primary" />
              TSPI Voice Clinical Note
            </h1>
            <p className="text-muted mb-0" style={{ fontSize: '14px' }}>
              AI-Powered Live Transcription & Automatic SOAP Structuring
            </p>
          </div>
          <button className="btn btn-outline-secondary d-flex align-items-center gap-2 fw-semibold px-4" style={{ borderRadius: '8px' }}>
            <History size={16} /> Voice Archive
          </button>
        </div>

        {error && (
          <div className="alert alert-danger border-danger d-flex align-items-center gap-2 rounded-4 shadow-sm mb-4">
            <AlertTriangle size={18} />
            <span className="fw-semibold">{error}</span>
          </div>
        )}

        <div className="row g-4">
          {/* ==================== LEFT COLUMN: RECORDING ==================== */}
          <div className="col-lg-4">
            <div className="card border-0 shadow-sm rounded-4 mb-4 overflow-hidden">
              <div className="card-header border-0 bg-white p-4 text-center pb-0">
                <h6 className="fw-bold text-muted mb-0" style={{ letterSpacing: '1px', fontSize: '12px' }}>
                  🎙️ VOICE RECORDING
                </h6>
              </div>
              <div className="card-body p-4 text-center">
                
                {/* Patient Selector */}
                <div className="mb-4 text-start border-bottom pb-4">
                  <label className="form-label small fw-bold text-muted uppercase tracking-wider mb-2" style={{ fontSize: '11px', letterSpacing: '0.5px' }}>
                    👤 เลือกคนไข้ตรวจรักษา (EMR Connect)
                  </label>
                  <select
                    className="form-select bg-light border py-2 px-3 fw-semibold text-dark rounded-3 shadow-none text-sm"
                    style={{ fontSize: '13px', borderColor: '#E2E8F0' }}
                    value={selectedPatientId}
                    onChange={(e) => {
                      setSelectedPatientId(e.target.value);
                      setIsSaved(false);
                    }}
                  >
                    {patients.length === 0 ? (
                      <option value="">กำลังโหลดรายชื่อคนไข้...</option>
                    ) : (
                      patients.map((p: any) => (
                        <option key={p.id} value={p.id}>
                          {p.first_name || p.fname} {p.last_name || p.lname} (HN: {p.hn || "N/A"})
                        </option>
                      ))
                    )}
                  </select>
                </div>

                {/* Record Button */}
                <div className="mb-4 position-relative d-inline-block">
                  {recording && (
                     <div className="position-absolute w-100 h-100 rounded-circle" style={{
                        background: '#DC2626', opacity: 0.2, animation: 'pulseGlow 1.5s infinite',
                        top: 0, left: 0, scale: '1.5'
                     }}></div>
                  )}
                  <button
                    onClick={recording ? stopRecording : startRecording}
                    className="position-relative z-1 d-flex align-items-center justify-content-center p-0 mx-auto"
                    style={{
                      width: '100px',
                      height: '100px',
                      borderRadius: '50%',
                      background: recording ? '#DC2626' : '#0A5C8E',
                      color: 'white',
                      border: 'none',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                      boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.2)'
                    }}
                  >
                    {recording ? <StopCircle size={40} /> : <Mic size={40} />}
                  </button>
                </div>

                {/* Timer */}
                <div className="mb-4">
                  <h1 className="mb-1" style={{
                    fontWeight: 700,
                    fontSize: '40px',
                    fontFamily: 'monospace',
                    color: recording ? '#DC2626' : '#0F172A',
                  }}>
                    {formatDuration(duration)}
                  </h1>
                  <div className="d-flex align-items-center justify-content-center gap-2">
                    {recording && (
                      <div className="spinner-grow spinner-grow-sm text-danger" role="status" style={{ width: '8px', height: '8px' }}></div>
                    )}
                    <p className="mb-0 fw-semibold" style={{ fontSize: '13px', color: recording ? '#DC2626' : '#64748B' }}>
                      {recording ? "Capturing Audio..." : "Ready for Session"}
                    </p>
                  </div>
                </div>
              </div>
              
              <div className="card-footer bg-light border-0 p-3">
                 <div className="d-flex align-items-start gap-3">
                   <div className="bg-white p-2 rounded shadow-sm text-primary">
                     <Sparkles size={16} />
                   </div>
                   <div>
                     <h6 className="fw-bold mb-1" style={{ fontSize: '12px', color: '#0A5C8E' }}>
                       INTELLIGENT MAPPING
                     </h6>
                     <p className="text-muted mb-0 lh-sm" style={{ fontSize: '11px' }}>
                       Speak naturally in Thai or English. The TSPI Engine will automatically structure the text into SOAP format and map Biological Axes.
                     </p>
                   </div>
                 </div>
              </div>
            </div>
          </div>

          {/* ==================== RIGHT COLUMN: OUTPUT ==================== */}
          <div className="col-lg-8">
            {!result && !processing && !recording && !transcript ? (
              // Empty State
              <div className="card border-0 shadow-sm rounded-4 d-flex align-items-center justify-content-center text-center p-5" style={{ backgroundColor: 'white', minHeight: '380px' }}>
                  <div className="mb-3" style={{ fontSize: '48px' }}>
                    🤖
                  </div>
                  <h5 className="fw-bold text-dark mb-2">Neural Output Terminal</h5>
                  <p className="text-muted max-w-md mx-auto">
                    Click the microphone to start recording your clinical observations. AI will process your voice in real-time.
                  </p>
              </div>
            ) : processing ? (
              // Loading State
              <div className="card border-0 shadow-sm rounded-4 d-flex align-items-center justify-content-center text-center p-5" style={{ backgroundColor: 'white', minHeight: '380px' }}>
                  <div className="position-relative mb-4">
                    <Loader2 size={48} className="text-primary spinner-border border-0" style={{ animationDuration: '3s' }} />
                  </div>
                  <h5 className="fw-bold text-dark mb-1">Synthesizing SOAP Note</h5>
                  <p className="text-muted">Applying TSPI mechanistic logic to audio input...</p>
              </div>
            ) : (
              // Results State
              <div className="d-flex flex-column gap-4">
                
                {/* Live Transcript Box */}
                {(recording || transcript) && (
                   <div className="card border-0 shadow-sm rounded-4 overflow-hidden">
                     <div className="card-header bg-white border-bottom py-3 d-flex justify-content-between align-items-center">
                        <div className="d-flex align-items-center gap-2">
                           <Activity size={18} className={recording ? "text-danger" : "text-primary"} />
                           <h6 className="mb-0 fw-bold text-dark" style={{ fontSize: '13px', letterSpacing: '0.5px' }}>LIVE TRANSCRIPT</h6>
                        </div>
                     </div>
                     <div className="card-body bg-light p-4" style={{ minHeight: '120px', maxHeight: '200px', overflowY: 'auto' }}>
                        <p className="mb-0 fs-6" style={{ color: '#1F2937', lineHeight: '1.6' }}>
                           {transcript}
                           <span className="text-muted fst-italic">{interimTranscript}</span>
                           {recording && <span className="ms-1" style={{ animation: 'blink 1s infinite' }}>|</span>}
                        </p>
                     </div>
                   </div>
                )}

                {/* AI SOAP Note Box */}
                {result && (
                  <div className="card border-0 shadow-sm rounded-4">
                    <div className="card-header bg-white border-bottom py-3 px-4 d-flex justify-content-between align-items-center">
                      <div className="d-flex align-items-center gap-2 text-primary">
                        <ClipboardCheck size={20} />
                        <h6 className="mb-0 fw-bold">Structured SOAP Analysis</h6>
                      </div>
                      <button 
                        onClick={handleSave}
                        disabled={isSaving || isSaved}
                        className={`btn ${isSaved ? 'btn-success' : 'btn-primary'} btn-sm d-flex align-items-center gap-2 fw-semibold px-3 py-2`}
                        style={{ borderRadius: '6px' }}
                      >
                        {isSaving ? <Loader2 size={14} className="spinner-border spinner-border-sm" /> : isSaved ? <CheckCircle size={14} /> : <Save size={14} />}
                        {isSaving ? "Saving..." : isSaved ? "Saved to Record" : "Commit to Record"}
                      </button>
                    </div>
                    
                    <div className="card-body p-4">
                      <div className="row g-3">
                        {[
                          { key: "S", label: "Subjective", content: result.S, color: "#0A5C8E", bg: "#E8F0F5" },
                          { key: "O", label: "Objective", content: result.O, color: "#059669", bg: "#ECFDF5" },
                          { key: "A", label: "Assessment", content: result.A, color: "#D97706", bg: "#FFFBEB" },
                          { key: "P", label: "Plan", content: result.P, color: "#6B7280", bg: "#F3F4F6" },
                        ].map((section) => (
                          <div key={section.key} className="col-12 col-md-6">
                            <div className="h-100 p-3 rounded-4 border" style={{
                              backgroundColor: section.bg,
                              borderColor: `${section.color}30`
                            }}>
                              <div className="d-flex align-items-center gap-2 mb-2">
                                <span className="d-flex align-items-center justify-content-center rounded text-white fw-bold" 
                                      style={{ width: '24px', height: '24px', fontSize: '13px', backgroundColor: section.color }}>
                                  {section.key}
                                </span>
                                <span className="fw-semibold text-dark" style={{ fontSize: '14px' }}>
                                  {section.label}
                                </span>
                              </div>
                              <p className="mb-0 text-dark" style={{ fontSize: '14px', lineHeight: '1.6' }}>
                                {section.content}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* Impacted Axes */}
                      {result.axes && result.axes.length > 0 && (
                         <div className="mt-4 pt-4 border-top">
                           <h6 className="fw-bold text-muted mb-3" style={{ fontSize: '12px', letterSpacing: '0.5px' }}>
                             IMPACTED BIOLOGICAL AXES DETECTED
                           </h6>
                           <div className="d-flex flex-wrap gap-2">
                             {result.axes.map((axis: string, idx: number) => (
                               <span key={idx} className="badge bg-light text-dark border px-3 py-2" style={{ fontSize: '12px', fontWeight: 600 }}>
                                 {axis}
                               </span>
                             ))}
                           </div>
                         </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

      </div>

      <style jsx global>{`
        @keyframes pulseGlow {
          0% { transform: scale(1); opacity: 0.5; }
          50% { transform: scale(1.3); opacity: 0; }
          100% { transform: scale(1); opacity: 0; }
        }
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
      `}</style>
    </div>
  );
}