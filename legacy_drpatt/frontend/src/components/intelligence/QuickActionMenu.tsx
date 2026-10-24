"use client";

import { 
  FlaskConical, 
  MessageSquare, 
  Search, 
  AlertCircle, 
  Activity, 
  FileText,
  ChevronRight,
  Zap
} from "lucide-react";

interface QuickActionMenuProps {
  patientId?: string | null;
  onActionSelect: (id: string, label: string) => void;
}

export default function QuickActionMenu({ onActionSelect }: QuickActionMenuProps) {
  const actions = [
    { id: "analyze_labs", label: "วิเคราะห์ผล Lab ล่าสุด", icon: FlaskConical, color: "text-primary-custom", bg: "bg-primary-custom" },
    { id: "symptom_review", label: "ประเมินอาการปัจจุบัน", icon: MessageSquare, color: "text-info", bg: "bg-info" },
    { id: "risk_assessment", label: "ประเมินความเสี่ยงด่วน", icon: AlertCircle, color: "text-danger", bg: "bg-danger" },
    { id: "mechanism_mapping", label: "วิเคราะห์กลไกชีวภาพ", icon: Activity, color: "text-success", bg: "bg-success" },
    { id: "treatment_suggestion", label: "แนะนำแผนการรักษา", icon: FileText, color: "text-warning", bg: "bg-warning" },
  ];

  return (
    <div className="d-grid gap-2">
      {actions.map((action) => (
        <button
          key={action.id}
          onClick={() => onActionSelect(action.id, action.label)}
          className="btn btn-white border-0 text-start p-3 rounded-4 d-flex align-items-center justify-content-between hover-bg-light transition-all group shadow-sm"
        >
          <div className="d-flex align-items-center gap-3">
            <div className={`${action.bg} bg-opacity-10 p-2 rounded-3 group-hover-scale transition-all`}>
              <action.icon size={18} className={action.color} />
            </div>
            <span className="small fw-bold text-dark">{action.label}</span>
          </div>
          <ChevronRight size={14} className="text-muted opacity-0 group-hover-opacity-100 transition-all" />
        </button>
      ))}

      <style jsx>{`
        .btn-white { background-color: white; }
        .hover-bg-light:hover { background-color: #f8f9fa; transform: translateX(4px); }
        .group-hover-scale { transition: transform 0.2s; }
        .btn-white:hover .group-hover-scale { transform: scale(1.1); }
      `}</style>
    </div>
  );
}
