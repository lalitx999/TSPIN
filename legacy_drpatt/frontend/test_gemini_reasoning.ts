import dotenv from "dotenv";
dotenv.config({ path: ".env.local" });

import { ai } from "./src/lib/genkit";

async function test() {
  try {
    console.log("Calling Gemini with system and prompt...");
    const result = await ai.generate({
      model: 'googleai/gemini-2.5-flash',
      system: 'You are a medical assistant.',
      prompt: 'Summarize the patient data.',
    });
    console.log("Success! Result text:", result.text);
  } catch (e: any) {
    console.error("Error calling Gemini:", e);
  }
}

test();
