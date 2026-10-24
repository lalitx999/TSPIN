import { workflowReviewView } from "@/lib/workflow-review-view";

const decisions: Record<string, string> = {
  PASS: "ผ่านการตรวจขั้นนี้ (ไม่ใช่อนุมัติ)", FAIL: "ไม่ผ่าน", DEFER: "รอผู้ตรวจ",
  ESCALATE: "ส่งต่อให้ผู้รับผิดชอบตรวจสอบ", STOP: "หยุด",
};

export default function WorkflowReviewTrace({ payload }: { payload: unknown }) {
  const view = workflowReviewView(payload);
  if (!view) return null;
  return <section aria-label="ลำดับตรวจ workflow">
    <h3 className="h5">ลำดับการตรวจ WORKFLOW</h3>
    <p className="alert alert-warning">ผลตรวจทางเทคนิค ไม่ใช่การรับรองความปลอดภัยหรืออนุญาตให้ส่งรายงาน ขั้นที่ไม่มีในประวัติไม่ได้หมายความว่าผ่านแล้ว</p>
    <dl><dt>สถานะ / เหตุผล</dt><dd>{view.state} / {view.reason}</dd>
      <dt>จำนวนรอบ</dt><dd>{view.rounds}</dd>
      <dt>Trace hash</dt><dd className="text-break">{view.traceHash}</dd></dl>
    {view.malformedTrace && <p role="alert">รูปแบบประวัติไม่ถูกต้อง กรุณาตรวจ JSON ต้นฉบับ</p>}
    {!view.steps.length && !view.malformedTrace && <p>ไม่มีขั้นตอนที่บันทึกไว้</p>}
    <ol className="ps-3">{view.steps.map(step => <li key={step.index} className="card p-3 mb-3">
      <h4 className="h6">{step.role} · {step.label} · รอบ {step.round}</h4>
      <strong>{decisions[step.decision] || "สถานะไม่รู้จัก"} [{step.decision}]</strong>
      {step.issues.length > 0 && <ul>{step.issues.map((issue, i) => <li key={i} style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{issue}</li>)}</ul>}
      <p>เริ่ม {step.started}<br />สิ้นสุด {step.finished}</p>
      {step.safety !== null && <div className="alert alert-danger"><strong>รายละเอียด safety precheck</strong><pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{step.safety}</pre></div>}
      <details><summary>เวอร์ชันและหลักฐานอ้างอิงขั้นนี้</summary><dl className="text-break">
        <dt>Handler version</dt><dd>{step.handler}</dd><dt>Input hash</dt><dd>{step.inputHash}</dd>
        <dt>Output hash</dt><dd>{step.outputHash}</dd><dt>Reviewed draft hash</dt><dd>{step.draftHash}</dd>
      </dl></details>
    </li>)}</ol>
  </section>;
}
