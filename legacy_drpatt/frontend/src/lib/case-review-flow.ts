import { z } from 'zod';
import { ai } from './genkit';

const CaseReviewInputSchema = z.object({
  patientId: z.union([z.string(), z.number()]).transform(val => String(val)),
  patientData: z.any(),
  focus: z.string().optional().describe('Specific focus, e.g., "Diabetes complications"'),
});

const CaseReviewOutputSchema = z.object({
  title: z.object({
    th: z.string(),
    en: z.string(),
  }),
  abstract: z.object({
    th: z.string(),
    en: z.string(),
  }),
  chapters: z.array(z.object({
    chapterNumber: z.number(),
    title: z.string(),
    content: z.string(),
  })),
  conclusion: z.string(),
});

/**
 * TSPI Integrative Case Review Engine (10-Chapter Research Style)
 * Inspired by the "Sima-porn Case Study" model.
 */
export const caseReviewFlow = ai.defineFlow(
  {
    name: 'caseReviewFlow',
    inputSchema: CaseReviewInputSchema,
    outputSchema: CaseReviewOutputSchema,
  },
  async (input) => {
    // Generate the full case review
    // For a 10-chapter deep analysis, we use a single comprehensive prompt 
    // or chain multiple calls. Here we use a high-instruction single call for the structure.
    
    const response = await ai.generate({
      prompt: `
        You are the TSPI Senior Medical Researcher. 
        Your task is to write a 10-Chapter Integrative Case Review for a patient.
        
        Reference Style: "C เคสคุณสีมาพร" (High-quality, systems biology focus, evidence-linked).
        
        Patient Data:
        ${JSON.stringify(input.patientData, null, 2)}
        
        Focus: ${input.focus || 'General clinical improvement via TSPI modules'}
        
        Structure (10 Chapters):
        1. Introduction: The burden of the disease and the limitations of conventional therapy.
        2. Clinical Perspective: Systems Biology, Mitochondrial, and Vascular mechanisms.
        3. Patient Baseline: Detailed history, baseline labs, and "Mitochondrial/Vascular failure" assessment.
        4. Conventional Therapy Analysis: Why standard drugs (Metformin, Statins, etc.) were insufficient for this case.
        5. TSPI Intervention: Detailed DB-1 (KS, KERRA, Minoza) or other modules used.
        6. Clinical Results: Changes in FBS, HbA1c, visual symptoms, and QOL (Quantitative & Qualitative).
        7. Mechanistic Interpretation: Linking ATP boosting, Anti-inflammation, and Antioxidant effects to the recovery.
        8. Vascular & Neurological Recovery: Deep dive into microvascular restoration.
        9. Quality of Life & Emotional Impact: The human element of recovery.
        10. Summary & Clinical Implications: Future outlook and research needs.
        
        Instructions:
        - Provide titles and abstracts in both Thai and English.
        - The content must be in Thai, using professional medical terminology.
        - Link clinical observations to research (e.g., "DB-1 increases ATP 18.81x").
        - Use a narrative that feels like a peer-reviewed publication.
      `,
      output: {
        schema: CaseReviewOutputSchema,
      }
    });

    if (!response.output) {
      throw new Error("Failed to generate structured Case Review output");
    }
    return response.output;
  }
);
