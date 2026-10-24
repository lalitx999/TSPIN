/** Presentation only: preserve trace order; never infer approval or skipped passes. */
function record(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}
function text(value: unknown): string {
  return value === null || value === undefined ? "ไม่ระบุ" : typeof value === "string" ? value : JSON.stringify(value);
}
export function workflowReviewView(payload: unknown) {
  const workflow = record(record(payload).workflow);
  if (!Object.keys(workflow).length) return null;
  return {
    state: text(workflow.state), reason: text(workflow.reason), rounds: text(workflow.rounds_used),
    traceHash: text(workflow.trace_hash),
    malformedTrace: !Array.isArray(workflow.trace),
    steps: (Array.isArray(workflow.trace) ? workflow.trace : []).map((raw, index) => {
      const step = record(raw), output = record(step.output);
      const issues = Array.isArray(output.issues) ? output.issues : [];
      return {
        index, role: text(step.role ?? step.stage), label: text(step.label),
        round: text(step.round), decision: text(step.decision),
        issues: [...(step.code === undefined ? [] : [text(step.code)]), ...issues.map(text)],
        started: text(step.started_at), finished: text(step.finished_at),
        handler: text(step.handler_version), inputHash: text(step.input_hash),
        outputHash: text(step.output_hash), draftHash: text(step.reviewed_draft_hash),
        safety: step.safety === undefined ? null : text(step.safety),
      };
    }),
  };
}
