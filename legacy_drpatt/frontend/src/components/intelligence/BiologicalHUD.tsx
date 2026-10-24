"use client";

import { 
  Shield, Droplet, TrendingUp, Leaf, Heart, Wrench, 
  Bone, Activity, Brain, Eye, FlaskConical, Layers, Zap 
} from "lucide-react";

const DOMAIN_STYLE: Record<string, { icon: any; color: string; bg: string; border: string }> = {
  D1:  { icon: Shield,       color: "text-blue-600",    bg: "bg-blue-50",    border: "border-blue-200" },
  D2:  { icon: Droplet,      color: "text-emerald-600", bg: "bg-emerald-50", border: "border-emerald-200" },
  D3:  { icon: TrendingUp,   color: "text-purple-600",  bg: "bg-purple-50",  border: "border-purple-200" },
  D4:  { icon: Leaf,         color: "text-lime-600",    bg: "bg-lime-50",    border: "border-lime-200" },
  D5:  { icon: Heart,        color: "text-rose-600",    bg: "bg-rose-50",    border: "border-rose-200" },
  D6:  { icon: Wrench,       color: "text-orange-600",  bg: "bg-orange-50",  border: "border-orange-200" },
  D7:  { icon: Bone,         color: "text-stone-600",   bg: "bg-stone-50",   border: "border-stone-200" },
  D8:  { icon: Activity,     color: "text-pink-600",    bg: "bg-pink-50",    border: "border-pink-200" },
  D9:  { icon: Brain,        color: "text-indigo-600",  bg: "bg-indigo-50",  border: "border-indigo-200" },
  D10: { icon: Eye,          color: "text-teal-600",    bg: "bg-teal-50",    border: "border-teal-200" },
  D11: { icon: FlaskConical, color: "text-red-600",     bg: "bg-red-50",     border: "border-red-200" },
  D12: { icon: Layers,       color: "text-violet-600",  bg: "bg-violet-50",  border: "border-violet-200" },
};

interface BiologicalHUDProps {
  axes: { axis_id: string; axis_name: string; severity: number }[];
}

export default function BiologicalHUD({ axes }: BiologicalHUDProps) {
  // Only show real data
  const displayAxes = axes || [];

  return (
    <div className="d-grid gap-3">
      {displayAxes.map((ax: any, i) => {
        const domainCode = ax.axis_id.split('_')[0] || "D1";
        const style = DOMAIN_STYLE[domainCode] || { icon: Zap, color: "text-muted", bg: "bg-light", border: "border-light" };
        const Icon = style.icon;

        return (
          <div key={i} className={`p-3 rounded-4 border-2 ${style.border} ${style.bg} transition-all hover-scale mb-2 ${ax.severity > 70 ? 'critical-pulse' : ''}`}>
            <div className="d-flex align-items-center justify-content-between mb-2">
              <div className="d-flex align-items-center gap-2">
                <div className={`p-2 rounded-3 bg-white shadow-sm ${style.color}`}>
                  <Icon size={18} />
                </div>
                <div className="overflow-hidden">
                  <p className={`tiny fw-bold mb-0 ${style.color}`}>{ax.axis_id}</p>
                  <p className="small fw-bold text-dark mb-0 text-truncate" style={{ maxWidth: '150px' }}>{ax.axis_name}</p>
                </div>
              </div>
              <div className="text-end">
                <span className={`h5 fw-bold mb-0 ${ax.severity > 70 ? 'text-danger' : ax.severity > 40 ? 'text-warning' : 'text-success'}`}>
                  {ax.severity}%
                </span>
              </div>
            </div>
            
            <div className="progress mb-2" style={{ height: '6px', backgroundColor: 'rgba(0,0,0,0.05)', overflow: 'hidden' }}>
              <div 
                className={`progress-bar rounded-pill ${ax.severity > 70 ? 'bg-danger' : ax.severity > 40 ? 'bg-warning' : 'bg-success'}`} 
                style={{ 
                  width: `${ax.severity}%`,
                  transition: "width 1.2s cubic-bezier(0.4, 0, 0.2, 1)"
                }}
              ></div>
            </div>

            {/* 🆕 Clinical Insight Area */}
            {(ax.insight || ax.evidence) && (
              <div className="mt-2 pt-2 border-top border-white opacity-75">
                <div className="d-flex gap-1 align-items-start">
                  <Brain size={12} className={style.color} style={{ marginTop: '2px' }} />
                  <p className="tiny mb-0 text-dark" style={{ lineHeight: 1.4 }}>
                    <span className="fw-bold">Insight:</span> {ax.insight || "ตรวจพบปัจจัยเสี่ยงที่มีนัยสำคัญ"}
                  </p>
                </div>
                {ax.evidence && (
                  <p className="tiny mb-0 mt-1 text-muted" style={{ fontSize: '9px' }}>
                    <span className="fw-bold">Evidence:</span> {ax.evidence}
                  </p>
                )}
              </div>
            )}
          </div>
        );
      })}

      <style jsx>{`
        .hover-scale:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }
        @keyframes pulse-red {
          0%, 100% { box-shadow: 0 0 0 0px rgba(239, 68, 68, 0.3); }
          50% { box-shadow: 0 0 8px 1px rgba(239, 68, 68, 0.15); }
        }
        .critical-pulse {
          animation: pulse-red 2s infinite ease-in-out;
        }
      `}</style>
    </div>
  );
}
