import { z } from 'genkit';
import { ai } from './genkit';
import { precisionEngine } from './tspi-engine';
import { logAudit } from '@/utils/api/audit';
import axesData from '@/data/39_last_x.json';

// 🧬 Define the Precision Medicine Digital Twin Schema
export const DigitalTwinSchema = z.object({
  patientId: z.string(),
  snapshotId: z.string(),
  timestamp: z.string(),
  axesState: z.record(z.object({
    score: z.number().nullable(),
    severity: z.string(),
    trend: z.enum(['Improving', 'Stable', 'Declining']).optional()
  })),
  mechanisticInsights: z.string(),
  recommendedProtocol: z.array(z.object({
    moduleId: z.string(),
    name: z.string(),
    rationale: z.string(),
    priority: z.number()
  }))
});

export const precisionMedicineFlow = ai.defineFlow(
  {
    name: 'precisionMedicineFlow',
    inputSchema: z.object({
      patientId: z.union([z.string(), z.number()]).transform(val => String(val)),
      rawInput: z.string().optional(), // Text from doctor/patient
      labData: z.any().optional(),     // Structured lab data
      voiceTranscript: z.string().optional()
    }),
    outputSchema: DigitalTwinSchema,
  },
  async (input) => {
    const startTime = Date.now();
    console.log(`🧬 Starting Precision Medicine Flow for Patient: ${input.patientId}`);

    try {
      await logAudit({
        action: "AI_INTAKE_REQUEST",
        patientId: input.patientId,
        details: {
          rawInput: input.rawInput || "",
          has_labs: !!input.labData,
          voiceTranscript: input.voiceTranscript || ""
        },
        metadata: { model: 'groq/llama-3.3-70b-versatile' }
      });
    } catch (auditErr) {
      console.warn("⚠️ AI_INTAKE_REQUEST audit log skipped:", auditErr);
    }

    // --- PHASE 1: INTELLIGENT INTAKE (Groq fallback to Gemini) ---
    // Groq is used for fast parsing of raw medical notes with fallback to Gemini
    let intakeResult: any = null;
    try {
      intakeResult = await ai.generate({
        model: 'groq/llama-3.3-70b-versatile',
        prompt: `Analyze the following patient data and extract key symptoms and clinical observations: ${input.rawInput || input.voiceTranscript}`,
        output: { schema: z.object({ symptoms: z.array(z.string()), observations: z.string() }) }
      });
    } catch (e: any) {
      console.warn("⚠️ Groq intake model failed, falling back to Gemini:", e.message);
      intakeResult = await ai.generate({
        model: 'googleai/gemini-2.5-flash',
        prompt: `Analyze the following patient data and extract key symptoms and clinical observations: ${input.rawInput || input.voiceTranscript}`,
        output: { schema: z.object({ symptoms: z.array(z.string()), observations: z.string() }) }
      });
    }

    const processedData = {
      labs: input.labData || {},
      symptoms: intakeResult.output?.symptoms || [],
      observations: intakeResult.output?.observations || ""
    };

    // --- PHASE 2: DETERMINISTIC ENGINE (The Core Logic) ---
    // Run the 39-axis mechanistic analysis on Python Django backend
    console.log(`🤖 Querying Django Clinical Decision Engine for Patient: ${input.patientId}`);
    let djangoResult: any = null;
    try {
      const backendBaseUrl = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";
      const djangoRes = await fetch(`${backendBaseUrl}/api/patients/${input.patientId}/tspi-analysis/`);
      if (!djangoRes.ok) {
        throw new Error(`Django backend returned status: ${djangoRes.status}`);
      }
      djangoResult = await djangoRes.json();
    } catch (e: any) {
      // Fail-closed (ans.txt DoD: "production remains fail-closed") — the previous behavior
      // silently fell back to a duplicate client-side scoring engine (tspi-engine.ts) with its
      // own severity thresholds/axis definitions, and even fabricated nss=50.0, both of which
      // could produce an analysis materially different from — and inconsistent with — Django's
      // deterministic engine (ans.txt problem #9). Surface the failure instead of guessing.
      console.error("❌ Django decision engine unavailable — refusing to fall back to a local/duplicate scoring engine:", e.message);
      throw new Error(
        `TSPI decision engine ไม่พร้อมใช้งาน (Django ตอบกลับผิดพลาด: ${e.message}) — ไม่สามารถวิเคราะห์ได้อย่างปลอดภัย กรุณาลองใหม่อีกครั้ง`
      );
    }

    const domainSummary = Object.entries(djangoResult.system_scores || {})
      .map(([name, score]) => `${name}: ${score}%`);

    // --- PHASE 2.5: CLOSED-CIRCUIT RAG RETRIEVAL ---
    let ragContexts: string[] = [];
    const criticalAxes = Object.entries(djangoResult.axesState || {})
      .filter(([_, val]: any) => val.score > 60)
      .map(([id, val]: any) => {
        const aDef = precisionEngine.getAxisDef(id);
        return `${aDef?.name || id}: ${val.score}% (${val.severity})`;
      });

    try {
      console.log("📚 Querying closed-circuit RAG knowledge base from Django PostgreSQL...");
      const criticalAxisNames = Object.entries(djangoResult.axesState || {})
        .filter(([_, val]: any) => val.score > 60)
        .map(([id, _]) => {
          const aDef = precisionEngine.getAxisDef(id);
          return aDef ? aDef.name : "";
        })
        .filter(Boolean);

      const backendBaseUrl = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";
      const res = await fetch(`${backendBaseUrl}/api/knowledge/`);
      if (res.ok) {
        const kbList = await res.json();
        kbList.forEach((item: any) => {
          const matchesCritical = criticalAxisNames.some(cName => item.axis && item.axis.includes(cName));
          if (matchesCritical || item.axis === "General") {
            ragContexts.push(`[Source: ${item.source}] (Target Axis: ${item.axis})\n${item.text}`);
          }
        });
      }
      console.log(`✅ Loaded ${ragContexts.length} relevant institutional knowledge blocks.`);
    } catch (ragError: any) {
      console.warn("⚠️ Closed-circuit RAG query skipped:", ragError.message);
    }

    // --- PHASE 3: MECHANISTIC ANALYSIS (Deep Clinical Reasoning via Groq fallback to Gemini) ---
    let deepSeekAnalysis: any = null;
    const systemInstruction = `You are the TSPI Precision Medicine Clinical Reasoning Engine.
               You analyze systems biology and precision medicine data using deep clinical reasoning.
               
               High-Burden Domains:
               ${domainSummary.join('\n')}
               
               Active Critical Axes (Scored > 60%):
               ${criticalAxes.join('\n')}
               
               Closed-Circuit Institutional RAG Knowledge (Targeted clinical research & clinical inputs):
               ${ragContexts.length > 0 ? ragContexts.join('\n\n') : 'No matching specialized guidelines loaded in local memory.'}
               
               Clinical Guidelines:
               1. Synthesize the "Network Effect" showing how these axes are biologically interconnected.
               2. Map clinical symptoms directly to physiological dysfunctions across the 39 systems biology axes.
               3. Incorporate the provided Closed-Circuit RAG Knowledge explicitly when proposing explanations or justifications.
               4. Outline mechanistic pathways of recommended therapeutic modules.
               5. Keep explanations clear, rigorous, and highly actionable for clinicians.`;

    const userPrompt = `Patient Symptoms: ${processedData.symptoms.join(', ')}
               Observations: ${processedData.observations}
               Based on the clinical observations, computed physiological scoring, and institutional RAG knowledge above, perform a Systems Biology synthesis of the patient's condition.`;

    try {
      deepSeekAnalysis = await ai.generate({
        model: 'groq/llama-3.3-70b-versatile',
        system: systemInstruction,
        prompt: userPrompt
      });
    } catch (e: any) {
      console.warn("⚠️ Groq clinical reasoning model failed, falling back to Gemini:", e.message);
      deepSeekAnalysis = await ai.generate({
        model: 'googleai/gemini-2.5-flash',
        system: systemInstruction,
        prompt: userPrompt
      });
    }

    // --- PHASE 4: MODULE ORCHESTRATION ---
    // Match the analysis with our modules using Django recommendations
    const finalProtocol = (djangoResult.recommended_modules || []).slice(0, 6).map((m: any) => ({
      moduleId: m.code || m.name,
      name: m.name,
      rationale: `Targeting axes: ${(m.primary_axes || []).map((ax: number) => `Axis ${ax}`).join(', ')} (Match Score: ${m.match_score}%)`,
      priority: Math.round(m.match_score)
    }));

    console.log("✅ Analysis complete, generating snapshot...");

    // --- PHASE 5: DIGITAL TWIN SNAPSHOT ---
    const snapshot = {
      patientId: input.patientId,
      snapshotId: `snap_${Date.now()}`,
      timestamp: new Date().toISOString(),
      axesState: djangoResult.axesState || {},
      mechanisticInsights: deepSeekAnalysis.text,
      recommendedProtocol: finalProtocol
    };

    try {
      console.log(`💾 Saving snapshot to Django PostgreSQL for patient: ${input.patientId}`);
      // Save scores to Django patient records
      const payload: any = {
        patient: parseInt(input.patientId),
        record_date: new Date().toISOString(),
        notes: deepSeekAnalysis.text
      };
      for (let i = 1; i <= 39; i++) {
        const scoreVal = djangoResult.axesState[`AXIS_${i}`]?.score;
        payload[`axis_${i}`] = (scoreVal !== undefined && scoreVal !== null) ? scoreVal : null;
      }

      const backendBaseUrl = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";
      const res = await fetch(`${backendBaseUrl}/api/records/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        throw new Error(`Django backend returned status: ${res.status}`);
      }
      console.log("✅ Snapshot scores saved successfully to PostgreSQL via Django.");
    } catch (apiError) {
      console.error("❌ Django Save Snapshot Error:", apiError);
    }

    try {
      await logAudit({
        action: "AI_INTAKE_RESPONSE",
        patientId: input.patientId,
        details: {
          outputStructured: snapshot,
          executionTimeMs: Date.now() - startTime,
          success: true
        },
        metadata: { model: 'groq/llama-3.3-70b-versatile' }
      });
    } catch (auditErr) {
      console.warn("⚠️ AI_INTAKE_RESPONSE audit log skipped:", auditErr);
    }

    return snapshot;
  }
);
