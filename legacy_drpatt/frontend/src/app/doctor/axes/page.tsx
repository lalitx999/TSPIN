"use client";

import { useState, useEffect, useMemo } from "react";
import {
   Search, Database, Activity, Info, X, ChevronDown, ChevronUp, Beaker
} from "lucide-react";
import { getAxes } from "@/utils/api/services";

interface AxisData {
  id: string;
  axis_id: string;
  name: string;
  domain_title: string;
  description?: string;
  sub_axes?: Record<string, { name: string; description: string }>;
}

export default function AxesExplorer() {
   const [axes, setAxes] = useState<AxisData[]>([]);
   const [loading, setLoading] = useState(true);
   const [searchTerm, setSearchTerm] = useState("");
   const [expandedId, setExpandedId] = useState<string | null>(null);

   useEffect(() => {
      const fetchAxes = async () => {
         try {
            const axesData = await getAxes();
            // Sort by axis_id numerically
            const sorted = axesData.sort((a: any, b: any) => {
               const idA = parseInt(String(a.axis_id).replace(/\D/g, '')) || 0;
               const idB = parseInt(String(b.axis_id).replace(/\D/g, '')) || 0;
               return idA - idB;
            });
            setAxes(sorted);
         } catch (error) {
            console.error(error);
         } finally {
            setLoading(false);
         }
      };
      fetchAxes();
   }, []);

   const filteredAxes = axes.filter(axis =>
      (axis.name || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      (axis.domain_title || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      String(axis.axis_id).toLowerCase().includes(searchTerm.toLowerCase())
   );

   // Group axes by domain_title
   const groupedAxes = useMemo(() => {
     const groups: Record<string, AxisData[]> = {};
     filteredAxes.forEach(axis => {
       const domain = axis.domain_title || "General Biology";
       if (!groups[domain]) groups[domain] = [];
       groups[domain].push(axis);
     });
     // Sort domains alphabetically
     const sortedGroups: Record<string, AxisData[]> = {};
     Object.keys(groups).sort().forEach(key => {
       sortedGroups[key] = groups[key];
     });
     return sortedGroups;
   }, [filteredAxes]);

   const toggleExpand = (id: string) => {
      setExpandedId(prev => prev === id ? null : id);
   };

   if (loading && axes.length === 0) {
      return (
         <div className="d-flex align-items-center justify-content-center py-5">
            <div className="text-center">
               <div className="spinner-border text-primary mb-3" role="status" style={{ width: '32px', height: '32px' }}>
                  <span className="visually-hidden">Loading...</span>
               </div>
               <p className="text-muted text-xs mb-0">Loading biological axes dictionary...</p>
            </div>
         </div>
      );
   }

   // 12 Core Domains metric
   const totalDomains = Object.keys(groupedAxes).length;

   return (
      <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
         {/* ==================== HEADER ==================== */}
         <div className="d-flex justify-content-between align-items-center mb-6">
            <div>
               <h1 className="fs-4 fw-semibold mb-1" style={{ color: '#1F2937' }}>
                  Biological Axes Dictionary
               </h1>
               <p className="text-xs text-muted" style={{ letterSpacing: '0.3px' }}>
                  Explore the 39 Core Mechanistic Pathways across {totalDomains} Domains
               </p>
            </div>
            <div className="search-bar" style={{ width: '320px' }}>
               <Search size={14} style={{ color: '#9CA3AF' }} />
               <input
                  type="text"
                  placeholder="Search axis, domain, or ID..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
               />
               {searchTerm && (
                  <button
                     onClick={() => setSearchTerm("")}
                     style={{ background: 'transparent', border: 'none', cursor: 'pointer' }}
                  >
                     <X size={12} style={{ color: '#9CA3AF' }} />
                  </button>
               )}
            </div>
         </div>

         {/* ==================== STATS ==================== */}
         <div className="row g-4 mb-6">
            <div className="col-lg-6 col-md-6">
               <div className="card p-4 border-0" style={{ background: 'linear-gradient(to right, #ffffff, #f8fafc)', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
                  <div className="d-flex align-items-center gap-3">
                     <div style={{
                        width: '48px', height: '48px', background: '#E8F0F5',
                        borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center'
                     }}>
                        <Activity size={24} style={{ color: '#0A5C8E' }} />
                     </div>
                     <div>
                        <p style={{ fontSize: '11px', fontWeight: 600, color: '#6B7280', letterSpacing: '0.5px', marginBottom: '2px' }}>
                           BIOLOGICAL AXES
                        </p>
                        <h3 style={{ fontWeight: 700, fontSize: '28px', color: '#1F2937', margin: 0 }}>
                           {axes.length} <span style={{ fontSize: '14px', fontWeight: 500, color: '#9CA3AF' }}>/ 39</span>
                        </h3>
                     </div>
                  </div>
               </div>
            </div>
            <div className="col-lg-6 col-md-6">
               <div className="card p-4 border-0" style={{ background: 'linear-gradient(to right, #ffffff, #f0fdf4)', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
                  <div className="d-flex align-items-center gap-3">
                     <div style={{
                        width: '48px', height: '48px', background: '#DCFCE7',
                        borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center'
                     }}>
                        <Database size={24} style={{ color: '#166534' }} />
                     </div>
                     <div>
                        <p style={{ fontSize: '11px', fontWeight: 600, color: '#6B7280', letterSpacing: '0.5px', marginBottom: '2px' }}>
                           CORE DOMAINS
                        </p>
                        <h3 style={{ fontWeight: 700, fontSize: '28px', color: '#1F2937', margin: 0 }}>
                           {totalDomains} <span style={{ fontSize: '14px', fontWeight: 500, color: '#9CA3AF' }}>Systems</span>
                        </h3>
                     </div>
                  </div>
               </div>
            </div>
         </div>

         {/* ==================== ACCORDION CONTENT ==================== */}
         {Object.keys(groupedAxes).length === 0 ? (
            <div className="card text-center py-5">
               <Database size={40} style={{ color: '#D1D5DB', marginBottom: '12px' }} />
               <p className="text-muted text-sm mb-0">No axes match your search criteria</p>
            </div>
         ) : (
            <div>
               {Object.entries(groupedAxes).map(([domain, domainAxes]) => (
                  <div key={domain} className="mb-6">
                     <div className="d-flex align-items-center gap-3 mb-3">
                        <div style={{ width: '8px', height: '24px', background: '#0A5C8E', borderRadius: '4px' }} />
                        <h3 className="fs-5 fw-bold m-0" style={{ color: '#1F2937' }}>
                           {domain}
                        </h3>
                        <span className="badge" style={{ background: '#F3F4F6', color: '#6B7280', fontSize: '12px', fontWeight: 600, padding: '4px 10px' }}>
                          {domainAxes.length} Axes
                        </span>
                     </div>

                     <div className="d-flex flex-column gap-2">
                        {domainAxes.map((axis) => {
                           const isExpanded = expandedId === axis.id;
                           
                           return (
                              <div 
                                 key={axis.id} 
                                 className="card border-0"
                                 style={{ 
                                    boxShadow: isExpanded ? '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)' : '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
                                    transition: 'all 0.2s ease',
                                    overflow: 'hidden'
                                 }}
                              >
                                 <div 
                                    onClick={() => toggleExpand(axis.id)}
                                    className="d-flex align-items-center justify-content-between p-3"
                                    style={{ 
                                       cursor: 'pointer',
                                       background: isExpanded ? '#F8FAFC' : '#FFFFFF',
                                       borderLeft: isExpanded ? '3px solid #0A5C8E' : '3px solid transparent'
                                    }}
                                 >
                                    <div className="d-flex align-items-center gap-3">
                                       <div style={{
                                          width: '40px',
                                          height: '40px',
                                          background: isExpanded ? '#E8F0F5' : '#F3F4F6',
                                          borderRadius: '8px',
                                          display: 'flex',
                                          alignItems: 'center',
                                          justifyContent: 'center',
                                          fontWeight: 700,
                                          fontSize: '13px',
                                          color: isExpanded ? '#0A5C8E' : '#4B5563'
                                       }}>
                                          A{axis.axis_id}
                                       </div>
                                       <h5 style={{
                                          fontWeight: 600,
                                          fontSize: '15px',
                                          color: isExpanded ? '#0A5C8E' : '#1F2937',
                                          margin: 0,
                                          transition: 'color 0.2s'
                                       }}>
                                          {axis.name}
                                       </h5>
                                    </div>
                                    <div style={{ color: '#9CA3AF' }}>
                                       {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                                    </div>
                                 </div>

                                 {/* Accordion Body */}
                                 {isExpanded && (
                                    <div className="p-4" style={{ background: '#FFFFFF', borderTop: '1px solid #F1F5F9' }}>
                                       {axis.sub_axes && Object.keys(axis.sub_axes).length > 0 ? (
                                          <div className="d-flex flex-column gap-3">
                                             {Object.keys(axis.sub_axes).sort().map((subKey) => {
                                                const subAxis = axis.sub_axes![subKey];
                                                return (
                                                   <div key={subKey} className="d-flex align-items-start gap-3">
                                                      <div style={{ 
                                                         marginTop: '3px',
                                                         width: '24px',
                                                         height: '24px',
                                                         background: '#F1F5F9',
                                                         borderRadius: '4px',
                                                         display: 'flex',
                                                         alignItems: 'center',
                                                         justifyContent: 'center',
                                                         fontWeight: 700,
                                                         fontSize: '12px',
                                                         color: '#475569',
                                                         flexShrink: 0
                                                      }}>
                                                         {subKey}
                                                      </div>
                                                      <div>
                                                         <h6 style={{ fontSize: '14px', fontWeight: 600, color: '#1F2937', marginBottom: '4px' }}>
                                                            {subAxis.name}
                                                         </h6>
                                                         <p style={{ fontSize: '14px', color: '#475569', margin: 0, lineHeight: 1.6 }}>
                                                            {subAxis.description}
                                                         </p>
                                                      </div>
                                                   </div>
                                                );
                                             })}
                                          </div>
                                       ) : (
                                          <div className="d-flex align-items-start gap-3">
                                             <div style={{ marginTop: '3px' }}>
                                                <Beaker size={18} style={{ color: '#64748B' }} />
                                             </div>
                                             <div>
                                                <h6 style={{ fontSize: '12px', fontWeight: 700, color: '#475569', letterSpacing: '0.5px', marginBottom: '8px' }}>
                                                   MECHANISTIC DESCRIPTION
                                                </h6>
                                                <p style={{ fontSize: '14px', color: '#334155', margin: 0, lineHeight: 1.6 }}>
                                                   {axis.description || (
                                                      <span style={{ fontStyle: 'italic', color: '#94A3B8' }}>
                                                         Detailed clinical description for this biological axis is currently being provisioned from the knowledge base.
                                                      </span>
                                                   )}
                                                </p>
                                             </div>
                                          </div>
                                       )}
                                    </div>
                                 )}
                              </div>
                           );
                        })}
                     </div>
                  </div>
               ))}
            </div>
         )}

         {/* ==================== INFO FOOTER ==================== */}
         <div className="mt-8" style={{
            padding: '16px 20px',
            background: '#F9FAFB',
            borderRadius: '8px',
            border: '1px solid #E5E7EB',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '12px'
         }}>
            <div style={{
               width: '32px',
               height: '32px',
               background: '#E8F0F5',
               borderRadius: '6px',
               display: 'flex',
               alignItems: 'center',
               justifyContent: 'center',
               flexShrink: 0
            }}>
               <Info size={14} style={{ color: '#0A5C8E' }} />
            </div>
            <div>
               <h6 style={{ fontWeight: 600, fontSize: '11px', color: '#0A5C8E', marginBottom: '4px', letterSpacing: '0.3px' }}>
                  CLINICAL FRAMEWORK
               </h6>
               <p style={{ fontSize: '12px', color: '#6B7280', margin: 0, lineHeight: 1.5 }}>
                  The <strong style={{ color: '#1F2937' }}>TSPI Framework</strong> organizes {axes.length} inter-connected pathways across {totalDomains} physiological domains. This structure forms the foundation of the precision medicine digital twin algorithm.
               </p>
            </div>
         </div>
      </div>
   );
}