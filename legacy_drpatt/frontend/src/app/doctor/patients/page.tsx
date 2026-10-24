"use client";

import { useState, useEffect } from "react";
import {
  Search, Users, Plus, Activity, Brain,
  FlaskConical, Microscope, ClipboardCheck, Import, History,
  ChevronRight
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getAllPatients } from "@/utils/api/services";

export default function PatientList() {
  const router = useRouter();
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [patients, setPatients] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 50;

  // รีเซ็ตหน้าแรกเสมอเมื่อเปลี่ยนคำค้นหาหรือเปลี่ยนตัวกรอง
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, selectedStatus]);

  useEffect(() => {
    const loadPatients = async () => {
      try {
        const data = await getAllPatients();
        setPatients(data);
      } catch (err) {
        console.error("Error loading patients:", err);
      } finally {
        setLoading(false);
      }
    };
    loadPatients();
  }, []);

  const filteredPatients = patients.filter(p => {
    const fullName = `${p.fname || p.name || ""} ${p.lname || ""}`.toLowerCase();
    const hn = (p.hn || "").toLowerCase();
    const search = searchTerm.toLowerCase();
    const matchesSearch = fullName.includes(search) || hn.includes(search);

    if (selectedStatus === "all") return matchesSearch;
    if (selectedStatus === "urgent") return matchesSearch && (p.status === 'ด่วน' || p.status === 'เคสด่วน');
    if (selectedStatus === "active") return matchesSearch && (p.status === 'กำลังตรวจ' || p.status === 'ติดตาม');
    if (selectedStatus === "completed") return matchesSearch && (p.status === 'เสร็จสิ้น' || p.status === 'ปกติ');
    return matchesSearch;
  });

  const totalPages = Math.ceil(filteredPatients.length / ITEMS_PER_PAGE);
  const paginatedPatients = filteredPatients.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  const stats = {
    total: patients.length,
    urgent: patients.filter(p => p.status === 'ด่วน' || p.status === 'เคสด่วน').length,
    active: patients.filter(p => p.status === 'กำลังตรวจ' || p.status === 'ติดตาม').length,
    completed: patients.filter(p => p.status === 'เสร็จสิ้น' || p.status === 'ปกติ').length,
  };

  if (loading) {
    return (
      <div className="d-flex align-items-center justify-content-center py-5">
        <div className="text-center">
          <div className="spinner-border text-primary mb-3" role="status" style={{ width: '32px', height: '32px' }}>
            <span className="visually-hidden">Loading...</span>
          </div>
          <p className="text-muted text-xs mb-0">Loading Clinical Registry...</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* ==================== HEADER ==================== */}
      <div className="d-flex justify-content-between align-items-center mb-6">
        <div>
          <h1 className="fs-4 fw-semibold mb-1" style={{ color: '#1F2937' }}>
            Patient Registry
          </h1>
          <p className="text-xs text-muted" style={{ letterSpacing: '0.3px' }}>
            Clinical Data & Biological Records
          </p>
        </div>
        <div className="d-flex gap-2">
          <button className="btn btn-outline" style={{ fontSize: '12px', padding: '6px 12px' }}>
            <Import size={14} className="me-1" /> Import CSV
          </button>
          <button className="btn btn-primary" style={{ fontSize: '12px', padding: '6px 12px' }}>
            <Plus size={14} className="me-1" /> New Patient
          </button>
        </div>
      </div>

      {/* ==================== STATS CARDS ==================== */}
      <div className="row g-4 mb-6">
        {/* Total Registered */}
        <div className="col-lg-3 col-md-6">
          <div className="card p-4">
            <div className="d-flex align-items-center justify-content-between mb-3">
              <div className="stat-icon" style={{
                width: '44px',
                height: '44px',
                background: '#E8F0F5',
                borderRadius: '6px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Users size={22} style={{ color: '#0A5C8E' }} />
              </div>
            </div>
            <h3 className="fs-2 fw-semibold mb-1" style={{ color: '#1F2937' }}>
              {stats.total}
            </h3>
            <p className="text-xs text-muted mb-0">Total Registered</p>
          </div>
        </div>

        {/* Urgent Triage */}
        <div className="col-lg-3 col-md-6">
          <div className="card p-4">
            <div className="d-flex align-items-center justify-content-between mb-3">
              <div className="stat-icon" style={{
                width: '44px',
                height: '44px',
                background: '#FEF2F2',
                borderRadius: '6px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Activity size={22} style={{ color: '#DC2626' }} />
              </div>
            </div>
            <h3 className="fs-2 fw-semibold mb-1" style={{ color: '#1F2937' }}>
              {stats.urgent}
            </h3>
            <p className="text-xs text-muted mb-0">Urgent Triage</p>
          </div>
        </div>

        {/* Active Treatment */}
        <div className="col-lg-3 col-md-6">
          <div className="card p-4">
            <div className="d-flex align-items-center justify-content-between mb-3">
              <div className="stat-icon" style={{
                width: '44px',
                height: '44px',
                background: '#ECFDF5',
                borderRadius: '6px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Microscope size={22} style={{ color: '#059669' }} />
              </div>
            </div>
            <h3 className="fs-2 fw-semibold mb-1" style={{ color: '#1F2937' }}>
              {stats.active}
            </h3>
            <p className="text-xs text-muted mb-0">Active Treatment</p>
          </div>
        </div>

        {/* Cases Completed */}
        <div className="col-lg-3 col-md-6">
          <div className="card p-4">
            <div className="d-flex align-items-center justify-content-between mb-3">
              <div className="stat-icon" style={{
                width: '44px',
                height: '44px',
                background: '#E8F0F5',
                borderRadius: '6px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <ClipboardCheck size={22} style={{ color: '#0A5C8E' }} />
              </div>
            </div>
            <h3 className="fs-2 fw-semibold mb-1" style={{ color: '#1F2937' }}>
              {stats.completed}
            </h3>
            <p className="text-xs text-muted mb-0">Cases Completed</p>
          </div>
        </div>
      </div>

      {/* ==================== SEARCH & FILTERS ==================== */}
      <div className="card mb-6">
        <div className="card-body p-4">
          <div className="row g-3 align-items-center">
            <div className="col-md-6">
              <div className="search-bar" style={{ width: '100%' }}>
                <Search size={16} style={{ color: '#9CA3AF' }} />
                <input
                  type="text"
                  placeholder="Search by Patient Name, HN, or ID..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
            </div>
            <div className="col-md-6">
              <div className="d-flex gap-2 justify-content-md-end">
                <button
                  onClick={() => setSelectedStatus("all")}
                  className={`btn ${selectedStatus === "all" ? 'btn-primary' : 'btn-outline'}`}
                  style={{ fontSize: '12px', padding: '6px 14px' }}
                >
                  All
                </button>
                <button
                  onClick={() => setSelectedStatus("urgent")}
                  className={`btn ${selectedStatus === "urgent" ? 'btn-primary' : 'btn-outline'}`}
                  style={{ fontSize: '12px', padding: '6px 14px' }}
                >
                  Urgent
                </button>
                <button
                  onClick={() => setSelectedStatus("active")}
                  className={`btn ${selectedStatus === "active" ? 'btn-primary' : 'btn-outline'}`}
                  style={{ fontSize: '12px', padding: '6px 14px' }}
                >
                  Active
                </button>
                <button
                  onClick={() => setSelectedStatus("completed")}
                  className={`btn ${selectedStatus === "completed" ? 'btn-primary' : 'btn-outline'}`}
                  style={{ fontSize: '12px', padding: '6px 14px' }}
                >
                  Completed
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ==================== PATIENT TABLE ==================== */}
      <div className="card">
        <div className="table-responsive">
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #E5E7EB', background: '#F9FAFB' }}>
                <th style={{ padding: '14px 20px', textAlign: 'left', fontSize: '11px', fontWeight: 600, color: '#6B7280', letterSpacing: '0.3px' }}>
                  PATIENT
                </th>
                <th style={{ padding: '14px 16px', textAlign: 'left', fontSize: '11px', fontWeight: 600, color: '#6B7280', letterSpacing: '0.3px' }}>
                  CONTACT / LAST VISIT
                </th>
                <th style={{ padding: '14px 16px', textAlign: 'left', fontSize: '11px', fontWeight: 600, color: '#6B7280', letterSpacing: '0.3px' }}>
                  STATUS
                </th>
                <th style={{ padding: '14px 16px', textAlign: 'left', fontSize: '11px', fontWeight: 600, color: '#6B7280', letterSpacing: '0.3px' }}>
                  PROGRESS
                </th>
                <th style={{ padding: '14px 20px', textAlign: 'right', fontSize: '11px', fontWeight: 600, color: '#6B7280', letterSpacing: '0.3px' }}>
                  ACTIONS
                </th>
              </tr>
            </thead>
            <tbody>
              {paginatedPatients.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '48px 16px' }}>
                    <p className="text-muted text-sm mb-0">No records found matching current criteria</p>
                  </td>
                </tr>
              ) : (
                paginatedPatients.map((patient) => {
                  // Status badge config
                  let statusBadge = { text: patient.status || "Active", color: "#6B7280", bg: "#F3F4F6" };
                  if (patient.status === 'เคสด่วน' || patient.status === 'ด่วน') {
                    statusBadge = { text: "Urgent", color: "#DC2626", bg: "#FEF2F2" };
                  } else if (patient.status === 'กำลังตรวจ') {
                    statusBadge = { text: "In Progress", color: "#D97706", bg: "#FFFBEB" };
                  } else if (patient.status === 'ติดตาม') {
                    statusBadge = { text: "Monitoring", color: "#0A5C8E", bg: "#E8F0F5" };
                  } else if (patient.status === 'เสร็จสิ้น' || patient.status === 'ปกติ') {
                    statusBadge = { text: "Completed", color: "#059669", bg: "#ECFDF5" };
                  }

                  return (
                    <tr key={patient.id} style={{ borderBottom: '1px solid #F3F4F6' }}>
                      <td style={{ padding: '14px 20px' }}>
                        <div className="d-flex align-items-center gap-3">
                          <div style={{
                            width: '40px',
                            height: '40px',
                            background: '#E8F0F5',
                            borderRadius: '6px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontWeight: 600,
                            fontSize: '14px',
                            color: '#0A5C8E'
                          }}>
                            {(patient.fname || patient.name || '?').charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <div style={{ fontWeight: 500, fontSize: '14px', color: '#1F2937' }}>
                              {patient.fname || patient.name} {patient.lname || ''}
                            </div>
                            <div style={{ fontSize: '10px', color: '#9CA3AF', letterSpacing: '0.3px' }}>
                              HN: {patient.hn || String(patient.id || '').slice(0, 8).toUpperCase()}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td style={{ padding: '14px 16px' }}>
                        <div style={{ fontSize: '12px', color: '#4B5563', marginBottom: '4px' }}>
                          {patient.phone || 'N/A'}
                        </div>
                        <div className="d-flex align-items-center gap-1">
                          <History size={10} style={{ color: '#9CA3AF' }} />
                          <span style={{ fontSize: '10px', color: '#9CA3AF' }}>
                            Last: {patient.lastVisit || 'First Admission'}
                          </span>
                        </div>
                      </td>
                      <td style={{ padding: '14px 16px' }}>
                        <span className="badge" style={{
                          background: statusBadge.bg,
                          color: statusBadge.color,
                          fontSize: '10px',
                          fontWeight: 500,
                          padding: '4px 10px',
                          borderRadius: '4px'
                        }}>
                          {statusBadge.text}
                        </span>
                      </td>
                      <td style={{ padding: '14px 16px' }}>
                        <div style={{ width: '140px' }}>
                          <div style={{
                            height: '4px',
                            background: '#E5E7EB',
                            borderRadius: '2px',
                            overflow: 'hidden',
                            marginBottom: '6px'
                          }}>
                            <div style={{
                              width: '75%',
                              height: '100%',
                              background: '#0A5C8E',
                              borderRadius: '2px'
                            }} />
                          </div>
                          <div style={{ fontSize: '10px', color: '#6B7280' }}>
                            Biological Analysis 75%
                          </div>
                        </div>
                      </td>
                      <td style={{ padding: '14px 20px', textAlign: 'right' }}>
                        <div className="d-flex gap-1 justify-content-end">
                          <button
                            onClick={() => router.push(`/doctor/digital-twin?id=${patient.id}`)}
                            className="btn btn-ghost"
                            style={{ padding: '6px 10px' }}
                            title="Digital Twin"
                          >
                            <Activity size={16} style={{ color: '#0A5C8E' }} />
                          </button>
                          <button
                            onClick={() => router.push(`/doctor/ai-physician?id=${patient.id}`)}
                            className="btn btn-ghost"
                            style={{ padding: '6px 10px' }}
                            title="AI Assistant"
                          >
                            <Brain size={16} style={{ color: '#0A5C8E' }} />
                          </button>
                          <button
                            onClick={() => router.push(`/doctor/lab-review?id=${patient.id}`)}
                            className="btn btn-ghost"
                            style={{ padding: '6px 10px' }}
                            title="Lab Review"
                          >
                            <FlaskConical size={16} style={{ color: '#0A5C8E' }} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
        
        {/* Pagination Controls */}
        {totalPages > 1 && (
          <div className="d-flex align-items-center justify-content-between p-3" style={{ borderTop: '1px solid #E5E7EB' }}>
            <div style={{ fontSize: '12px', color: '#6B7280' }}>
              Showing <strong>{((currentPage - 1) * ITEMS_PER_PAGE) + 1}</strong> to <strong>{Math.min(currentPage * ITEMS_PER_PAGE, filteredPatients.length)}</strong> of <strong>{filteredPatients.length}</strong> patients
            </div>
            <div className="d-flex gap-2">
              <button
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
                className="btn btn-outline"
                style={{ fontSize: '12px', padding: '6px 12px', opacity: currentPage === 1 ? 0.5 : 1 }}
              >
                Previous
              </button>
              <div className="d-flex align-items-center px-2" style={{ fontSize: '12px', color: '#374151', fontWeight: 500 }}>
                Page {currentPage} of {totalPages}
              </div>
              <button
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                disabled={currentPage === totalPages}
                className="btn btn-outline"
                style={{ fontSize: '12px', padding: '6px 12px', opacity: currentPage === totalPages ? 0.5 : 1 }}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}