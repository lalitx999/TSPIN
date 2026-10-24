import { z } from 'zod';
import { ai, models } from './genkit';
import axesData from '@/data/tspi_36_axes_v2.json';

// Input Schema: Patient Data for any axis
const AxisScoringInputSchema = z.object({
  axisId: z.string().describe('The ID of the axis to score (e.g., AXIS_1)'),
  patientData: z.object({
    labs: z.record(z.any()).optional(),
    symptoms: z.array(z.string()).optional(),
    medications: z.array(z.string()).optional(),
    genomics: z.record(z.any()).optional(),
    microbiome: z.record(z.any()).optional(),
  }),
});

// Output Schema: Single Axis Score
const AxisScoreOutputSchema = z.object({
  axisId: z.string(),
  score: z.number().min(0).max(100),
  severity: z.enum(['Low', 'Moderate', 'High', 'Critical']),
  interpretation: z.string(),
  contributingFactors: z.array(z.string()),
  recommendedModules: z.array(z.string()),
  reasoning: z.string().describe('Deep clinical reasoning for this score'),
});

/**
 * 🧠 Logic Engine: Powered by DeepSeek (Groq)
 */
export const axisScoringFlow = ai.defineFlow(
  {
    name: 'axisScoringFlow',
    inputSchema: AxisScoringInputSchema,
    outputSchema: AxisScoreOutputSchema,
  },
  async (input) => {
    let axisDef: any = null;
    for (const domain of axesData.domains) {
        const found = domain.axes.find(a => a.axis_id === input.axisId);
        if (found) { axisDef = found; break; }
    }

    if (!axisDef) throw new Error(`Axis ${input.axisId} not found.`);

    const response = await ai.generate({
      model: models.logic, // ⚡ Use DeepSeek for logic
      prompt: `
        Analyze "${axisDef.name}" (${input.axisId}).
        Scope: ${axisDef.scope}
        Patient Data: ${JSON.stringify(input.patientData, null, 2)}
        
        Calculate a score (0-100) based on systems biology principles.
      `,
      output: { schema: AxisScoreOutputSchema }
    });

    if (!response.output) throw new Error("Scoring failed.");
    return response.output;
  }
);

export const biologicalScoringFlow = ai.defineFlow(
  {
    name: 'biologicalScoringFlow',
    inputSchema: z.object({
      patientData: AxisScoringInputSchema.shape.patientData,
      axisIds: z.array(z.string()).optional(),
    }),
    outputSchema: z.record(AxisScoreOutputSchema),
  },
  async (input) => {
    const results: Record<string, any> = {};
    const axisIds = input.axisIds || axesData.domains.flatMap(d => d.axes.map(a => a.axis_id));

    for (const axisId of axisIds) {
      results[axisId] = await axisScoringFlow({ axisId, patientData: input.patientData });
    }
    return results;
  }
);
