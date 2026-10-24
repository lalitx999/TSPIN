export type Review = { id: number; actor_id: number; created_at: string; decision: string; reason: string; artifact_hash: string };
export type History = { results: Review[]; next_before_id: number | null };

/** Refuse malformed/wrong-snapshot history before rendering or enabling review. */
export function readReviewHistory(raw: unknown, artifactHash: string, beforeId?: number): History {
  const fail = () => { throw new Error("ประวัติผลตรวจไม่ครบถ้วนหรือไม่ตรงกับร่าง กรุณาเปิดใหม่"); };
  if (!raw || typeof raw !== "object") return fail();
  const data = raw as Record<string, unknown>;
  if (data.artifact_hash !== artifactHash || data.send_allowed !== false || data.clinical_use_authorized !== false ||
      !Array.isArray(data.results) || data.results.length > 50) return fail();
  let previous = beforeId ?? Infinity;
  const results = data.results.map((value: unknown): Review => {
    if (!value || typeof value !== "object") return fail();
    const row = value as Record<string, unknown>;
    if (typeof row.id !== "number" || !Number.isSafeInteger(row.id) || row.id < 1 || row.id >= previous ||
        typeof row.actor_id !== "number" || !Number.isSafeInteger(row.actor_id) || row.actor_id < 1 ||
        typeof row.created_at !== "string" || !Number.isFinite(Date.parse(row.created_at)) ||
        typeof row.reason !== "string" || typeof row.decision !== "string" ||
        !["REVIEWED_NOT_APPROVED", "REQUEST_CHANGES", "REJECT"].includes(row.decision) ||
        row.artifact_hash !== artifactHash) return fail();
    previous = row.id;
    return { id: row.id, actor_id: row.actor_id, created_at: row.created_at,
      reason: row.reason, decision: row.decision, artifact_hash: artifactHash };
  });
  if (data.next_before_id !== null && (results.length !== 50 || data.next_before_id !== previous)) return fail();
  return { results, next_before_id: data.next_before_id as number | null };
}
