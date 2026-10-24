import { z } from 'zod';
import { ai } from './genkit';

// High-Priority Alert Schema
export const SafetyAlertSchema = z.object({
  type: z.enum(['AnesthesiaRisk', 'Pharmacogenomics', 'DrugContraindication', 'AllergyAlert', 'RedFlag']),
  severity: z.enum(['Low', 'Moderate', 'High', 'Critical']),
  title: z.string(),
  description: z.string(),
  actionableGuideline: z.string(),
  evidenceLevel: z.enum(['FDA-Approved', 'CPIC-Guideline', 'Clinical-Evidence', 'Exploratory']),
  affectedDrugs: z.array(z.string()).optional(),
  geneVariant: z.string().optional(),
});

export const SafetyAnalysisOutputSchema = z.object({
  alerts: z.array(SafetyAlertSchema),
  summary: z.string(),
  physicianReviewRequired: z.boolean(),
});

/**
 * TSPI Safety & Pharmacogenomics Engine
 * Focuses on high-risk clinical outputs: Anesthesia, PGx, and Drug Safety.
 */
export const safetyAnalysisFlow = ai.defineFlow(
  {
    name: 'safetyAnalysisFlow',
    inputSchema: z.object({
      patientId: z.union([z.string(), z.number()]).transform(val => String(val)),
      genomics: z.any().optional(),
      medications: z.array(z.string()).optional(),
      history: z.any().optional(),
    }),
    outputSchema: SafetyAnalysisOutputSchema,
  },
  async (input) => {
    const response = await ai.generate({
      prompt: `
        You are the TSPI Clinical Safety Engine. Your goal is to identify high-risk alerts based on patient data.
        
        Mandatory Checkpoints (SOP Standards):
        1. RYR1 / CACNA1S / STAC3 -> Malignant Hyperthermia (Anesthesia Risk).
        2. BCHE -> Prolonged Apnea / Neuromuscular blockade risk.
        3. HLA-B*57:01 -> Abacavir hypersensitivity.
        4. HLA-B15:02 / HLA-A31:01 -> Carbamazepine SCAR (SJS/TEN).
        5. CYP2D6 -> Codeine/Tramadol response and toxicity.
        6. TPMT / NUDT15 -> Thiopurine myelotoxicity.
        7. DPYD -> Fluoropyrimidine toxicity.
        8. SLCO1B1 -> Statin-induced myopathy.
        
        Patient Data:
        - Medications: ${JSON.stringify(input.medications ?? [])}
        - Genomics: ${JSON.stringify(input.genomics ?? {})}
        - Clinical History: ${JSON.stringify(input.history ?? {})}
        
        Instructions:
        - If any of the mandatory high-priority variants are found, flag them as 'Critical' or 'High'.
        - If the patient is taking a drug that interacts with their genotype (PGx), flag as 'Critical'.
        - For Anesthesia risks, always require 'Physician Review'.
        - Be precise. State the gene, allele, and specific risk.
        - Follow CPIC and FDA guidelines.
      `,
      output: {
        schema: SafetyAnalysisOutputSchema,
      }
    });

    if (!response.output) {
      throw new Error("Failed to generate structured Safety Analysis output");
    }
    return response.output;
  }
);
