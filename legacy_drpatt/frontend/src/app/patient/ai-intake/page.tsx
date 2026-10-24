"use client";

import { useState, useEffect, useRef } from "react";
import {
  Brain,
  Send,
  Mic,
  Camera,
  ArrowLeft,
  Stethoscope,
  ShieldAlert,
  RefreshCw,
  Menu,
  X,
  Home,
  User,
  Calendar,
  FileText,
  LogOut,
  ChevronDown,
  Sparkles,
  Clock,
  CheckCircle,
  AlertCircle,
  Phone,
  MessageCircle,
  Globe,
  Play,
  Pause,
  Activity,
  HeartPulse,
  AlertTriangle,
  Volume2,
  ShieldCheck,
  Zap,
  Info,
  Image,
  Paperclip
} from "lucide-react";
import Link from "next/link";

import { getPatient, createIntakeSession, getIntakeSession, saveIntakeSessionMessage } from "@/utils/api/services";
import { encryptMessage, decryptMessage } from "@/utils/crypto";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Message = {
  role: "user" | "assistant" | "doctor";
  content: string;
  isImage?: boolean;
  imageBase64?: string;
  isAudio?: boolean;
  audioBase64?: string;
  timestamp?: any;
  isSystem?: boolean;
};

// ==========================================
// CUSTOM AUDIO PLAYER COMPONENT
// ==========================================
function CustomAudioPlayer({ src, isUser }: { src: string; isUser: boolean }) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  const togglePlay = (e: React.MouseEvent) => {
    e.preventDefault();
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play().catch(err => console.error("Audio playback error:", err));
    }
  };

  const handleTimeUpdate = () => {
    if (!audioRef.current) return;
    setCurrentTime(audioRef.current.currentTime);
  };

  const handleLoadedMetadata = () => {
    if (!audioRef.current) return;
    const dur = audioRef.current.duration;
    if (isFinite(dur)) {
      setDuration(dur);
    }
  };

  const handleAudioEnded = () => {
    setIsPlaying(false);
    setCurrentTime(0);
  };

  const formatTime = (time: number) => {
    if (isNaN(time) || !isFinite(time)) return "0:00";
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds < 10 ? "0" : ""}${seconds}`;
  };

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  const handleProgressBarClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!audioRef.current || duration === 0) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const width = rect.width;
    const newTime = (clickX / width) * duration;
    audioRef.current.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const theme = isUser
    ? {
      playBtnBg: '#D4AF37',
      playBtnColor: '#1a1a2e',
      trackBg: 'rgba(255,255,255,0.2)',
      fillBg: '#fff',
      textColor: 'rgba(255,255,255,0.8)',
      borderColor: 'rgba(255,255,255,0.1)',
      cardBg: 'rgba(255,255,255,0.06)'
    }
    : {
      playBtnBg: '#0f172a',
      playBtnColor: '#fff',
      trackBg: '#e2e8f0',
      fillBg: '#D4AF37',
      textColor: '#64748b',
      borderColor: '#e2e8f0',
      cardBg: '#f8fafc'
    };

  return (
    <div
      className="d-flex align-items-center gap-3 p-2.5 rounded-3 border w-100 mt-1"
      style={{
        minWidth: '200px',
        backgroundColor: theme.cardBg,
        borderColor: theme.borderColor
      }}
    >
      <audio
        ref={audioRef}
        src={src}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={handleAudioEnded}
        preload="metadata"
      />

      <button
        onClick={togglePlay}
        className="btn d-flex align-items-center justify-content-center p-0 rounded-circle border-0 flex-shrink-0 shadow-sm"
        style={{
          width: '32px',
          height: '32px',
          backgroundColor: theme.playBtnBg,
          color: theme.playBtnColor,
          transition: 'all 0.2s ease',
        }}
      >
        {isPlaying ? <Pause size={12} fill="currentColor" /> : <Play size={12} className="ms-0.5" fill="currentColor" />}
      </button>

      <div className="flex-grow-1">
        <div
          onClick={handleProgressBarClick}
          className="position-relative cursor-pointer py-1.5"
        >
          <div style={{ height: '3px', backgroundColor: theme.trackBg, borderRadius: '2px' }}>
            <div
              className="position-absolute top-0 start-0 h-100"
              style={{
                width: `${progress}%`,
                backgroundColor: theme.fillBg,
                borderRadius: '2px',
                height: '3px',
                transition: 'width 0.1s linear'
              }}
            />
          </div>
        </div>
        <div className="d-flex justify-content-between" style={{ fontSize: '9px', color: theme.textColor, fontWeight: 500 }}>
          <span>{formatTime(currentTime)}</span>
          <span>{formatTime(duration || 0)}</span>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// MAIN PAGE COMPONENT
// ==========================================
export default function PatientAIIntakePage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [aiActive, setAiActive] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);
  const [showImageOptions, setShowImageOptions] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const prevLengthRef = useRef(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const quickPrompts = [
    "🤒 มีไข้ตัวร้อน",
    "🤢 ปวดท้อง",
    "🤕 ปวดหัว",
    "🦠 ผื่นคัน"
  ];

  // Auth & Session Init
  useEffect(() => {
    const checkAuthAndInit = async () => {
      if (typeof window === "undefined") return;
      const token = localStorage.getItem("patient_access_token");
      if (!token) {
        window.location.href = "/patient/login";
        return;
      }

      try {
        const res = await fetch(`${API_BASE}/api/auth/me/`, {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          const uid = String(data.id);
          setUserId(uid);

          const sessions = data.extra_data?.intake_sessions || {};
          let activeSessionId = Object.keys(sessions).find(
            (sid) => sessions[sid].status === "active"
          ) || null;

          if (!activeSessionId) {
            activeSessionId = `sess_${Date.now()}`;
            const initialMsg = {
              role: "assistant",
              content: encryptMessage("สวัสดีครับ 👋\n\nวันนี้มีอาการอะไรให้ผมช่วยคัดกรองเบื้องต้นไหมครับ?\n\nคุณสามารถพิมพ์ อัดเสียง หรือส่งรูปภาพอาการได้เลยครับ"),
              timestamp: new Date().toISOString()
            };
            await createIntakeSession(uid, activeSessionId, initialMsg);
          }
          setSessionId(activeSessionId);
        } else {
          window.location.href = "/patient/login";
        }
      } catch (err) {
        console.error("Auth and session initialization failed:", err);
      }
    };
    checkAuthAndInit();
  }, []);

  const manualRefresh = async () => {
    if (!userId || !sessionId) return;
    try {
      const sessionData = await getIntakeSession(userId, sessionId);
      if (sessionData) {
        setAiActive(sessionData.aiActive !== false);
        if (sessionData.messages) {
          const decrypted = sessionData.messages.map((m: any) => ({
            ...m,
            content: decryptMessage(m.content)
          }));
          setMessages(decrypted);
        }
      }
    } catch (err) {
      console.error("Failed to manual refresh session messages:", err);
    }
  };

  useEffect(() => {
    if (!userId || !sessionId) return;
    manualRefresh();
    const intervalId = setInterval(manualRefresh, 3000);
    return () => clearInterval(intervalId);
  }, [userId, sessionId]);

  useEffect(() => {
    if (messages.length > prevLengthRef.current || isTyping) {
      if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      }
      prevLengthRef.current = messages.length;
    } else if (messages.length < prevLengthRef.current) {
      prevLengthRef.current = messages.length;
    }
  }, [messages.length, isTyping]);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const handleSend = async (
    overrideInput?: string,
    isImage = false,
    imageBase64?: string,
    imageMimeType?: string,
    audioBase64?: string
  ) => {
    const textToSend = overrideInput || input;
    if (!textToSend.trim() && !isImage && !audioBase64) return;

    const isAudio = !!audioBase64;
    const encryptedContent = encryptMessage(textToSend);
    const userMsg = {
      role: "user",
      content: encryptedContent,
      isImage,
      imageBase64: imageBase64 || null,
      isAudio,
      audioBase64: audioBase64 || null,
      timestamp: new Date().toISOString()
    };

    setInput("");
    setIsTyping(true);

    try {
      if (sessionId && userId) {
        await saveIntakeSessionMessage(userId, sessionId, userMsg);
      }

      let aiActive = true;
      if (sessionId && userId) {
        const sessionData = await getIntakeSession(userId, sessionId);
        if (sessionData && sessionData.aiActive === false) {
          aiActive = false;
        }
      }

      if (!aiActive) {
        setIsTyping(false);
        return;
      }

      const currentContext = [...messages, { ...userMsg, content: textToSend }];
      const hasImage = currentContext.some((m: any) => m.isImage);
      const hasAudio = currentContext.some((m: any) => m.isAudio);

      const response = await fetch("/api/patient/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: currentContext.map(m => ({
            role: m.role,
            content: decryptMessage(m.content),
            isImage: m.isImage,
            imageBase64: m.imageBase64,
            isAudio: m.isAudio,
            audioBase64: m.audioBase64
          })),
          hasImage,
          hasAudio
        }),
      });

      if (!response.ok) throw new Error("API request failed");

      const aiData = await response.json();

      const aiMsg = {
        role: "assistant",
        content: encryptMessage(aiData.content || "ขออภัยครับ ระบบเกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง"),
        timestamp: new Date().toISOString()
      };

      if (sessionId && userId) {
        await saveIntakeSessionMessage(userId, sessionId, aiMsg);
      }

      setIsTyping(false);

    } catch (error) {
      console.error("Chat error:", error);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "เกิดข้อผิดพลาดในการเชื่อมต่อ กรุณาลองใหม่อีกครั้งครับ",
        timestamp: new Date().toISOString()
      } as any]);
      setIsTyping(false);
    }
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const base64 = event.target?.result as string;
      handleSend(`[รูปภาพ: ${file.name}]`, true, base64, file.type);
    };
    reader.readAsDataURL(file);
    e.target.value = "";
    setShowImageOptions(false);
  };

  const toggleRecording = async () => {
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

        mediaRecorder.onstop = () => {
          const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
          const reader = new FileReader();
          reader.onloadend = () => {
            const base64Audio = reader.result as string;
            handleSend("[ข้อความเสียง]", false, undefined, undefined, base64Audio);
          };
          reader.readAsDataURL(audioBlob);
          stream.getTracks().forEach((track) => track.stop());
        };

        mediaRecorder.start();
        setIsRecording(true);
      } catch (err) {
        console.error("Failed to start audio recording:", err);
        alert("ไมโครโฟนถูกบล็อก กรุณาเปิดสิทธิ์การใช้งานไมโครโฟน");
      }
    }
  };

  return (
    <div className="d-flex flex-column vh-100" style={{ backgroundColor: '#f7f8fa', fontFamily: "'Sarabun', 'Inter', sans-serif" }}>

      {/* ===== HEADER ===== */}
      <header
        className="d-flex align-items-center justify-content-between px-3 py-2 flex-shrink-0 bg-white border-bottom"
        style={{ zIndex: 10 }}
      >
        <div className="d-flex align-items-center gap-2">
          <Link href="/patient/dashboard" className="text-dark text-decoration-none p-1 rounded-circle d-flex align-items-center justify-content-center hover-bg">
            <ArrowLeft size={20} />
          </Link>
          <div className="bg-dark rounded-circle d-flex align-items-center justify-content-center" style={{ width: '36px', height: '36px' }}>
            <Stethoscope size={16} color="white" />
          </div>
          <div>
            <div className="fw-bold text-dark" style={{ fontSize: '14px' }}>ประเมินอาการ AI</div>
            <div className="text-muted" style={{ fontSize: '10px' }}>คัดกรองเบื้องต้น</div>
          </div>
        </div>
        <div className="d-flex align-items-center gap-1">
          <button onClick={manualRefresh} className="btn btn-sm btn-light rounded-circle border-0 d-flex align-items-center justify-content-center" style={{ width: '32px', height: '32px' }}>
            <RefreshCw size={14} />
          </button>
          <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="btn btn-sm btn-light rounded-circle border-0 d-flex align-items-center justify-content-center d-md-none" style={{ width: '32px', height: '32px' }}>
            <Menu size={16} />
          </button>
        </div>
      </header>

      {/* ===== MOBILE MENU ===== */}
      {mobileMenuOpen && (
        <div className="position-fixed top-0 start-0 w-100 h-100 bg-white" style={{ zIndex: 100, paddingTop: '60px' }}>
          <div className="d-flex flex-column p-3">
            <Link href="/patient/dashboard" className="d-flex align-items-center gap-3 p-2 text-decoration-none text-dark border-bottom py-2">
              <Home size={18} /> หน้าหลัก
            </Link>
            <Link href="/patient/profile" className="d-flex align-items-center gap-3 p-2 text-decoration-none text-dark border-bottom py-2">
              <User size={18} /> โปรไฟล์
            </Link>
            <Link href="/patient/appointments" className="d-flex align-items-center gap-3 p-2 text-decoration-none text-dark border-bottom py-2">
              <Calendar size={18} /> นัดหมาย
            </Link>
            <Link href="/patient/records" className="d-flex align-items-center gap-3 p-2 text-decoration-none text-dark border-bottom py-2">
              <FileText size={18} /> ประวัติ
            </Link>
            <button className="d-flex align-items-center gap-3 p-2 text-danger border-0 bg-transparent text-start mt-2">
              <LogOut size={18} /> ออกจากระบบ
            </button>
          </div>
        </div>
      )}

      {/* ===== CHAT AREA ===== */}
      <div
        ref={scrollRef}
        className="flex-grow-1 overflow-auto px-3 py-3 d-flex flex-column gap-2"
        style={{ scrollBehavior: 'smooth' }}
      >
        {messages.length === 0 ? (
          <div className="d-flex flex-column align-items-center justify-content-center h-100 text-center">
            <Brain size={48} className="text-muted mb-3" style={{ opacity: 0.3 }} />
            <p className="text-muted" style={{ fontSize: '14px' }}>กำลังเชื่อมต่อ...</p>
          </div>
        ) : (
          messages.map((msg, idx) => {
            const isUser = msg.role === 'user';
            const isDoctor = msg.role === 'doctor';

            if (msg.isSystem) {
              return (
                <div key={idx} className="text-center my-1">
                  <span className="px-3 py-1 rounded-pill bg-light text-muted" style={{ fontSize: '11px' }}>
                    {msg.content}
                  </span>
                </div>
              );
            }

            return (
              <div
                key={idx}
                className={`d-flex ${isUser ? 'justify-content-end' : 'justify-content-start'}`}
              >
                <div className={`d-flex gap-2 ${isUser ? 'flex-row-reverse' : ''}`} style={{ maxWidth: '80%' }}>

                  {/* Avatar */}
                  <div
                    className="rounded-circle d-flex align-items-center justify-content-center flex-shrink-0"
                    style={{
                      width: '32px',
                      height: '32px',
                      backgroundColor: isUser ? '#e5e7eb' : isDoctor ? '#10b981' : '#1a1a2e',
                      color: isUser ? '#4b5563' : 'white'
                    }}
                  >
                    {isUser ? <User size={14} /> : isDoctor ? <Stethoscope size={14} /> : <Brain size={14} />}
                  </div>

                  {/* Bubble */}
                  <div>
                    <div
                      className={`p-3 ${isUser ? 'text-white' : 'text-dark'}`}
                      style={{
                        borderRadius: '16px',
                        borderTopRightRadius: isUser ? '4px' : '16px',
                        borderTopLeftRadius: isUser ? '16px' : '4px',
                        fontSize: '14px',
                        lineHeight: '1.6',
                        backgroundColor: isUser ? '#1a1a2e' : 'white',
                        border: isUser ? 'none' : '1px solid #e5e7eb',
                        boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
                        wordBreak: 'break-word'
                      }}
                    >
                      {isDoctor && (
                        <div className="text-success mb-1" style={{ fontSize: '10px', fontWeight: 600 }}>
                          <Stethoscope size={10} className="me-1" />
                          แพทย์
                        </div>
                      )}

                      {msg.isAudio ? (
                        <div>
                          <div className="text-muted mb-1" style={{ fontSize: '11px' }}>
                            <Mic size={12} className="me-1" /> ข้อความเสียง
                          </div>
                          <CustomAudioPlayer src={msg.audioBase64 || ""} isUser={isUser} />
                        </div>
                      ) : msg.isImage ? (
                        <div>
                          {msg.imageBase64 && (
                            <img
                              src={msg.imageBase64}
                              alt="รูปภาพ"
                              className="rounded-3 mb-1"
                              style={{ maxHeight: '180px', maxWidth: '100%', objectFit: 'cover', cursor: 'pointer' }}
                              onClick={() => window.open(msg.imageBase64, '_blank')}
                            />
                          )}
                          <div className="text-muted" style={{ fontSize: '11px' }}>
                            <Image size={12} className="me-1" />
                            {msg.content}
                          </div>
                        </div>
                      ) : (
                        <span style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</span>
                      )}
                    </div>
                    <div className={`text-muted mt-1 px-1`} style={{ fontSize: '9px', textAlign: isUser ? 'right' : 'left' }}>
                      {msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString("th-TH", { hour: '2-digit', minute: '2-digit' }) : ''}
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}

        {/* Typing Indicator */}
        {isTyping && (
          <div className="d-flex justify-content-start">
            <div className="d-flex gap-2">
              <div
                className="rounded-circle d-flex align-items-center justify-content-center flex-shrink-0"
                style={{ width: '32px', height: '32px', backgroundColor: '#1a1a2e' }}
              >
                <Brain size={14} color="white" />
              </div>
              <div className="p-3 bg-white border rounded-3" style={{ borderRadius: '16px', borderTopLeftRadius: '4px' }}>
                <div className="d-flex gap-1">
                  <span className="typing-dot"></span>
                  <span className="typing-dot" style={{ animationDelay: '0.2s' }}></span>
                  <span className="typing-dot" style={{ animationDelay: '0.4s' }}></span>
                </div>
                <div className="text-muted mt-1" style={{ fontSize: '10px' }}>
                  {aiActive ? 'AI กำลังพิมพ์...' : 'แพทย์กำลังพิมพ์...'}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ===== INPUT AREA ===== */}
      <div className="bg-white border-top px-3 py-2 flex-shrink-0" style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>

        {/* Quick Prompts */}
        {messages.length <= 2 && !isTyping && (
          <div className="d-flex gap-1.5 overflow-auto pb-2" style={{ scrollbarWidth: 'none' }}>
            {quickPrompts.map((prompt, i) => (
              <button
                key={i}
                onClick={() => handleSend(prompt)}
                className="btn btn-sm border rounded-pill flex-shrink-0 text-dark"
                style={{ fontSize: '11px', backgroundColor: '#f3f4f6', borderColor: '#e5e7eb' }}
              >
                {prompt}
              </button>
            ))}
          </div>
        )}

        <div className="d-flex align-items-center gap-2">
          {/* Attach Button */}
          <div className="position-relative">
            <button
              onClick={() => setShowImageOptions(!showImageOptions)}
              className="btn p-0 rounded-circle d-flex align-items-center justify-content-center border-0"
              style={{ width: '38px', height: '38px', backgroundColor: '#f3f4f6' }}
            >
              <Paperclip size={16} className="text-muted" />
            </button>

            {showImageOptions && (
              <div className="position-absolute bottom-100 start-0 mb-1 bg-white border rounded-3 shadow p-1" style={{ zIndex: 50, minWidth: '140px' }}>
                <button
                  onClick={() => {
                    setShowImageOptions(false);
                    document.getElementById('file-input')?.click();
                  }}
                  className="btn btn-sm w-100 text-start d-flex align-items-center gap-2 rounded-2 border-0"
                  style={{ fontSize: '12px', padding: '6px 12px' }}
                >
                  <Image size={14} /> อัปโหลดรูป
                </button>
                <button
                  onClick={() => {
                    setShowImageOptions(false);
                    document.getElementById('camera-input')?.click();
                  }}
                  className="btn btn-sm w-100 text-start d-flex align-items-center gap-2 rounded-2 border-0"
                  style={{ fontSize: '12px', padding: '6px 12px' }}
                >
                  <Camera size={14} /> ถ่ายภาพ
                </button>
              </div>
            )}

            <input id="file-input" type="file" accept="image/*" className="d-none" onChange={handleImageUpload} />
            <input id="camera-input" type="file" accept="image/*" capture="environment" className="d-none" onChange={handleImageUpload} />
          </div>

          {/* Text Input */}
          <div className="flex-grow-1 position-relative">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="พิมพ์ข้อความ..."
              className="form-control border-0 py-2 px-3"
              style={{
                backgroundColor: '#f3f4f6',
                borderRadius: '20px',
                fontSize: '14px',
                paddingRight: '40px'
              }}
            />
            <button
              onClick={toggleRecording}
              className={`btn position-absolute top-50 end-0 translate-middle-y p-0 border-0 bg-transparent ${isRecording ? 'text-danger' : 'text-muted'}`}
              style={{ marginRight: '10px' }}
            >
              <Mic size={16} className={isRecording ? 'recording-pulse' : ''} />
            </button>
          </div>

          {/* Send Button */}
          <button
            onClick={() => handleSend()}
            disabled={!input.trim()}
            className="btn p-0 rounded-circle d-flex align-items-center justify-content-center border-0 flex-shrink-0"
            style={{
              width: '38px',
              height: '38px',
              backgroundColor: input.trim() ? '#1a1a2e' : '#e5e7eb'
            }}
          >
            <Send size={16} style={{ color: input.trim() ? 'white' : '#9ca3af' }} />
          </button>
        </div>
      </div>

      <style jsx global>{`
        .hover-bg:hover { background-color: #f3f4f6; }
        
        .typing-dot {
          width: 6px;
          height: 6px;
          background-color: #9ca3af;
          border-radius: 50%;
          display: inline-block;
          animation: typingBounce 1.4s infinite ease-in-out both;
        }
        @keyframes typingBounce {
          0%, 80%, 100% { transform: scale(0.3); }
          40% { transform: scale(1.0); }
        }

        .recording-pulse {
          animation: pulse 1.2s infinite;
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }

        .overflow-auto::-webkit-scrollbar {
          width: 4px;
        }
        .overflow-auto::-webkit-scrollbar-track {
          background: transparent;
        }
        .overflow-auto::-webkit-scrollbar-thumb {
          background: #d1d5db;
          border-radius: 4px;
        }
        .overflow-auto::-webkit-scrollbar-thumb:hover {
          background: #9ca3af;
        }
      `}</style>
    </div>
  );
}