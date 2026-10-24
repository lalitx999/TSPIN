"use client";

import { Shield, Lock, Scale, FileText, ArrowLeft, CheckCircle } from "lucide-react";
import Link from "next/link";

export default function TermsOfServicePage() {
  return (
    <div className="min-h-screen bg-white font-kanit">
      {/* Header */}
      <div className="bg-light border-bottom py-5">
        <div className="container max-w-4xl px-4">
          <Link href="/" className="text-muted text-decoration-none small fw-bold d-flex align-items-center gap-2 mb-4">
            <ArrowLeft size={16} /> กลับสู่หน้าแรก
          </Link>
          <h1 className="fw-bold text-dark display-5 mb-3">Terms of Service</h1>
          <p className="lead text-muted">ข้อกำหนดและเงื่อนไขการใช้งานแพลตฟอร์ม TSPI Clinical Intelligence</p>
          <div className="d-flex gap-3 mt-4">
            <span className="tiny fw-bold bg-white px-3 py-1 rounded-pill border shadow-sm">Version 1.0 (May 2026)</span>
            <span className="tiny fw-bold bg-white px-3 py-1 rounded-pill border shadow-sm">Effective: June 1, 2026</span>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="container max-w-4xl py-5 px-4 text-start">
        <div className="row g-5">
          <div className="col-12">
            <div className="bg-primary-custom bg-opacity-5 p-4 rounded-4 border border-primary-custom border-opacity-10 mb-5">
              <h5 className="fw-bold text-primary-custom d-flex align-items-center gap-2 mb-3">
                <Shield size={20} /> บทสรุปสำหรับผู้ใช้
              </h5>
              <p className="small text-dark mb-0 leading-relaxed">
                TSPI เป็นแพลตฟอร์มสนับสนุนการตัดสินใจทางคลินิก (Clinical Decision Support) โดยใช้ AI ประมวลผล 
                ข้อมูลที่แสดงผลเป็นคำแนะนำเท่านั้น **ไม่ใช่การวินิจฉัยหรือการรักษาทางการแพทย์โดยตรง** 
                ผู้ใช้งานที่เป็นแพทย์ยังคงมีหน้าที่รับผิดชอบสูงสุดในการตัดสินใจรักษา
              </p>
            </div>

            <section className="mb-5">
              <h4 className="fw-bold text-dark mb-4 d-flex align-items-center gap-3">
                <Scale className="text-primary-custom" /> 1. คำนิยามและการให้บริการ
              </h4>
              <p className="text-muted">
                "TSPI Platform" หมายรวมถึงระบบเว็บไซต์ แอปพลิเคชัน และเทคโนโลยี AI (V-Twin Engine) 
                ที่ให้บริการรวบรวมและวิเคราะห์ข้อมูลสุขภาพเพื่อความแม่นยำทางการแพทย์
              </p>
            </section>

            <section className="mb-5">
              <h4 className="fw-bold text-dark mb-4 d-flex align-items-center gap-3">
                <FileText className="text-primary-custom" /> 2. สิทธิและหน้าที่ของผู้ใช้งาน
              </h4>
              <div className="d-grid gap-3">
                {[
                  "ผู้ใช้ต้องให้ข้อมูลสุขภาพที่เป็นจริงและถูกต้องที่สุดเพื่อความแม่นยำในการวิเคราะห์",
                  "ห้ามมิให้ผู้ใช้งานนำผลการวิเคราะห์ไปทำการรักษาด้วยตนเองโดยไม่อยู่ภายใต้การดูแลของแพทย์",
                  "แพทย์ผู้ใช้งานต้องปฏิบัติตามมาตรฐานวิชาชีพในการตรวจสอบความถูกต้องของ AI Output"
                ].map((item, i) => (
                  <div key={i} className="d-flex gap-3 align-items-start">
                    <CheckCircle size={18} className="text-success mt-1" />
                    <p className="text-dark mb-0">{item}</p>
                  </div>
                ))}
              </div>
            </section>

            <section className="mb-5">
              <h4 className="fw-bold text-dark mb-4 d-flex align-items-center gap-3">
                <Lock className="text-primary-custom" /> 3. ความปลอดภัยของข้อมูลและระบบ
              </h4>
              <p className="text-muted">
                เราใช้มาตรฐานการรักษาความปลอดภัยระดับเดียวกับสถาบันการเงินและการแพทย์ระดับสากล 
                ข้อมูลของคุณจะถูกเก็บรักษาภายใต้กฎหมาย PDPA (ไทย) และสอดคล้องกับแนวทาง HIPAA (สากล) 
                เพื่อป้องกันการเข้าถึงข้อมูลโดยไม่ได้รับอนุญาต
              </p>
            </section>

            <section className="mb-5">
              <h4 className="fw-bold text-dark mb-4 d-flex align-items-center gap-3">
                <Shield size={20} className="text-primary-custom" /> 4. ข้อจำกัดความรับผิดชอบ (Disclaimer)
              </h4>
              <div className="bg-light p-4 rounded-4 border border-warning border-opacity-20 text-start">
                <p className="small text-muted mb-0 italic leading-relaxed">
                  "TSPI จะไม่รับผิดชอบต่อความเสียหายใดๆ ที่เกิดขึ้นจากการนำข้อมูลจากแพลตฟอร์มไปใช้โดยผิดวัตถุประสงค์ 
                  หรือความผิดพลาดที่เกิดจากข้อจำกัดของเทคโนโลยี AI และข้อมูล Lab ที่ไม่สมบูรณ์"
                </p>
              </div>
            </section>
          </div>
        </div>
      </div>

      {/* Footer CTA */}
      <div className="bg-dark text-white py-5">
        <div className="container max-w-4xl px-4 text-center">
          <h4 className="fw-bold mb-3">เข้าใจข้อกำหนดเรียบร้อยแล้ว?</h4>
          <p className="text-white opacity-50 mb-4">หากคุณมีข้อสงสัยเกี่ยวกับเงื่อนไขการใช้งาน สามารถติดต่อทีมกฎหมายของเราได้ที่ legal@tspi.ai</p>
          <div className="d-flex justify-content-center gap-3">
            <Link href="/patient/register" className="btn btn-primary-custom rounded-pill px-5 py-3 fw-bold">ยอมรับและลงทะเบียน</Link>
            <Link href="/legal/privacy" className="btn btn-outline-light rounded-pill px-5 py-3 fw-bold">อ่านนโยบายความเป็นส่วนตัว</Link>
          </div>
        </div>
      </div>

      <style jsx>{`
        .bg-primary-custom { background-color: var(--drpat-primary); color: white; }
        .text-primary-custom { color: var(--drpat-primary); }
        .btn-primary-custom { background-color: var(--drpat-primary); color: white; border: none; }
        .btn-primary-custom:hover { background-color: #e6683d; }
        .leading-relaxed { line-height: 1.8; }
        .max-w-4xl { max-width: 900px; }
      `}</style>
    </div>
  );
}
