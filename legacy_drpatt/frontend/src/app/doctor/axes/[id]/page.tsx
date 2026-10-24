"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Activity,
  Shield,
  Zap,
  Info,
  Pill,
  ChevronRight,
  ExternalLink,
  Loader2,
  Target,
  TrendingUp
} from "lucide-react";
import { getModules, getAxes } from "@/utils/api/services";
import Link from "next/link";

export default function AxisDetail() {
  const params = useParams();
  const router = useRouter();
  const axisId = params.id as string;

  const [axis, setAxis] = useState<any>(null);
  const [modules, setModules] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // 1. Get Axis Details from local metadata adapter
        const axesList = await getAxes();
        const axisData = axesList.find((a: any) => a.axis_id === axisId || a.id === axisId);
        if (axisData) {
          setAxis(axisData);

          // 2. Get Related Modules
          const axisNum = axisId.split('_')[1] || axisId.replace(/\D/g, '');
          const modulesList = await getModules();

          const filteredMods = modulesList
            .map((m: any) => {
              return {
                ...m,
                module_name: m.name,
                mainMechanism: m["Mechanistic Function"] || m.mechanistic_function || m.mainMechanism || m.category || "General"
              };
            })
            .filter((m: any) => {
              const mappingStr = m.tspi_axis_mapping || "";
              const regex = new RegExp(`Axis\\s+${axisNum}\\b`, 'i');
              return regex.test(mappingStr);
            });

          setModules(filteredMods.slice(0, 10));
        }
      } catch (error) {
        console.error("Error fetching axis details:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [axisId]);

  if (loading) {
    return (
      <div className="d-flex align-items-center justify-content-center py-5" style={{ minHeight: '60vh' }}>
        <div className="text-center">
          <div className="spinner-border text-primary mb-3" role="status" style={{ width: '32px', height: '32px' }}>
            <span className="visually-hidden">Loading...</span>
          </div>
          <p className="text-muted text-xs mb-0">Loading axis data...</p>
        </div>
      </div>
    );
  }

  if (!axis) {
    return (
      <div className="text-center py-5" style={{ minHeight: '60vh' }}>
        <div style={{
          width: '80px',
          height: '80px',
          background: '#F3F4F6',
          borderRadius: '12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 16px'
        }}>
          <Info size={40} style={{ color: '#D1D5DB' }} />
        </div>
        <h4 style={{ fontWeight: 500, fontSize: '16px', color: '#1F2937', marginBottom: '8px' }}>
          Axis Not Found
        </h4>
        <p style={{ fontSize: '12px', color: '#6B7280', marginBottom: '16px' }}>
          The requested biological axis could not be found.
        </p>
        <button onClick={() => router.back()} className="btn btn-primary" style={{ fontSize: '12px', padding: '6px 14px' }}>
          <ArrowLeft size={14} className="me-1" /> Go Back
        </button>
      </div>
    );
  }

  return (
    <div>
      {/* ==================== HEADER NAVIGATION ==================== */}
      <div className="card mb-6" style={{ borderRadius: 0, borderLeft: 'none', borderRight: 'none', borderTop: 'none', marginTop: '-20px' }}>
        <div className="p-4">
          <div className="d-flex align-items-center justify-content-between">
            <button
              onClick={() => router.back()}
              className="btn btn-ghost"
              style={{ padding: '6px 12px' }}
            >
              <ArrowLeft size={16} className="me-1" /> Back
            </button>
            <div className="text-center">
              <span style={{ fontSize: '9px', fontWeight: 600, color: '#9CA3AF', letterSpacing: '0.3px', display: 'block', marginBottom: '4px' }}>
                DETAILED ANALYSIS
              </span>
              <h1 style={{ fontWeight: 600, fontSize: '18px', color: '#1F2937', margin: 0 }}>
                {axis.name}
              </h1>
            </div>
            <div style={{ width: '70px' }} />
          </div>
        </div>
      </div>

      <div>
        {/* ==================== AXIS ID BANNER ==================== */}
        <div className="card mb-6" style={{ background: '#F9FAFB', textAlign: 'center' }}>
          <div className="p-4">
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              background: '#E8F0F5',
              padding: '6px 16px',
              borderRadius: '20px',
              marginBottom: '12px'
            }}>
              <Target size={12} style={{ color: '#0A5C8E' }} />
              <span style={{ fontSize: '11px', fontWeight: 600, color: '#0A5C8E' }}>
                Axis {axis.axis_id || axisId}
              </span>
            </div>
            <p style={{ fontSize: '13px', color: '#4B5563', margin: 0, maxWidth: '600px', marginInline: 'auto' }}>
              {axis.description || "This biological axis represents a key mechanistic pathway in the TSPI precision medicine framework."}
            </p>
          </div>
        </div>

        {/* ==================== MECHANISTIC BREAKDOWN ==================== */}
        <section className="mb-6">
          <div className="d-flex align-items-center gap-2 mb-4">
            <div style={{
              width: '28px',
              height: '28px',
              background: '#E8F0F5',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Zap size={14} style={{ color: '#0A5C8E' }} />
            </div>
            <h2 style={{ fontWeight: 600, fontSize: '14px', color: '#374151', letterSpacing: '0.3px', margin: 0 }}>
              MECHANISTIC BREAKDOWN
            </h2>
          </div>

          <div className="row g-4">
            {['A', 'B', 'C'].map((label) => {
              const subAxis = axis.sub_axes?.[label];
              return (
                <div key={label} className="col-md-4">
                  <div className="card h-100 shadow-sm" style={{ borderTop: `4px solid ${label === 'A' ? '#0A5C8E' : label === 'B' ? '#059669' : '#D97706'}` }}>
                    <div className="p-4">
                      <div className="d-flex align-items-center gap-2 mb-3">
                        <div style={{
                          width: '24px',
                          height: '24px',
                          background: '#F3F4F6',
                          borderRadius: '4px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontWeight: 700,
                          fontSize: '11px',
                          color: '#4B5563'
                        }}>
                          {label}
                        </div>
                        <h4 style={{ fontWeight: 600, fontSize: '13px', color: '#1F2937', margin: 0 }}>
                          {subAxis?.name || `Component ${label}`}
                        </h4>
                      </div>
                      <p style={{ fontSize: '12px', color: '#4B5563', margin: 0, lineHeight: 1.6 }}>
                        {subAxis?.description || 'No detailed information available for this mechanistic component.'}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* ==================== SUGGESTED MODULES ==================== */}
        <section className="mb-6">
          <div className="d-flex align-items-center justify-content-between mb-4">
            <div className="d-flex align-items-center gap-2">
              <div style={{
                width: '28px',
                height: '28px',
                background: '#E8F0F5',
                borderRadius: '6px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Pill size={14} style={{ color: '#0A5C8E' }} />
              </div>
              <h2 style={{ fontWeight: 600, fontSize: '14px', color: '#374151', letterSpacing: '0.3px', margin: 0 }}>
                SUGGESTED CLINICAL MODULES
              </h2>
            </div>
            <span style={{ fontSize: '11px', color: '#9CA3AF' }}>{modules.length} modules</span>
          </div>

          {modules.length === 0 ? (
            <div className="card text-center py-5">
              <Pill size={40} style={{ color: '#D1D5DB', marginBottom: '12px' }} />
              <p className="text-muted text-sm mb-0">No clinical modules associated with this axis</p>
            </div>
          ) : (
            <div className="row g-3">
              {modules.map((mod, idx) => (
                <div key={mod.id} className="col-12">
                  <div className="card">
                    <div className="p-4">
                      <div className="d-flex align-items-center justify-content-between flex-wrap gap-3">
                        <div className="d-flex align-items-center gap-3">
                          <div style={{
                            width: '44px',
                            height: '44px',
                            background: '#E8F0F5',
                            borderRadius: '6px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                          }}>
                            <Pill size={20} style={{ color: '#0A5C8E' }} />
                          </div>
                          <div>
                            <h4 style={{ fontWeight: 600, fontSize: '14px', color: '#1F2937', marginBottom: '4px' }}>
                              {mod.module_name || mod.name}
                            </h4>
                            <p style={{ fontSize: '11px', color: '#9CA3AF', margin: 0 }}>
                              {mod.module_code || mod.id}
                            </p>
                          </div>
                        </div>
                        <div className="d-flex align-items-center gap-4">
                          <div className="text-end d-none d-md-block">
                            <span style={{ fontSize: '9px', color: '#9CA3AF', letterSpacing: '0.3px', display: 'block' }}>
                              KEY MECHANISM
                            </span>
                            <span style={{ fontSize: '11px', color: '#4B5563' }}>
                              {mod.mainMechanism || mod.category || 'General'}
                            </span>
                          </div>
                          <Link
                            href={`/doctor/modules/${mod.id}`}
                            className="btn btn-ghost"
                            style={{ padding: '6px 10px' }}
                          >
                            <ExternalLink size={16} style={{ color: '#0A5C8E' }} />
                          </Link>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* ==================== CLINICAL GUIDELINES ==================== */}
        <section>
          <div className="card" style={{ background: '#1F2937' }}>
            <div className="p-4">
              <div className="d-flex align-items-start gap-3">
                <div style={{
                  width: '36px',
                  height: '36px',
                  background: 'rgba(255,255,255,0.1)',
                  borderRadius: '6px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0
                }}>
                  <Info size={16} style={{ color: '#9CA3AF' }} />
                </div>
                <div>
                  <h3 style={{ fontWeight: 600, fontSize: '14px', color: 'white', marginBottom: '8px', letterSpacing: '0.3px' }}>
                    CLINICAL GUIDELINES
                  </h3>
                  <p style={{ fontSize: '13px', color: '#D1D5DB', margin: 0, lineHeight: 1.5 }}>
                    Assessment of <strong style={{ color: 'white' }}>{axis.name}</strong> should consider laboratory results alongside clinical phenotype.
                    If elevated scores persist for more than 2 weeks, initiate balance restoration using the recommended modules in order of priority.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}