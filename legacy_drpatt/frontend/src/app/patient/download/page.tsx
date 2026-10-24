"use client";

import { useState, useEffect } from "react";
import { 
  ArrowLeft, 
  Download, 
  FileText, 
  FileImage, 
  File, 
  Search,
  Filter,
  Stethoscope,
  Microscope,
  Receipt,
  FileArchive,
  Loader2
} from "lucide-react";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const categories = [
  { id: "all", label: "ทั้งหมด" },
  { id: "medical_cert", label: "ใบรับรองแพทย์" },
  { id: "lab_result", label: "ผลตรวจ Lab" },
  { id: "receipt", label: "ใบเสร็จรับเงิน" },
];

export default function PatientDownloadPage() {
  const [activeTab, setActiveTab] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuthAndLoad = async () => {
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
          const patientProfile = await res.json();
          const docsData: any[] = [];

          // 1. Process generated clinical reports from extra_data
          const generatedReports = patientProfile.extra_data?.generated_reports || [];
          generatedReports.forEach((rep: any) => {
            const dateObj = rep.createdAt ? new Date(rep.createdAt) : new Date();
            let docType = "lab_result";
            if (rep.reportType === "physician") docType = "medical_cert";
            else if (rep.reportType === "patient") docType = "prescription";

            docsData.push({
              id: rep.id,
              type: docType,
              title: `รายงาน TSPI (${rep.reportType.toUpperCase()})`,
              date: dateObj.toLocaleDateString('th-TH', { day: 'numeric', month: 'short', year: 'numeric' }),
              doctor: "TSPI Systemic AI",
              size: "1.2 MB",
              format: "PDF / MD",
              url: "#",
              timestamp: dateObj.getTime()
            });
          });

          // 2. Process other general documents if uploaded/listed in extra_data.documents
          const generalDocs = patientProfile.extra_data?.documents || [];
          generalDocs.forEach((doc: any) => {
            const dateObj = doc.createdAt ? new Date(doc.createdAt) : new Date();
            docsData.push({
              id: doc.id || String(Math.random()),
              type: doc.type || "other",
              title: doc.title || "เอกสารแนบ",
              date: dateObj.toLocaleDateString('th-TH', { day: 'numeric', month: 'short', year: 'numeric' }),
              doctor: doc.doctorName || "เจ้าหน้าที่",
              size: doc.size || "Unknown",
              format: doc.format || "PDF",
              url: doc.url || "#",
              timestamp: dateObj.getTime()
            });
          });

          docsData.sort((a, b) => b.timestamp - a.timestamp);
          setDocuments(docsData);
        } else {
          window.location.href = "/patient/login";
        }
      } catch (error) {
        console.error("Error fetching documents from Django EMR:", error);
      } finally {
        setLoading(false);
      }
    };
    
    checkAuthAndLoad();
  }, []);

  const filteredDocs = documents.filter(doc => 
    (activeTab === "all" || doc.type === activeTab) &&
    (doc.title.includes(searchQuery) || doc.date.includes(searchQuery))
  );

  const getIconForType = (type: string) => {
    switch (type) {
      case "medical_cert": return <Stethoscope size={24} className="text-primary-custom" />;
      case "lab_result": return <Microscope size={24} className="text-info" />;
      case "receipt": return <Receipt size={24} className="text-success" />;
      case "prescription": return <FileText size={24} className="text-warning" />;
      default: return <File size={24} className="text-secondary" />;
    }
  };

  return (
    <div className="min-vh-100 font-kanit pb-5" style={{ backgroundColor: '#F2F2F7' }}>
      
      {/* Header */}
      <div className="bg-white px-3 py-3 d-flex align-items-center justify-content-between shadow-sm position-sticky top-0" style={{ zIndex: 10 }}>
        <div className="d-flex align-items-center gap-3">
          <Link href="/patient/dashboard" className="text-muted text-decoration-none p-1">
            <ArrowLeft size={22} />
          </Link>
          <div>
            <h5 className="fw-bold text-dark mb-0 lh-1">เอกสารของฉัน</h5>
            <p className="small text-muted mb-0" style={{ fontSize: '0.8rem' }}>ดาวน์โหลดใบรับรองแพทย์และผลตรวจ</p>
          </div>
        </div>
        <div className="bg-light rounded-circle p-2 shadow-sm border border-white">
          <FileArchive size={20} className="text-primary-custom" />
        </div>
      </div>

      <div className="container-fluid p-3 max-w-md mx-auto mt-2">
        
        {/* Search Bar */}
        <div className="mb-4 position-relative animate-fade-in">
          <Search size={18} className="position-absolute text-muted" style={{ top: '50%', left: '16px', transform: 'translateY(-50%)' }} />
          <input 
            type="text" 
            className="form-control rounded-pill ps-5 bg-white border-0 shadow-sm py-3 small fw-medium" 
            placeholder="ค้นหาเอกสาร, วันที่..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <button className="btn btn-link position-absolute end-0 top-50 translate-middle-y text-muted text-decoration-none">
            <Filter size={18} />
          </button>
        </div>

        {/* Categories (Horizontal Scroll) */}
        <div className="d-flex gap-2 overflow-auto pb-2 mb-3 no-scrollbar animate-fade-in">
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setActiveTab(cat.id)}
              className={`btn btn-sm rounded-pill px-3 py-2 fw-medium flex-shrink-0 transition-all ${
                activeTab === cat.id 
                  ? 'btn-primary-custom shadow-sm' 
                  : 'bg-white text-muted border-light shadow-sm'
              }`}
              style={{ fontSize: '0.85rem' }}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Document List */}
        <h6 className="fw-bold text-dark mb-3 ps-1 mt-4">รายการเอกสาร {!loading && `(${filteredDocs.length})`}</h6>
        
        {loading ? (
          <div className="d-flex flex-column align-items-center justify-content-center py-5">
            <Loader2 size={32} className="animate-spin text-primary-custom mb-2" />
            <p className="text-muted small">กำลังดึงข้อมูลเอกสาร...</p>
          </div>
        ) : filteredDocs.length > 0 ? (
          <div className="d-grid gap-3">
            {filteredDocs.map((doc, idx) => (
              <div 
                key={doc.id} 
                className="bg-white rounded-4 p-3 shadow-sm border border-light d-flex align-items-center gap-3 animate-fade-in"
                style={{ animationDelay: `${idx * 0.1}s` }}
              >
                {/* Icon Box */}
                <div className="rounded-circle bg-light d-flex align-items-center justify-content-center flex-shrink-0" style={{ width: '50px', height: '50px' }}>
                  {getIconForType(doc.type)}
                </div>
                
                {/* Info */}
                <div className="flex-grow-1 overflow-hidden">
                  <h6 className="fw-bold text-dark mb-1 text-truncate" style={{ fontSize: '0.95rem' }}>{doc.title}</h6>
                  <p className="text-muted mb-1 text-truncate" style={{ fontSize: '0.8rem' }}>{doc.doctor}</p>
                  <div className="d-flex align-items-center gap-2">
                    <span className="badge bg-light text-secondary border px-2 py-1" style={{ fontSize: '0.7rem' }}>{doc.format}</span>
                    <span className="text-muted" style={{ fontSize: '0.75rem' }}>• {doc.size}</span>
                    <span className="text-muted" style={{ fontSize: '0.75rem' }}>• {doc.date}</span>
                  </div>
                </div>

                {/* Actions */}
                <div className="d-flex flex-column gap-2">
                  <a href={doc.url} target="_blank" rel="noopener noreferrer" className="btn btn-light rounded-circle p-2 text-primary-custom hover-bg-primary d-flex align-items-center justify-content-center">
                    <Download size={18} />
                  </a>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-white rounded-4 p-5 text-center shadow-sm border-light mt-4 animate-fade-in">
            <div className="bg-light rounded-circle d-inline-flex align-items-center justify-content-center mb-3" style={{ width: '64px', height: '64px' }}>
              <File size={32} className="text-muted opacity-50" />
            </div>
            <h6 className="fw-bold text-dark">ไม่พบเอกสาร</h6>
            <p className="small text-muted mb-0">ไม่มีเอกสารในหมวดหมู่นี้ หรือลองค้นหาด้วยคำอื่น</p>
          </div>
        )}

      </div>

      <style jsx global>{`
        .bg-primary-custom { background-color: var(--drpat-primary, #0d6efd); }
        .text-primary-custom { color: var(--drpat-primary, #0d6efd); }
        .btn-primary-custom { background-color: var(--drpat-primary, #0d6efd); color: white; border: none; }
        .btn-primary-custom:hover { filter: brightness(0.9); color: white; }
        
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }

        .hover-bg-primary:hover {
          background-color: var(--drpat-primary, #0d6efd) !important;
          color: white !important;
          transition: all 0.2s ease;
        }
        
        .animate-fade-in { animation: fadeIn 0.4s ease-out both; }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-spin { animation: spin 1s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
