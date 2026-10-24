/** Monotonic generation also rejects A -> B -> A responses, not just token mismatch. */
export function createReviewSessionGuard() {
  let generation = 0;
  return {
    capture: () => generation,
    invalidate: () => { generation += 1; },
    assertCurrent: (captured: number) => {
      if (captured !== generation) throw new Error("บัญชีเปลี่ยน กรุณาเปิดร่างใหม่");
    },
    isCurrent: (captured: number) => captured === generation,
  };
}
