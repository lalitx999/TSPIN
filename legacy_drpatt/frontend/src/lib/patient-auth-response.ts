/** Accept both deployed configuration forms: origin and origin/api/. */
export function patientAuthEndpoint(base: string, action: "login" | "register"): string {
  return `${base.replace(/\/+$/, "").replace(/\/api$/, "")}/api/auth/${action}/`;
}

/** Validate the response before persisting either credential. */
export function readPatientTokens(value: unknown): { access: string; refresh: string } {
  if (!value || typeof value !== "object" || !("tokens" in value)) {
    throw new Error("ระบบส่งข้อมูลบัญชีไม่ครบถ้วน กรุณาติดต่อคลินิกก่อนลองสมัครซ้ำ");
  }
  const tokens = value.tokens;
  if (!tokens || typeof tokens !== "object" ||
      !("access" in tokens) || typeof tokens.access !== "string" || !tokens.access.trim() ||
      !("refresh" in tokens) || typeof tokens.refresh !== "string" || !tokens.refresh.trim()) {
    throw new Error("ระบบส่งข้อมูลบัญชีไม่ครบถ้วน กรุณาติดต่อคลินิกก่อนลองสมัครซ้ำ");
  }
  return { access: tokens.access, refresh: tokens.refresh };
}
