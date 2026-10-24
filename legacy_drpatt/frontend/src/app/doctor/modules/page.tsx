"use client";

import { useState, useEffect } from "react";
import {
  Plus, Search, Edit2, Trash2, Download,
  Filter, Loader2, FileText, AlertCircle,
  CheckCircle, Database, LayoutGrid, Import,
  Library, Settings2, FileOutput, RefreshCw,
  ChevronLeft, ChevronRight, X
} from "lucide-react";
import { getModules, createModule, updateModule, deleteModule } from "@/utils/api/services";
import "./../theme-inapp.css";
import Swal from "sweetalert2";

// ตาม tspi_control.txt ข้อ 3b: Bowel regulation modules ใช้ dosing พิเศษ
const BOWEL_MODULES = ["KS", "Be Lax", "Cathartic", "Lypholax", "Venta"];

const isBowelModule = (name: string) => {
  if (!name) return false;
  return BOWEL_MODULES.some(bm => name.toLowerCase().includes(bm.toLowerCase()));
};

export default function ModuleMasterPage() {
  const [modules, setModules] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [showImport, setShowImport] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState("All Protocols");

  // Manual Add Form States
  const [showAddForm, setShowAddForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [newModuleName, setNewModuleName] = useState("");
  const [newModuleCategory, setNewModuleCategory] = useState("Standard");
  const [newModuleProperties, setNewModuleProperties] = useState("");
  const [newModuleIndications, setNewModuleIndications] = useState("");

  const [currentPage, setCurrentPage] = useState(1);
  const [selectedModule, setSelectedModule] = useState<any | null>(null);
  const itemsPerPage = 15;

  // Edit Form States
  const [showEditForm, setShowEditForm] = useState(false);
  const [editingModule, setEditingModule] = useState<any | null>(null);
  const [editModuleName, setEditModuleName] = useState("");
  const [editModuleCategory, setEditModuleCategory] = useState("Standard");
  const [editModuleIndications, setEditModuleIndications] = useState("");
  const [editModuleMechanism, setEditModuleMechanism] = useState("");
  const [editModuleMarkers, setEditModuleMarkers] = useState("");
  const [editModuleAxisMapping, setEditModuleAxisMapping] = useState("");

  const handleOpenEdit = (m: any) => {
    setEditingModule(m);
    setEditModuleName(m.name || "");
    setEditModuleCategory(m.category || "Standard");
    setEditModuleIndications(m.indications || "");
    setEditModuleMechanism(m.mechanism || "");
    setEditModuleMarkers(m.markers || m.active_markers || "");
    setEditModuleAxisMapping(m.tspi_axis_mapping || "");
    setShowEditForm(true);
  };

  const handleSaveEdit = async () => {
    if (!editModuleName.trim()) {
      Swal.fire({
        icon: "warning",
        title: "กรุณากรอกชื่อโมดูล",
        confirmButtonColor: "#0A5C8E"
      });
      return;
    }
    setSubmitting(true);
    try {
      await updateModule(editingModule.id, {
        name: editModuleName.trim(),
        category: editModuleCategory,
        indications: editModuleIndications.trim(),
        mechanism: editModuleMechanism.trim(),
        markers: editModuleMarkers.trim(),
        tspi_axis_mapping: editModuleAxisMapping.trim()
      });
      Swal.fire({
        icon: "success",
        title: "แก้ไขสำเร็จ! 🎉",
        text: `อัปเดตข้อมูลโมดูล "${editModuleName}" เรียบร้อยแล้ว`,
        confirmButtonColor: "#0A5C8E"
      });
      setShowEditForm(false);
      setEditingModule(null);
      fetchModules();
    } catch (err) {
      console.error(err);
      Swal.fire("เกิดข้อผิดพลาด", "ไม่สามารถแก้ไขโมดูลได้", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteModule = async (id: string, name: string) => {
    const confirm = await Swal.fire({
      title: "ยืนยันการลบโมดูล? 🗑️",
      text: `คุณต้องการลบโมดูล "${name}" ออกจากระบบใช่หรือไม่?`,
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: "ยืนยันการลบ",
      cancelButtonText: "ยกเลิก",
      confirmButtonColor: "#dc3545",
      cancelButtonColor: "#6c757d"
    });
    
    if (confirm.isConfirmed) {
      try {
        await deleteModule(id);
        Swal.fire({
          icon: "success",
          title: "ลบโมดูลสำเร็จ! 🎉",
          text: `โมดูล "${name}" ถูกลบออกแล้ว`,
          confirmButtonColor: "#0A5C8E"
        });
        fetchModules();
      } catch (err) {
        console.error(err);
        Swal.fire("เกิดข้อผิดพลาด", "ไม่สามารถลบโมดูลได้", "error");
      }
    }
  };

  const fetchModules = async () => {
    setLoading(true);
    try {
      const data = await getModules();
      // ตาม tspi_control.txt ข้อ 1b: De-duplicate — product เดียวกัน = module เดียวกัน
      const seen = new Set<string>();
      const unique = data.filter((m: any) => {
        const key = (m.name || m.module_name || "").toLowerCase().trim();
        if (!key || seen.has(key)) return false;
        seen.add(key);
        return true;
      });
      setModules(unique);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModules();
  }, []);

  // Reset to first page when search or filter changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, categoryFilter]);

  const handleAddModule = async () => {
    if (!newModuleName.trim()) {
      Swal.fire({
        icon: 'warning',
        title: 'คำเตือน',
        text: 'กรุณากรอกชื่อโปรโตคอลด้วยครับ',
        confirmButtonText: 'ตกลง',
        confirmButtonColor: '#0A5C8E'
      });
      return;
    }
    // ตาม tspi_control.txt ข้อ 1a: 1 Module = 1 Product — ป้องกันการสร้าง duplicate
    const duplicate = modules.find(
      (m: any) => (m.name || "").toLowerCase().trim() === newModuleName.toLowerCase().trim()
    );
    if (duplicate) {
      Swal.fire({
        icon: 'warning',
        title: 'Product นี้มีอยู่ในระบบแล้ว',
        text: `"${newModuleName}" มีอยู่แล้วในทะเบียน (ID: ${duplicate.id || 'N/A'}) ตาม tspi_control.txt: 1 Module = 1 Product`,
        confirmButtonText: 'ตกลง',
        confirmButtonColor: '#0A5C8E'
      });
      return;
    }
    setSubmitting(true);
    try {
      await createModule({
        name: newModuleName.trim(),
        category: newModuleCategory,
        properties: newModuleProperties.trim(),
        indications: newModuleIndications.trim(),
      });
      
      // Reset form
      setNewModuleName("");
      setNewModuleCategory("Standard");
      setNewModuleProperties("");
      setNewModuleIndications("");
      setShowAddForm(false);
      
      Swal.fire({
        icon: 'success',
        title: 'บันทึกสำเร็จ',
        text: 'บันทึกตำรับโปรโตคอลการรักษาใหม่เรียบร้อยแล้วครับ',
        confirmButtonText: 'ตกลง',
        confirmButtonColor: '#0A5C8E'
      });
      
      // Re-fetch modules
      await fetchModules();
    } catch (err) {
      console.error("Error saving module:", err);
      Swal.fire({
        icon: 'error',
        title: 'เกิดข้อผิดพลาด',
        text: 'ไม่สามารถบันทึกข้อมูลได้',
        confirmButtonText: 'ตกลง',
        confirmButtonColor: '#0A5C8E'
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCSVImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsImporting(true);
    const reader = new FileReader();
    reader.onload = async (event) => {
      const text = event.target?.result as string;
      const rows = text.split("\n").slice(1);

      let count = 0;
      for (const row of rows) {
        if (!row.trim()) continue;
        const [name, category, properties, indications] = row.split(",");

        await createModule({
          name: name?.trim(),
          category: category?.trim(),
          properties: properties?.trim(),
          indications: indications?.trim(),
        });
        count++;
      }
      Swal.fire({
        icon: 'success',
        title: 'นำเข้าสำเร็จ',
        text: `นำเข้าตำรับการรักษาสำเร็จทั้งหมด ${count} รายการเรียบร้อยแล้วครับ`,
        confirmButtonText: 'ตกลง',
        confirmButtonColor: '#0A5C8E'
      });
      fetchModules();
      setIsImporting(false);
      setShowImport(false);
    };
    reader.readAsText(file);
  };

  const filteredModules = modules.filter(m => {
    const matchSearch = (m.name || m.module_name || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
                        (m.category || "").toLowerCase().includes(searchTerm.toLowerCase());
    const matchCategory = categoryFilter === "All Protocols" || (m.category || "") === categoryFilter;
    return matchSearch && matchCategory;
  });

  const totalPages = Math.ceil(filteredModules.length / itemsPerPage);
  const currentItems = filteredModules.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  const CATEGORY_EMOJIS: any = {
    "Standard": "💊",
    "Experimental": "🔬",
    "Legacy": "📜",
    "Default": "✨"
  };

  return (
    <div className="pb-5" style={{ fontFamily: "Kanit, sans-serif" }}>
      {/* 🧭 Header Section */}
      <div className="d-flex justify-content-between align-items-end mb-4">
        <div>
          <h1 className="fs-3 fw-bold mb-1 text-dark d-flex align-items-center gap-2">
            <div className="bg-primary bg-opacity-10 p-2 rounded-3 text-primary shadow-sm">
              <Library size={24} />
            </div>
            คลังความรู้ตำรับยาการรักษา (Therapeutic Knowledge Base)
          </h1>
          <p className="text-muted text-xs uppercase font-bold tracking-widest ms-5 mb-0">ทะเบียนโปรโตคอลและระบบบริหารจัดการข้อมูลหลัก (Master Data Registry)</p>
        </div>
        <div className="d-flex gap-2">
          <button
            onClick={() => {
              setShowImport(!showImport);
              setShowAddForm(false);
            }}
            className="btn btn-outline-secondary font-bold uppercase tracking-widest text-[10px] px-4 py-2 bg-white shadow-sm d-flex align-items-center gap-2 rounded-pill"
          >
            <Import size={14} /> นำเข้าไฟล์ CSV
          </button>
          <button 
            onClick={() => {
              setShowAddForm(!showAddForm);
              setShowImport(false);
            }}
            className={`btn font-bold uppercase tracking-widest text-[10px] px-4 py-2 shadow-sm d-flex align-items-center gap-2 rounded-pill ${showAddForm ? 'btn-light border bg-white text-dark' : 'btn-primary text-white'}`}
          >
            {showAddForm ? <X size={14} /> : <Plus size={14} />} {showAddForm ? 'ยกเลิก' : 'เพิ่มโปรโตคอลใหม่'}
          </button>
          <button 
             onClick={fetchModules}
             disabled={loading}
             className="btn btn-light border font-bold uppercase tracking-widest text-[10px] px-3 py-2 bg-white shadow-sm d-flex align-items-center rounded-pill"
          >
             <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* 🛠️ Action Tools & Filters */}
      <div className="card shadow-sm border-0 mb-4 bg-white rounded-4 overflow-hidden">
        <div className="card-body p-4">
          <div className="row align-items-center g-3">
            <div className="col-md-6">
              <div className="position-relative">
                <Search size={16} className="position-absolute top-50 start-0 translate-middle-y ms-3 text-muted" />
                <input
                  type="text"
                  className="form-control rounded-pill bg-light border-0 py-2.5 ps-5 pe-3 text-sm font-semibold text-dark"
                  placeholder="ค้นหาโปรโตคอลด้วยชื่อ หรือกลุ่มหมวดหมู่..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
            </div>
            <div className="col-md-6 text-md-end">
              <div className="btn-group shadow-sm rounded-pill overflow-hidden">
                {["All Protocols", "Standard", "Experimental", "Legacy"].map((cat) => {
                  const labelMap: Record<string, string> = {
                    "All Protocols": "ทุกโปรโตคอล",
                    "Standard": "มาตรฐาน",
                    "Experimental": "วิจัยทดลอง",
                    "Legacy": "ดั้งเดิม"
                  };
                  return (
                    <button
                      key={cat}
                      onClick={() => setCategoryFilter(cat)}
                      className={`btn btn-sm px-4 py-2.5 font-bold uppercase tracking-widest text-[10px] border-0 ${cat === categoryFilter ? 'btn-primary text-white' : 'bg-light text-muted'}`}
                    >
                      {labelMap[cat] || cat}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ➕ New Protocol Form Area */}
      {showAddForm && (
        <div className="card border-0 shadow-sm bg-white rounded-4 overflow-hidden mb-4 border-primary border-opacity-25 border-top border-4 animate-in fade-in slide-in-from-top-2">
             <div className="card-header bg-transparent py-3 px-4 border-0">
                  <h5 className="fw-bold text-primary text-xs uppercase tracking-widest mb-0">สร้างโปรโตคอลการรักษาใหม่</h5>
             </div>
             <div className="card-body p-4 pt-0">
                <div className="row g-3">
                   <div className="col-md-4">
                      <label className="text-[10px] font-bold text-muted uppercase tracking-widest mb-2 d-block">ชื่อโปรโตคอล / ตำรับยา</label>
                      <input 
                         type="text" 
                         className="form-control rounded-pill bg-light border-0 py-2.5 px-3 text-sm font-semibold text-dark" 
                         placeholder="ระบุชื่อภาษาอังกฤษ หรือภาษาไทย..." 
                         value={newModuleName}
                         onChange={(e) => setNewModuleName(e.target.value)}
                      />
                   </div>
                   <div className="col-md-4">
                      <label className="text-[10px] font-bold text-muted uppercase tracking-widest mb-2 d-block">หมวดหมู่ประเภท</label>
                      <select 
                         className="form-select rounded-pill bg-light border-0 py-2.5 px-3 text-sm font-semibold text-dark shadow-none"
                         value={newModuleCategory}
                         onChange={(e) => setNewModuleCategory(e.target.value)}
                      >
                         <option value="Standard">Standard (มาตรฐาน)</option>
                         <option value="Experimental">Experimental (วิจัยทดลอง)</option>
                         <option value="Legacy">Legacy (ดั้งเดิม)</option>
                      </select>
                   </div>
                   <div className="col-md-4">
                      <label className="text-[10px] font-bold text-muted uppercase tracking-widest mb-2 d-block">คุณสมบัติการออกฤทธิ์ (Properties)</label>
                      <input 
                         type="text" 
                         className="form-control rounded-pill bg-light border-0 py-2.5 px-3 text-sm font-semibold text-dark" 
                         placeholder="เช่น Anti-inflammatory, Hormonal balance..." 
                         value={newModuleProperties}
                         onChange={(e) => setNewModuleProperties(e.target.value)}
                      />
                   </div>
                   <div className="col-12">
                      <label className="text-[10px] font-bold text-muted uppercase tracking-widest mb-2 d-block">ข้อบ่งชี้ทางคลินิก (Clinical Indications)</label>
                      <textarea 
                         className="form-control rounded-4 bg-light border-0 py-2.5 px-3 text-sm font-semibold text-dark" 
                         rows={2}
                         placeholder="ระบุข้อบ่งชี้ทางคลินิกสำหรับการใช้งานการรักษานี้..." 
                         value={newModuleIndications}
                         onChange={(e) => setNewModuleIndications(e.target.value)}
                      />
                   </div>
                   <div className="col-12 mt-4 text-end d-flex justify-content-end gap-2">
                      <button 
                         className="btn btn-light border bg-white px-4 py-2.5 rounded-pill font-bold uppercase tracking-widest text-[10px] shadow-sm text-dark"
                         onClick={() => setShowAddForm(false)}
                      >
                         ยกเลิก
                      </button>
                      <button 
                         className="btn btn-primary btn-sm px-4 py-2.5 font-bold uppercase tracking-widest text-[10px] shadow-sm rounded-pill text-white"
                         onClick={handleAddModule}
                         disabled={submitting}
                      >
                         {submitting ? <Loader2 size={14} className="animate-spin d-inline me-1" /> : null}
                         บันทึกโปรโตคอล
                      </button>
                   </div>
                </div>
             </div>
        </div>
      )}

      {/* 🧪 Import HUD */}
      {showImport && (
        <div className="card border-0 shadow-sm bg-primary bg-opacity-5 border-dashed border-2 border-primary border-opacity-20 mb-4 rounded-4 animate-in fade-in slide-in-from-top-2">
          <div className="card-body p-5 text-center">
            <div className="bg-white d-inline-flex p-3 rounded-circle shadow-sm mb-3 text-primary border border-primary border-opacity-10">
              <FileOutput size={32} />
            </div>
            <h5 className="fw-bold text-primary mb-2 text-sm uppercase tracking-widest">เครื่องมือนำเข้าโปรโตคอลทีละหลายรายการ</h5>
            <p className="text-muted text-[11px] mx-auto mb-4" style={{ maxWidth: '400px' }}>เลือกไฟล์ CSV ที่มีข้อมูลโปรโตคอลทางคลินิก ระบบจะประมวลผลและลงทะเบียนโมดูลการรักษาแต่ละรายการเข้าสู่คลังความรู้โดยอัตโนมัติ</p>
            <div className="d-flex justify-content-center gap-2">
              <input
                type="file"
                id="csvInput"
                className="d-none"
                accept=".csv"
                onChange={handleCSVImport}
              />
              <label htmlFor="csvInput" className="btn btn-primary px-4 py-2.5 rounded-pill font-bold uppercase tracking-widest text-[10px] shadow-sm mb-0 cursor-pointer d-flex align-items-center gap-2 text-white">
                {isImporting ? <Loader2 className="animate-spin" size={14} /> : <Import size={14} />} 
                {isImporting ? 'กำลังนำเข้าข้อมูล...' : 'เลือกไฟล์ CSV'}
              </label>
              <button onClick={() => setShowImport(false)} className="btn btn-light border bg-white px-4 py-2.5 rounded-pill font-bold uppercase tracking-widest text-[10px] shadow-sm">ยกเลิก</button>
            </div>
          </div>
        </div>
      )}

      {/* 🏛️ Data Registry Table */}
      <div className="card shadow-sm border-0 bg-white rounded-4 overflow-hidden mb-5">
        <div className="card-header bg-transparent border-bottom border-light py-4 px-4 d-flex justify-content-between align-items-center">
          <h3 className="card-title text-[10px] font-bold uppercase text-muted tracking-widest mb-0">ทะเบียนข้อมูลหลักตำรับการรักษา</h3>
          <div className="text-[10px] font-bold text-primary bg-primary bg-opacity-10 px-3 py-1 rounded-pill uppercase tracking-widest">{filteredModules.length} รายการที่กำลังใช้งาน</div>
        </div>
        <div className="table-responsive">
          <table className="table table-hover table-valign-middle mb-0 text-nowrap align-middle">
            <thead className="bg-light text-[10px] uppercase font-bold text-muted tracking-wider">
              <tr>
                <th className="px-4 py-3 border-0" style={{ minWidth: '220px' }}>รหัสและชื่อโมดูล</th>
                <th className="py-3 border-0" style={{ width: '130px' }}>กลุ่มหมวดหมู่</th>
                <th className="py-3 border-0" style={{ minWidth: '250px' }}>ข้อบ่งชี้ทางคลินิก</th>
                <th className="py-3 border-0" style={{ width: '100px' }}>สถานะ</th>
                <th className="py-3 text-end pe-4 border-0" style={{ width: '120px' }}>จัดการ</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={5} className="text-center py-5 border-0"><Loader2 className="animate-spin text-primary opacity-20 mx-auto" size={32} /></td></tr>
              ) : filteredModules.length === 0 ? (
                <tr>
                   <td colSpan={5} className="text-center py-5 border-0">
                      <div className="opacity-10 mb-2"><Database size={48} className="mx-auto text-muted" /></div>
                      <p className="text-muted text-xs font-bold mb-0">ไม่พบรายการโปรโตคอลการรักษาในทะเบียนข้อมูลหลัก</p>
                   </td>
                </tr>
              ) : currentItems.map((m, index) => {
                const catEmoji = CATEGORY_EMOJIS[m.category] || CATEGORY_EMOJIS["Default"];
                return (
                <tr key={`${m.id || index}-${index}`} className="border-bottom border-light transition-all hover:bg-light" onClick={() => setSelectedModule(m)} style={{ cursor: "pointer" }}>
                  <td className="px-4 py-3">
                    <div className="d-flex align-items-center">
                      <div className="bg-primary bg-opacity-10 text-primary rounded-circle me-3 d-flex items-center justify-content-center font-bold" style={{ width: '40px', height: '40px', flexShrink: 0 }}>
                        <Settings2 size={18} />
                      </div>
                      <div>
                        <div className="font-bold text-dark text-sm mb-1">{m.name || m.module_name || "ไม่ระบุชื่อโมดูล"}</div>
                        <div className="d-flex align-items-center gap-1 flex-wrap">
                          {/* H-Code: Primary ID ตาม tspi_control.txt ข้อ 1c */}
                          <span className="badge text-[9px] px-2 py-1 rounded-pill fw-bold" style={{ background: '#EFF6FF', color: '#0A5C8E', border: '1px solid #BFDBFE' }}>
                            {String(m.id || '').toUpperCase()}
                          </span>
                          {/* PhytoCore Code: Future canonical ID ตาม tspi_control.txt ข้อ 3d */}
                          {m.module_code && (
                            <span className="badge text-[9px] px-2 py-1 rounded-pill" style={{ background: '#F3F4F6', color: '#6B7280', border: '1px solid #E5E7EB', fontFamily: 'monospace' }}>
                              {m.module_code}
                            </span>
                          )}
                          {/* Dosing type badge ตาม tspi_control.txt ข้อ 3b */}
                          {isBowelModule(m.name || m.module_name || '') ? (
                            <span className="badge text-[9px] px-2 py-1 rounded-pill fw-bold" style={{ background: '#FEF3C7', color: '#92400E', border: '1px solid #FDE68A' }}>
                              ⚠️ Individualized Dosing
                            </span>
                          ) : (
                            <span className="badge text-[9px] px-2 py-1 rounded-pill" style={{ background: '#F0FDF4', color: '#15803D', border: '1px solid #BBF7D0' }}>
                              Severity L0–L3
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="py-3">
                    <span className="badge bg-light border text-muted text-[9px] px-2 py-1.5 rounded-pill uppercase font-black tracking-widest d-inline-flex align-items-center gap-1">
                      {catEmoji} {m.category || "General"}
                    </span>
                  </td>
                  <td className="py-3">
                    <div className="text-xs text-dark font-medium text-wrap" style={{ maxWidth: '300px' }} title={m.indications}>{m.indications || "ไม่พบการระบุข้อบ่งชี้ทางคลินิกเป็นพิเศษ"}</div>
                  </td>
                  <td className="py-3">
                    <div className="d-flex align-items-center gap-1 text-success font-bold text-[9px] uppercase tracking-widest">
                      🟢 เปิดใช้งาน
                    </div>
                  </td>
                  <td className="py-3 text-end pe-4" onClick={(e) => e.stopPropagation()}>
                    <div className="btn-group shadow-sm rounded-pill overflow-hidden">
                      <button 
                        onClick={() => handleOpenEdit(m)}
                        className="btn btn-light btn-sm border-0 bg-light px-3 py-2 hover:bg-primary hover:text-white transition-colors" 
                        title="แก้ไขโปรโตคอล"
                      >
                        <Edit2 size={14} className="text-primary" />
                      </button>
                      <button 
                        onClick={() => handleDeleteModule(m.id, m.name || m.module_name || "ไม่ระบุชื่อ")}
                        className="btn btn-light btn-sm border-0 border-start px-3 py-2 text-danger hover:bg-danger hover:text-white transition-colors" 
                        title="ลบโปรโตคอล"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              )})}
            </tbody>
          </table>
        </div>
        
        {/* Pagination Controls */}
        {!loading && filteredModules.length > 0 && (
          <div className="card-footer bg-white border-top py-3 d-flex justify-content-between align-items-center px-4">
            <div className="text-[10px] font-bold text-muted uppercase tracking-widest">
              แสดง {(currentPage - 1) * itemsPerPage + 1} ถึง {Math.min(currentPage * itemsPerPage, filteredModules.length)} จากทั้งหมด {filteredModules.length} รายการ
            </div>
            <div className="d-flex gap-1">
              <button 
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="btn btn-sm btn-light border font-bold text-[10px] uppercase tracking-widest rounded-pill px-3 text-dark"
              >
                ก่อนหน้า
              </button>
              
              {/* Simple page numbers */}
              {Array.from({ length: totalPages }).map((_, idx) => {
                // Show max 5 pages, centered around current page if possible
                const p = idx + 1;
                if (p === 1 || p === totalPages || Math.abs(currentPage - p) <= 1) {
                  return (
                    <button 
                      key={p}
                      onClick={() => setCurrentPage(p)}
                      className={`btn btn-sm font-bold text-[10px] rounded-pill px-3 ${currentPage === p ? 'btn-primary text-white' : 'btn-light border text-dark'}`}
                    >
                      {p}
                    </button>
                  );
                } else if (p === 2 && currentPage > 3) {
                  return <span key="dots-1" className="px-2 text-muted d-flex align-items-center">...</span>;
                } else if (p === totalPages - 1 && currentPage < totalPages - 2) {
                  return <span key="dots-2" className="px-2 text-muted d-flex align-items-center">...</span>;
                }
                return null;
              })}

              <button 
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="btn btn-sm btn-light border font-bold text-[10px] uppercase tracking-widest rounded-pill px-3 text-dark"
              >
                ถัดไป
              </button>
            </div>
          </div>
        )}
      </div>
      
      {selectedModule && (
        <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1050 }}>
          <div className="modal-dialog modal-dialog-centered modal-lg">
            <div className="modal-content border-0 rounded-4 shadow-lg overflow-hidden" style={{ background: '#FFFFFF' }}>
              <div className="modal-header bg-primary text-white p-4 border-0 position-relative" style={{ background: '#0A5C8E' }}>
                <div>
                  <span className="badge text-[10px] px-2.5 py-1.5 rounded-pill fw-bold uppercase tracking-wider mb-2 d-inline-block" style={{ background: 'rgba(255,255,255,0.15)', color: 'white', border: '1px solid rgba(255,255,255,0.2)' }}>
                    ID: {selectedModule.id}
                  </span>
                  <h4 className="modal-title fw-bold text-lg mb-0 text-white">{selectedModule.name || "ไม่ระบุชื่อ"}</h4>
                  {selectedModule.module_code && (
                    <div className="text-[11px] opacity-80 mt-1 font-mono text-white">PhytoCore Code: {selectedModule.module_code}</div>
                  )}
                </div>
                <button type="button" className="btn-close btn-close-white position-absolute top-0 end-0 m-4" onClick={() => setSelectedModule(null)} aria-label="Close" style={{ filter: 'invert(1) grayscale(1) brightness(2)' }}></button>
              </div>
              <div className="modal-body p-4" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
                <div className="row g-4">
                  {/* Indications & Category */}
                  <div className="col-md-6">
                    <h6 className="text-[11px] font-bold text-muted uppercase tracking-widest mb-2">หมวดหมู่ / Category</h6>
                    <p className="text-sm font-semibold text-dark mb-4">
                      {CATEGORY_EMOJIS[selectedModule.category] || CATEGORY_EMOJIS["Default"]} {selectedModule.category || "General"}
                    </p>

                    <h6 className="text-[11px] font-bold text-muted uppercase tracking-widest mb-2">ข้อบ่งชี้ทางคลินิก / Indications</h6>
                    <p className="text-sm text-dark bg-light p-3 rounded-3 border mb-0" style={{ minHeight: '80px', lineHeight: 1.6, background: '#F9FAFB' }}>
                      {selectedModule.indications || "ไม่ระบุข้อบ่งชี้ทางคลินิกเป็นพิเศษ"}
                    </p>
                  </div>

                  {/* Mechanism & Active Markers */}
                  <div className="col-md-6">
                    <h6 className="text-[11px] font-bold text-muted uppercase tracking-widest mb-2">กลไกการออกฤทธิ์ / Mechanism</h6>
                    <p className="text-sm text-dark bg-light p-3 rounded-3 border mb-4" style={{ minHeight: '80px', lineHeight: 1.6, background: '#F9FAFB' }}>
                      {selectedModule.mechanism || "ไม่ระบุข้อมูลกลไกเชิงลึก"}
                    </p>

                    <h6 className="text-[11px] font-bold text-muted uppercase tracking-widest mb-2">สารสกัดสำคัญ / Active Markers</h6>
                    <p className="text-sm text-dark bg-light p-3 rounded-3 border mb-0" style={{ lineHeight: 1.6, background: '#F9FAFB' }}>
                      {selectedModule.markers || "ไม่ระบุสารออกฤทธิ์เฉพาะ"}
                    </p>
                  </div>

                  {/* Safety & Dosing (Rules 3b, 3c) */}
                  <div className="col-12 border-top pt-4">
                    <div className="row g-3">
                      <div className="col-md-6">
                        <div className="d-flex align-items-center gap-2 mb-2">
                          <span className="text-primary">🛡️</span>
                          <h6 className="text-[11px] font-bold text-muted uppercase tracking-widest mb-0">ความปลอดภัย & ข้อควรระวัง (Safety / Precautions)</h6>
                        </div>
                        <div className="text-sm text-dark bg-light p-3 rounded-3 border" style={{ minHeight: '60px', lineHeight: 1.6, background: '#F9FAFB' }}>
                          {selectedModule.safety || "⚠️ ยังไม่มีข้อมูลความปลอดภัยในฐานข้อมูล (รอ Master Registry Update)"}
                        </div>
                      </div>
                      <div className="col-md-6">
                        <div className="d-flex align-items-center gap-2 mb-2">
                          <span className="text-primary">📋</span>
                          <h6 className="text-[11px] font-bold text-muted uppercase tracking-widest mb-0">ปริมาณการสั่งใช้ (Dosing Regimen)</h6>
                        </div>
                        <div className="text-sm text-dark bg-light p-3 rounded-3 border" style={{ minHeight: '60px', lineHeight: 1.6, background: '#F9FAFB' }}>
                          {isBowelModule(selectedModule.name) ? (
                            <div>
                              <strong className="text-warning d-block mb-1">⚠️ Bowel Regulation Exception:</strong>
                              1–4 แคปซูล ก่อนนอน และทานซ้ำหลังตื่นนอน (ปรับตามสภาพการขับถ่ายของคนไข้)
                            </div>
                          ) : (
                            <div>
                              <strong>Standard Regimen:</strong> อิงตามระดับความรุนแรงของโรค (Severity Level L0–L3)
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Connected Axes (Rule 1d) */}
                  <div className="col-12 border-top pt-4">
                    <h6 className="text-[11px] font-bold text-muted uppercase tracking-widest mb-3">แกนสรีรวิทยาที่เชื่อมโยง (Mapped Biological Axes)</h6>
                    <div className="d-flex flex-wrap gap-2">
                      {selectedModule.axes && selectedModule.axes.length > 0 ? (
                        selectedModule.axes.map((axisNum: number) => (
                          <span key={axisNum} className="badge bg-light text-dark border px-3 py-2 rounded-pill font-semibold text-xs" style={{ background: '#F3F4F6' }}>
                            Axis {axisNum}
                          </span>
                        ))
                      ) : selectedModule.tspi_axis_mapping ? (
                        <div className="text-xs text-muted">{selectedModule.tspi_axis_mapping}</div>
                      ) : (
                        <span className="text-xs text-muted">ไม่ได้เชื่อมโยงกับแกนสรีรวิทยาใดๆ</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
              <div className="modal-footer bg-light p-3 border-0">
                <button type="button" className="btn btn-outline-secondary font-bold uppercase tracking-widest text-[10px] px-4 py-2 bg-white shadow-sm rounded-pill" onClick={() => setSelectedModule(null)}>
                  ปิดหน้าต่าง
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showEditForm && editingModule && (
        <div className="modal show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1060 }}>
          <div className="modal-dialog modal-dialog-centered modal-lg">
            <div className="modal-content border-0 rounded-4 shadow-lg overflow-hidden" style={{ background: '#FFFFFF' }}>
              <div className="modal-header bg-primary text-white p-4 border-0 position-relative" style={{ background: '#0A5C8E' }}>
                <div>
                  <h4 className="modal-title fw-bold text-lg mb-0 text-white">แก้ไขข้อมูลโมดูลความปลอดภัย</h4>
                  <div className="text-[11px] opacity-80 mt-1">ID: {editingModule.id}</div>
                </div>
                <button type="button" className="btn-close btn-close-white position-absolute top-0 end-0 m-4" onClick={() => { setShowEditForm(false); setEditingModule(null); }} aria-label="Close" style={{ filter: 'invert(1) grayscale(1) brightness(2)' }}></button>
              </div>
              <div className="modal-body p-4" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
                <div className="row g-3">
                  <div className="col-md-6">
                    <label className="form-label text-xs font-bold text-muted uppercase">ชื่อโมดูล / Product Name *</label>
                    <input 
                      type="text" 
                      className="form-control" 
                      required 
                      value={editModuleName} 
                      onChange={e => setEditModuleName(e.target.value)} 
                    />
                  </div>
                  <div className="col-md-6">
                    <label className="form-label text-xs font-bold text-muted uppercase">หมวดหมู่ / Category</label>
                    <select 
                      className="form-select" 
                      value={editModuleCategory} 
                      onChange={e => setEditModuleCategory(e.target.value)}
                    >
                      <option value="Standard">Standard Protocol</option>
                      <option value="Phytotherapy">Phytotherapy</option>
                      <option value="Bowel Regulation">Bowel Regulation</option>
                      <option value="Core Pathway">Core Pathway</option>
                      <option value="Custom">Custom Formula</option>
                    </select>
                  </div>
                  
                  <div className="col-12">
                    <label className="form-label text-xs font-bold text-muted uppercase">ข้อบ่งชี้ทางคลินิก / Indications</label>
                    <textarea 
                      className="form-control" 
                      rows={2} 
                      value={editModuleIndications} 
                      onChange={e => setEditModuleIndications(e.target.value)}
                    />
                  </div>

                  <div className="col-md-6">
                    <label className="form-label text-xs font-bold text-muted uppercase">กลไกการออกฤทธิ์ / Mechanism</label>
                    <textarea 
                      className="form-control" 
                      rows={3} 
                      value={editModuleMechanism} 
                      onChange={e => setEditModuleMechanism(e.target.value)}
                    />
                  </div>
                  <div className="col-md-6">
                    <label className="form-label text-xs font-bold text-muted uppercase">สารสกัดสำคัญ / Active Markers</label>
                    <textarea 
                      className="form-control" 
                      rows={3} 
                      value={editModuleMarkers} 
                      onChange={e => setEditModuleMarkers(e.target.value)}
                    />
                  </div>

                  <div className="col-12">
                    <label className="form-label text-xs font-bold text-muted uppercase">เชื่อมโยงแกนชีวภาพ / Mapped Axes (ระบุตัวเลขเช่น 1, 3, 37)</label>
                    <input 
                      type="text" 
                      className="form-control" 
                      placeholder="เช่น 1, 3, 37" 
                      value={editModuleAxisMapping} 
                      onChange={e => setEditModuleAxisMapping(e.target.value)} 
                    />
                  </div>
                </div>
              </div>
              <div className="modal-footer bg-light p-3 border-0 d-flex gap-2 justify-content-end">
                <button type="button" className="btn btn-outline-secondary font-bold uppercase tracking-widest text-[10px] px-4 py-2 bg-white shadow-sm rounded-pill" onClick={() => { setShowEditForm(false); setEditingModule(null); }}>
                  ยกเลิก
                </button>
                <button type="button" className="btn btn-primary font-bold uppercase tracking-widest text-[10px] px-4 py-2 shadow-sm rounded-pill text-white" style={{ background: '#0A5C8E', border: 'none' }} onClick={handleSaveEdit} disabled={submitting}>
                  {submitting ? "กำลังบันทึก..." : "บันทึกการแก้ไข"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <style jsx>{`
         .animate-spin { animation: spin 1s linear infinite; }
         @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
