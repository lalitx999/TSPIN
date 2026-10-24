
import { NextResponse } from 'next/server';
import { ai } from '@/lib/genkit';
import { precisionMedicineFlow } from '@/lib/precision-medicine-flow';
import { logAudit } from '@/utils/api/audit';

export async function POST(req: Request) {
  console.log("📥 API: Received request to /api/ai/precision");
  try {
    const body = await req.json().catch(e => {
        console.error("❌ API: Failed to parse JSON body");
        return null;
    });

    if (!body || !body.patientId) {
      return NextResponse.json({ error: "Missing patientId" }, { status: 400 });
    }

    const { patientId, rawInput, labData } = body;
    console.log(`🧬 API: Processing analysis for Patient: ${patientId}`);

    // Shielding the flow execution
    const result = await precisionMedicineFlow({
      patientId,
      rawInput,
      labData
    }).catch(flowError => {
        console.error("❌ API: Flow Execution Error:", flowError);
        throw flowError;
    });

    console.log("✅ API: Flow execution successful");

    // Log audit (non-blocking)
    logAudit({
      action: "ADMIN_ACTION",
      details: { type: "PRECISION_ANALYSIS", patientId, snapshotId: result.snapshotId },
      metadata: { engine: "TSPI-Multi-Model" }
    }).catch(e => console.error("⚠️ Audit log failed (ignored):", e));

    return NextResponse.json(result);
  } catch (error: any) {
    console.error("💥 CRITICAL API ERROR:", error);
    // FORCE JSON RESPONSE
    return new Response(JSON.stringify({ 
      error: "Critical Server Error", 
      message: error.message,
      stack: error.stack?.slice(0, 200) 
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
