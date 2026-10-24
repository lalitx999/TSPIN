import dotenv from "dotenv";
dotenv.config({ path: ".env.local" });
import { genkit } from "genkit";
import { googleAI } from "@genkit-ai/google-genai";
import { groq } from "genkitx-groq";
import { anthropic } from "genkitx-anthropic";

// 🚀 TSPI AI Command Center: Orchestrating the Best Minds
export const ai = genkit({
  plugins: [
    googleAI({ apiKey: process.env.GOOGLE_AI_API_KEY }),
    groq({ apiKey: process.env.GROQ_API_KEY }),
    anthropic({ apiKey: process.env.ANTHROPIC_API_KEY }),
  ],
  model: "googleai/gemini-flash-latest", // Default fallback
});

// --- Model Shortcuts for easy access ---
export const models = {
  // ⚡ Groq: Ultra-fast Intake & Reasoning
  intake: "groq/llama-3.3-70b-versatile", 
  logic: "groq/llama-3.3-70b-versatile", 
  
  // 👁️ Gemini: Vision & OCR & Fast General
  vision: "googleai/gemini-flash-latest",
  
  // ✍️ Claude: Clinical Grade Writing & PDF Formatting
  writer: "anthropic/claude-3-5-sonnet-latest",
};

// --- Embedder ---
export const embedder = "googleai/gemini-embedding-001";

// --- Register Flows ---
// Flows will be imported explicitly where needed to avoid circular dependencies

