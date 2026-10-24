"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  User,
  Phone,
  Mail,
  MapPin,
  Calendar,
  Activity,
  FileText,
  MessageSquare,
  Brain,
  Heart,
  Droplet,
  Thermometer,
  Clock,
  ChevronRight,
  Stethoscope,
  AlertCircle,
  CheckCircle2,
  Edit3,
  ShieldAlert,
  Sparkles,
  Loader2,
  ArrowRight,
  X
} from "lucide-react";
import { getPatient } from "@/utils/api/services";

export default function PatientDetailPage() {
  const params = useParams();
  const patientId = params?.id as string;

  const [patient, setPatient] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // AI Brain States
  const [aiInput, setAiInput] = useState("");
  const [aiResponse, setAiResponse] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleAskAI = async () => {
    if (!aiInput.trim()) return;

    setIsAnalyzing(true);
    try {
      const res = await fetch("/api/ai/brain", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          engine: "gemini",
          messages: [
            {
              role: "system",
              content: `You are TSPI Clinical Intelligence Brain. Current patient: ${patient.name}, Age: ${patient.age}, Conditions: ${patient.disease}, Allergies: ${patient.allergy}. Provide accurate medical analysis.`
            },
            { role: "user", content: aiInput }
          ]
        })
      });
      const data = await res.json();
      setAiResponse(data.content);
    } catch (err) {
      console.error("AI Brain Error:", err);
      setAiResponse("AI system temporarily unavailable. Please try again.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  useEffect(() => {
    const loadPatient = async () => {
      try {
        const data = await getPatient(patientId);
        setPatient(data);
      } catch (err) {
        console.error("Error loading patient:", err);
      } finally {
        setLoading(false);
      }
    };
    if (patientId) loadPatient();
  }, [patientId]);

  if (loading) {
    return (
      <div className="d-flex align-items-center justify-content-center py-5" style={{ minHeight: '60vh' }}>
        <div className="text-center">
          <div className="spinner-border text-primary mb-3" role="status" style={{ width: '32px', height: '32px' }}>
            <span className="visually-hidden">Loading...</span>
          </div>
          <p className="text-muted text-xs mb-0">Loading patient data...</p>
        </div>
      </div>
    );
  }

  if (!patient) {
    return (
      <div className="text-center py-5">
        <AlertCircle size={48} style={{ color: '#DC2626', marginBottom: '16px' }} />
        <h5 style={{ fontWeight: 500, marginBottom: '8px' }}>Patient Not Found</h5>
        <Link href="/doctor/patients" className="btn btn-primary mt-3">
          Back to Registry
        </Link>
      </div>
    );
  }

  // Status badge config
  const statusBadge = (() => {
    if (patient.status === 'เคสด่วน' || patient.status === 'ด่วน') {
      return { text: "Urgent", color: "#DC2626", bg: "#FEF2F2" };
    }
    if (patient.status === 'กำลังตรวจ') {
      return { text: "In Progress", color: "#D97706", bg: "#FFFBEB" };
    }
    if (patient.status === 'ติดตาม') {
      return { text: "Monitoring", color: "#0A5C8E", bg: "#E8F0F5" };
    }
    if (patient.status === 'เสร็จสิ้น' || patient.status === 'ปกติ') {
      return { text: "Completed", color: "#059669", bg: "#ECFDF5" };
    }
    return { text: patient.status || "Active", color: "#6B7280", bg: "#F3F4F6" };
  })();

  return (
    <div>
      {/* ==================== BREADCRUMB & ACTIONS ==================== */}
      <div className="d-flex align-items-center justify-content-between mb-6">
        <div className="d-flex align-items-center gap-3">
          <Link
            href="/doctor/patients"
            className="btn btn-ghost"
            style={{ padding: '8px', borderRadius: '6px' }}
          >
            <ArrowLeft size={18} />
          </Link>
          <nav className="d-flex align-items-center gap-2">
            <Link href="/doctor/patients" style={{ fontSize: '11px', color: '#6B7280', textDecoration: 'none', letterSpacing: '0.3px' }}>
              PATIENTS
            </Link>
            <ChevronRight size={10} style={{ color: '#9CA3AF' }} />
            <span style={{ fontSize: '11px', color: '#0A5C8E', fontWeight: 500, letterSpacing: '0.3px' }}>
              {patient.name}
            </span>
          </nav>
        </div>
        <div className="d-flex gap-2">
          <Link
            href={`/doctor/axis-timeline?id=${patientId}`}
            className="btn btn-outline"
            style={{ fontSize: '12px', padding: '6px 14px' }}
          >
            <FileText size={14} className="me-1" /> History
          </Link>
          <Link
            href={`/doctor/ai-physician?id=${patientId}`}
            className="btn btn-primary"
            style={{ fontSize: '12px', padding: '6px 14px' }}
          >
            <Brain size={14} className="me-1" /> AI Consultation
          </Link>
        </div>
      </div>

      {/* ==================== PROFILE HEADER CARD ==================== */}
      <div className="card mb-6">
        <div className="p-5">
          <div className="row align-items-center g-4">
            {/* Avatar */}
            <div className="col-auto">
              <div style={{
                width: '88px',
                height: '88px',
                background: '#E8F0F5',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 600,
                fontSize: '32px',
                color: '#0A5C8E'
              }}>
                {patient.name?.charAt(0)?.toUpperCase() || 'P'}
              </div>
            </div>

            {/* Patient Info */}
            <div className="col">
              <div className="d-flex align-items-center gap-2 mb-2">
                <h4 style={{ fontWeight: 600, fontSize: '20px', color: '#1F2937', margin: 0 }}>
                  {patient.name}
                </h4>
                <span className="badge" style={{
                  background: statusBadge.bg,
                  color: statusBadge.color,
                  fontSize: '10px',
                  fontWeight: 500,
                  padding: '2px 8px',
                  borderRadius: '4px'
                }}>
                  {statusBadge.text}
                </span>
              </div>
              <p style={{ fontSize: '12px', color: '#6B7280', marginBottom: '12px' }}>
                HN: {patient.hn || String(patient.id || '').slice(0, 8)} • Age: {patient.age} yrs • {patient.sex || 'Not specified'}
              </p>
              <div className="d-flex flex-wrap gap-4">
                <div className="d-flex align-items-center gap-2">
                  <Phone size={12} style={{ color: '#9CA3AF' }} />
                  <span style={{ fontSize: '12px', color: '#4B5563' }}>{patient.phone || 'N/A'}</span>
                </div>
                <div className="d-flex align-items-center gap-2">
                  <Mail size={12} style={{ color: '#9CA3AF' }} />
                  <span style={{ fontSize: '12px', color: '#4B5563' }}>{patient.email || 'N/A'}</span>
                </div>
                <div className="d-flex align-items-center gap-2">
                  <Clock size={12} style={{ color: '#9CA3AF' }} />
                  <span style={{ fontSize: '12px', color: '#4B5563' }}>Last Visit: {patient.lastVisit || 'First admission'}</span>
                </div>
              </div>
            </div>

            {/* Progress */}
            <div className="col-auto">
              <div style={{ minWidth: '160px' }}>
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <span style={{ fontSize: '10px', color: '#6B7280', letterSpacing: '0.3px' }}>CLINICAL PROGRESS</span>
                  <span style={{ fontSize: '12px', fontWeight: 600, color: '#0A5C8E' }}>{patient.progress || 0}%</span>
                </div>
                <div style={{
                  height: '6px',
                  background: '#E5E7EB',
                  borderRadius: '3px',
                  overflow: 'hidden'
                }}>
                  <div style={{
                    width: `${patient.progress || 0}%`,
                    height: '100%',
                    background: '#0A5C8E',
                    borderRadius: '3px'
                  }} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ==================== MAIN TWO COLUMN LAYOUT ==================== */}
      <div className="row g-6">
        {/* LEFT COLUMN */}
        <div className="col-lg-8">
          {/* Health Metrics Grid */}
          <div className="row g-4 mb-6">
            {[
              { label: "BMI", value: patient.bmi_val || '--', unit: "kg/m²", icon: Activity },
              { label: "Weight", value: patient.weight || '--', unit: "kg", icon: Heart },
              { label: "Height", value: patient.height || '--', unit: "cm", icon: User },
              { label: "BP", value: patient.blood_pressure || '--', unit: "mmHg", icon: Droplet }
            ].map((stat, idx) => (
              <div key={idx} className="col-6 col-md-3">
                <div className="card p-3">
                  <div className="d-flex align-items-center gap-2 mb-2">
                    <stat.icon size={14} style={{ color: '#0A5C8E' }} />
                    <span style={{ fontSize: '10px', fontWeight: 600, color: '#6B7280', letterSpacing: '0.3px' }}>
                      {stat.label}
                    </span>
                  </div>
                  <h5 style={{ fontWeight: 600, fontSize: '18px', color: '#1F2937', margin: 0 }}>
                    {stat.value} <span style={{ fontSize: '11px', color: '#9CA3AF', fontWeight: 400 }}>{stat.unit}</span>
                  </h5>
                </div>
              </div>
            ))}
          </div>

          {/* Medical Information */}
          <div className="card mb-6">
            <div className="card-header">
              <div className="d-flex align-items-center gap-2">
                <Stethoscope size={14} style={{ color: '#6B7280' }} />
                <h3 className="mb-0" style={{ fontSize: '13px', fontWeight: 600, color: '#374151', letterSpacing: '0.3px' }}>
                  MEDICAL INFORMATION
                </h3>
              </div>
            </div>
            <div className="p-4">
              <div className="row g-4">
                <div className="col-md-6">
                  <p style={{ fontSize: '11px', fontWeight: 600, color: '#6B7280', marginBottom: '8px', letterSpacing: '0.3px' }}>
                    CONDITIONS / DIAGNOSIS
                  </p>
                  <div style={{
                    padding: '12px',
                    background: '#F9FAFB',
                    borderRadius: '6px',
                    fontSize: '13px',
                    color: '#1F2937',
                    border: '1px solid #F3F4F6'
                  }}>
                    {patient.disease || 'No documented conditions'}
                  </div>
                </div>
                <div className="col-md-6">
                  <p style={{ fontSize: '11px', fontWeight: 600, color: '#6B7280', marginBottom: '8px', letterSpacing: '0.3px' }}>
                    ALLERGIES
                  </p>
                  <div style={{
                    padding: '12px',
                    background: '#FEF2F2',
                    borderRadius: '6px',
                    fontSize: '13px',
                    color: '#DC2626',
                    border: '1px solid #FEE2E2'
                  }}>
                    {patient.allergy || 'No known allergies'}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* AI Clinical Intelligence Workspace */}
          <div className="card">
            <div className="card-header">
              <div className="d-flex align-items-center justify-content-between w-100">
                <div className="d-flex align-items-center gap-2">
                  <div style={{
                    width: '32px',
                    height: '32px',
                    background: '#E8F0F5',
                    borderRadius: '6px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    <Brain size={16} style={{ color: '#0A5C8E' }} />
                  </div>
                  <div>
                    <h3 className="mb-0" style={{ fontSize: '13px', fontWeight: 600, color: '#374151', letterSpacing: '0.3px' }}>
                      AI CLINICAL INTELLIGENCE
                    </h3>
                    <p style={{ fontSize: '10px', color: '#9CA3AF', margin: 0 }}>Powered by Gemini • Precision Analysis</p>
                  </div>
                </div>
                <span className="badge" style={{
                  background: '#ECFDF5',
                  color: '#059669',
                  fontSize: '9px',
                  fontWeight: 500,
                  padding: '2px 8px'
                }}>
                  <Sparkles size={8} className="me-1" /> ONLINE
                </span>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="p-4 border-bottom" style={{ borderBottom: '1px solid #F3F4F6' }}>
              <div className="d-flex flex-wrap gap-2">
                {[
                  { label: "Analyze PGx", icon: ShieldAlert },
                  { label: "Summarize Case", icon: FileText },
                  { label: "12-Week Care Plan", icon: Calendar },
                  { label: "Compare Trends", icon: Activity }
                ].map((btn, idx) => (
                  <button
                    key={idx}
                    onClick={() => setAiInput(btn.label)}
                    className="btn btn-outline"
                    style={{ fontSize: '11px', padding: '6px 12px' }}
                  >
                    <btn.icon size={12} className="me-1" /> {btn.label}
                  </button>
                ))}
              </div>
            </div>

            {/* AI Response Area */}
            <div className="p-4">
              {aiResponse ? (
                <div style={{
                  marginBottom: '20px',
                  background: '#F9FAFB',
                  borderRadius: '8px',
                  padding: '16px',
                  borderLeft: '3px solid #0A5C8E'
                }}>
                  <div className="d-flex justify-content-between align-items-start mb-3">
                    <p style={{ fontSize: '10px', fontWeight: 600, color: '#0A5C8E', letterSpacing: '0.3px', margin: 0 }}>
                      AI INTERPRETATION
                    </p>
                    <button
                      onClick={() => setAiResponse("")}
                      style={{ background: 'transparent', border: 'none', cursor: 'pointer' }}
                    >
                      <X size={14} style={{ color: '#9CA3AF' }} />
                    </button>
                  </div>
                  <div style={{ fontSize: '13px', color: '#1F2937', lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>
                    {aiResponse}
                  </div>
                  <div className="d-flex gap-2 mt-3 pt-3" style={{ borderTop: '1px solid #E5E7EB' }}>
                    <button className="btn btn-primary" style={{ fontSize: '11px', padding: '5px 12px' }}>
                      <CheckCircle2 size={12} className="me-1" /> Save to Notes
                    </button>
                    <button className="btn btn-outline" style={{ fontSize: '11px', padding: '5px 12px' }}>
                      <Edit3 size={12} className="me-1" /> Refine
                    </button>
                  </div>
                </div>
              ) : (
                <div className="text-center py-5">
                  <Brain size={40} style={{ color: '#D1D5DB', marginBottom: '12px' }} />
                  <p style={{ fontSize: '12px', color: '#9CA3AF', margin: 0 }}>
                    Ask a clinical question or select a quick action above
                  </p>
                </div>
              )}

              {/* Input Area */}
              <div className="position-relative">
                <textarea
                  className="form-control"
                  rows={3}
                  placeholder="Ask about disease progression, summarize abnormalities, or suggest TSPI modules..."
                  value={aiInput}
                  onChange={(e) => setAiInput(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '1px solid #E5E7EB',
                    borderRadius: '8px',
                    fontSize: '13px',
                    resize: 'vertical'
                  }}
                />
                <button
                  onClick={handleAskAI}
                  disabled={!aiInput.trim() || isAnalyzing}
                  style={{
                    position: 'absolute',
                    bottom: '12px',
                    right: '12px',
                    background: '#0A5C8E',
                    border: 'none',
                    borderRadius: '6px',
                    padding: '8px',
                    cursor: aiInput.trim() && !isAnalyzing ? 'pointer' : 'not-allowed',
                    opacity: aiInput.trim() && !isAnalyzing ? 1 : 0.5
                  }}
                >
                  {isAnalyzing ? (
                    <div className="spinner-border" style={{ width: '16px', height: '16px', color: 'white' }} role="status">
                      <span className="visually-hidden">Loading...</span>
                    </div>
                  ) : (
                    <ArrowRight size={16} style={{ color: 'white' }} />
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Personal Information */}
        <div className="col-lg-4">
          <div className="card">
            <div className="card-header">
              <div className="d-flex align-items-center gap-2">
                <User size={14} style={{ color: '#6B7280' }} />
                <h3 className="mb-0" style={{ fontSize: '13px', fontWeight: 600, color: '#374151', letterSpacing: '0.3px' }}>
                  PERSONAL INFORMATION
                </h3>
              </div>
            </div>
            <div className="p-4">
              <div className="d-grid gap-4">
                {[
                  { icon: User, label: "National ID", value: patient.idCard || 'Not provided' },
                  { icon: Calendar, label: "Date of Birth", value: patient.birthday || 'Not provided' },
                  { icon: MapPin, label: "Address", value: patient.address || 'Not provided' },
                ].map((item, idx) => (
                  <div key={idx} className="d-flex gap-3">
                    <div style={{
                      width: '32px',
                      height: '32px',
                      background: '#F3F4F6',
                      borderRadius: '6px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0
                    }}>
                      <item.icon size={14} style={{ color: '#6B7280' }} />
                    </div>
                    <div>
                      <p style={{ fontSize: '10px', fontWeight: 600, color: '#6B7280', letterSpacing: '0.3px', marginBottom: '4px' }}>
                        {item.label}
                      </p>
                      <p style={{ fontSize: '13px', color: '#1F2937', margin: 0, lineHeight: 1.4 }}>
                        {item.value}
                      </p>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-5 pt-4" style={{ borderTop: '1px solid #F3F4F6' }}>
                <button className="btn btn-outline w-100" style={{ fontSize: '12px', padding: '8px' }}>
                  <Edit3 size={14} className="me-2" /> Edit Patient Information
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}