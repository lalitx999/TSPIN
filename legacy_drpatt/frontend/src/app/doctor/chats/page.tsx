"use client";

import { useState, useRef, useEffect } from "react";
import {
   Search, MessageSquare, Clock, Send, Mic,
   ChevronLeft, Phone, Video, MoreVertical,
   CheckCheck, Paperclip, Plus, Brain, Stethoscope, Sparkles, X, Copy, Check, RefreshCw
} from "lucide-react";
import { getAllPatients, getIntakeSessions, saveIntakeSessionMessage, updateIntakeSessionStatus } from "@/utils/api/services";
import { encryptMessage, decryptMessage } from "@/utils/crypto";

export default function DoctorChatsPage() {
   const [sessions, setSessions] = useState<any[]>([]);
   const [selectedSession, setSelectedSession] = useState<any>(null);
   const [input, setInput] = useState("");
   const [searchTerm, setSearchTerm] = useState("");
   const [loading, setLoading] = useState(true);
   const scrollRef = useRef<HTMLDivElement>(null);
   const [isRecording, setIsRecording] = useState(false);
   const mediaRecorderRef = useRef<MediaRecorder | null>(null);
   const audioChunksRef = useRef<Blob[]>([]);

   // Telehealth Modal States
   const [showPhoneModal, setShowPhoneModal] = useState(false);
   const [showMeetModal, setShowMeetModal] = useState(false);
   const [generatedMeetLink, setGeneratedMeetLink] = useState("");
   const [copied, setCopied] = useState(false);
   const [refreshTrigger, setRefreshTrigger] = useState(0);

   // 1. Listen to all active patient intake sessions in real-time (Django adapter)
   useEffect(() => {
      let active = true;
      setLoading(true);

      const syncSessions = async () => {
         try {
            const activeSessionsData = await getIntakeSessions();
            const patientsList = await getAllPatients();
            const patientsMap = new Map(patientsList.map((p: any) => [p.id, p]));

            const activeSessions: any[] = [];
            activeSessionsData.forEach((data: any) => {
               if (data.status !== "active") return;
               const patientId = data.patientId;
               const patient = patientsMap.get(patientId) as any;
               const patientName = patient 
                  ? `${patient.first_name || ""} ${patient.last_name || ""}`.trim()
                  : "ไม่ทราบชื่อคนไข้";
               const patientHn = patient?.hn || patientId.slice(0, 8);
               const patientPhone = patient?.phone || "ไม่ระบุเบอร์โทร"; // 📞 For Telehealth Phone Popup

               const msgs = data.messages || [];
               const lastMsg = msgs[msgs.length - 1];

               activeSessions.push({
                  id: data.id,
                  patientId: patientId,
                  name: patientName,
                  hn: patientHn,
                  phone: patientPhone,
                  lastMsg: lastMsg?.content ? decryptMessage(lastMsg.content) : "ยังไม่มีการสนทนา",
                  time: lastMsg?.timestamp 
                     ? new Date(lastMsg.timestamp).toLocaleTimeString("th-TH", { hour: '2-digit', minute: '2-digit' })
                     : "00:00",
                  unread: 0,
                  status: "online",
                  messages: msgs,
                  refPath: data.refPath,
                  aiActive: data.aiActive !== false
               });
            });

            // Sort by last message timestamp descending (Most active chats at the top)
            activeSessions.sort((a, b) => {
               const aMsgs = a.messages || [];
               const bMsgs = b.messages || [];
               const aTime = aMsgs.length > 0 ? new Date(aMsgs[aMsgs.length - 1].timestamp).getTime() : 0;
               const bTime = bMsgs.length > 0 ? new Date(bMsgs[bMsgs.length - 1].timestamp).getTime() : 0;
               return bTime - aTime;
            });

            if (active) {
               setSessions(activeSessions);
               if (selectedSession) {
                  const currentUpdated = activeSessions.find(s => s.id === selectedSession.id);
                  if (currentUpdated) {
                     setSelectedSession(currentUpdated);
                  }
               }
            }
         } catch (err) {
            console.error("Failed to sync active sessions: ", err);
         } finally {
            setLoading(false);
         }
      };

      syncSessions();
      const timer = setInterval(syncSessions, 3000);

      return () => {
         active = false;
         clearInterval(timer);
      };
   }, [selectedSession?.id, refreshTrigger]);

   // Scroll to bottom when message arrives
   useEffect(() => {
      if (scrollRef.current) {
         scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      }
   }, [selectedSession?.messages?.length]);

   // Send doctor message (intervene in chat with auto-disable AI)
   const handleSend = async () => {
      if (!input.trim() || !selectedSession) return;

      const originalInput = input;
      const inputMessage = input.trim();
      setInput("");

      try {
         let currentAiActive = selectedSession.aiActive;
         let updatedMsgs = [...(selectedSession.messages || [])];
         
         const doctorMsg = {
            role: "doctor",
            content: encryptMessage(inputMessage),
            timestamp: new Date().toISOString()
         };

         // 💡 Auto-Intervene: If AI is active, disable it and bundle a system announcement
         if (currentAiActive) {
            currentAiActive = false;
            
            const systemAnnouncement = {
               role: "doctor",
               content: encryptMessage("📣 ขณะนี้แพทย์ได้เข้าร่วมการสนทนาโดยตรงและปิดระบบคัดกรอง AI ชั่วคราว ท่านสามารถพิมพ์คุยกับแพทย์ได้เลยครับ"),
               timestamp: new Date().toISOString(),
               isSystem: true
            };
            
            // Send everything in 1 HTTP Request (message, aiActive=false, and systemAnnouncement)
            await saveIntakeSessionMessage(
               selectedSession.patientId,
               selectedSession.id,
               doctorMsg,
               false,
               systemAnnouncement
            );
            
            updatedMsgs.push(systemAnnouncement);
         } else {
            // Send normally in 1 HTTP Request
            await saveIntakeSessionMessage(
               selectedSession.patientId,
               selectedSession.id,
               doctorMsg
            );
         }

         updatedMsgs.push(doctorMsg);

         // 4. Update local states
         setSelectedSession({ 
            ...selectedSession, 
            aiActive: currentAiActive, 
            messages: updatedMsgs 
         });

         // 5. Update sessions list status immediately so sidebar reflects the state change
         setSessions(prev => prev.map(s => 
            s.id === selectedSession.id 
               ? { ...s, aiActive: currentAiActive, messages: updatedMsgs, lastMsg: inputMessage }
               : s
         ));

      } catch (err) {
         console.error("Failed to send doctor message with intervention: ", err);
         setInput(originalInput); // Restore on error
      }
   };

   // Toggle AI Copilot active status
   const toggleAICopilot = async () => {
      if (!selectedSession) return;
      try {
         const currentStatus = selectedSession.aiActive;
         const newStatus = !currentStatus;

         const systemAnnouncement = {
            role: newStatus ? "assistant" : "doctor",
            content: encryptMessage(newStatus 
               ? "🤖 ระบบคัดกรองอัตโนมัติ (AI Triage) เปิดใช้งานอีกครั้ง" 
               : "📣 ขณะนี้แพทย์ได้เข้าร่วมการสนทนาโดยตรงและปิดระบบคัดกรอง AI ชั่วคราว ท่านสามารถพิมพ์คุยกับแพทย์ได้เลยครับ"
            ),
            timestamp: new Date().toISOString(),
            isSystem: true
         };

         await updateIntakeSessionStatus(selectedSession.patientId, selectedSession.id, newStatus);
         await saveIntakeSessionMessage(selectedSession.patientId, selectedSession.id, systemAnnouncement);
         
         const updatedMsgs = [...(selectedSession.messages || []), systemAnnouncement];
         setSelectedSession({ ...selectedSession, aiActive: newStatus, messages: updatedMsgs });
      } catch (err) {
         console.error("Failed to toggle AI copilot: ", err);
      }
   };

   // Telehealth - Generate Google Meet Link
   const handleGenerateMeet = () => {
      const code1 = Math.random().toString(36).substring(2, 5);
      const code2 = Math.random().toString(36).substring(2, 6);
      const code3 = Math.random().toString(36).substring(2, 5);
      const link = `https://meet.google.com/${code1}-${code2}-${code3}`;
      setGeneratedMeetLink(link);
      setCopied(false);
   };

   // Telehealth - Copy Meet Link to Clipboard
   const handleCopyLink = () => {
      if (!generatedMeetLink) return;
      navigator.clipboard.writeText(generatedMeetLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
   };

   // Telehealth - Send Meet Link to Patient Chat
   const handleSendMeetToChat = async () => {
      if (!generatedMeetLink || !selectedSession) return;

      const meetMessage = `🏥 ลิงก์ห้องวิดีโอคอลตรวจประเมินกับแพทย์ (Google Meet):\n👉 ${generatedMeetLink}`;
      
      const doctorMsg = {
         role: "doctor",
         content: encryptMessage(meetMessage),
         timestamp: new Date().toISOString()
      };

      try {
         await saveIntakeSessionMessage(selectedSession.patientId, selectedSession.id, doctorMsg);
         
         const updatedMsgs = [...(selectedSession.messages || []), doctorMsg];
         setSelectedSession({ ...selectedSession, messages: updatedMsgs });
         
         setSessions(prev => prev.map(s => 
            s.id === selectedSession.id 
               ? { ...s, messages: updatedMsgs, lastMsg: "ส่งลิงก์วิดีโอคอล" }
               : s
         ));
         
         setShowMeetModal(false);
      } catch (err) {
         console.error("Failed to send Meet link to chat:", err);
      }
   };

   const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file || !selectedSession) return;
      
      const reader = new FileReader();
      reader.onload = async (event) => {
         const base64 = event.target?.result as string;
         const doctorMsg = {
            role: "doctor",
            content: encryptMessage(`[ส่งไฟล์รูปภาพ: ${file.name}]`),
            isImage: true,
            imageBase64: base64,
            timestamp: new Date().toISOString()
         };
         try {
            await saveIntakeSessionMessage(selectedSession.patientId, selectedSession.id, doctorMsg);
            const updatedMsgs = [...(selectedSession.messages || []), doctorMsg];
            setSelectedSession({ ...selectedSession, messages: updatedMsgs });
         } catch (err) {
            console.error("Failed to upload doctor image:", err);
         }
      };
      reader.readAsDataURL(file);
   };

   const toggleRecording = async () => {
      if (!selectedSession) return;
      if (isRecording) {
         if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
         }
      } else {
         try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorderRef.current = mediaRecorder;
            audioChunksRef.current = [];

            mediaRecorder.ondataavailable = (event) => {
               if (event.data.size > 0) {
                  audioChunksRef.current.push(event.data);
               }
            };

            mediaRecorder.onstop = async () => {
               const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
               const reader = new FileReader();
               reader.onloadend = async () => {
                  const base64Audio = reader.result as string;
                  const doctorMsg = {
                     role: "doctor",
                     content: encryptMessage("[ข้อความเสียง]"),
                     isAudio: true,
                     audioBase64: base64Audio,
                     timestamp: new Date().toISOString()
                  };
                  try {
                     await saveIntakeSessionMessage(selectedSession.patientId, selectedSession.id, doctorMsg);
                     const updatedMsgs = [...(selectedSession.messages || []), doctorMsg];
                     setSelectedSession({ ...selectedSession, messages: updatedMsgs });
                  } catch (err) {
                     console.error("Failed to send doctor audio:", err);
                  }
               };
               reader.readAsDataURL(audioBlob);
               stream.getTracks().forEach((track) => track.stop());
            };

            mediaRecorder.start();
            setIsRecording(true);
         } catch (err) {
            console.error("Failed to start audio recording:", err);
            alert("ไม่สามารถเข้าถึงไมโครโฟนได้ กรุณาอนุญาตสิทธิ์การใช้ไมโครโฟน");
         }
      }
   };

   const filtered = sessions.filter(s =>
      s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.hn.toLowerCase().includes(searchTerm.toLowerCase())
   );

   // Styles helper
   const avatarBase = (size: number, bg: string, color: string): React.CSSProperties => ({
      width: size, height: size, borderRadius: '50%',
      background: bg, color, border: '1px solid #E5E7EB',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontWeight: 600, fontSize: size > 40 ? '14px' : '11px',
      flexShrink: 0,
   });

   const iconBtn: React.CSSProperties = {
      background: '#F9FAFB', border: '1px solid #E5E7EB',
      borderRadius: '50%', width: '34px', height: '34px',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      cursor: 'pointer', color: '#6B7280', flexShrink: 0,
   };

   return (
      <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 70px - 64px)', marginTop: '-32px' }}>
         <div style={{
            flex: 1,
            display: 'flex',
            background: '#FFFFFF',
            border: '1px solid #E5E7EB',
            borderRadius: '12px',
            overflow: 'hidden',
            minHeight: 0,
            boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)'
         }}>

            {/* ══════════════════ SESSION LIST ══════════════════ */}
            <div style={{
               width: '320px',
               flexShrink: 0,
               borderRight: '1px solid #E5E7EB',
               display: selectedSession ? 'none' : 'flex',
               flexDirection: 'column',
               background: '#FCFCFD',
            }}
               className="chat-sidebar"
            >
               {/* Sidebar Header */}
               <div style={{ padding: '20px', borderBottom: '1px solid #E5E7EB', background: '#FFFFFF' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                     <span style={{ fontSize: '12px', fontWeight: 700, color: '#374151', letterSpacing: '0.5px' }}>
                        ศูนย์คุยประเมินอาการคนไข้
                     </span>
                     <span className="badge bg-teal-50 text-teal-700 border border-teal-200" style={{ fontSize: '10px', padding: '4px 8px' }}>
                        สด {sessions.length} เคส
                     </span>
                  </div>

                  {/* Search */}
                  <div style={{
                     display: 'flex', alignItems: 'center', gap: '8px',
                     background: '#F3F4F6', border: '1px solid #E5E7EB',
                     borderRadius: '6px', padding: '6px 12px',
                  }}>
                     <Search size={14} style={{ color: '#9CA3AF', flexShrink: 0 }} />
                     <input
                        type="text"
                        placeholder="ค้นหาชื่อคนไข้ / HN..."
                        value={searchTerm}
                        onChange={e => setSearchTerm(e.target.value)}
                        style={{ background: 'transparent', border: 'none', outline: 'none', fontSize: '13px', flex: 1, color: '#1F2937' }}
                     />
                  </div>
               </div>

               {/* Session List */}
               <div style={{ flex: 1, overflowY: 'auto' }} className="custom-scrollbar">
                  {loading ? (
                     <div className="py-5 text-center">
                        <div className="spinner-border spinner-border-sm text-teal mb-2" role="status" style={{ color: '#0D9488' }}></div>
                        <p className="text-xs text-muted mb-0">กำลังซิงค์แชทสด...</p>
                     </div>
                  ) : filtered.length === 0 ? (
                     <div className="py-5 text-center px-4">
                        <MessageSquare size={32} style={{ color: '#D1D5DB', marginBottom: '12px' }} />
                        <p className="text-xs text-muted mb-0 fw-medium">ไม่มีห้องสนทนาที่กำลังใช้งานขณะนี้</p>
                     </div>
                  ) : (
                     filtered.map(s => {
                        const active = selectedSession?.id === s.id;
                        return (
                          <div
                             key={s.id}
                             onClick={() => setSelectedSession(s)}
                             style={{
                                display: 'flex', alignItems: 'center', gap: '12px',
                                padding: '14px 16px',
                                borderBottom: '1px solid #F3F4F6',
                                borderLeft: active ? '3px solid #0D9488' : '3px solid transparent',
                                background: active ? '#F0FDFA' : 'transparent',
                                cursor: 'pointer',
                                transition: 'background 0.15s ease',
                                position: 'relative',
                             }}
                             onMouseEnter={e => { if (!active) e.currentTarget.style.background = '#F9FAFB'; }}
                             onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent'; }}
                          >
                             {/* Avatar */}
                             <div style={{ position: 'relative', flexShrink: 0 }}>
                                <div style={avatarBase(42, '#E8F0F5', '#0D9488')}>
                                   {s.name.charAt(0)}
                                </div>
                                <div style={{
                                   position: 'absolute',
                                   bottom: 0, right: 0,
                                   width: '10px', height: '10px', borderRadius: '50%',
                                   background: s.aiActive ? '#059669' : '#D97706',
                                   border: '2px solid white',
                                }} title={s.aiActive ? "AI Copilot ทำงานอยู่" : "คุณหมอคุมหลัก"} />
                             </div>

                             {/* Info */}
                             <div style={{ flex: 1, minWidth: 0 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '3px' }}>
                                   <div style={{ display: 'flex', alignItems: 'center', gap: '4px', minWidth: 0 }}>
                                      <span style={{ fontSize: '13px', fontWeight: 600, color: '#1F2937', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                         {s.name}
                                      </span>
                                      {s.aiActive ? (
                                         <span className="badge bg-teal-50 text-teal-700 border border-teal-200" style={{ fontSize: '9px', padding: '1px 4px', scale: '0.8', flexShrink: 0 }}>🤖 AI</span>
                                      ) : (
                                         <span className="badge bg-amber-50 text-amber-700 border border-amber-200" style={{ fontSize: '9px', padding: '1px 4px', scale: '0.8', flexShrink: 0 }}>👨‍⚕️ หมอ</span>
                                      )}
                                   </div>
                                   <span style={{ fontSize: '10px', color: '#9CA3AF', flexShrink: 0, marginLeft: '8px' }}>
                                      {s.time}
                                   </span>
                                </div>
                                <p style={{ fontSize: '12px', color: '#6B7280', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                   {s.aiActive ? "🤖 AI: " : "👨‍⚕️ หมอ: "}{s.lastMsg}
                                </p>
                             </div>
                          </div>
                        );
                     })
                  )}
               </div>
            </div>

            {/* ══════════════════ CHAT AREA ══════════════════ */}
            <div style={{
               flex: 1,
               display: (!selectedSession ? 'none' : 'flex'),
               flexDirection: 'column',
               background: '#FFFFFF',
               minWidth: 0,
            }}
               className="chat-main"
            >
               {selectedSession ? (
                  <>
                     {/* Chat Header */}
                     <div style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                        padding: '14px 20px', borderBottom: '1px solid #E5E7EB',
                        background: '#FFFFFF', flexShrink: 0,
                     }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                           {/* Back button (mobile) */}
                           <button
                              onClick={() => setSelectedSession(null)}
                              style={{ ...iconBtn, display: 'none' }}
                              className="chat-back-btn"
                           >
                              <ChevronLeft size={18} />
                           </button>

                           <div style={avatarBase(38, '#E8F0F5', '#0D9488')}>
                              {selectedSession.name.charAt(0)}
                           </div>

                           <div>
                              <div style={{ fontSize: '14px', fontWeight: 600, color: '#1F2937' }}>
                                 {selectedSession.name}
                              </div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
                                 <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#059669' }} />
                                 <span style={{ fontSize: '11px', color: '#6B7280' }}>
                                    HN: {selectedSession.hn} · กำลังตรวจประเมินอาการออนไลน์
                                 </span>
                              </div>
                           </div>
                        </div>

                        {/* AI COPILOT MODE TOGGLE (Third Party Copilot Status) */}
                        <div className="d-flex align-items-center gap-3">
                           <div className="d-flex align-items-center gap-3 px-3 py-1.5 rounded-3 border shadow-sm" style={{
                              background: selectedSession.aiActive ? '#F0FDF4' : '#F9FAFB',
                              borderColor: selectedSession.aiActive ? '#D1FAE5' : '#E5E7EB',
                              transition: 'all 0.3s ease'
                           }}>
                              <div className="d-flex align-items-center gap-2">
                                 {selectedSession.aiActive ? (
                                    <>
                                       <Brain size={15} style={{ color: '#0D9488' }} className="animate-pulse" />
                                       <span style={{ fontSize: '12px', fontWeight: 700, color: '#0F766E' }}>
                                          🤖 ระบบ AI คัดกรองอาการ
                                       </span>
                                    </>
                                 ) : (
                                    <>
                                       <Stethoscope size={15} style={{ color: '#4B5563' }} />
                                       <span style={{ fontSize: '12px', fontWeight: 700, color: '#4B5563' }}>
                                          👨‍⚕️ แพทย์ควบคุม (ปิด AI)
                                       </span>
                                    </>
                                 )}
                              </div>
                              
                              {/* iOS Toggle Switch */}
                              <label style={{
                                 position: 'relative',
                                 display: 'inline-block',
                                 width: '38px',
                                 height: '20px',
                                 margin: 0,
                                 cursor: 'pointer'
                              }}>
                                 <input 
                                    type="checkbox" 
                                    checked={selectedSession.aiActive}
                                    onChange={toggleAICopilot}
                                    style={{ opacity: 0, width: 0, height: 0 }}
                                 />
                                 <span style={{
                                    position: 'absolute',
                                    cursor: 'pointer',
                                    top: 0, left: 0, right: 0, bottom: 0,
                                    backgroundColor: selectedSession.aiActive ? '#0D9488' : '#D1D5DB',
                                    transition: '.3s',
                                    borderRadius: '20px',
                                    boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.1)'
                                 }}>
                                    <span style={{
                                       position: 'absolute',
                                       content: '""',
                                       height: '14px',
                                       width: '14px',
                                       left: selectedSession.aiActive ? '20px' : '4px',
                                       bottom: '3px',
                                       backgroundColor: 'white',
                                       transition: '.3s',
                                       borderRadius: '50%',
                                       boxShadow: '0 1px 3px rgba(0,0,0,0.2)'
                                    }} />
                                 </span>
                              </label>
                           </div>

                           <div style={{ display: 'flex', gap: '6px' }} className="d-none d-md-flex">
                              <button onClick={() => setRefreshTrigger(prev => prev + 1)} style={iconBtn} title="รีเฟรชข้อความ"><RefreshCw size={15} /></button>
                              <button onClick={() => setShowPhoneModal(true)} style={iconBtn} title="คุยสายเสียง"><Phone size={15} /></button>
                              <button onClick={() => { setGeneratedMeetLink(""); setShowMeetModal(true); }} style={iconBtn} title="คอลวิดีโอ"><Video size={15} /></button>
                           </div>
                        </div>
                     </div>

                     {/* Message History Grid */}
                     <div
                        ref={scrollRef}
                        style={{
                           flex: 1, overflowY: 'auto', padding: '24px 20px',
                           display: 'flex', flexDirection: 'column', gap: '16px',
                           background: '#F9FAFB',
                        }}
                        className="custom-scrollbar"
                      >
                        {selectedSession.messages && selectedSession.messages.map((m: any, idx: number) => {
                           if (m.isSystem) {
                              return (
                                 <div key={idx} style={{ display: 'flex', justifyContent: 'center', margin: '12px 0', width: '100%' }}>
                                    <div style={{
                                       padding: '6px 16px',
                                       borderRadius: '20px',
                                       textAlign: 'center',
                                       border: m.role === 'doctor' ? '1px solid #A7F3D0' : '1px solid #BAE6FD',
                                       background: m.role === 'doctor' ? '#ECFDF5' : '#F0F9FF',
                                       color: m.role === 'doctor' ? '#065F46' : '#0369A1',
                                       fontSize: '11px',
                                       fontWeight: 600,
                                       lineHeight: 1.4,
                                       maxWidth: '85%',
                                       boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)'
                                    }}>
                                       {decryptMessage(m.content)}
                                    </div>
                                 </div>
                              );
                           }

                           const isPatient = m.role === 'user';
                           const isDoctor = m.role === 'doctor';
                           const isAI = m.role === 'assistant';

                           return (
                              <div
                                 key={idx}
                                 style={{
                                    display: 'flex',
                                    justifyContent: isDoctor ? 'flex-end' : 'flex-start',
                                    alignItems: 'flex-start',
                                    gap: '10px',
                                 }}
                              >
                                 {/* Left Side Avatars (Patient or AI) */}
                                 {!isDoctor && (
                                    <div style={avatarBase(30, isAI ? '#E0F2FE' : '#F3F4F6', isAI ? '#0369A1' : '#4B5563')}>
                                       {isAI ? <Brain size={14} /> : "👤"}
                                    </div>
                                 )}

                                 <div style={{ maxWidth: '68%', display: 'flex', flexDirection: 'column', alignItems: isDoctor ? 'flex-end' : 'flex-start' }}>
                                    
                                    {/* Sender Badge */}
                                    <span style={{ fontSize: '9px', fontWeight: 700, color: '#9CA3AF', marginBottom: '3px', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
                                       {isPatient ? "คนไข้" : isAI ? "🤖 AI Triage" : "👨‍⚕️ คุณหมอ (คุณ)"}
                                    </span>

                                    {/* Message Bubble */}
                                    <div style={{
                                       padding: '11px 15px',
                                       background: isDoctor 
                                          ? '#0E7490' // Teal for Doctor
                                          : isAI 
                                             ? '#F0F9FF' // Very Light Blue for AI
                                             : '#FFFFFF', // White for Patient
                                       color: isDoctor ? '#FFFFFF' : '#1F2937',
                                       borderRadius: isDoctor ? '12px 0 12px 12px' : '0 12px 12px 12px',
                                       border: isDoctor ? 'none' : isAI ? '1px solid #BAE6FD' : '1px solid #E5E7EB',
                                       fontSize: '13px',
                                       lineHeight: 1.5,
                                       boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.03)'
                                    }}>
                                       {m.isAudio ? (
                                          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', minWidth: '220px' }}>
                                             <div style={{ display: 'flex', alignItems: 'center', gap: '6px', opacity: 0.75 }}>
                                                <Mic size={14} />
                                                <span style={{ fontSize: '11px', fontStyle: 'italic' }}>ข้อความเสียง</span>
                                             </div>
                                             <audio src={m.audioBase64} controls style={{ width: '100%', maxHeight: '36px' }} />
                                          </div>
                                       ) : m.isImage ? (
                                          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                             {m.imageBase64 && (
                                                <img
                                                   src={m.imageBase64}
                                                   alt="ไฟล์รูปภาพใบแล็บ/ผลตรวจ"
                                                   style={{ maxHeight: '200px', width: '100%', objectFit: 'cover', borderRadius: '6px' }}
                                                />
                                             )}
                                             <p style={{ margin: 0, fontSize: '12px', fontStyle: 'italic' }}>{decryptMessage(m.content)}</p>
                                          </div>
                                       ) : (
                                          <p style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{decryptMessage(m.content)}</p>
                                       )}
                                    </div>

                                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginTop: '4px', padding: '0 2px' }}>
                                       <span style={{ fontSize: '9px', color: '#9CA3AF' }}>
                                          {m.timestamp 
                                             ? new Date(m.timestamp).toLocaleTimeString("th-TH", { hour: '2-digit', minute: '2-digit' })
                                             : "00:00"}
                                       </span>
                                       {isDoctor && <CheckCheck size={11} style={{ color: '#0E7490' }} />}
                                    </div>
                                 </div>

                                 {/* Right Side Avatar (Doctor) */}
                                 {isDoctor && (
                                    <div style={avatarBase(30, '#ECFDF5', '#047857')}>
                                       <Stethoscope size={14} />
                                    </div>
                                 )}
                              </div>
                           );
                        })}
                     </div>

                     {/* Doctor Input Intervene Console */}
                     <div style={{
                        padding: '16px 20px', borderTop: '1px solid #E5E7EB',
                        background: '#FFFFFF', flexShrink: 0,
                     }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                           {/* Attachment placeholder icons */}
                           <div style={{ display: 'flex', gap: '6px' }}>
                              <button 
                                 style={iconBtn} 
                                 title="แนบรูปภาพผลแล็บ/วิจัย" 
                                 onClick={() => document.getElementById("doctor-image-upload")?.click()}
                              >
                                 <Paperclip size={15} />
                              </button>
                              <input 
                                 type="file" 
                                 accept="image/*" 
                                 className="d-none" 
                                 id="doctor-image-upload" 
                                 onChange={handleImageUpload} 
                              />
                              <button 
                                 style={{ 
                                    ...iconBtn, 
                                    color: isRecording ? '#DC2626' : '#6B7280', 
                                    borderColor: isRecording ? '#FCA5A5' : '#E5E7EB',
                                    background: isRecording ? '#FEF2F2' : '#F9FAFB'
                                 }} 
                                 title={isRecording ? "กำลังอัดเสียง... กดอีกครั้งเพื่อส่ง" : "อัดเสียงส่งคนไข้"} 
                                 onClick={toggleRecording}
                                 className={isRecording ? "animate-pulse" : ""}
                              >
                                 <Mic size={15} />
                              </button>
                           </div>

                           {/* Input text field */}
                           <div style={{ flex: 1, position: 'relative' }}>
                              <input
                                 type="text"
                                 placeholder="พิมพ์ส่งคำแนะนำทางแพทย์เชิงลึกในฐานะคุณหมอ (แทรกแซง AI ทันที)..."
                                 value={input}
                                 onChange={e => setInput(e.target.value)}
                                 onKeyDown={e => { if (e.key === 'Enter') handleSend(); }}
                                 style={{
                                    width: '100%', padding: '10px 16px',
                                    border: '1px solid #E5E7EB', borderRadius: '24px',
                                    background: '#F9FAFB', fontSize: '13px',
                                    outline: 'none', color: '#1F2937',
                                 }}
                              />
                           </div>

                           {/* Send Button */}
                           <button
                              style={{
                                 width: '40px', height: '40px', borderRadius: '50%',
                                 background: input.trim() ? '#0D9488' : '#E5E7EB',
                                 border: 'none', cursor: input.trim() ? 'pointer' : 'default',
                                 display: 'flex', alignItems: 'center', justifyContent: 'center',
                                 transition: 'background 0.15s ease', flexShrink: 0,
                              }}
                              onClick={handleSend}
                           >
                              <Send size={15} style={{ color: input.trim() ? 'white' : '#9CA3AF', marginLeft: '1px' }} />
                           </button>
                        </div>
                     </div>
                  </>
               ) : (
                  /* Empty State */
                  <div style={{
                     flex: 1, display: 'flex', flexDirection: 'column',
                     alignItems: 'center', justifyContent: 'center',
                     textAlign: 'center', padding: '40px', opacity: 0.6,
                  }}>
                     <div style={{
                        width: '72px',
                        height: '72px',
                        borderRadius: '50%',
                        background: '#F0FDFA',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        marginBottom: '16px',
                        border: '1px solid #CCFBF1'
                     }}>
                        <Brain size={32} style={{ color: '#0D9488' }} />
                     </div>
                     <div style={{ fontSize: '14.5px', fontWeight: 700, color: '#374151', marginBottom: '6px' }}>
                        ศูนย์คุยตรวจอาการออนไลน์ (AI Copilot Hub)
                     </div>
                     <p style={{ fontSize: '12px', color: '#6B7280', maxWidth: '320px', lineHeight: 1.6, margin: 0 }}>
                        เลือกห้องสนทนาของคนไข้ในแถบซ้ายมือ เพื่อเข้าไปดู RAG Chat แบบสด ๆ ร่วมกัน หรือส่งคำสั่งการตรวจนัดในฐานะคุณหมอแทรกแซงแบบบุคคลที่สามได้ทันที
                     </p>
                  </div>
               )}
            </div>
         </div>

         {/* 📞 TELEHEALTH: PHONE CALL MODAL */}
         {showPhoneModal && selectedSession && (
            <div style={{
               position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
               background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center',
               justifyContent: 'center', zIndex: 1050
            }}>
               <div style={{
                  background: 'white', borderRadius: '16px', padding: '24px',
                  width: '360px', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)',
                  position: 'relative'
               }}>
                  <button 
                     onClick={() => setShowPhoneModal(false)}
                     style={{ position: 'absolute', top: '16px', right: '16px', border: 'none', background: 'transparent', cursor: 'pointer', color: '#9CA3AF' }}
                  >
                     <X size={18} />
                  </button>
                  <div style={{ textAlign: 'center', marginTop: '8px' }}>
                     <div style={{
                        width: '56px', height: '56px', borderRadius: '50%',
                        background: '#ECFDF5', color: '#059669', display: 'flex',
                        alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px',
                        border: '1px solid #A7F3D0'
                     }}>
                        <Phone size={24} />
                     </div>
                     <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#1F2937', marginBottom: '4px' }}>
                        ติดต่อคนไข้ทางโทรศัพท์
                     </h3>
                     <p style={{ fontSize: '12px', color: '#6B7280', marginBottom: '20px' }}>
                        HN: {selectedSession.hn} · {selectedSession.name}
                     </p>
                     
                     <div style={{
                        background: '#F9FAFB', border: '1px solid #E5E7EB',
                        borderRadius: '12px', padding: '16px', marginBottom: '24px'
                     }}>
                        <span style={{ fontSize: '11px', color: '#9CA3AF', display: 'block', marginBottom: '4px', fontWeight: 600 }}>
                           เบอร์โทรศัพท์ติดต่อ
                        </span>
                        <span style={{ fontSize: '20px', fontWeight: 700, color: '#0D9488', letterSpacing: '1px' }}>
                           {selectedSession.phone}
                        </span>
                     </div>

                     <div style={{ display: 'flex', gap: '10px' }}>
                        <button 
                           onClick={() => setShowPhoneModal(false)}
                           className="btn btn-outline-secondary"
                           style={{ flex: 1, borderRadius: '8px', fontSize: '13px', padding: '10px' }}
                        >
                           ยกเลิก
                        </button>
                        <a 
                           href={`tel:${selectedSession.phone}`}
                           className="btn"
                           style={{ 
                              flex: 1, borderRadius: '8px', fontSize: '13px', padding: '10px',
                              background: '#0D9488', color: 'white', fontWeight: 600,
                              display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '6px'
                           }}
                        >
                           <Phone size={14} /> โทรออก
                        </a>
                     </div>
                  </div>
               </div>
            </div>
         )}

         {/* 📹 TELEHEALTH: GOOGLE MEET GENERATOR MODAL */}
         {showMeetModal && selectedSession && (
            <div style={{
               position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
               background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center',
               justifyContent: 'center', zIndex: 1050
            }}>
               <div style={{
                  background: 'white', borderRadius: '16px', padding: '24px',
                  width: '420px', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)',
                  position: 'relative'
               }}>
                  <button 
                     onClick={() => setShowMeetModal(false)}
                     style={{ position: 'absolute', top: '16px', right: '16px', border: 'none', background: 'transparent', cursor: 'pointer', color: '#9CA3AF' }}
                  >
                     <X size={18} />
                  </button>
                  <div style={{ marginTop: '4px' }}>
                     <div style={{ display: 'flex', gap: '14px', alignItems: 'center', marginBottom: '16px' }}>
                        <div style={{
                           width: '44px', height: '44px', borderRadius: '10px',
                           background: '#EFF6FF', color: '#2563EB', display: 'flex',
                           alignItems: 'center', justifyContent: 'center', border: '1px solid #BFDBFE'
                        }}>
                           <Video size={20} />
                        </div>
                        <div>
                           <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#1F2937', margin: 0 }}>
                              สร้างลิงก์วิดีโอคอลตรวจประเมิน
                           </h3>
                           <p style={{ fontSize: '11px', color: '#6B7280', margin: '2px 0 0' }}>
                              HN: {selectedSession.hn} · {selectedSession.name}
                           </p>
                        </div>
                     </div>

                     <p style={{ fontSize: '12.5px', color: '#4B5563', lineHeight: 1.5, marginBottom: '20px' }}>
                        คุณหมอสามารถสร้างลิงก์ห้องประชุม Google Meet แบบด่วน และคัดลอกส่งต่อ หรือกดส่งเข้าไปในห้องแชทของคนไข้ได้ทันทีเพื่อให้เริ่มตรวจออนไลน์ได้ทันที
                     </p>

                     {!generatedMeetLink ? (
                        <button
                           onClick={handleGenerateMeet}
                           className="btn w-100"
                           style={{
                              background: '#2563EB', color: 'white', fontWeight: 600,
                              fontSize: '13px', padding: '12px', borderRadius: '8px',
                              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px'
                           }}
                        >
                           <Video size={16} /> สร้างห้องตรวจ Google Meet
                        </button>
                     ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                           <div style={{
                              background: '#F3F4F6', border: '1px solid #E5E7EB',
                              borderRadius: '8px', padding: '10px 14px', display: 'flex',
                              alignItems: 'center', justifyContent: 'space-between', gap: '10px'
                           }}>
                              <span style={{ fontSize: '13px', fontWeight: 600, color: '#2563EB', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                                 {generatedMeetLink}
                              </span>
                              <button 
                                 onClick={handleCopyLink}
                                 style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: copied ? '#059669' : '#6B7280' }}
                                 title="คัดลอกลิงก์"
                              >
                                 {copied ? <Check size={16} /> : <Copy size={16} />}
                              </button>
                           </div>

                           <div style={{ display: 'flex', gap: '10px' }}>
                              <button 
                                 onClick={handleGenerateMeet}
                                 className="btn btn-outline-secondary btn-sm"
                                 style={{ fontSize: '12px', padding: '8px 12px', borderRadius: '6px' }}
                              >
                                 สร้างใหม่
                              </button>
                              <button 
                                 onClick={handleSendMeetToChat}
                                 className="btn btn-success btn-sm flex-1"
                                 style={{ 
                                    fontSize: '12px', padding: '8px 12px', borderRadius: '6px',
                                    background: '#059669', border: 'none', color: 'white', fontWeight: 600
                                 }}
                              >
                                 ส่งเข้าห้องแชทคนไข้ 🚀
                              </button>
                           </div>
                        </div>
                     )}

                     <div style={{ borderTop: '1px solid #F3F4F6', marginTop: '20px', paddingTop: '16px', display: 'flex', justifyContent: 'flex-end' }}>
                        <button 
                           onClick={() => setShowMeetModal(false)}
                           className="btn btn-light"
                           style={{ fontSize: '12px', padding: '6px 16px', borderRadius: '6px' }}
                        >
                           ปิด
                        </button>
                     </div>
                  </div>
               </div>
            </div>
         )}

         <style>{`
        /* Show sidebar always on desktop */
        @media (min-width: 769px) {
          .chat-sidebar { display: flex !important; }
          .chat-main    { display: flex !important; }
          .chat-back-btn { display: none !important; }
        }
        /* Mobile: toggle panels */
        @media (max-width: 768px) {
          .chat-sidebar { width: 100% !important; }
          .chat-back-btn { display: flex !important; }
        }
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #D1D5DB; border-radius: 4px; }
        
        .hover-shadow {
          transition: all 0.15s ease;
        }
        .hover-shadow:hover {
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        }
      `}</style>
      </div>
   );
}