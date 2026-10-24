"use client";

import { useState, useEffect } from "react";
import {
   Microscope, Save, AlertTriangle, RefreshCw,
   Clock, Eye, Activity, Brain, FileText, Loader2, 
   Upload, CheckCircle, AlertCircle, Info, ShieldCheck,
   Trash2, Plus, ArrowRight, User
} from "lucide-react";
import { getAllPatients, getLabResults, updatePatient, getPatient, saveLabResult, analyzeLabOcr } from "@/utils/api/services";
import { logAudit } from "@/utils/api/audit";
import Swal from "sweetalert2";
import "./../theme-inapp.css";

export default function LabOCRPage() {
   // Patients & Results Lists
   const [patients, setPatients] = useState<any[]>([]);
   const [selectedPatientId, setSelectedPatientId] = useState<string>("");
   const [pendingResults, setPendingResults] = useState<any[]>([]);
   const [allResults, setAllResults] = useState<any[]>([]);
   
   // UI State
   const [isAnalyzing, setIsAnalyzing] = useState(false);
   const [isSaving, setIsSaving] = useState(false);
   const [ocrResult, setOcrResult] = useState<any>(null);
   const [message, setMessage] = useState<{ type: "success" | "error" | ""; text: string }>({ type: "", text: "" });
   const [uploadError, setUploadError] = useState<string>("");

   const [chatImages, setChatImages] = useState<any[]>([]);

   // Load Patients and Lab Results on Mount
   useEffect(() => {
      loadInitialData();
   }, []);

   // Load images from patient's intake chat sessions
   useEffect(() => {
      const loadChatImages = async () => {
         if (!selectedPatientId) {
            setChatImages([]);
            return;
         }
         try {
            const patient = await getPatient(selectedPatientId);
            if (patient && patient.extra_data && patient.extra_data.intake_sessions) {
               const sessions = Object.values(patient.extra_data.intake_sessions);
               const imgs: any[] = [];
               sessions.forEach((sess: any) => {
                  const msgs = sess.messages || [];
                  msgs.forEach((m: any) => {
                     if (m.imageBase64) {
                        imgs.push({
                           imageBase64: m.imageBase64,
                           text: m.text || "ไฟล์แนบภาพผลตรวจ",
                           timestamp: sess.createdAt || sess.updatedAt || new Date().toISOString()
                        });
                     }
                  });
               });
               setChatImages(imgs);
            } else {
               setChatImages([]);
            }
         } catch (err) {
            console.error("Failed to load chat images:", err);
            setChatImages([]);
         }
      };
      loadChatImages();
   }, [selectedPatientId]);

   const handleScanChatImage = async (imgBase64: string) => {
      setIsAnalyzing(true);
      setUploadError("");
      setMessage({ type: "", text: "" });

      try {
         const aiResponse = await analyzeLabOcr(
            selectedPatientId,
            "image/jpeg",
            imgBase64
         );

         const patient = patients.find(p => p.id === selectedPatientId);

         const mappedResults = aiResponse.extractedBiomarkers.map((b: any) => ({
            parameter: b.name,
            value: b.value,
            unit: b.unit,
            reference_range: b.referenceRange || "",
            status: b.status || "Normal"
         }));
         
         const mappedAxes = aiResponse.recommendedAxesUpdates.map((a: any) => ({
            axis_id: a.axisId,
            axis_name: a.axisName || ("Axis " + a.axisId),
            score_impact: a.scoreImpact,
            reasoning: a.reasoning || ""
         }));

         setOcrResult({
            id: "",
            patientId: selectedPatientId,
            patientName: patient ? `${patient.fname} ${patient.lname || ""}` : "Unknown Patient",
            testDate: new Date().toISOString().split("T")[0],
            hospitalName: "TSPI Clinic (จากแชทคัดกรอง)",
            results: mappedResults,
            axis_analysis: mappedAxes,
            verified: false
         });
         
         setMessage({ type: "success", text: "สกัดข้อมูลผลแล็บสำเร็จ! กรุณาตรวจสอบและอนุมัติข้อมูล" });
         Swal.fire({
            title: "สกัดข้อมูลสำเร็จ! 🎉",
            text: "แปลงข้อมูลและวิเคราะห์แกนหลักแล้ว กรุณาตรวจตารางและกดยืนยัน",
            icon: "success",
            confirmButtonColor: "#0A5C8E"
         });
      } catch (error: any) {
         console.error("OCR scan chat image error:", error);
         setUploadError(error.message || "การประมวลผล OCR ล้มเหลว โปรดลองใหม่อีกครั้ง");
         Swal.fire("สแกนล้มเหลว", "เกิดข้อผิดพลาดในการประมวลผลรูปภาพแล็บ", "error");
      } finally {
         setIsAnalyzing(false);
      }
   };

   const loadInitialData = async () => {
      try {
         const pList = await getAllPatients();
         setPatients(pList);
         
         // Try to get patient ID from URL query params
         let patientIdFromUrl = "";
         if (typeof window !== "undefined") {
            const urlParams = new URLSearchParams(window.location.search);
            patientIdFromUrl = urlParams.get("id") || "";
         }

         if (patientIdFromUrl && pList.some((p: any) => p.id === patientIdFromUrl)) {
            setSelectedPatientId(patientIdFromUrl);
         } else if (pList.length > 0) {
            setSelectedPatientId(pList[0].id);
         }
         await loadLabResultsList();
      } catch (error) {
         console.error("Error loading clinical data:", error);
      }
   };

   const loadLabResultsList = async () => {
      try {
         const results = await getLabResults();
         setAllResults(results);
         // Filter for unverified results
         const pending = results.filter((r: any) => !r.verified);
         setPendingResults(pending);
      } catch (error) {
         console.error("Error loading lab results:", error);
      }
   };

   // Handles Lab Result Image Upload and calls Genkit AI Function
   const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      
      setIsAnalyzing(true);
      setUploadError("");
      setMessage({ type: "", text: "" });

      try {
         // Convert File to base64
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
         
         const base64Data = await getBase64(file);
         
         const aiResponse = await analyzeLabOcr(
            selectedPatientId,
            file.type,
            base64Data
         );

         const patient = patients.find(p => p.id === selectedPatientId);

         const mappedResults = aiResponse.extractedBiomarkers.map((b: any) => ({
            parameter: b.name,
            value: b.value,
            unit: b.unit,
            reference_range: b.referenceRange || "",
            status: b.status || "Normal"
         }));
         
         const mappedAxes = aiResponse.recommendedAxesUpdates.map((a: any) => ({
            axis_id: a.axisId,
            axis_name: a.axisName || ("Axis " + a.axisId),
            score_impact: a.scoreImpact,
            reasoning: a.reasoning || ""
         }));

         // Set active OCR result under review
         setOcrResult({
            id: "", // Will be assigned on save
            patientId: selectedPatientId,
            patientName: patient ? `${patient.fname} ${patient.lname || ""}` : "Unknown Patient",
            testDate: new Date().toISOString().split("T")[0],
            hospitalName: "TSPI Clinic",
            results: mappedResults,
            axis_analysis: mappedAxes,
            verified: false
         });
         
         setMessage({ type: "success", text: "สกัดข้อมูลผลแล็บสำเร็จ! กรุณาตรวจสอบและอนุมัติข้อมูล" });
      } catch (error: any) {
         console.error("OCR upload error:", error);
         setUploadError(error.message || "การประมวลผล OCR ล้มเหลว โปรดลองใหม่อีกครั้ง");
      } finally {
         setIsAnalyzing(false);
      }
   };

   // Load a pending result from the list for review
   const handleSelectPending = (item: any) => {
      setOcrResult({
         id: item.id,
         patientId: item.patientId,
         patientName: item.patientName || "Unknown Patient",
         testDate: item.testDate || new Date().toISOString().split("T")[0],
         hospitalName: item.hospitalName || "TSPI Clinic",
         results: item.results || [],
         axis_analysis: item.axis_analysis || [],
         verified: item.verified
      });
      setSelectedPatientId(item.patientId);
      setMessage({ type: "", text: "" });
      setUploadError("");
   };

   // Parameter editing handlers
   const handleParameterChange = (index: number, key: string, val: any) => {
      if (!ocrResult) return;
      const updatedResults = [...ocrResult.results];
      updatedResults[index] = { ...updatedResults[index], [key]: val };
      setOcrResult({ ...ocrResult, results: updatedResults });
   };

   const handleAddParameter = () => {
      if (!ocrResult) return;
      const newRow = { parameter: "", value: "", unit: "", reference_range: "", status: "Normal" };
      setOcrResult({ ...ocrResult, results: [...ocrResult.results, newRow] });
   };

   const handleDeleteParameter = (index: number) => {
      if (!ocrResult) return;
      const updatedResults = ocrResult.results.filter((_: any, i: number) => i !== index);
      setOcrResult({ ...ocrResult, results: updatedResults });
   };

   // Axis analysis editing handlers
   const handleAxisChange = (index: number, key: string, val: any) => {
      if (!ocrResult) return;
      const updatedAxes = [...ocrResult.axis_analysis];
      updatedAxes[index] = { ...updatedAxes[index], [key]: val };
      setOcrResult({ ...ocrResult, axis_analysis: updatedAxes });
   };

   const handleAddAxis = () => {
      if (!ocrResult) return;
      const newAxis = { axis_id: 1, axis_name: "Systemic Inflammatory Load", score_impact: 50, reasoning: "" };
      setOcrResult({ ...ocrResult, axis_analysis: [...ocrResult.axis_analysis, newAxis] });
   };

   const handleDeleteAxis = (index: number) => {
      if (!ocrResult) return;
      const updatedAxes = ocrResult.axis_analysis.filter((_: any, i: number) => i !== index);
      setOcrResult({ ...ocrResult, axis_analysis: updatedAxes });
   };

   // Confirm edits, save to Firestore unverified result, update verified status, and sync to Digital Twin
   const handleVerifyAndSync = async () => {
      if (!ocrResult || !ocrResult.patientId) return;
      setIsSaving(true);
      setMessage({ type: "", text: "" });

      try {
         // 1. Save and verify lab result via unified Django EMR service adapter
         let resultDocId = ocrResult.id;
         resultDocId = await saveLabResult({
            id: resultDocId,
            patientId: ocrResult.patientId,
            patientName: ocrResult.patientName,
            testDate: ocrResult.testDate,
            hospitalName: ocrResult.hospitalName,
            results: ocrResult.results,
            axis_analysis: ocrResult.axis_analysis,
            verified: true,
         });
         ocrResult.id = resultDocId;

         // 2. Fetch the patient's current record
         const patientData = (await getPatient(ocrResult.patientId)) as any;
         if (patientData) {
            const currentAxes = patientData.axes || {};
            const updatedAxes = { ...currentAxes };

            // Merge the new axis analysis into the 39-Axis Digital Twin structure
            ocrResult.axis_analysis.forEach((a: any) => {
               const axisKey = String(a.axis_id);
               updatedAxes[axisKey] = {
                  axisId: Number(a.axis_id),
                  axisName: a.axis_name,
                  score: Number(a.score_impact),
                  updatedAt: new Date().toISOString(),
                  markers: {
                     reasoning: a.reasoning,
                     source: "Clinical Lab OCR Verification",
                     testDate: ocrResult.testDate,
                     hospitalName: ocrResult.hospitalName,
                     raw_value: String(ocrResult.results.find((r: any) => r.parameter.toLowerCase().includes(a.axis_name.toLowerCase()) || r.status !== "Normal")?.value || "N/A")
                  }
               };
            });

            // Merge verified lab results into EMR patient labs dictionary (FBS, HbA1c, hs-CRP, etc.)
            const currentLabs = patientData.labs || {};
            const updatedLabs = { ...currentLabs };

            ocrResult.results.forEach((r: any) => {
               const paramName = String(r.parameter).toLowerCase().trim();
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
                     // Save general other labs as well
                     updatedLabs[r.parameter] = numericVal;
                  }
               }
            });

            // 3. Save the merged axes and updated labs back to the patient record
            await updatePatient(ocrResult.patientId, {
               axes: updatedAxes,
               labs: updatedLabs,
               lastClinicalUpdate: new Date().toISOString()
            });

            // 4. Create an audit trail log
            await logAudit({
               action: "ADMIN_ACTION",
               patientId: ocrResult.patientId,
               details: {
                  event: "LAB_RESULT_VERIFIED",
                  lab_result_id: resultDocId || "client-created",
                  hospital_name: ocrResult.hospitalName,
                  parameters_verified: ocrResult.results.length,
                  axes_updated: ocrResult.axis_analysis.map((a: any) => a.axis_id)
               }
            });

            // Beautiful SweetAlert success popups
            await Swal.fire({
               title: "ซิงค์ระบบสำเร็จ! 🎉",
               html: `อนุมัติและเชื่อมโยงผลแล็บของ <b>คุณ${ocrResult.patientName}</b> เข้าสู่ระบบ Digital Twin สำเร็จเรียบร้อยแล้ว`,
               icon: "success",
               confirmButtonText: "ตกลง",
               confirmButtonColor: "#10B981",
               timer: 3000,
               timerProgressBar: true,
               customClass: {
                  popup: 'rounded-4 shadow-lg border-0'
               }
            });

            setMessage({ type: "success", text: `อนุมัติและเชื่อมโยงผลแล็บของ คุณ${ocrResult.patientName} เข้าสู่ Digital Twin สำเร็จแล้ว!` });
            setOcrResult(null);
            await loadLabResultsList();
         } else {
            throw new Error("Patient record not found in system database");
         }
      } catch (error: any) {
         console.error("Error verifying result:", error);
         await Swal.fire({
            title: "เกิดข้อผิดพลาด ❌",
            text: error.message || "ไม่สามารถบันทึกและซิงค์ข้อมูลได้",
            icon: "error",
            confirmButtonText: "ตกลง",
            confirmButtonColor: "#EF4444",
            customClass: {
               popup: 'rounded-4 shadow-lg border-0'
            }
         });
         setMessage({ type: "error", text: "เกิดข้อผิดพลาดในการบันทึกข้อมูล: " + error.message });
      } finally {
         setIsSaving(false);
      }
   };

   return (
      <div className="pb-5 container-fluid px-4">
         {/* 🧭 Header Section */}
         <div className="d-flex justify-content-between align-items-center mb-4 border-bottom pb-3">
            <div>
               <h1 className="fs-3 fw-bold mb-1 text-dark d-flex align-items-center gap-2">
                  <div className="bg-primary bg-opacity-10 p-2 rounded-3 text-primary">
                     <Microscope size={24} />
                  </div>
                  TSPI Laboratory OCR & Systems Biology Sync
               </h1>
               <p className="text-muted text-xs uppercase font-bold tracking-widest ms-5">Advanced Digital Twin Integration Engine</p>
            </div>
            <div className="d-flex gap-2">
               <button onClick={loadInitialData} className="btn btn-light btn-sm border d-flex align-items-center gap-1">
                  <RefreshCw size={14} /> รีเฟรชข้อมูล
               </button>
            </div>
         </div>

         {/* 📣 Notifications Alert Banner */}
         {message.text && (
            <div className={`alert ${message.type === 'success' ? 'alert-success border-success' : 'alert-danger border-danger'} alert-dismissible fade show rounded-3 shadow-sm mb-4`} role="alert">
               <div className="d-flex align-items-center gap-2">
                  {message.type === 'success' ? <CheckCircle size={18} className="text-success" /> : <AlertCircle size={18} className="text-danger" />}
                  <span className="font-semibold text-sm">{message.text}</span>
               </div>
            </div>
         )}

         {uploadError && (
            <div className="alert alert-danger border-danger rounded-3 shadow-sm mb-4" role="alert">
               <div className="d-flex align-items-center gap-2">
                  <AlertTriangle size={18} className="text-danger" />
                  <span className="font-semibold text-sm">{uploadError}</span>
               </div>
            </div>
         )}

         <div className="row g-4">
            {/* 🔬 Left Column: Active Workspace / OCR Editor */}
            <div className="col-lg-8">
               <div className="card border-0 shadow-sm bg-white rounded-4 overflow-hidden mb-4">
                  <div className="card-header bg-transparent border-bottom border-light py-3 d-flex justify-content-between align-items-center">
                     <h3 className="card-title text-[11px] font-bold uppercase text-muted tracking-widest mb-0 d-flex align-items-center gap-2">
                        <Brain size={14} className="text-primary" /> 
                        {ocrResult ? `กำลังตรวจสอบผลแล็บ: ${ocrResult.patientName}` : "เครื่องมืออัปโหลด & สกัดผลแล็บ"}
                     </h3>
                     {ocrResult && (
                        <button 
                           onClick={() => setOcrResult(null)} 
                           className="btn btn-light btn-xs border text-[10px] font-bold"
                        >
                           ยกเลิกการตรวจ
                        </button>
                     )}
                  </div>
                  
                  <div className="card-body p-4">
                     {isAnalyzing ? (
                        <div className="p-5 text-center my-4">
                           <Loader2 size={48} className="text-primary animate-spin mb-3 mx-auto" />
                           <h5 className="font-bold text-dark mb-1">กำลังสกัดข้อมูลผลแล็บด้วย AI OCR...</h5>
                           <p className="text-xs text-muted">Gemini 1.5 กำลังทำความเข้าใจตัวเลข ช่วงอ้างอิง และจับคู่แกนชีววิทยา 39 แกนแบบเรียลไทม์</p>
                        </div>
                     ) : ocrResult ? (
                        <div>
                           {/* 📋 Meta Form Elements */}
                           <div className="row g-3 mb-4 bg-light p-3 rounded-3 border">
                              <div className="col-md-6">
                                 <label className="form-label text-xs font-bold text-muted uppercase">ชื่อโรงพยาบาล/ห้องแล็บ</label>
                                 <input 
                                    type="text" 
                                    className="form-control form-control-sm"
                                    value={ocrResult.hospitalName} 
                                    onChange={(e) => setOcrResult({ ...ocrResult, hospitalName: e.target.value })}
                                 />
                              </div>
                              <div className="col-md-6">
                                 <label className="form-label text-xs font-bold text-muted uppercase">วันที่ตรวจสุขภาพ</label>
                                 <input 
                                    type="date" 
                                    className="form-control form-control-sm"
                                    value={ocrResult.testDate} 
                                    onChange={(e) => setOcrResult({ ...ocrResult, testDate: e.target.value })}
                                 />
                              </div>
                           </div>

                           {/* 🧪 Parameters Table */}
                           <div className="mb-4">
                              <div className="d-flex justify-content-between align-items-center mb-2">
                                 <h4 className="text-xs font-bold text-muted uppercase tracking-wider mb-0">Biomarker Values ({ocrResult.results.length})</h4>
                                 <button 
                                    onClick={handleAddParameter} 
                                    className="btn btn-primary btn-xs border d-flex align-items-center gap-1 text-[10px] py-1 px-2 font-bold"
                                 >
                                    <Plus size={10} /> เพิ่มค่าตรวจ
                                 </button>
                              </div>
                              
                              <div className="table-responsive rounded-3 border">
                                 <table className="table table-sm table-striped table-hover text-sm mb-0">
                                    <thead className="bg-light">
                                       <tr>
                                          <th className="p-2 ps-3 text-xs uppercase font-bold text-muted">Parameter Name</th>
                                          <th className="p-2 text-xs uppercase font-bold text-muted" style={{ width: "120px" }}>Value</th>
                                          <th className="p-2 text-xs uppercase font-bold text-muted" style={{ width: "100px" }}>Unit</th>
                                          <th className="p-2 text-xs uppercase font-bold text-muted" style={{ width: "120px" }}>Ref Range</th>
                                          <th className="p-2 text-xs uppercase font-bold text-muted" style={{ width: "110px" }}>Status</th>
                                          <th className="p-2 text-center" style={{ width: "50px" }}></th>
                                       </tr>
                                    </thead>
                                    <tbody>
                                       {ocrResult.results.map((r: any, i: number) => (
                                          <tr key={i} className="align-middle">
                                             <td className="p-2 ps-3">
                                                <input 
                                                   type="text" 
                                                   className="form-control form-control-xs border-0 bg-transparent font-bold"
                                                   value={r.parameter} 
                                                   onChange={(e) => handleParameterChange(i, "parameter", e.target.value)}
                                                   placeholder="e.g. ALT, HbA1c"
                                                />
                                             </td>
                                             <td className="p-2">
                                                <input 
                                                   type="text" 
                                                   className="form-control form-control-xs border-0 bg-transparent font-semibold text-primary"
                                                   value={r.value} 
                                                   onChange={(e) => handleParameterChange(i, "value", e.target.value)}
                                                   placeholder="e.g. 54"
                                                />
                                             </td>
                                             <td className="p-2">
                                                <input 
                                                   type="text" 
                                                   className="form-control form-control-xs border-0 bg-transparent text-muted"
                                                   value={r.unit} 
                                                   onChange={(e) => handleParameterChange(i, "unit", e.target.value)}
                                                   placeholder="e.g. U/L"
                                                />
                                             </td>
                                             <td className="p-2">
                                                <input 
                                                   type="text" 
                                                   className="form-control form-control-xs border-0 bg-transparent text-muted"
                                                   value={r.reference_range} 
                                                   onChange={(e) => handleParameterChange(i, "reference_range", e.target.value)}
                                                   placeholder="e.g. < 40"
                                                />
                                             </td>
                                             <td className="p-2">
                                                <select 
                                                   className={`form-select form-select-xs border-0 text-[10px] font-bold rounded-2 px-2 py-1 ${r.status === 'High' || r.status === 'Low' ? 'bg-danger bg-opacity-10 text-danger' : 'bg-success bg-opacity-10 text-success'}`}
                                                   value={r.status}
                                                   onChange={(e) => handleParameterChange(i, "status", e.target.value)}
                                                >
                                                   <option value="Normal">Normal</option>
                                                   <option value="High">High</option>
                                                   <option value="Low">Low</option>
                                                   <option value="Unclear">Unclear</option>
                                                </select>
                                             </td>
                                             <td className="p-2 text-center">
                                                <button 
                                                   onClick={() => handleDeleteParameter(i)} 
                                                   className="btn btn-link text-danger p-0 border-0 hover:scale-110 transition-transform"
                                                >
                                                   <Trash2 size={14} />
                                                </button>
                                             </td>
                                          </tr>
                                       ))}
                                    </tbody>
                                 </table>
                              </div>
                           </div>

                           {/* 🧬 Mapped Biological Axes */}
                           <div className="mb-4">
                              <div className="d-flex justify-content-between align-items-center mb-2">
                                 <h4 className="text-xs font-bold text-muted uppercase tracking-wider mb-0">Systems Biology Axis Analysis</h4>
                                 <button 
                                    onClick={handleAddAxis} 
                                    className="btn btn-primary btn-xs border d-flex align-items-center gap-1 text-[10px] py-1 px-2 font-bold"
                                 >
                                    <Plus size={10} /> เพิ่มความสัมพันธ์
                                 </button>
                              </div>

                              <div className="row g-3">
                                 {ocrResult.axis_analysis.map((axis: any, i: number) => (
                                    <div key={i} className="col-md-6">
                                       <div className="p-3 bg-white rounded-3 border border-1 h-100 d-flex flex-column justify-content-between transition-all" style={{ borderLeft: '4px solid #10B981', boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)', borderColor: '#E2E8F0' }}>
                                          <div>
                                             <div className="d-flex justify-content-between align-items-center mb-2">
                                                <div className="d-flex align-items-center gap-2 flex-grow-1">
                                                   <span className="badge text-white text-[10px] font-bold px-2 py-1.5 rounded-2" style={{ backgroundColor: '#10B981' }}>Axis {axis.axis_id}</span>
                                                   <input 
                                                      type="text" 
                                                      className="form-control form-control-xs border-0 bg-transparent font-bold py-0 text-sm flex-grow-1"
                                                      value={axis.axis_name} 
                                                      onChange={(e) => handleAxisChange(i, "axis_name", e.target.value)}
                                                      style={{ minWidth: "120px" }}
                                                   />
                                                </div>
                                                
                                                <div className="d-flex align-items-center gap-2">
                                                   <div className="d-flex align-items-center gap-1">
                                                      <small className="text-[10px] font-bold text-muted uppercase">Impact:</small>
                                                      <input 
                                                         type="number" 
                                                         className="form-control form-control-xs font-bold text-center text-primary"
                                                         value={axis.score_impact} 
                                                         onChange={(e) => handleAxisChange(i, "score_impact", Number(e.target.value))}
                                                         style={{ width: "55px" }}
                                                         min="0"
                                                         max="100"
                                                      />
                                                   </div>
                                                   
                                                   <button 
                                                      onClick={() => handleDeleteAxis(i)} 
                                                      className="btn btn-link text-danger p-0 border-0 hover:scale-110 transition-transform"
                                                   >
                                                      <Trash2 size={14} />
                                                   </button>
                                                </div>
                                             </div>
                                             
                                             <textarea 
                                                className="form-control form-control-xs text-xs text-dark mt-1" 
                                                rows={2}
                                                value={axis.reasoning}
                                                onChange={(e) => handleAxisChange(i, "reasoning", e.target.value)}
                                                placeholder="คำอธิบายผลกระทบต่อระบบอวัยวะและแกนชีวภาพ..."
                                             />
                                          </div>
                                       </div>
                                    </div>
                                 ))}
                              </div>
                           </div>

                           {/* 🚀 Action Buttons */}
                           <div className="d-flex justify-content-end gap-2 pt-3 border-top mt-4">
                              <button 
                                 onClick={() => setOcrResult(null)} 
                                 className="btn btn-light btn-sm px-4 py-2.5 font-bold rounded-3 transition-all border"
                                 style={{ 
                                    backgroundColor: '#F8FAFC', 
                                    color: '#64748B', 
                                    borderColor: '#E2E8F0',
                                    transition: 'all 0.2s ease-in-out'
                                 }}
                              >
                                 ปิดหน้าจอนี้
                              </button>
                               <button 
                                  onClick={handleVerifyAndSync} 
                                  disabled={isSaving}
                                  className="btn btn-sm px-4 py-2.5 font-bold rounded-3 shadow-md d-flex align-items-center gap-2 hover:scale-[1.02] active:scale-95 transition-all text-white border-0"
                                  style={{ 
                                     backgroundColor: '#10B981', 
                                     color: '#FFFFFF',
                                     boxShadow: '0 4px 14px rgba(16, 185, 129, 0.35)',
                                     transition: 'all 0.2s'
                                  }}
                               >
                                  {isSaving ? (
                                     <>
                                        <Loader2 size={16} className="animate-spin" /> กำลังตรวจสอบและซิงค์...
                                     </>
                                  ) : (
                                     <>
                                        <Save size={16} /> ยืนยันข้อมูล & อัปเดตเข้าระบบ Digital Twin
                                     </>
                                  )}
                               </button>
                           </div>
                        </div>
                     ) : (
                        <div className="p-5 text-center text-muted border border-dashed rounded-4 bg-light my-2">
                           <FileText size={56} className="mx-auto mb-3 opacity-25 text-primary" />
                           <h5 className="font-bold text-dark mb-1">ยินดีต้อนรับสู่ศูนย์บริการข้อมูลแล็บและประมวลผล OCR</h5>
                           <p className="text-xs max-w-lg mx-auto mb-4">
                              คุณสามารถเริ่มต้นใช้งานโดยเลือกคนไข้ด้านล่างนี้ แล้วอัปโหลดเอกสารผลตรวจสุขภาพเพื่อแปลงเป็น Digital Twin
                           </p>

                           {/* 🤵 Patient Selector Form */}
                           <div className="max-w-md mx-auto p-4 bg-white rounded-3 shadow-sm border border-light text-start mb-2">
                              <label className="form-label text-xs font-bold text-muted uppercase mb-2 d-flex align-items-center gap-1">
                                 <User size={12} className="text-primary" /> ขั้นตอนที่ 1: เลือกคนไข้ที่รับผลตรวจ
                              </label>
                              <select 
                                 className="form-select form-select-sm font-semibold mb-4"
                                 value={selectedPatientId} 
                                 onChange={(e) => setSelectedPatientId(e.target.value)}
                              >
                                 {patients.map((p) => (
                                    <option key={p.id} value={p.id}>
                                       {p.fname ? `${p.fname} ${p.lname || ""}` : p.name} (HN: {p.hn || "N/A"})
                                    </option>
                                 ))}
                              </select>

                              <label className="form-label text-xs font-bold text-muted uppercase mb-2 d-flex align-items-center gap-1">
                                 <Upload size={12} className="text-primary" /> ขั้นตอนที่ 2: อัปโหลดเอกสาร / รูปภาพผลแล็บ
                              </label>
                              <label 
                                 className="btn btn-success w-100 font-bold uppercase py-2 cursor-pointer shadow-sm d-flex align-items-center justify-content-center gap-2 text-white"
                                 style={{
                                    backgroundColor: "#10B981",
                                    borderColor: "#10B981",
                                    fontSize: "13px",
                                    fontWeight: 700,
                                    borderRadius: "8px",
                                    boxShadow: "0 4px 6px -1px rgba(16, 185, 129, 0.25)",
                                    transition: "all 0.2s ease"
                                 }}
                              >
                                 <Upload size={16} /> เลือกไฟล์รูปภาพผลแล็บเพื่อสแกน
                                 <input type="file" className="d-none" accept="image/*" onChange={handleFileUpload} />
                              </label>
                           </div>

                           {/* 🖼️ Chat Images Gallery */}
                           {selectedPatientId && (
                              <div className="max-w-md mx-auto mt-4 p-4 bg-white rounded-3 shadow-sm border border-light text-start">
                                 <label className="form-label text-xs font-bold text-muted uppercase mb-3 d-flex align-items-center gap-1">
                                    🖼️ รูปภาพผลแล็บแนบในแชทคัดกรอง ({chatImages.length})
                                 </label>
                                 {chatImages.length === 0 ? (
                                    <div className="p-3 text-center text-muted rounded bg-light" style={{ fontSize: '11px' }}>
                                       ไม่พบเอกสารรูปภาพในประวัติแชทคนไข้รายนี้
                                    </div>
                                 ) : (
                                    <div className="row g-2">
                                       {chatImages.map((img, index) => (
                                          <div key={index} className="col-4">
                                             <div 
                                                className="chat-img-thumb border rounded overflow-hidden position-relative"
                                                style={{ height: '70px', borderColor: '#E2E8F0' }}
                                                onClick={() => handleScanChatImage(img.imageBase64)}
                                                title="คลิกเพื่อสั่งสแกนประมวลผลรูปภาพนี้ด้วย AI OCR"
                                             >
                                                <img 
                                                   src={img.imageBase64} 
                                                   alt="Chat Attachment" 
                                                   className="w-100 h-100 object-fit-cover" 
                                                />
                                                <div className="chat-img-overlay position-absolute w-100 h-100 top-0 left-0 d-flex align-items-center justify-content-center text-white text-[10px] font-bold">
                                                   สแกนรูป
                                                </div>
                                             </div>
                                          </div>
                                       ))}
                                    </div>
                                 )}
                              </div>
                           )}

                           {/* 📜 Patient Recent History in Central Area */}
                           {selectedPatientId && allResults.filter((r: any) => r.patientId === selectedPatientId).length > 0 && (
                              <div className="max-w-md mx-auto mt-4 p-4 bg-white rounded-3 shadow-sm border border-light text-start">
                                 <h6 className="text-xs font-bold text-muted uppercase mb-3 d-flex align-items-center gap-1">
                                    <Activity size={12} className="text-primary" /> ประวัติประมวลผลล่าสุดของคนไข้รายนี้
                                 </h6>
                                 <div className="d-flex flex-column gap-2">
                                    {allResults
                                       .filter((r: any) => r.patientId === selectedPatientId)
                                       .slice(0, 3)
                                       .map((item) => (
                                          <div 
                                             key={item.id}
                                             onClick={() => handleSelectPending(item)}
                                             className="p-2.5 rounded-2 border border-light hover:bg-light transition-all cursor-pointer d-flex justify-content-between align-items-center"
                                             style={{ fontSize: "11px" }}
                                          >
                                             <div>
                                                <div className="font-bold text-dark">{item.hospitalName || "ไม่ระบุแล็บ"}</div>
                                                <div className="text-muted mt-0.5">วันที่: {item.testDate}</div>
                                             </div>
                                             <div className="d-flex align-items-center gap-2">
                                                <span className={`badge ${item.verified ? 'bg-success bg-opacity-10 text-success' : 'bg-warning bg-opacity-10 text-warning'} px-2 py-1`} style={{ fontSize: "9px" }}>
                                                   {item.verified ? 'เสร็จสมบูรณ์' : 'รอรีวิว'}
                                                </span>
                                                <ArrowRight size={12} className="text-muted" />
                                             </div>
                                          </div>
                                       ))}
                                 </div>
                              </div>
                           )}
                        </div>
                     )}
                  </div>
               </div>
            </div>

            {/* ⏱️ Right Column: Pending & Recent List */}
            <div className="col-lg-4">
               {/* 📂 Pending Approvals Grid */}
               <div className="card border-0 shadow-sm bg-white rounded-4 overflow-hidden mb-4">
                  <div className="card-header bg-transparent border-bottom border-light py-3 d-flex justify-content-between align-items-center">
                     <h3 className="card-title text-[11px] font-bold uppercase text-muted tracking-widest mb-0 d-flex align-items-center gap-2">
                        <Clock size={14} className="text-warning animate-pulse" /> รายการรออนุมัติ ({pendingResults.length})
                     </h3>
                     <button onClick={loadLabResultsList} className="btn btn-light btn-xs border p-1 rounded-2 shadow-xs">
                        <RefreshCw size={12} />
                     </button>
                  </div>
                  <div className="card-body p-0 max-h-[400px] overflow-y-auto">
                     {pendingResults.length > 0 ? (
                        <div className="list-group list-group-flush">
                           {pendingResults.map((item) => (
                              <div key={item.id} className="list-group-item border-bottom border-light px-4 py-3 hover:bg-light transition-colors">
                                 <div className="d-flex justify-content-between align-items-start mb-2">
                                    <div>
                                       <span className="font-bold text-sm text-dark d-block">{item.patientName}</span>
                                       <small className="text-muted text-[10px] font-bold uppercase block mt-0.5">
                                          แล็บ: {item.hospitalName} • {item.testDate}
                                       </small>
                                    </div>
                                    <span className="badge bg-danger bg-opacity-10 text-danger text-[10px] font-bold px-2 py-1">
                                       {item.results?.filter((r: any) => r.status !== 'Normal').length || 0} Alerts
                                    </span>
                                 </div>
                                 
                                 <div className="d-flex justify-content-between align-items-center mt-2.5">
                                    <small className="text-[10px] text-muted font-semibold">
                                       จำนวนตรวจพบ: {item.results?.length || 0} ค่า
                                    </small>
                                    <div className="d-flex gap-1">
                                       <button 
                                          onClick={() => handleSelectPending(item)} 
                                          className="btn btn-success btn-xs border px-2 py-1 text-[10px] font-bold d-flex align-items-center gap-1 text-white"
                                          style={{
                                             backgroundColor: "#10B981",
                                             borderColor: "#10B981"
                                          }}
                                       >
                                          <Eye size={10} /> รีวิว
                                       </button>
                                    </div>
                                 </div>
                              </div>
                           ))}
                        </div>
                     ) : (
                        <div className="p-4 text-center text-muted">
                           <ShieldCheck size={32} className="mx-auto mb-2 text-success opacity-50" />
                           <p className="text-xs mb-0">ไม่มีผลแล็บค้างตรวจสอบในระบบ</p>
                        </div>
                     )}
                  </div>
                  <div className="card-footer bg-white border-top border-light text-center py-2.5">
                     <small className="text-muted italic text-[10px]">ผลแล็บที่ได้รับอนุมัติจะซิงค์เข้า Digital Twin อัตโนมัติ</small>
                  </div>
               </div>

               {/* 📜 System Status Widget */}
                <div className="card border-0 shadow-sm bg-white rounded-4 overflow-hidden mb-4">
                   <div className="card-header bg-transparent border-bottom border-light py-3">
                      <h3 className="card-title text-[11px] font-bold uppercase text-muted tracking-widest mb-0 d-flex align-items-center gap-2">
                         <Activity size={14} className="text-primary" /> ประวัติประมวลผลล่าสุด {patients.find(p => p.id === selectedPatientId) ? `(คุณ${patients.find(p => p.id === selectedPatientId)?.fname || patients.find(p => p.id === selectedPatientId)?.name})` : ""}
                      </h3>
                   </div>
                   <div className="card-body p-0 max-h-[300px] overflow-y-auto">
                      {allResults.filter((r: any) => r.patientId === selectedPatientId).length > 0 ? (
                         <div className="list-group list-group-flush">
                            {allResults
                               .filter((r: any) => r.patientId === selectedPatientId)
                               .slice(0, 5)
                               .map((item) => (
                                  <div 
                                     key={item.id} 
                                     onClick={() => handleSelectPending(item)}
                                     className="list-group-item list-group-item-action border-bottom border-light px-4 py-2.5 hover:bg-light transition-colors text-xs cursor-pointer d-flex justify-content-between align-items-center"
                                  >
                                     <div className="flex-grow-1">
                                        <div className="d-flex justify-content-between align-items-center mb-1">
                                           <span className="font-bold text-dark">{item.hospitalName || "ผลแล็บวิเคราะห์"}</span>
                                           <span className={`badge text-[9px] ${item.verified ? 'bg-success text-white' : 'bg-warning text-dark'}`}>
                                              {item.verified ? 'Verified & Synced' : 'Pending'}
                                           </span>
                                        </div>
                                        <div className="text-[10px] text-muted d-flex justify-content-between align-items-center">
                                           <span>วันที่ตรวจ: {item.testDate}</span>
                                           <span className="text-primary font-bold hover:underline d-flex align-items-center gap-0.5">
                                              คลิกเพื่อดู/แก้ไข <ArrowRight size={10} />
                                           </span>
                                        </div>
                                     </div>
                                  </div>
                               ))}
                         </div>
                      ) : (
                         <div className="p-4 text-center text-muted">
                            <p className="text-xs mb-0">ไม่มีประวัติการบันทึกแล็บสำหรับคนไข้รายนี้</p>
                         </div>
                      )}
                   </div>
                </div>

               {/* 🛡️ Privacy and Compliance Shield */}
               <div className="p-4 bg-primary bg-opacity-5 rounded-4 border border-primary border-opacity-10 d-flex align-items-center gap-3">
                  <div className="bg-primary text-white p-2 rounded-circle shadow-sm">
                     <ShieldCheck size={20} />
                  </div>
                  <div>
                     <h6 className="fw-bold text-primary mb-1 text-[10px] uppercase tracking-widest">Clinical Security Compliant</h6>
                     <p className="text-[10px] text-muted mb-0">โครงสร้างเก็บข้อมูลผ่านรหัสความปลอดภัยตามมาตรฐาน PDPA ของแพทย์และคนไข้เพื่อการรักษาที่มีประสิทธิภาพสูงสุด</p>
                  </div>
               </div>
            </div>
         </div>
      
      <style jsx>{`
        .chat-img-thumb {
          cursor: pointer;
          transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .chat-img-thumb:hover {
          transform: translateY(-2px) scale(1.03);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        .chat-img-overlay {
          opacity: 0;
          transition: opacity 0.2s ease;
          background: rgba(10, 92, 142, 0.6);
        }
        .chat-img-thumb:hover .chat-img-overlay {
          opacity: 1;
        }
      `}</style>
      </div>
   );
}
