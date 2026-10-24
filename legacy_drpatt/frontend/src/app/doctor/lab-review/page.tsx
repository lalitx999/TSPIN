"use client";

import { useState, useEffect } from "react";
import Swal from "sweetalert2";
import {
  FileText, Upload, Activity, Database, AlertCircle,
  Zap, Loader2, Microscope, Brain, User, Image as ImageIcon,
  CheckCircle
} from "lucide-react";
import { getAllPatients, getPatient, updatePatient, saveLabResult, analyzeLabOcr } from "@/utils/api/services";

export default function LabReviewPage() {
  const [patients, setPatients] = useState<any[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState("");
  
  const [inputType, setInputType] = useState<"text" | "image">("text");
  const [textInput, setTextInput] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  
  const [isProcessing, setIsProcessing] = useState(false);
  const [labData, setLabData] = useState<any>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    loadPatients();
  }, []);

  const loadPatients = async () => {
    try {
      const pList = await getAllPatients();
      setPatients(pList);
      if (pList.length > 0) setSelectedPatientId(pList[0].id);
    } catch (error) {
      console.error("Error loading patients:", error);
    }
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setImageFile(e.target.files[0]);
    }
  };

  const handleAnalyze = async () => {
    if (!selectedPatientId) {
      Swal.fire({ title: "Missing Data", text: "Please select a patient.", icon: "warning", confirmButtonColor: "#0A5C8E" });
      return;
    }

    if (inputType === "text" && !textInput.trim()) {
      Swal.fire({ title: "Missing Data", text: "Please paste lab text.", icon: "warning", confirmButtonColor: "#0A5C8E" });
      return;
    }
    
    if (inputType === "image" && !imageFile) {
      Swal.fire({ title: "Missing Data", text: "Please upload a lab image.", icon: "warning", confirmButtonColor: "#0A5C8E" });
      return;
    }

    setIsProcessing(true);
    
    try {
      let data;
      if (inputType === "text") {
        const response = await fetch('/api/doctor/lab-text-analyzer', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: textInput, patientId: selectedPatientId }),
        });
        if (!response.ok) throw new Error('Failed to analyze text');
        data = await response.json();
        
        // Normalize text API response
        setLabData({
          markers: data.markers || [],
          axes: data.axes || [],
          summary: data.summary || "Biological text processing complete."
        });

      } else {
        const getBase64 = (file: File): Promise<string> => {
          return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => {
              const result = reader.result as string;
              const base64 = result.split(',')[1];
              resolve(base64);
            };
            reader.onerror = error => reject(error);
          });
        };

        const base64Data = await getBase64(imageFile!);
        const rawData = await analyzeLabOcr(selectedPatientId, imageFile!.type, base64Data);
        
        // Normalize OCR API response from unified Django adapter
        const normalizedMarkers = (rawData.extractedBiomarkers || []).map((r: any) => ({
          name: r.name,
          value: r.value,
          unit: r.unit,
          reference: r.referenceRange || "",
          flag: r.status?.toUpperCase() || "NORMAL"
        }));
        
        const normalizedAxes = (rawData.recommendedAxesUpdates || []).map((a: any) => ({
          id: `A${a.axisId}`,
          name: a.axisName || `Axis ${a.axisId}`,
          score: (parseInt(a.scoreImpact) || 0) / 100
        }));

        setLabData({
          markers: normalizedMarkers,
          axes: normalizedAxes,
          summary: "Lab document successfully digitized and biological markers extracted."
        });
      }

      Swal.fire({
        title: "Analysis Complete",
        text: "Lab results successfully mapped to biological axes.",
        icon: "success",
        timer: 2000,
        showConfirmButton: false
      });
    } catch (error) {
      console.error('Error analyzing lab data:', error);
      Swal.fire({
        title: "Analysis Failed",
        text: "Unable to process the lab data. Please check input format and try again.",
        icon: "error",
        confirmButtonColor: "#0A5C8E"
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleClear = () => {
    setTextInput("");
    setImageFile(null);
    setLabData(null);
  };

  const handleSaveToEMR = async () => {
    if (!selectedPatientId || !labData) return;
    setIsSaving(true);

    try {
      // 1. Map to EMR result object structure
      const mappedResults = labData.markers.map((m: any) => ({
         parameter: m.name,
         value: m.value,
         unit: m.unit,
         reference_range: m.reference || "",
         status: m.flag || "Normal"
      }));

      const mappedAxes = labData.axes.map((a: any) => {
         const numericId = parseInt(String(a.id).replace(/\D/g, ''));
         return {
            axis_id: numericId,
            axis_name: a.name,
            score_impact: Math.round(a.score * 100),
            reasoning: labData.summary
         };
      });

      // 2. Save lab result list to EMR
      const resultDocId = await saveLabResult({
         patientId: selectedPatientId,
         patientName: patients.find(p => p.id === selectedPatientId)?.name || "EMR Patient",
         testDate: new Date().toISOString().split("T")[0],
         hospitalName: "TSPI Clinic (Lab Review Ingest)",
         results: mappedResults,
         axis_analysis: mappedAxes,
         verified: true,
      });

      // 3. Fetch current patient profile to merge labs and axes
      const patientData = (await getPatient(selectedPatientId)) as any;
      if (patientData) {
         const currentAxes = patientData.axes || {};
         const updatedAxes = { ...currentAxes };

         mappedAxes.forEach((a: any) => {
            const axisKey = String(a.axis_id);
            updatedAxes[axisKey] = {
               axisId: Number(a.axis_id),
               axisName: a.axis_name,
               score: Number(a.score_impact),
               updatedAt: new Date().toISOString(),
               markers: {
                  reasoning: a.reasoning || "Clinical Lab Ingestion Analysis",
                  source: "EMR Lab Ingest Verification",
                  testDate: new Date().toISOString().split("T")[0],
                  hospitalName: "TSPI Clinic"
               }
            };
         });

         const currentLabs = patientData.labs || {};
         const updatedLabs = { ...currentLabs };

         labData.markers.forEach((r: any) => {
            const paramName = String(r.name).toLowerCase().trim();
            const numericVal = parseFloat(r.value);
            if (!isNaN(numericVal)) {
               if (paramName.includes("sugar") || paramName.includes("glucose") || paramName === "fbs") {
                  updatedLabs["FBS"] = numericVal;
               } else if (paramName.includes("hba1c")) {
                  updatedLabs["HbA1c"] = numericVal;
               } else if (paramName === "crp" || paramName.includes("hscrp") || paramName.includes("c-reactive")) {
                  updatedLabs["CRP"] = numericVal;
               } else if (paramName === "ldl" || paramName.includes("ldl cholesterol")) {
                  updatedLabs["LDL"] = numericVal;
               } else if (paramName === "alt" || paramName === "sgpt") {
                  updatedLabs["ALT"] = numericVal;
               } else if (paramName === "ggt") {
                  updatedLabs["GGT"] = numericVal;
               } else {
                  updatedLabs[r.name] = numericVal;
               }
            }
         });

         // 4. Update EMR patient database record
         await updatePatient(selectedPatientId, {
            axes: updatedAxes,
            labs: updatedLabs,
            lastClinicalUpdate: new Date().toISOString()
         });

         // Trigger FCM push notification to the patient if registered
         const fcmToken = patientData.extra_data?.fcm_token;
         if (fcmToken) {
            try {
               await fetch("/api/ai/send-fcm-notification", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                     token: fcmToken,
                     title: "ผลตรวจแล็บอัปเดตใหม่ 🦾",
                     body: `คุณหมอได้อัปเดตผลตรวจล่าสุดของคุณแล้ว เปิดดูหน้าต่างประวัติสุขภาพพหุมิติบนแอปได้ทันที!`
                  })
               });
               console.log("FCM push notification triggered successfully to patient.");
            } catch (fcmErr) {
               console.error("FCM dispatch error:", fcmErr);
            }
         }

         // 5. SweetAlert popup confirmation
         Swal.fire({
            icon: "success",
            title: "บันทึกสำเร็จ",
            text: "ผลแล็บและค่าแกนชีววิทยาได้รับการจัดเก็บลงฐานข้อมูลเรียบร้อยแล้ว",
            confirmButtonColor: "#10B981"
         });
      }
    } catch (error) {
      console.error("Failed to save lab data to EMR:", error);
      Swal.fire({
         icon: "error",
         title: "เกิดข้อผิดพลาด",
         text: "ไม่สามารถบันทึกข้อมูลเข้าฐานข้อมูลของระบบได้",
         confirmButtonColor: "#EF4444"
      });
    } finally {
      setIsSaving(false);
    }
  };

  const getFlagStyle = (flag: string) => {
    const f = flag?.toUpperCase() || "NORMAL";
    if (f.includes("HIGH")) return { color: "#DC2626", bg: "#FEF2F2", label: "HIGH" };
    if (f.includes("LOW")) return { color: "#D97706", bg: "#FFFBEB", label: "LOW" };
    if (f.includes("BORDERLINE") || f.includes("WARNING")) return { color: "#D97706", bg: "#FFFBEB", label: "BORDERLINE" };
    if (f.includes("NORMAL")) return { color: "#059669", bg: "#ECFDF5", label: "NORMAL" };
    return { color: "#4B5563", bg: "#F3F4F6", label: f || "UNKNOWN" };
  };

  return (
    <div style={{ backgroundColor: '#FFFFFF', minHeight: '100vh' }}>
      {/* HEADER */}
      <div style={{ padding: '24px 0', borderBottom: '1px solid #E5E7EB', marginBottom: '32px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 600, color: '#111827', margin: 0 }}>
          Clinical Lab Entry & Analysis
        </h1>
        <p style={{ fontSize: '14px', color: '#6B7280', margin: '4px 0 0 0' }}>
          Automated Biomarker Extraction and Systems Biology Mapping
        </p>
      </div>

      <div className="row g-5">
        {/* LEFT COLUMN: INPUT */}
        <div className="col-lg-5">
          {/* STEP 1: PATIENT SELECTOR */}
          <div style={{ border: '1px solid #E5E7EB', borderRadius: '8px', padding: '20px', marginBottom: '24px' }}>
            <div className="d-flex align-items-center mb-3">
              <User size={18} style={{ color: '#0A5C8E', marginRight: '8px' }} />
              <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#111827', margin: 0 }}>
                1. Select Patient
              </h3>
            </div>
            <select
              value={selectedPatientId}
              onChange={(e) => setSelectedPatientId(e.target.value)}
              style={{
                width: '100%',
                padding: '10px 12px',
                border: '1px solid #D1D5DB',
                borderRadius: '6px',
                fontSize: '14px',
                color: '#111827',
                backgroundColor: '#FFFFFF',
                boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
              }}
            >
              <option value="" disabled>-- Select a Patient --</option>
              {patients.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.hn} | {p.fname} {p.lname}
                </option>
              ))}
            </select>
          </div>

          {/* STEP 2: INPUT SOURCE */}
          <div style={{ border: '1px solid #E5E7EB', borderRadius: '8px', padding: '20px', marginBottom: '24px' }}>
            <div className="d-flex align-items-center mb-3">
              <Database size={18} style={{ color: '#0A5C8E', marginRight: '8px' }} />
              <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#111827', margin: 0 }}>
                2. Input Lab Data
              </h3>
            </div>
            
            <div className="d-flex gap-2 mb-4">
              <button
                onClick={() => setInputType("text")}
                style={{
                  flex: 1, padding: '8px', fontSize: '13px', fontWeight: 500,
                  backgroundColor: inputType === "text" ? '#0A5C8E' : '#F9FAFB',
                  color: inputType === "text" ? '#FFFFFF' : '#4B5563',
                  border: `1px solid ${inputType === "text" ? '#0A5C8E' : '#E5E7EB'}`,
                  borderRadius: '6px', transition: 'all 0.2s'
                }}
              >
                <FileText size={14} className="me-2" /> Paste Text
              </button>
              <button
                onClick={() => setInputType("image")}
                style={{
                  flex: 1, padding: '8px', fontSize: '13px', fontWeight: 500,
                  backgroundColor: inputType === "image" ? '#0A5C8E' : '#F9FAFB',
                  color: inputType === "image" ? '#FFFFFF' : '#4B5563',
                  border: `1px solid ${inputType === "image" ? '#0A5C8E' : '#E5E7EB'}`,
                  borderRadius: '6px', transition: 'all 0.2s'
                }}
              >
                <ImageIcon size={14} className="me-2" /> Upload Image
              </button>
            </div>

            {inputType === "text" ? (
              <textarea
                style={{
                  width: '100%', padding: '12px', border: '1px solid #D1D5DB',
                  borderRadius: '6px', fontSize: '13px', fontFamily: 'monospace',
                  resize: 'vertical', minHeight: '200px', backgroundColor: '#FFFFFF'
                }}
                placeholder="Paste lab results text here...&#10;&#10;Glucose: 160 mg/dL&#10;HbA1C: 7.5%&#10;LDL: 195 mg/dL"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
              />
            ) : (
              <div style={{
                border: '2px dashed #D1D5DB', borderRadius: '6px', padding: '40px 20px',
                textAlign: 'center', backgroundColor: '#F9FAFB'
              }}>
                <Upload size={24} style={{ color: '#9CA3AF', marginBottom: '12px' }} />
                <p style={{ fontSize: '13px', color: '#4B5563', marginBottom: '16px' }}>
                  Select a Lab Image (JPG, PNG) or PDF
                </p>
                <input
                  type="file"
                  accept="image/*,application/pdf"
                  onChange={handleImageUpload}
                  style={{ fontSize: '12px', color: '#111827' }}
                />
              </div>
            )}
          </div>

          {/* ACTION BUTTONS */}
          <div className="d-flex gap-3">
            <button
              onClick={handleAnalyze}
              disabled={isProcessing}
              style={{
                flex: 1, padding: '12px', fontSize: '14px', fontWeight: 600,
                backgroundColor: '#0A5C8E', color: '#FFFFFF', border: 'none',
                borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}
            >
              {isProcessing ? (
                <><Loader2 size={16} className="me-2 spinner-border" style={{ animationDuration: '1s' }} /> PROCESSING AI...</>
              ) : (
                <><Zap size={16} className="me-2" /> EXTRACT & MAP DATA</>
              )}
            </button>
            <button
              onClick={handleClear}
              disabled={isProcessing}
              style={{
                padding: '12px 24px', fontSize: '14px', fontWeight: 500,
                backgroundColor: '#FFFFFF', color: '#374151', border: '1px solid #D1D5DB',
                borderRadius: '6px'
              }}
            >
              Clear
            </button>
          </div>
        </div>

        {/* RIGHT COLUMN: OUTPUT */}
        <div className="col-lg-7">
          {!labData && !isProcessing ? (
            <div style={{
              border: '1px solid #E5E7EB', borderRadius: '8px', minHeight: '500px',
              display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
              backgroundColor: '#F9FAFB'
            }}>
              <Microscope size={48} style={{ color: '#D1D5DB', marginBottom: '16px' }} />
              <h4 style={{ fontSize: '16px', fontWeight: 500, color: '#4B5563', margin: '0 0 8px 0' }}>
                Awaiting Data Input
              </h4>
              <p style={{ fontSize: '14px', color: '#9CA3AF', maxWidth: '300px', textAlign: 'center', margin: 0 }}>
                Select a patient and input lab data on the left to generate clinical insights.
              </p>
            </div>
          ) : isProcessing ? (
            <div style={{
              border: '1px solid #E5E7EB', borderRadius: '8px', minHeight: '500px',
              display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
              backgroundColor: '#F9FAFB'
            }}>
              <div className="spinner-border mb-3" style={{ color: '#0A5C8E', width: '3rem', height: '3rem' }} />
              <h4 style={{ fontSize: '15px', fontWeight: 500, color: '#111827', margin: '0 0 4px 0' }}>
                AI Analysis in Progress
              </h4>
              <p style={{ fontSize: '13px', color: '#6B7280', margin: 0 }}>
                Extracting biomarkers and mapping to 39 Biological Axes...
              </p>
            </div>
          ) : (
            <div>
              {/* RESULTS TABLE */}
              <div style={{ border: '1px solid #E5E7EB', borderRadius: '8px', marginBottom: '24px', overflow: 'hidden' }}>
                <div style={{ padding: '16px 20px', borderBottom: '1px solid #E5E7EB', backgroundColor: '#F9FAFB', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#111827', margin: 0 }}>
                    Extracted Biomarkers
                  </h3>
                </div>
                <div className="table-responsive">
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ backgroundColor: '#F3F4F6' }}>
                        <th style={{ padding: '12px 20px', textAlign: 'left', fontSize: '12px', fontWeight: 600, color: '#4B5563', borderBottom: '1px solid #E5E7EB' }}>CLINICAL MARKER</th>
                        <th style={{ padding: '12px 20px', textAlign: 'left', fontSize: '12px', fontWeight: 600, color: '#4B5563', borderBottom: '1px solid #E5E7EB' }}>RESULT</th>
                        <th style={{ padding: '12px 20px', textAlign: 'left', fontSize: '12px', fontWeight: 600, color: '#4B5563', borderBottom: '1px solid #E5E7EB' }}>REFERENCE</th>
                        <th style={{ padding: '12px 20px', textAlign: 'center', fontSize: '12px', fontWeight: 600, color: '#4B5563', borderBottom: '1px solid #E5E7EB' }}>STATUS</th>
                      </tr>
                    </thead>
                    <tbody>
                      {labData.markers.map((marker: any, idx: number) => {
                        const style = getFlagStyle(marker.flag);
                        return (
                          <tr key={idx} style={{ borderBottom: '1px solid #E5E7EB', backgroundColor: '#FFFFFF' }}>
                            <td style={{ padding: '14px 20px', fontSize: '14px', fontWeight: 500, color: '#111827' }}>
                              {marker.name}
                            </td>
                            <td style={{ padding: '14px 20px' }}>
                              <span style={{ fontSize: '15px', fontWeight: 600, color: '#111827' }}>{marker.value}</span>
                              <span style={{ fontSize: '12px', color: '#6B7280', marginLeft: '4px' }}>{marker.unit}</span>
                            </td>
                            <td style={{ padding: '14px 20px', fontSize: '13px', color: '#6B7280' }}>
                              {marker.reference}
                            </td>
                            <td style={{ padding: '14px 20px', textAlign: 'center' }}>
                              <span style={{
                                backgroundColor: style.bg, color: style.color,
                                padding: '4px 10px', borderRadius: '4px', fontSize: '11px', fontWeight: 600
                              }}>
                                {style.label}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* SAVE TO EMR ACTION BUTTON */}
              <div className="mb-4 text-end" style={{ fontFamily: 'Kanit, sans-serif' }}>
                <button
                  onClick={handleSaveToEMR}
                  disabled={isSaving}
                  className="btn btn-drpat-primary rounded-3 px-4 py-2.5 fw-bold shadow-sm d-flex align-items-center gap-2 ms-auto"
                  style={{ fontSize: '13px' }}
                >
                  {isSaving ? (
                     <>
                        <Loader2 size={16} className="animate-spin" />
                        กำลังบันทึกเวชระเบียน...
                     </>
                  ) : (
                     <>
                        <CheckCircle size={16} />
                        อนุมัติและบันทึกลงฐานข้อมูล EMR
                     </>
                  )}
                </button>
              </div>
 
              {/* SUMMARY */}
              <div style={{ padding: '20px', border: '1px solid #E5E7EB', borderRadius: '8px', backgroundColor: '#F9FAFB', marginBottom: '24px' }}>
                <div className="d-flex align-items-center mb-2">
                  <AlertCircle size={16} style={{ color: '#0A5C8E', marginRight: '8px' }} />
                  <h4 style={{ fontSize: '14px', fontWeight: 600, color: '#111827', margin: 0 }}>Clinical Interpretation</h4>
                </div>
                <p style={{ fontSize: '14px', color: '#4B5563', margin: 0, lineHeight: 1.5 }}>
                  {labData.summary}
                </p>
              </div>

              {/* BIOLOGICAL AXES */}
              <div style={{ border: '1px solid #E5E7EB', borderRadius: '8px', overflow: 'hidden' }}>
                <div style={{ padding: '16px 20px', borderBottom: '1px solid #E5E7EB', backgroundColor: '#F9FAFB', display: 'flex', alignItems: 'center' }}>
                  <Brain size={16} style={{ color: '#111827', marginRight: '8px' }} />
                  <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#111827', margin: 0 }}>
                    Biological Axes Impact
                  </h3>
                </div>
                <div style={{ padding: '20px', backgroundColor: '#FFFFFF' }}>
                  <div className="row g-3">
                    {labData.axes.map((axis: any, idx: number) => (
                      <div key={idx} className="col-md-6">
                        <div style={{ border: '1px solid #E5E7EB', borderRadius: '6px', padding: '12px' }}>
                          <div style={{ fontSize: '12px', fontWeight: 600, color: '#0A5C8E', marginBottom: '4px' }}>
                            {axis.id}
                          </div>
                          <div style={{ fontSize: '14px', fontWeight: 500, color: '#111827', marginBottom: '12px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {axis.name}
                          </div>
                          <div style={{ width: '100%', height: '6px', backgroundColor: '#F3F4F6', borderRadius: '3px', overflow: 'hidden' }}>
                            <div style={{
                              width: `${axis.score * 100}%`,
                              height: '100%',
                              backgroundColor: '#0A5C8E',
                              borderRadius: '3px'
                            }} />
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '6px' }}>
                            <span style={{ fontSize: '11px', color: '#6B7280' }}>Impact Score</span>
                            <span style={{ fontSize: '11px', fontWeight: 600, color: '#111827' }}>{(axis.score * 100).toFixed(0)}%</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

            </div>
          )}
        </div>
      </div>
    </div>
  );
}