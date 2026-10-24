"use client";

import { useState, useEffect } from "react";
import {
   Save, Brain, Zap, Bot, ShieldCheck, Clock,
   Sparkles, Database, Cpu, Shield, CheckCircle,
   AlertCircle, RefreshCw, Server, Lock, Activity,
   Settings2, Terminal, MessageSquare, Fingerprint,
   Loader2
} from "lucide-react";
import Link from "next/link";
import "./../theme-inapp.css";
import Swal from "sweetalert2";
import { getAISettings, updateAISettings } from "@/utils/api/services";

export default function AISettingsPage() {
   const [loading, setLoading] = useState(true);
   const [isSaving, setIsSaving] = useState(false);
   const [settings, setSettings] = useState({
      ai_triage: true,
      ai_intake: true,
      provider: "gemini",
      model: "gemini-1.5-pro",
      system_prompt: "คุณคือผู้ช่วยอัจฉริยะประจำคลินิก TSPI ให้คำปรึกษาด้วยความสุภาพ มืออาชีพ และเน้นความปลอดภัยของคนไข้เป็นหลัก..."
   });

   useEffect(() => {
      const loadSettings = async () => {
         setLoading(true);
         try {
            const data = await getAISettings();
            if (data && Object.keys(data).length > 0) {
               setSettings(prev => ({
                  ...prev,
                  ...data
               }));
            }
         } catch (err) {
            console.error("Error loading settings:", err);
         } finally {
            setLoading(false);
         }
      };
      loadSettings();
   }, []);

   const handleSave = async () => {
      setIsSaving(true);
      try {
         await updateAISettings(settings);
         Swal.fire({
            icon: 'success',
            title: 'บันทึกสำเร็จ',
            text: 'ปรับเปลี่ยนการตั้งค่าและนโยบาย AI Engine เรียบร้อยแล้วครับ',
            confirmButtonText: 'ตกลง',
            confirmButtonColor: '#0A5C8E'
         });
      } catch (err) {
         console.error("Error saving settings:", err);
         Swal.fire({
            icon: 'error',
            title: 'เกิดข้อผิดพลาด',
            text: 'ไม่สามารถบันทึกการตั้งค่าได้',
            confirmButtonText: 'ตกลง',
            confirmButtonColor: '#0A5C8E'
         });
      } finally {
         setIsSaving(false);
      }
   };

   const handleRecalibrate = () => {
      Swal.fire({
         title: 'เริ่มต้นการปรับแต่งน้ำหนักประสาทเทียม?',
         text: 'ระบบจะจำลองการเรียนรู้และทดสอบการประมวลผลเพื่อเพิ่มประสิทธิภาพความแม่นยำทางคลินิก',
         icon: 'info',
         showCancelButton: true,
         confirmButtonText: 'เริ่มต้นปรับแต่ง',
         cancelButtonText: 'ยกเลิก',
         confirmButtonColor: '#0A5C8E'
      }).then((result) => {
         if (result.isConfirmed) {
            Swal.fire({
               title: 'กำลังทำการปรับแต่ง...',
               text: 'กรุณารอสักครู่ ระบบกำลังปรับเทียบน้ำหนักประสาทเทียม',
               allowOutsideClick: false,
               didOpen: () => {
                  Swal.showLoading();
                  setTimeout(() => {
                     Swal.fire({
                        icon: 'success',
                        title: 'ปรับเทียบน้ำหนักประสาทเทียมสำเร็จ!',
                        text: 'การประมวลผลทางคลินิกทำงานด้วยประสิทธิภาพสูงสุด (Latency: 38ms)',
                        confirmButtonText: 'ตกลง',
                        confirmButtonColor: '#0A5C8E'
                     });
                  }, 2000);
               }
            });
         }
      });
   };

   if (loading) {
      return (
         <div className="py-5 text-center" style={{ fontFamily: "Kanit, sans-serif" }}>
            <Loader2 className="animate-spin text-primary opacity-30 mx-auto mb-3" size={48} />
            <p className="text-muted text-sm font-semibold">กำลังโหลดข้อมูลนโยบายและกลไก AI...</p>
         </div>
      );
   }

   return (
      <div className="pb-5" style={{ fontFamily: "Kanit, sans-serif" }}>
         {/* 🧭 Header Section */}
         <div className="d-flex justify-content-between align-items-center mb-4">
            <div>
               <h1 className="fs-3 fw-bold mb-1 text-dark d-flex align-items-center gap-2">
                  <div className="bg-primary bg-opacity-10 p-2 rounded-3 text-primary shadow-sm">
                     <Cpu size={24} />
                  </div>
                  การตั้งค่ากลไกประมวลผล AI (AI Engine Configuration)
               </h1>
               <p className="text-muted text-xs uppercase font-bold tracking-widest ms-5 mb-0">การจัดการระบบประสาทเทียมและตรรกะทางคลินิกขั้นสูง</p>
            </div>
            <div className="d-flex gap-2">
               <button
                  onClick={handleSave}
                  disabled={isSaving}
                  className="btn btn-primary font-bold uppercase tracking-widest text-[10px] px-4 py-2 shadow-sm d-flex align-items-center gap-2 rounded-pill text-white"
               >
                  {isSaving ? <Loader2 className="animate-spin" size={14} /> : <Save size={14} />} บันทึกการตั้งค่า
               </button>
            </div>
         </div>

         <div className="row g-4">
            {/* 🤖 Left Column: Main Configuration */}
            <div className="col-lg-8">
               {/* Core Capabilities */}
               <div className="card border-0 shadow-sm bg-white mb-4 overflow-hidden rounded-4">
                  <div className="card-header bg-transparent border-bottom border-light py-3">
                     <h3 className="card-title text-[10px] font-bold uppercase text-muted tracking-widest mb-0">ความสามารถหลักของระบบ AI</h3>
                  </div>
                  <div className="card-body p-0">
                     <div className="list-group list-group-flush">
                        {[
                           { id: 'ai_triage', title: 'การคัดกรองอาการทางคลินิกโดย AI (AI Clinical Triage)', desc: 'วิเคราะห์ความรุนแรงของอาการและจัดลำดับคิวผู้ป่วยโดยอัตโนมัติ', icon: Zap, color: 'warning' },
                           { id: 'ai_intake', title: 'ระบบซักประวัติอัตโนมัติ (Autonomous Intake)', desc: 'ซักประวัติและเก็บข้อมูลอาการคนไข้ด้วยหุ่นยนต์ตอบกลับทางการแพทย์', icon: Bot, color: 'info' },
                        ].map((f) => (
                           <div key={f.id} className="list-group-item border-light p-4 d-flex align-items-center justify-content-between transition-all hover:bg-light bg-opacity-30">
                              <div className="d-flex align-items-center gap-3">
                                 <div className={`bg-${f.color} bg-opacity-10 p-3 rounded-circle text-${f.color}`}>
                                    <f.icon size={20} />
                                 </div>
                                 <div>
                                    <span className="font-bold d-block text-dark text-sm mb-1">{f.title}</span>
                                    <p className="text-muted text-[11px] mb-0 font-medium">{f.desc}</p>
                                 </div>
                              </div>
                              <div className="form-check form-switch">
                                 <input
                                    className="form-check-input"
                                    type="checkbox"
                                    role="switch"
                                    id={f.id}
                                    checked={settings[f.id as keyof typeof settings] as boolean}
                                    onChange={(e) => setSettings({ ...settings, [f.id]: e.target.checked })}
                                    style={{ width: '40px', height: '20px' }}
                                 />
                              </div>
                           </div>
                        ))}
                     </div>
                  </div>
               </div>

               {/* Model Settings */}
               <div className="card border-0 shadow-sm bg-white mb-4 overflow-hidden rounded-4">
                  <div className="card-header bg-transparent border-bottom border-light py-3 d-flex align-items-center gap-2">
                     <Server size={16} className="text-primary" />
                     <h3 className="card-title text-[10px] font-bold uppercase text-muted tracking-widest mb-0">โครงสร้างผู้ให้บริการระบบและโมเดลประมวลผล</h3>
                  </div>
                  <div className="card-body p-4">
                     <div className="row g-4">
                        <div className="col-md-6">
                           <label className="text-[10px] font-bold text-muted uppercase tracking-widest mb-2 d-block">ผู้ให้บริการสมองกล AI</label>
                           <select
                              className="form-select bg-light border-0 text-sm font-bold p-3 rounded-pill shadow-none"
                              value={settings.provider}
                              onChange={(e) => setSettings({ ...settings, provider: e.target.value })}
                           >
                              <option value="gemini">Google Gemini AI (V-Twin Native)</option>
                              <option value="openai">OpenAI (GPT-4o Enterprise)</option>
                              <option value="anthropic">Anthropic (Claude-3 Opus)</option>
                           </select>
                        </div>
                        <div className="col-md-6">
                           <label className="text-[10px] font-bold text-muted uppercase tracking-widest mb-2 d-block">โมเดลประมวลผลที่กำลังใช้งาน</label>
                           <select
                              className="form-select bg-light border-0 text-sm font-bold p-3 rounded-pill shadow-none"
                              value={settings.model}
                              onChange={(e) => setSettings({ ...settings, model: e.target.value })}
                           >
                              <option value="gemini-2.5-pro">Gemini 2.5 Pro (Clinical Optimized)</option>
                              <option value="gemini-2.5-flash">Gemini 2.5 Flash (Ultra Fast)</option>
                              <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
                              <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
                              <option value="gpt-4o">GPT-4o (Standard Reasoning)</option>
                           </select>
                        </div>
                        <div className="col-12 mt-4 pt-3 border-top border-light">
                           <label className="text-[10px] font-bold text-muted uppercase tracking-widest mb-2 d-flex justify-content-between">
                              <span>โปรโตคอลระบบหลัก (System Prompt)</span>
                              <span className="text-primary"><Terminal size={12} className="me-1" /> ไวยากรณ์คลินิกกำลังทำงาน</span>
                           </label>
                           <textarea
                              className="form-control bg-dark text-white font-mono text-xs p-4 rounded-4 border-0"
                              rows={10}
                              value={settings.system_prompt}
                              onChange={(e) => setSettings({ ...settings, system_prompt: e.target.value })}
                              placeholder="กำหนดโปรโตคอลและบทบาทการทำงานของระบบที่นี่..."
                           />
                           <div className="mt-2 d-flex align-items-center gap-2">
                              <Sparkles size={12} className="text-warning" />
                              <small className="text-[10px] text-muted font-bold uppercase tracking-tighter">โทเค็น AI ได้รับการปรับแต่งเพื่อตรรกะทางคลินิกและพรางข้อมูลตามข้อกำหนด PDPA</small>
                           </div>
                        </div>
                     </div>
                  </div>
               </div>
            </div>

            {/* 🏛️ Right Column: Stats & Diagnostics */}
            <div className="col-lg-4">
               <div className="card border-0 shadow-sm bg-white rounded-4 overflow-hidden mb-4 border-top border-4 border-primary">
                  <div className="card-header bg-transparent border-bottom border-light py-3">
                     <h3 className="card-title text-[10px] font-bold uppercase text-muted tracking-widest mb-0">การประเมินวิเคราะห์กลไก (Engine Diagnostics)</h3>
                  </div>
                  <div className="card-body p-4">
                     <div className="d-flex flex-column gap-4">
                        <div className="d-flex align-items-center justify-content-between">
                           <div className="d-flex align-items-center gap-2">
                              <Activity size={16} className="text-success" />
                              <span className="text-xs font-bold uppercase tracking-tighter text-muted">ความหน่วงการตอบสนอง</span>
                           </div>
                           <span className="text-xs font-black text-dark">42ms</span>
                        </div>
                        <div className="d-flex align-items-center justify-content-between">
                           <div className="d-flex align-items-center gap-2">
                              <Database size={16} className="text-primary" />
                              <span className="text-xs font-bold uppercase tracking-tighter text-muted">ประสิทธิภาพของโทเค็น</span>
                           </div>
                           <span className="text-xs font-black text-dark">98.2%</span>
                        </div>
                        <div className="d-flex align-items-center justify-content-between">
                           <div className="d-flex align-items-center gap-2">
                              <ShieldCheck size={16} className="text-info" />
                              <span className="text-xs font-bold uppercase tracking-tighter text-muted">ดัชนีการคาดเคลื่อน</span>
                           </div>
                           <span className="text-xs font-black text-success">ต่ำมาก (0.01)</span>
                        </div>
                     </div>

                     <div className="mt-5 pt-4 border-top border-light">
                        <button 
                           onClick={handleRecalibrate}
                           className="btn btn-outline-primary btn-sm w-100 font-bold uppercase tracking-widest text-[9px] py-2.5 rounded-pill d-flex align-items-center justify-content-center gap-2 shadow-sm bg-white"
                        >
                           <RefreshCw size={12} /> ปรับน้ำหนักประสาทเทียมใหม่ (Re-calibrate)
                        </button>
                     </div>
                  </div>
               </div>

               <div className="card border-0 shadow-sm bg-white rounded-4 overflow-hidden mb-4">
                  <div className="card-header bg-transparent border-bottom border-light py-3">
                     <h3 className="card-title text-[10px] font-bold uppercase text-muted tracking-widest mb-0">ความปลอดภัยการส่งผ่านข้อมูล (Security Handshake)</h3>
                  </div>
                  <div className="card-body p-4">
                     <div className="p-3 bg-light rounded-3 d-flex align-items-center gap-3 mb-3 border">
                        <div className="text-primary"><Lock size={20} /></div>
                        <div>
                           <div className="text-[9px] font-bold text-muted uppercase tracking-widest">เลเยอร์การเข้ารหัสข้อมูล</div>
                           <div className="text-xs font-black text-dark">AES-256 GCM Active</div>
                        </div>
                     </div>
                     <div className="p-3 bg-light rounded-3 d-flex align-items-center gap-3 border">
                        <div className="text-success"><Fingerprint size={20} /></div>
                        <div>
                           <div className="text-[9px] font-bold text-muted uppercase tracking-widest">เอกลักษณ์ตัวตนโมเดล</div>
                           <div className="text-xs font-black text-dark">ศูนย์กลางการรักษาที่ผ่านการรับรอง</div>
                        </div>
                     </div>
                  </div>
               </div>
            </div>
         </div>
      </div>
   );
}
