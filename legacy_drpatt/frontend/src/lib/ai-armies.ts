import { genkit } from 'genkit';
import { googleAI } from '@genkit-ai/google-genai';
// import { groq } from '@genkit-ai/groq'; // Assuming plugin exists or will be added
// import { deepseek } from '@genkit-ai/deepseek'; // Assuming plugin exists or will be added

/**
 * TSPI AI Armies Orchestrator
 * 
 * 1. Groq - For Speed (Real-time Chat, Intake)
 * 2. Gemini - For Depth & Vision (Clinical Analysis, Document Parsing)
 * 3. DeepSeek - For Logic (Scoring Heuristics, Complex Reasoning)
 */

export const ai = genkit({
  plugins: [
    googleAI({
      apiKey: process.env.GOOGLE_AI_API_KEY,
    }),
    // Add Groq and DeepSeek plugins when API keys are ready
  ],
});

// Model References
export const models = {
  depth: 'googleai/gemini-2.5-pro',
  vision: 'googleai/gemini-2.5-flash',
  // speed: 'groq/llama3-70b',
  // logic: 'deepseek/deepseek-chat',
};
