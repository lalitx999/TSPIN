import dotenv from "dotenv";
dotenv.config({ path: ".env.local" });

import { ai } from "./src/lib/genkit";

async function test() {
  try {
    console.log("Calling Groq model via Genkit...");
    const result = await ai.generate({
      model: 'groq/llama-3.3-70b-versatile',
      prompt: 'Hello, are you available?',
    });
    console.log("Success! Result text:", result.text);
  } catch (e: any) {
    console.error("Error calling Groq:", e);
  }
}

test();
