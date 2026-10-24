import dotenv from "dotenv";
dotenv.config({ path: ".env.local" });
import { genkit } from "genkit";
import { googleAI } from "@genkit-ai/google-genai";
import { groq } from "genkitx-groq";
import { OpenAI } from "openai";

// 🚀 TSPI AI Command Center: Orchestrating the Best Minds
export const ai = genkit({
  plugins: [
    googleAI({ apiKey: process.env.GOOGLE_AI_API_KEY || "placeholder_key" }),
    groq({ apiKey: process.env.GROQ_API_KEY || "placeholder_key" }),
  ],
  model: "googleai/gemini-2.5-flash", // Default fallback
});

// Configure DeepSeek client via OpenAI compatibility
const deepseekClient = new OpenAI({
  apiKey: process.env.DEEPSEEK_API_KEY || "placeholder_key",
  baseURL: "https://api.deepseek.com/v1",
});

// Define DeepSeek model in Genkit
export const deepseekModel = ai.defineModel(
  {
    name: "deepseek/deepseek-chat",
    label: "DeepSeek Chat",
    apiVersion: "v2",
  },
  async (request) => {
    const messages = request.messages.map((m) => ({
      role: (m.role === "model" ? "assistant" : m.role) as "system" | "user" | "assistant",
      content: m.content[0].text || "",
    }));

    const response = await deepseekClient.chat.completions.create({
      model: "deepseek-chat",
      messages: messages,
      temperature: request.config?.temperature ?? 0.7,
      max_tokens: request.config?.maxOutputTokens,
      response_format: (request.output?.schema || request.output?.format === "json")
        ? { type: "json_object" }
        : undefined,
    });

    const choice = response.choices[0];
    return {
      message: {
        role: "model",
        content: [{ text: choice.message.content || "" }],
      },
      finishReason: "stop",
    };
  }
);

// --- Model Shortcuts for easy access ---
export const models = {
  // ⚡ Groq: Ultra-fast Intake
  intake: "groq/llama-3.3-70b-versatile", 
  
  // 🧠 DeepSeek: Mathematical & Logical Analysis
  logic: "deepseek/deepseek-chat", 
  
  // 👁️ Gemini: Vision, OCR, Audio, and Report Writing
  vision: "googleai/gemini-2.5-flash",
  writer: "googleai/gemini-2.5-pro", 
};

// --- Embedder ---
export const embedder = "googleai/gemini-embedding-001";


// --- Register Flows ---
// Flows will be imported explicitly where needed to avoid circular dependencies

