"use client";

import { Eye, Lock, Database, UserCheck, ArrowLeft, ShieldCheck, Server, Key } from "lucide-react";
import Link from "next/link";

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-[#FDFDFD] font-kanit">
      {/* Header */}
      <div className="bg-white border-bottom py-5">
        <div className="container max-w-4xl px-4">
          <Link href="/" className="text-muted text-decoration-none small fw-bold d-flex align-items-center gap-2 mb-4">
            <ArrowLeft size={16} /> กลับสู่หน้าแรก
          </Link>
          <div className="d-flex align-items-center gap-3 mb-3">
             <div className="bg-primary-custom bg-opacity-10 p-2 rounded-3 text-primary-custom">
                <Lock size={24} />
             </div>
             <h1 className="fw-bold text-dark h2 mb-0">Privacy Policy</h1>
          </div>
          <p className="lead text-muted">นโยบายความเป็นส่วนตัวและการคุ้มครองข้อมูลสุขภาพ (PDPA & HIPAA Compliance)</p>
        </div>
      </div>

      <div className="container max-w-4xl py-5 px-4 text-start">
        <div className="row g-5">
          <div className="col-12">
            
            {/* PDPA Section */}
            <div className="mb-5">
              <h4 className="fw-bold text-dark mb-4 d-flex align-items-center gap-3">
                <ShieldCheck className="text-success" /> 1. การคุ้มครองข้อมูลส่วนบุคคล (PDPA)
              </h4>
              <p className="text-muted leading-relaxed">
                TSPI ให้ความสำคัญสูงสุดกับความเป็นส่วนตัวของคุณ เราปฏิบัติตามพระราชบัญญัติคุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2562 (PDPA) 
                อย่างเคร่งครัด โดยข้อมูลสุขภาพของคุณจะถูกจัดเป็น "ข้อมูลที่มีความอ่อนไหว" (Sensitive Data) 
                ซึ่งต้องได้รับความยินยอมโดยชัดแจ้งก่อนการประมวลผล
              </p>
            </div>

            {/* Data Collection */}
            <div className="mb-5">
              <h4 className="fw-bold text-dark mb-4 d-flex align-items-center gap-3">
                <Database className="text-primary-custom" /> 2. ข้อมูลที่เราจัดเก็บ
              </h4>
              <div className="row g-4">
                {[
                  { title: "ข้อมูลระบุตัวตน", desc: "ชื่อ, อายุ, เพศ, เลขบัตรประชาชน, ข้อมูลติดต่อ", icon: UserCheck },
                  { title: "ข้อมูลทางคลินิก", desc: "ผลเลือด (Labs), อาการ (Symptoms), ประวัติแพ้ยา", icon: Server },
                  { title: "ข้อมูล Omics", desc: "Genomics, Microbiome, Proteomics Data", icon: Key },
                ].map((item, i) => (
                  <div key={i} className="col-md-4">
                    <div className="bg-white p-4 rounded-4 border shadow-sm h-100">
                      <item.icon className="text-primary-custom mb-3" size={24} />
                      <h6 className="fw-bold text-dark">{item.title}</h6>
                      <p className="tiny text-muted mb-0">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* AI Processing */}
            <div className="mb-5">
              <h4 className="fw-bold text-dark mb-4 d-flex align-items-center gap-3">
                <Eye className="text-info" /> 3. การประมวลผลโดย AI (V-Twin Engine)
              </h4>
              <p className="text-muted leading-relaxed">
                เราใช้ข้อมูลของคุณในการสร้าง "Biological Digital Twin" เพื่อวิเคราะห์แนวโน้มสุขภาพ 
                โดยข้อมูลจะถูกประมวลผลแบบเข้ารหัส (Encrypted) และจะไม่ถูกส่งไปยัง Third-party 
                โดยไม่มีการทำ Anonymization (การทำข้อมูลนิรนาม) อย่างเหมาะสม
              </p>
            </div>

            {/* Security Standards */}
            <div className="mb-5 bg-dark text-white p-5 rounded-5 shadow-lg relative overflow-hidden">
              <div className="absolute top-0 right-0 p-5 opacity-10">
                <Lock size={150} />
              </div>
              <h4 className="fw-bold mb-4 d-flex align-items-center gap-3">
                <Lock className="text-primary-custom" /> มาตรฐานความปลอดภัย (HIPAA Baseline)
              </h4>
              <ul className="d-grid gap-3 opacity-80 small list-unstyled">
                <li>• Data at Rest: ข้อมูลในฐานข้อมูลถูกเข้ารหัสด้วย AES-256</li>
                <li>• Data in Transit: การรับส่งข้อมูลผ่าน SSL/TLS 1.3 เสมอ</li>
                <li>• Audit Logs: มีการบันทึกการเข้าถึงข้อมูลของเจ้าหน้าที่ทุกคน (Immutable Logs)</li>
                <li>• Access Control: การเข้าถึงข้อมูลใช้ระบบ Multi-factor Authentication (MFA)</li>
              </ul>
            </div>

            {/* Rights */}
            <div className="mt-5">
              <h4 className="fw-bold text-dark mb-4">4. สิทธิของเจ้าของข้อมูล</h4>
              <p className="text-muted mb-4">คุณมีสิทธิในการเข้าถึง, แก้ไข, ขอสำเนา หรือขอให้ลบข้อมูลของคุณออกจากระบบของเราได้ทุกเมื่อ โดยติดต่อผ่าน DPO (Data Protection Officer)</p>
              <div className="p-4 bg-light rounded-4 border">
                <h6 className="fw-bold text-dark mb-2">ช่องทางการติดต่อ DPO</h6>
                <p className="small text-muted mb-0">Email: dpo@tspi.ai<br/>Address: TSPI Precision Medicine Center, Bangkok, Thailand</p>
              </div>
            </div>

          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="border-top py-5 bg-white">
        <div className="container max-w-4xl px-4 text-center">
          <p className="small text-muted mb-0">© 2026 TSPI Precision Medicine Engine. All rights reserved.</p>
        </div>
      </div>

      <style jsx>{`
        .bg-primary-custom { background-color: var(--drpat-primary); color: white; }
        .text-primary-custom { color: var(--drpat-primary); }
        .leading-relaxed { line-height: 1.8; }
        .max-w-4xl { max-width: 900px; }
        .tiny { font-size: 0.75rem; }
      `}</style>
    </div>
  );
}
