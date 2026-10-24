"use client";

import React, { useState, useEffect } from "react";
import { Brain, Cpu, Database, Trash2, ShieldAlert, CheckCircle2, TrendingUp, RefreshCw } from "lucide-react";
import Swal from "sweetalert2";

export default function TSPILearningBrainConsole() {
   const [logs, setLogs] = useState<any[]>([]);
   const [stats, setStats] = useState<any>({ logged_cases: 0, ready: false, required_cases: 30 });
   const [loading, setLoading] = useState(true);
   const [training, setTraining] = useState(false);
   const [coefficients, setCoefficients] = useState<any>(null);

   const fetchLogsAndStats = async () => {
      setLoading(true);
      const token = localStorage.getItem("doctor_access_token") || sessionStorage.getItem("doctor_access_token");
      const headers: Record<string, string> = {};
      if (token) {
         headers["Authorization"] = `Bearer ${token}`;
      }

      const apiBase = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";
      try {
         // 1. Fetch stats
         const statsRes = await fetch(`${apiBase}/api/ai/brain-training-stats/`, { headers });
         if (statsRes.ok) {
            const statsData = await statsRes.json();
            setStats(statsData);
         }

         // 2. Fetch recent logs
         const logsRes = await fetch(`${apiBase}/api/brain-training-logs/`, { headers });
         if (logsRes.ok) {
            const logsData = await logsRes.json();
            setLogs(logsData.results || logsData || []);
         }
      } catch (err) {
         console.error("Failed to load TSPI Brain console data:", err);
      } finally {
         setLoading(false);
      }
   };

   useEffect(() => {
      fetchLogsAndStats();
   }, []);

   const handleTrainModel = async () => {
      if (stats.logged_cases === 0) {
         Swal.fire({
            icon: "warning",
            title: "ไม่สามารถเริ่มฝึกฝนได้",
            text: "กรุณาสะสมเคสทดสอบจากการประเมินคนไข้ด้วย AI ก่อนอย่างน้อย 1 เคส",
            confirmButtonColor: "#0A5C8E"
         });
         return;
      }

      setTraining(true);
      const token = localStorage.getItem("doctor_access_token") || sessionStorage.getItem("doctor_access_token");
      
      try {
         const apiBase = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";
         const res = await fetch(`${apiBase}/api/ai/train-brain-model/`, {
            method: "POST",
            headers: {
               "Content-Type": "application/json",
               ...(token ? { "Authorization": `Bearer ${token}` } : {})
            }
         });

         if (res.ok) {
            const result = await res.json();
            setCoefficients(result.coefficients);
            Swal.fire({
               icon: "success",
               title: "ฝึกฝนสมองกลโลคอลสำเร็จ!",
               text: result.message,
               confirmButtonColor: "#10B981"
            });
            fetchLogsAndStats();
         } else {
            const errData = await res.json();
            throw new Error(errData.message || "การคำนวณโมเดลล้มเหลว");
         }
      } catch (err: any) {
         Swal.fire({
            icon: "error",
            title: "การฝึกฝนล้มเหลว",
            text: err.message,
            confirmButtonColor: "#EF4444"
         });
      } finally {
         setTraining(false);
      }
   };

   const handleDeleteLog = async (id: number) => {
      const result = await Swal.fire({
         title: "ยืนยันการลบชุดข้อมูล?",
         text: "การลบจะเอาคู่วิเคราะห์เคสนี้ออกจากคลังความรู้การจดจำของสมองกลถาวร",
         icon: "warning",
         showCancelButton: true,
         confirmButtonColor: "#EF4444",
         cancelButtonColor: "#6B7280",
         confirmButtonText: "ใช่, ลบออก",
         cancelButtonText: "ยกเลิก"
      });

      if (!result.isConfirmed) return;

      const token = localStorage.getItem("doctor_access_token") || sessionStorage.getItem("doctor_access_token");
      try {
         const deleteHeaders: Record<string, string> = {};
         if (token) {
            deleteHeaders["Authorization"] = `Bearer ${token}`;
         }
         const apiBase = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";
         const res = await fetch(`${apiBase}/api/brain-training-logs/${id}/`, {
            method: "DELETE",
            headers: deleteHeaders
         });

         if (res.ok) {
            Swal.fire({
               icon: "success",
               title: "ลบสำเร็จ",
               text: "ลบชุดข้อมูลเรียนรู้ออกแล้ว",
               confirmButtonColor: "#10B981",
               timer: 1500
            });
            fetchLogsAndStats();
         }
      } catch (err) {
         console.error("Failed to delete log:", err);
      }
   };

   // Calculate learning progress percentage
   const progressPercent = Math.min(100, Math.round((stats.logged_cases / stats.required_cases) * 100));

   return (
      <div className="container-fluid py-4" style={{ minHeight: "100vh", backgroundColor: "#F3F4F6", fontFamily: "inherit" }}>
         {/* Header */}
         <div className="d-flex align-items-center justify-content-between mb-4 pb-3 border-bottom" style={{ borderColor: "#E5E7EB" }}>
            <div className="d-flex align-items-center gap-3">
               <div style={{
                  background: "linear-gradient(135deg, #0A5C8E 0%, #0D82CA 100%)",
                  borderRadius: "12px",
                  padding: "10px",
                  color: "white",
                  boxShadow: "0 4px 10px rgba(10, 92, 142, 0.2)"
               }}>
                  <Brain size={32} />
               </div>
               <div>
                  <h2 style={{ fontSize: "22px", fontWeight: 800, color: "#1F2937", margin: 0 }}>TSPI Learning Brain Console</h2>
                  <span style={{ fontSize: "12px", color: "#6B7280" }}>แผงควบคุมและสะสมความรู้ปัญญาประดิษฐ์โลคอลเฉพาะคลินิก</span>
               </div>
            </div>
            <button
               onClick={fetchLogsAndStats}
               className="btn btn-outline-secondary d-flex align-items-center gap-2"
               style={{ borderRadius: "8px", fontSize: "13px" }}
            >
               <RefreshCw size={14} className={loading ? "spin-animation" : ""} />
               รีเฟรชข้อมูล
            </button>
         </div>

         {/* Dashboard Cards Grid */}
         <div className="row g-4 mb-4">
            {/* 1. Training Status Card */}
            <div className="col-12 col-md-4">
               <div className="card border-0 shadow-sm p-4 h-100" style={{ borderRadius: "16px", backgroundColor: "white" }}>
                  <div className="d-flex align-items-center justify-content-between mb-3">
                     <span style={{ fontSize: "14px", fontWeight: 700, color: "#4B5563" }}>ความก้าวหน้าการสะสมเคส</span>
                     <Database size={20} style={{ color: "#0A5C8E" }} />
                  </div>
                  <h3 style={{ fontSize: "28px", fontWeight: 800, color: "#1F2937", marginBottom: "8px" }}>
                     {stats.logged_cases} <span style={{ fontSize: "16px", fontWeight: 500, color: "#6B7280" }}>/ {stats.required_cases} เคส</span>
                  </h3>
                  
                  {/* Progress Bar */}
                  <div className="progress mb-3" style={{ height: "10px", borderRadius: "10px", backgroundColor: "#E5E7EB" }}>
                     <div
                        className="progress-bar progress-bar-striped progress-bar-animated"
                        style={{
                           width: `${progressPercent}%`,
                           backgroundColor: progressPercent >= 100 ? "#10B981" : "#0A5C8E",
                           borderRadius: "10px"
                        }}
                     />
                  </div>

                  <div className="d-flex align-items-center gap-2 mb-2">
                     {stats.ready ? (
                        <CheckCircle2 size={16} style={{ color: "#10B981" }} />
                     ) : (
                        <ShieldAlert size={16} style={{ color: "#F59E0B" }} />
                     )}
                     <span style={{ fontSize: "12px", color: "#4B5563", fontWeight: 600 }}>
                        {stats.ready ? "สมองกลพร้อมเริ่มทดลองคำนวณขั้นพื้นฐานแล้ว" : `ต้องการสะสมอีกอย่างน้อย ${stats.required_cases - stats.logged_cases} เคสเพื่อให้แม่นยำ`}
                     </span>
                  </div>
               </div>
            </div>

            {/* 2. Machine Learning Trainer Card */}
            <div className="col-12 col-md-4">
               <div className="card border-0 shadow-sm p-4 h-100" style={{ borderRadius: "16px", backgroundColor: "white" }}>
                  <div className="d-flex align-items-center justify-content-between mb-3">
                     <span style={{ fontSize: "14px", fontWeight: 700, color: "#4B5563" }}>การฝึกฝนปัญญาประดิษฐ์โลคอล</span>
                     <Cpu size={20} style={{ color: "#10B981" }} />
                  </div>
                  <p style={{ fontSize: "12.5px", color: "#6B7280", lineHeight: "1.5", marginBottom: "16px" }}>
                     ประมวลผลวิเคราะห์คู่ข้อมูล (Inputs/Outputs) ด้วยวิธีถดถอยพหุคูณ OLS Ridge Regression ทันทีแบบออฟไลน์ เพื่อสร้างค่าน้ำหนักอัจฉริยะในเครื่อง
                  </p>
                  <button
                     onClick={handleTrainModel}
                     disabled={training}
                     className="btn btn-success w-100 py-2 d-flex align-items-center justify-content-center gap-2 text-white"
                     style={{
                        borderRadius: "10px",
                        backgroundColor: training ? "#6B7280" : "#10B981",
                        borderColor: "transparent",
                        fontWeight: 700,
                        fontSize: "14px"
                     }}
                  >
                     <RefreshCw size={16} className={training ? "spin-animation" : ""} />
                     {training ? "กำลังคำนวณค่าน้ำหนัก..." : "เริ่มกระบวนการฝึกฝน (Train)"}
                  </button>
               </div>
            </div>

            {/* 3. Model Accuracy Info */}
            <div className="col-12 col-md-4">
               <div className="card border-0 shadow-sm p-4 h-100" style={{ borderRadius: "16px", backgroundColor: "white" }}>
                  <div className="d-flex align-items-center justify-content-between mb-3">
                     <span style={{ fontSize: "14px", fontWeight: 700, color: "#4B5563" }}>สถิติประสิทธิภาพโมเดล</span>
                     <TrendingUp size={20} style={{ color: "#6366F1" }} />
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                     <div className="d-flex justify-content-between border-bottom pb-2" style={{ borderColor: "#F3F4F6", fontSize: "13px" }}>
                        <span style={{ color: "#6B7280" }}>ประเภทสมองกล:</span>
                        <strong style={{ color: "#1F2937" }}>OLS Ridge Regressor</strong>
                     </div>
                     <div className="d-flex justify-content-between border-bottom pb-2" style={{ borderColor: "#F3F4F6", fontSize: "13px" }}>
                        <span style={{ color: "#6B7280" }}>สถิติฟีเจอร์พิจารณา:</span>
                        <strong style={{ color: "#1F2937" }}>6 ตัวแปรชีวภาพหลัก</strong>
                     </div>
                     <div className="d-flex justify-content-between" style={{ fontSize: "13px" }}>
                        <span style={{ color: "#6B7280" }}>ความผิดเพี้ยนเป้าหมาย (MSE):</span>
                        <strong style={{ color: "#1F2937" }}>{stats.logged_cases > 0 ? "คำนวณปกติ" : "รอข้อมูลฝึกฝน"}</strong>
                     </div>
                  </div>
               </div>
            </div>
         </div>

         {/* Main Content splits */}
         <div className="row g-4">
            {/* Left Column: Recent Logs Table */}
            <div className="col-12 col-lg-8">
               <div className="card border-0 shadow-sm p-4" style={{ borderRadius: "16px", backgroundColor: "white" }}>
                  <h4 style={{ fontSize: "16px", fontWeight: 800, color: "#1F2937", marginBottom: "16px" }}>
                     คลังคู่ข้อมูลจำลองล่าสุด (Training Registry)
                  </h4>
                  {logs.length === 0 ? (
                     <div className="text-center py-5" style={{ color: "#9CA3AF" }}>
                        <Database size={36} className="mb-2" style={{ opacity: 0.5 }} />
                        <p style={{ fontSize: "13.5px", margin: 0 }}>ยังไม่มีข้อมูลสะสมในระบบ รันการประเมินคนไข้ผ่าน AI เพื่อเก็บเกี่ยวบทเรียนคู่แรก</p>
                     </div>
                  ) : (
                     <div className="table-responsive">
                        <table className="table align-middle" style={{ fontSize: "13px" }}>
                           <thead>
                              <tr style={{ color: "#4B5563", borderBottom: "2px solid #F3F4F6" }}>
                                 <th style={{ padding: "10px 0" }}> HN คนไข้ </th>
                                 <th> อาการ </th>
                                 <th> ค่าแล็บจำลอง (Inputs) </th>
                                 <th> คะแนนเป้าหมาย (Outputs) </th>
                                 <th> เอนจินบันทึก </th>
                                 <th className="text-end"> จัดการ </th>
                              </tr>
                           </thead>
                           <tbody>
                              {logs.map((log: any) => {
                                 const labs = log.inputs?.labs || {};
                                 const axesKeys = Object.keys(log.output_axes || {});
                                 return (
                                    <tr key={log.id} style={{ borderBottom: "1px solid #F3F4F6" }}>
                                       <td style={{ padding: "12px 0", fontWeight: 700, color: "#0A5C8E" }}>
                                          {log.patient_name} <br/>
                                          <span style={{ fontSize: "11px", color: "#6B7280", fontWeight: 500 }}>HN: {log.patient_hn || "N/A"}</span>
                                       </td>
                                       <td style={{ maxWidth: "160px", textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap" }}>
                                          {log.inputs?.symptoms || "N/A"}
                                       </td>
                                       <td>
                                          <div style={{ fontSize: "11px", display: "flex", flexWrap: "wrap", gap: "4px" }}>
                                             {labs.fbs && <span className="badge bg-light text-dark border">FBS: {labs.fbs}</span>}
                                             {labs.hba1c && <span className="badge bg-light text-dark border">HbA1c: {labs.hba1c}%</span>}
                                             {labs.crp && <span className="badge bg-light text-dark border">CRP: {labs.crp}</span>}
                                             {labs.ldl && <span className="badge bg-light text-dark border">LDL: {labs.ldl}</span>}
                                          </div>
                                       </td>
                                       <td style={{ fontWeight: 600, color: "#1F2937" }}>
                                          ปรับจูน {axesKeys.length} แกนสรีรวิทยา
                                       </td>
                                       <td>
                                          <span className="badge" style={{ backgroundColor: "#E0F2FE", color: "#0369A1" }}>
                                             {log.engine_used}
                                          </span>
                                       </td>
                                       <td className="text-end">
                                          <button
                                             onClick={() => handleDeleteLog(log.id)}
                                             className="btn text-danger p-1"
                                             style={{ background: "transparent", border: "none" }}
                                          >
                                             <Trash2 size={16} />
                                          </button>
                                       </td>
                                    </tr>
                                 );
                              })}
                           </tbody>
                        </table>
                     </div>
                  )}
               </div>
            </div>

            {/* Right Column: Model Coefficients Inspector */}
            <div className="col-12 col-lg-4">
               <div className="card border-0 shadow-sm p-4" style={{ borderRadius: "16px", backgroundColor: "white" }}>
                  <h4 style={{ fontSize: "16px", fontWeight: 800, color: "#1F2937", marginBottom: "16px" }}>
                     ดัชนีผลกระทบฟีเจอร์ (Feature Impact Coefficients)
                  </h4>
                  {!coefficients ? (
                     <div className="text-center py-5" style={{ color: "#9CA3AF" }}>
                        <Brain size={36} className="mb-2" style={{ opacity: 0.5 }} />
                        <p style={{ fontSize: "13px", margin: 0 }}>กรุณากดรัน "กระบวนการฝึกฝน (Train)" ด้านบนเพื่อดูค่าน้ำหนักแล็บที่ส่งผลต่อสรีรวิทยา</p>
                     </div>
                  ) : (
                     <div>
                        <p style={{ fontSize: "12px", color: "#6B7280", marginBottom: "12px" }}>
                           ค่าบวกบ่งบอกฟีเจอร์กระตุ้นความตึงเครียดของแกน ค่าน้อยแสดงความเสถียร
                        </p>
                        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                           {Object.keys(coefficients).map((key) => {
                              const coefs = coefficients[key] || [];
                              // Compute average absolute weight of this feature across all 39 axes
                              const avgWeight = coefs.reduce((sum: number, val: number) => sum + Math.abs(val), 0) / coefs.length;
                              return (
                                 <div key={key} style={{ background: "#F9FAFB", padding: "10px", borderRadius: "8px" }}>
                                    <div className="d-flex justify-content-between mb-1" style={{ fontSize: "12.5px" }}>
                                       <strong style={{ color: "#374151", textTransform: "uppercase" }}>{key}</strong>
                                       <span style={{ color: "#0A5C8E", fontWeight: 700 }}>เฉลี่ย: {avgWeight.toFixed(3)}</span>
                                    </div>
                                    <div className="progress" style={{ height: "4px", backgroundColor: "#E5E7EB" }}>
                                       <div
                                          className="progress-bar"
                                          style={{
                                             width: `${Math.min(100, avgWeight * 300)}%`,
                                             backgroundColor: "#0A5C8E"
                                          }}
                                       />
                                    </div>
                                 </div>
                              );
                           })}
                        </div>
                     </div>
                  )}
               </div>
            </div>
         </div>

         {/* Spin and Fade animation keyframes inline */}
         <style jsx global>{`
            @keyframes spin {
               from { transform: rotate(0deg); }
               to { transform: rotate(360deg); }
            }
            .spin-animation {
               animation: spin 1s linear infinite;
            }
         `}</style>
      </div>
   );
}
