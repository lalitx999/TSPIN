import dotenv from "dotenv";
dotenv.config({ path: ".env.local" });

const key = process.env.GOOGLE_AI_API_KEY;
const url = `https://generativelanguage.googleapis.com/v1beta/models?key=${key}`;

console.log("🔍 Checking available models for your API Key...");

fetch(url)
  .then(res => res.json())
  .then(data => {
    if (data.error) {
      console.error("❌ Error:", data.error.message);
    } else {
      console.log("✅ Available Models:");
      data.models.forEach(m => console.log(`- ${m.name}`));
    }
  })
  .catch(err => console.error("❌ Fetch Error:", err));
