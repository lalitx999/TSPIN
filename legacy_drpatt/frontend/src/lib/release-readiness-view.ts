const messages: Record<string, string> = {
  CURRENT_INPUT_REVALIDATION_FAILED: "ตรวจข้อมูลต้นทางปัจจุบันไม่สำเร็จ",
  WORKFLOW_REVIEW_INCOMPLETE: "ขั้นตอนตรวจ workflow ยังไม่ครบ",
  ARTIFACT_BOUND_PHYSICIAN_APPROVAL_UNAVAILABLE: "ยังไม่มีการอนุมัติจากแพทย์ที่ยืนยันตัวตนและผูกกับร่างนี้",
  CURRENT_RELEASE_CONSENT_UNVERIFIED: "ยังไม่ยืนยันความยินยอมสำหรับการส่งครั้งนี้",
  RECIPIENT_AND_CHANNEL_UNVERIFIED: "ยังไม่ยืนยันผู้รับและช่องทางส่ง",
  PRE_SEND_SAFETY_RECHECK_REQUIRED: "ต้องตรวจความปลอดภัยซ้ำก่อนส่ง",
};

/** Accept only the current diagnostic-only contract. Never infer delivery permission. */
export function releaseReadinessView(raw: unknown, artifactId: string) {
  if (!raw || typeof raw !== "object") throw new Error("ข้อมูลผลตรวจไม่ครบถ้วน");
  const data = raw as Record<string, unknown>;
  const hash = (v: unknown): v is string => typeof v === "string" && /^[a-f0-9]{64}$/.test(v);
  if (data.artifact_id !== artifactId || data.state !== "BLOCKED" ||
      data.diagnostic_only !== true || data.send_allowed !== false || data.clinical_use_authorized !== false ||
      typeof data.input_is_current !== "boolean" || !hash(data.artifact_manifest_hash) ||
      !(data.current_manifest_hash === null || hash(data.current_manifest_hash)) ||
      !Array.isArray(data.issues) || data.issues.length === 0) {
    throw new Error("ผลตรวจไม่ตรงกับร่างหรือรูปแบบที่รองรับ ยังไม่สามารถยืนยันความพร้อมได้");
  }
  if (data.input_is_current && data.current_manifest_hash !== data.artifact_manifest_hash) {
    throw new Error("ผลตรวจความสดของข้อมูลไม่สอดคล้องกัน");
  }
  return {
    current: data.input_is_current,
    artifactHash: data.artifact_manifest_hash,
    currentHash: data.current_manifest_hash,
    issues: data.issues.map(issue => {
      if (!issue || typeof issue !== "object" || typeof issue.code !== "string" || !issue.code.trim()) {
        throw new Error("รายละเอียดเหตุผลไม่ครบถ้วน");
      }
      return { code: issue.code as string, message: messages[issue.code] || "มีเงื่อนไขที่ต้องตรวจสอบเพิ่มเติม" };
    }),
  };
}
