const { GoogleGenerativeAI } = require("@google/generative-ai");
const dotenv = require("dotenv");
const path = require("path");

// Load .env.local
dotenv.config({ path: path.join(__dirname, "../.env.local") });

const apiKey = process.env.GOOGLE_AI_API_KEY;
const genAI = new GoogleGenerativeAI(apiKey || "");

async function run() {
  try {
    console.log("Testing with gemini-2.5-flash and systemInstruction...");
    const model = genAI.getGenerativeModel({ 
      model: "gemini-2.5-flash",
      systemInstruction: "You are a helpful AI assistant that ONLY speaks in pirate slang."
    });
    const result = await model.generateContent("Who are you?");
    console.log("Response:", result.response.text());
  } catch (err) {
    console.error("Error:", err);
  }
}

run();
