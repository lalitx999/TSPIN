"use client";

import { useState, useEffect } from "react";
import {
  Cpu, MessageSquare, Bell, CheckCircle, Clock, Search,
  Zap, Activity, Bot, RefreshCw, Loader2, PlayCircle, AlertCircle,
  ArrowRightCircle, Plus, Terminal, Send
} from "lucide-react";
import { getAutomations, createAutomationTask, runBackendWorkers } from "@/utils/api/services";
import Swal from "sweetalert2";
import "./../theme-inapp.css";

const STATUS_CONFIG: Record<string, { color: string; label: string; icon: any }> = {
  pending: { color: "warning", label: "รอคิวประมวลผล", icon: Clock },
  processing: { color: "primary", label: "กำลังดำเนินงาน", icon: RefreshCw },
  completed: { color: "success", label: "สำเร็จเสร็จสิ้น", icon: CheckCircle },
  failed: { color: "danger", label: "ขัดข้อง/ล้มเหลว", icon: AlertCircle },
};

const TYPE_TRANSLATIONS: Record<string, string> = {
  "FOLLOW_UP": "ติดตามอาการหลังรักษา (LINE/FCM)",
  "NO_SHOW_CHECK": "ตรวจสอบนัดตกหล่น (No-Show Check)",
  "PRE_VISIT_REMINDER": "แจ้งเตือนการนัดล่วงหน้า (Reminder)",
  "CONFIRMATION_REMINDER": "แจ้งเตือนนัดหมายคนไข้",
  "DATA_SYNC": "ซิงก์ข้อมูลเวชระเบียน EMR"
};

const TYPE_ICONS: Record<string, any> = {
  "FOLLOW_UP": MessageSquare,
  "NO_SHOW_CHECK": AlertCircle,
  "PRE_VISIT_REMINDER": Bell,
  "CONFIRMATION_REMINDER": Bell,
  "DATA_SYNC": RefreshCw,
};

export default function ClinicalAutomationsPage() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  
  // Panel state
  const [showNewTask, setShowNewTask] = useState(false);
  const [newTaskType, setNewTaskType] = useState("FOLLOW_UP");
  const [newTaskPatient, setNewTaskPatient] = useState("");
  const [newTaskHn, setNewTaskHn] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Trigger state & Terminal Logs state
  const [isRunningWorker, setIsRunningWorker] = useState(false);
  const [viewingLogTask, setViewingLogTask] = useState<any | null>(null);

  const fetchTasks = async () => {
    try {
      const data = await getAutomations();
      
      // Sort newest first based on created_at or createdAt
      data.sort((a: any, b: any) => {
        const timeA = a.created_at || a.createdAt ? new Date(a.created_at || a.createdAt).getTime() : 0;
        const timeB = b.created_at || b.createdAt ? new Date(b.created_at || b.createdAt).getTime() : 0;
        return timeB - timeA;
      });
      
      setTasks(data);
      setLoading(false);
    } catch (e) {
      console.error("Failed to load automations:", e);
    }
  };

  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 3000); // 3-second poll for simulated worker
    return () => {
      clearInterval(interval);
    };
  }, []);

  const handleRunAutomation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTaskPatient || !newTaskHn) return;
    
    setIsSubmitting(true);
    try {
      // Create task as pending on backend
      await createAutomationTask({
        type: newTaskType,
        status: "pending",
        patientName: newTaskPatient,
        patientHn: newTaskHn,
        scheduledFor: new Date().toISOString(),
        logs: ["จัดตั้งคิวงานแจ้งเตือนอัตโนมัติลง PostgreSQL เรียบร้อย รอดำเนินการโดย Django worker..."]
      });

      setNewTaskPatient("");
      setNewTaskHn("");
      setShowNewTask(false);
      
      Swal.fire({
         title: "เพิ่มงานรันคิวสำเร็จ!",
         text: "งานแจ้งเตือนได้รับบรรจุเข้าระบบ EMR แล้ว ท่านสามารถกดปุ่มเพื่อกระตุ้นให้บอทรันงานได้ทันที",
         icon: "success",
         confirmButtonColor: "#0A5C8E"
      });
      fetchTasks();
    } catch (error) {
      console.error(error);
      Swal.fire("ขัดข้อง", "ไม่สามารถจัดตั้งคิวงานได้", "error");
    }
    setIsSubmitting(false);
  };

  const handleTriggerWorker = async () => {
     setIsRunningWorker(true);
     try {
        const res: any = await runBackendWorkers();
        if (res && res.success) {
           Swal.fire({
              title: "รันหน่วยประมวลผลหลังบ้านสำเร็จ!",
              text: `ระบบหลังบ้านประมวลผลสำเร็จเสร็จสิ้น จำนวน ${res.processed} งานเรียบร้อย`,
              icon: "success",
              confirmButtonColor: "#0A5C8E"
           });
        } else {
           Swal.fire({
              title: "รันระบบประมวลผลสำเร็จ",
              text: "คิวงานทั้งหมดได้รับการตรวจสอบและอัปเดตเรียบร้อยแล้ว",
              icon: "success",
              confirmButtonColor: "#0A5C8E"
           });
        }
        fetchTasks();
     } catch (err) {
        console.error("Failed to run backend worker:", err);
        Swal.fire("ข้อผิดพลาด", "การรันคิวงานหลังบ้านขัดข้อง", "error");
     } finally {
        setIsRunningWorker(false);
     }
  };

  const parseDate = (createdVal: any) => {
     if (!createdVal) return "ไม่ระบุ";
     const date = new Date(createdVal);
     return date.toLocaleString("th-TH", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
     }) + " น.";
  };

  const filteredTasks = tasks.filter(t => 
     (t.patientName && t.patientName.toLowerCase().includes(searchQuery.toLowerCase())) ||
     (t.patientHn && t.patientHn.toLowerCase().includes(searchQuery.toLowerCase())) ||
     (t.type && t.type.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="pb-5 font-kanit text-start">
      {/* 🧭 Header Section */}
      <div className="d-flex justify-content-between align-items-end mb-4">
        <div>
          <h1 className="fs-3 fw-bold mb-1 text-dark d-flex align-items-center gap-2">
            <div className="bg-primary bg-opacity-10 p-2 rounded-3 text-primary shadow-sm">
              <Cpu size={24} />
            </div>
            ระบบวิเคราะห์และแจ้งเตือนอัตโนมัติ (Clinical Automations)
          </h1>
          <p className="text-muted text-xs uppercase font-bold tracking-widest ms-5 mb-0" style={{ fontSize: '10px' }}>การดำเนินงานดูแลคนไข้และบริหารคิวประมวลผลอัตโนมัติหลังบ้าน (Dual Channel LINE/FCM)</p>
        </div>
        <div className="d-flex gap-2">
          <button 
            onClick={handleTriggerWorker}
            disabled={isRunningWorker}
            className="btn btn-outline-primary font-bold uppercase tracking-tighter px-4 shadow d-flex align-items-center gap-2 rounded-pill"
          >
            {isRunningWorker ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />} 
            {isRunningWorker ? "กำลังรันคิว..." : "กระตุ้นการทำงานบอท (Trigger Worker)"}
          </button>

          <button 
            onClick={() => setShowNewTask(!showNewTask)}
            className="btn btn-primary font-bold uppercase tracking-tighter px-4 shadow d-flex align-items-center gap-2 rounded-pill"
          >
            {showNewTask ? <ArrowRightCircle size={16} /> : <Plus size={16} />} 
            {showNewTask ? "ปิดฟอร์ม" : "สั่งงานอัตโนมัติใหม่ (New)"}
          </button>
        </div>
      </div>

      {/* 📊 High-Level Metrics */}
      <div className="row g-3 mb-4">
        {[
          { label: "รอดำเนินการในคิว", val: tasks.filter(t => t.status === 'pending' || t.status === 'processing').length, color: "primary", icon: Bot, desc: "คิวงานทั้งหมดที่จัดตั้งค้างไว้" },
          { label: "ดำเนินการสำเร็จ", val: tasks.filter(t => t.status === 'completed').length, color: "success", icon: CheckCircle, desc: "ยิง LINE/FCM แจ้งเตือนคนไข้สำเร็จ" },
          { label: "ขัดข้อง/ล้มเหลว", val: tasks.filter(t => t.status === 'failed').length, color: "danger", icon: AlertCircle, desc: "งานที่ข้อมูลคนไข้ไม่ครบหรือเกิดข้อผิดพลาด" },
          { label: "ประวัติงานทั้งหมด", val: tasks.length, color: "dark", icon: Zap, desc: "ยอดการดำเนินงานทั้งหมดสะสม" },
        ].map((s, idx) => (
          <div key={idx} className="col-lg-3 col-6">
            <div className="card p-4 border-0 shadow-sm rounded-4 h-100" style={{ background: 'linear-gradient(145deg, #ffffff, #f8f9fa)'}}>
              <div className="d-flex justify-content-between align-items-center mb-3">
                <p className="text-[10px] font-bold text-muted uppercase tracking-widest mb-0" style={{ fontSize: '10.5px' }}>{s.label}</p>
                <s.icon size={18} className={`text-${s.color}`} />
              </div>
              <h3 className="fw-black mb-1 h3 text-dark">{loading ? "-" : s.val}</h3>
              <small className="text-[10px] text-muted font-bold uppercase tracking-tighter" style={{ fontSize: '9px' }}>{s.desc}</small>
            </div>
          </div>
        ))}
      </div>

      {/* 🚀 Trigger New Automation Form */}
      {showNewTask && (
        <div className="card border border-primary border-opacity-10 shadow-sm rounded-4 mb-4 bg-white overflow-hidden animate-fade-in">
          <div className="card-header border-0 bg-primary bg-opacity-10 p-4 pb-0 d-flex align-items-center gap-2">
             <PlayCircle size={18} className="text-primary" />
             <h6 className="mb-0 fw-bold tracking-widest uppercase text-primary text-sm">จัดตั้งคิวงานแจ้งเตือนอัตโนมัติด้วยตนเอง (Manual Trigger)</h6>
          </div>
          <div className="card-body p-4 bg-primary bg-opacity-10">
            <form onSubmit={handleRunAutomation} className="row g-3 align-items-end">
              <div className="col-md-3">
                <label className="form-label text-[10px] uppercase tracking-widest text-muted fw-bold" style={{ fontSize: '9px' }}>ประเภทงานบอทประมวลผล</label>
                <select 
                  className="form-select bg-white border-0 shadow-sm" 
                  value={newTaskType}
                  onChange={(e) => setNewTaskType(e.target.value)}
                >
                  <option value="FOLLOW_UP">คำถามติดตามอาการหลังพบแพทย์ (LINE/FCM)</option>
                  <option value="NO_SHOW_CHECK">ตรวจสอบนัดตกหล่นเบี้ยวตรวจ (No-Show)</option>
                  <option value="PRE_VISIT_REMINDER">แจ้งเตือนวันนัดหมายล่วงหน้า (Reminder)</option>
                  <option value="DATA_SYNC">บังคับซิงก์ข้อมูล EMR</option>
                </select>
              </div>
              <div className="col-md-3">
                <label className="form-label text-[10px] uppercase tracking-widest text-muted fw-bold" style={{ fontSize: '9px' }}>ชื่อคนไข้เป้าหมาย</label>
                <input 
                  type="text" 
                  className="form-control bg-white border-0 shadow-sm" 
                  placeholder="เช่น สมชาย เจริญดี"
                  value={newTaskPatient}
                  onChange={(e) => setNewTaskPatient(e.target.value)}
                  required
                />
              </div>
              <div className="col-md-3">
                <label className="form-label text-[10px] uppercase tracking-widest text-muted fw-bold" style={{ fontSize: '9px' }}>เลขทะเบียนคนไข้ (HN)</label>
                <input 
                  type="text" 
                  className="form-control bg-white border-0 shadow-sm" 
                  placeholder="เช่น 67-00022"
                  value={newTaskHn}
                  onChange={(e) => setNewTaskHn(e.target.value)}
                  required
                />
              </div>
              <div className="col-md-3">
                <button 
                  type="submit" 
                  className="btn btn-primary shadow-sm w-100 fw-bold tracking-widest uppercase d-flex align-items-center justify-content-center gap-2"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                  {isSubmitting ? "กำลังดำเนินการ..." : "จัดตั้งคิวงาน"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Search Input */}
      <div className="position-relative mb-4">
         <Search className="position-absolute top-50 start-0 translate-middle-y ms-3 text-muted" size={18} />
         <input 
            type="text" 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="form-control rounded-4 ps-5 bg-white border-light shadow-sm py-3 small fw-medium text-dark" 
            placeholder="ค้นหาตามชื่อคนไข้, HN, หรือประเภทของงาน..." 
         />
      </div>

      {/* 🏛️ Automation Mission Board */}
      <div className="card shadow-sm border-0 bg-white overflow-hidden rounded-4">
        <div className="card-header bg-white border-bottom border-light py-4 d-flex justify-content-between align-items-center px-4">
          <div className="d-flex align-items-center gap-2">
            <Activity size={18} className="text-primary" />
            <h3 className="card-title text-sm font-bold uppercase text-dark tracking-widest mb-0" style={{ fontSize: '13.5px' }}>รายการคิวงานและสถานะการประมวลผลบอท (Postgres Table)</h3>
          </div>
        </div>
        <div className="table-responsive">
          <table className="table table-hover align-middle mb-0 text-nowrap">
            <thead className="bg-light border-bottom text-[10px] uppercase font-bold text-muted tracking-wider">
              <tr>
                <th className="px-4 py-3">รหัสงาน</th>
                <th className="py-3">ประเภทงานวิเคราะห์</th>
                <th className="py-3">เป้าหมายคนไข้</th>
                <th className="py-3">วันเวลาจัดคิว</th>
                <th className="py-3 text-center">สถานะการรัน</th>
                <th className="py-3 text-center pr-4"> บันทึกการทำงาน (Logs)</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="text-center py-5"><Loader2 className="animate-spin text-primary opacity-50 mx-auto" size={32} /></td></tr>
              ) : filteredTasks.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-5">
                    <div className="d-flex flex-column align-items-center justify-content-center opacity-50">
                       <Bot size={48} className="mb-3 text-muted" />
                       <span className="text-muted font-bold tracking-widest uppercase text-xs">ไม่พบคิวงานในระบบ EMR หรือผลลัพธ์การค้นหา</span>
                    </div>
                  </td>
                </tr>
              ) : filteredTasks.map((task) => {
                const Icon = TYPE_ICONS[task.type] || Bot;
                const status = STATUS_CONFIG[task.status] || { color: "secondary", label: task.status, icon: Activity };
                const StatusIcon = status.icon;
                
                return (
                  <tr key={task.id} className="border-bottom border-light">
                    <td className="px-4 py-3">
                      <div className="text-[11px] font-mono text-muted uppercase font-bold">#{String(task.id || '').slice(-8).toUpperCase()}</div>
                    </td>
                    <td className="py-3">
                      <div className="d-flex align-items-center gap-3">
                        <div className="bg-light p-2 rounded-circle text-dark shadow-sm border"><Icon size={14} /></div>
                        <span className="text-xs font-bold text-dark uppercase tracking-wider">{TYPE_TRANSLATIONS[task.type] || task.type}</span>
                      </div>
                    </td>
                    <td className="py-3">
                      <div className="text-xs font-bold text-dark">{task.patientName || "เป้าหมายระบบภายนอก"}</div>
                      <div className="text-[10px] text-muted uppercase tracking-wider mt-1">HN: {task.patientHn || "ไม่ระบุ"}</div>
                    </td>
                    <td className="py-3">
                      <div className="d-flex align-items-center gap-2 text-[11px] font-bold text-muted">
                        <Clock size={12} /> {parseDate(task.created_at || task.createdAt)}
                      </div>
                    </td>
                    <td className="py-3 text-center">
                      <div className={`d-inline-flex align-items-center gap-1 badge bg-${status.color} bg-opacity-10 text-${status.color} text-[10px] uppercase px-3 py-2 border border-${status.color} border-opacity-20 rounded-pill font-black tracking-wider`}>
                        {task.status === 'processing' ? <RefreshCw size={10} className="animate-spin" /> : <StatusIcon size={10} />}
                        {status.label}
                      </div>
                    </td>
                    <td className="py-3 text-center pr-4">
                      <button 
                        onClick={() => setViewingLogTask(task)}
                        className="btn btn-light btn-sm border px-3 rounded-pill" 
                        title="ดูประวัติการทำงาน (Logs Console)"
                      >
                        <Terminal size={12} className="text-muted" /> ดู Logs
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Live Terminal Log Modal Popup */}
      {viewingLogTask && (
         <div className="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center bg-dark bg-opacity-50" style={{ zIndex: 1050, backdropFilter: 'blur(3px)' }}>
            <div className="bg-dark text-success rounded-4 p-4 max-w-lg w-100 mx-3 shadow-lg border border-secondary" style={{ fontFamily: 'monospace' }}>
               <div className="d-flex justify-content-between align-items-center border-bottom border-secondary pb-3 mb-3">
                  <span className="text-light fw-bold" style={{ fontSize: '13px' }}>📟 บันทึกการทำงานระบบอัตโนมัติ (Console Logs)</span>
                  <button className="btn-close btn-close-white" onClick={() => setViewingLogTask(null)}></button>
               </div>
               
               <div className="p-3 rounded-3 text-start overflow-auto bg-black" style={{ height: '300px', fontSize: '12px', lineHeight: '1.7', color: '#10B981', border: '1px solid #1f2937' }}>
                  <div className="mb-2 text-muted">// รหัสงาน (Task ID): #{viewingLogTask.id}</div>
                  <div className="mb-2 text-muted">// ประเภทงาน: {TYPE_TRANSLATIONS[viewingLogTask.type] || viewingLogTask.type}</div>
                  <div className="mb-3 text-muted">// หมายเลข HN คนไข้: {viewingLogTask.patientHn || "ไม่มี"}</div>
                  
                  {viewingLogTask.logs && viewingLogTask.logs.length > 0 ? (
                     viewingLogTask.logs.map((log: string, idx: number) => (
                        <div key={idx} className="mb-1">
                           <span className="text-success">&gt;&gt;</span> {log}
                        </div>
                     ))
                  ) : (
                     <div className="text-muted">&gt; ไม่พบข้อมูลบันทึก Logs การประมวลผลสำหรับงานนี้</div>
                  )}
               </div>
               
               <div className="mt-3 text-end d-flex justify-content-end gap-2">
                  <button className="btn btn-outline-light btn-sm rounded-pill px-4" onClick={() => setViewingLogTask(null)}>ปิดหน้าต่างคอนโซล</button>
               </div>
            </div>
         </div>
      )}

      <style jsx>{`
        .animate-spin {
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .animate-fade-in {
          animation: fadeInDown 0.35s ease;
        }
        @keyframes fadeInDown {
          from { opacity: 0; transform: translateY(-8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
