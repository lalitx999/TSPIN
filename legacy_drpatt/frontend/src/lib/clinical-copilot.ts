import { z } from 'zod';
import { ai } from './genkit';
import { copilotTools } from './copilot-tools';
import { medicalDb } from './medical-data';
import { safetyAnalysisFlow } from './safety-flow';
import { tspiRetriever } from './rag-flow';

/**
 * Grounded Clinical Copilot Flow
 * Orchestrates multi-turn conversation with tool-calling and safety boundaries.
 */

export const clinicalCopilotFlow = ai.defineFlow(
  {
    name: 'clinicalCopilotFlow',
    inputSchema: z.object({
      patientId: z.union([z.string(), z.number()]).transform(val => String(val)),
      message: z.string(),
      history: z.array(z.object({
        role: z.enum(['user', 'model']),
        content: z.string(),
      })).optional(),
    }),
    outputSchema: z.object({
      response: z.string(),
      sources: z.array(z.string()),
      needsPhysicianReview: z.boolean(),
      safetyAlerts: z.array(z.any()).optional(),
    }),
  },
  async (input) => {
    // 1. Log the interaction
    await medicalDb.logAccess('ai-copilot', input.patientId, 'chat_interaction', 'D');

    // 2. Generate response with tool calling
    const response = await ai.generate({
      system: `
        You are the TSPI Grounded Clinical Copilot. 
        Your goal is to assist patients and physicians in understanding health data through the lens of TSPI Systems Biology.
        
        STRICT BOUNDARIES:
        1. Answer ONLY using the tools provided to fetch patient data and TSPI knowledge.
        2. DO NOT make new diagnoses.
        3. DO NOT recommend changing medications without a physician's review.
        4. If you don't have enough data, state it clearly.
        5. Use empathetic but professional language.
        6. Always relate findings to the 36 Biological Axes and 9-Step Ladder when possible.
        7. If the user mentions suicidal thoughts, chest pain, or emergencies, provide immediate emergency instructions and escalate.
        
        GOVERNANCE:
        - You have access to Layers A, B, C, and D. 
        - DO NOT disclose Layer E (internal model weights/logic).
        
        CONTEXT FROM TSPI KNOWLEDGE BASE:
        {{retrieval}}
      `,
      prompt: input.message,
      tools: copilotTools,
      // Add retrieval context
      context: [
        {
          retriever: tspiRetriever,
          query: input.message,
        }
      ],
    });

    // 3. Optional: Run Safety Check if tools were used to fetch genomics
    let safetyAlerts: any[] = [];
    if (response.toolRequests.some((tr: any) => tr.name === 'getOmicsReport')) {
      const omicsData: any = await medicalDb.getPatientDataLayer(input.patientId, 'C', 'ai-copilot');
      if (omicsData?.genomics) {
        const safetyResult = await safetyAnalysisFlow({
          patientId: input.patientId,
          genomics: omicsData.genomics
        });
        safetyAlerts = safetyResult.alerts;
      }
    }

    // 4. Post-process to check for red flags or safety
    const text = response.text;
    const needsReview = text.includes('emergency') || 
                      text.includes('physician review') || 
                      text.includes('contact your doctor') ||
                      safetyAlerts.some(a => a.severity === 'Critical' || a.severity === 'High');

    return {
      response: text,
      sources: response.toolRequests.map((tr: any) => tr.name),
      needsPhysicianReview: needsReview,
      safetyAlerts: safetyAlerts.length > 0 ? safetyAlerts : undefined
    };
  }
);
