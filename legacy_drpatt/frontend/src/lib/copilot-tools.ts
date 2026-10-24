import { ai } from './genkit';
import { z } from 'zod';
import { medicalDb } from './medical-data';

/**
 * GenKit Tools for the Clinical Copilot
 * These tools allow the AI to fetch specific patient data layers
 * while maintaining the 5-layer governance (A-E).
 */

export const getPatientProfile = ai.defineTool(
  {
    name: 'getPatientProfile',
    description: 'Fetches the raw clinical record of the patient (Layer A)',
    inputSchema: z.object({ patientId: z.string() }),
    outputSchema: z.any(),
  },
  async (input) => {
    return await medicalDb.getPatientDataLayer(input.patientId, 'A', 'ai-copilot');
  }
);

export const getRecentLabs = ai.defineTool(
  {
    name: 'getRecentLabs',
    description: 'Fetches recent laboratory results for a patient (Layer A)',
    inputSchema: z.object({ patientId: z.string() }),
    outputSchema: z.any(),
  },
  async (input) => {
    const data: any = await medicalDb.getPatientDataLayer(input.patientId, 'A', 'ai-copilot');
    return data?.labs || { message: 'No lab data found.' };
  }
);

export const getBiologicalScores = ai.defineTool(
  {
    name: 'getBiologicalScores',
    description: 'Fetches the 36-axis biological scores and recommendations (Layer D)',
    inputSchema: z.object({ patientId: z.string() }),
    outputSchema: z.any(),
  },
  async (input) => {
    return await medicalDb.getPatientDataLayer(input.patientId, 'D', 'ai-copilot');
  }
);

export const getOmicsReport = ai.defineTool(
  {
    name: 'getOmicsReport',
    description: 'Fetches interpreted microbiome, proteomics, or genomics reports (Layer C)',
    inputSchema: z.object({ patientId: z.string() }),
    outputSchema: z.any(),
  },
  async (input) => {
    return await medicalDb.getPatientDataLayer(input.patientId, 'C', 'ai-copilot');
  }
);

export const getModuleKnowledge = ai.defineTool(
  {
    name: 'getModuleKnowledge',
    description: 'Fetches detailed information about a TSPI treatment module',
    inputSchema: z.object({ moduleId: z.string() }),
    outputSchema: z.any(),
  },
  async (input) => {
    // This would typically query a modules collection or a knowledge base
    // For now, we mock a lookup
    return {
      moduleId: input.moduleId,
      status: 'TSPI Approved',
      evidenceLevel: 'High',
      mechanisms: ['Anti-inflammatory', 'Mitochondrial Support'],
    };
  }
);

export const copilotTools = [
  getPatientProfile,
  getRecentLabs,
  getBiologicalScores,
  getOmicsReport,
  getModuleKnowledge
];
