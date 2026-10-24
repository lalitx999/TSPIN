import { OpenAI } from "openai";
import { GoogleGenerativeAI } from "@google/generative-ai";
import { NextResponse } from "next/server";

// Initialize APIs
const groq = new OpenAI({
  apiKey: process.env.GROQ_API_KEY || "dummy-key",
  baseURL: "https://api.groq.com/openai/v1",
});

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY || process.env.GOOGLE_AI_API_KEY || "dummy-key");

const SYSTEM_PROMPT = `
คุณคือ "พยาบาลคัดกรองอัจฉริยะ" (Smart Triage Assistant) ของ TSPI Clinical Platform
หน้าที่หลัก: 
1. คัดกรองอาการเบื้องต้น ถามข้อมูลอาการ ระยะเวลา และความรุนแรง
2. ให้คำแนะนำเบื้องต้นที่ปลอดภัย (เช่น การพักผ่อน การดื่มน้ำ)
3. เตือนอาการอันตราย (Red Flags) ถ้ามี ให้รีบไปพบแพทย์

กฎเหล็กสำคัญที่สุด:
- ห้ามวินิจฉัยโรคเด็ดขาด (ห้ามบอกว่า "คุณเป็นโรค...")
- ห้ามสั่งยาเด็ดขาด
- ใช้ภาษาที่สุภาพ เป็นกันเอง เข้าใจง่าย
`;

export async function POST(req: Request) {
  try {
    const { messages, hasImage, hasAudio } = await req.json();

    // 🌐 0. Retrieve AI engine configurations from Django Backend settings key 'ai_settings'
    let activeModel = "gemini-1.5-pro";
    let provider = "gemini";
    let systemPrompt = SYSTEM_PROMPT;

    try {
      const backendBaseUrl = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";
      const settingsRes = await fetch(`${backendBaseUrl}/api/settings/ai_settings/`);
      if (settingsRes.ok) {
        const settingsData = await settingsRes.json();
        const config = typeof settingsData.setting_value === "string"
          ? JSON.parse(settingsData.setting_value)
          : settingsData.setting_value;
          
        if (config) {
          if (config.model) activeModel = config.model;
          if (config.provider) provider = config.provider;
          if (config.system_prompt) systemPrompt = config.system_prompt;
        }
      }
    } catch (err) {
      console.warn("⚠️ Failed to load dynamic AI settings from EMR backend, falling back to defaults:", err);
    }

    // 🔍 1. Retrieve the latest user message for RAG Query
    const lastUserMessage = messages.filter((m: any) => m.role === "user").pop();
    const queryText = lastUserMessage ? lastUserMessage.content : "";

    let medicalContext = "";
    if (queryText) {
      try {
        const searchUrl = `${process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online"}/api/knowledge-segments/search/`;
        
        // Forward authorization header if it exists
        const authHeader = req.headers.get("authorization");
        const searchHeaders: Record<string, string> = {
          "Content-Type": "application/json"
        };
        if (authHeader) {
          searchHeaders["Authorization"] = authHeader;
        }

        const searchRes = await fetch(searchUrl, {
          method: "POST",
          headers: searchHeaders,
          body: JSON.stringify({ query: queryText })
        });
        
        if (searchRes.ok) {
          const searchData = await searchRes.json();
          if (searchData.success && searchData.results && searchData.results.length > 0) {
            // Pick top 3 results
            medicalContext = searchData.results
              .slice(0, 3)
              .map((r: any, idx: number) => `[ความรู้ที่ ${idx + 1}] หัวข้อ: ${r.title || "ทั่วไป"}\nเนื้อหา: ${r.content}`)
              .join("\n\n");
          }
        }
      } catch (err) {
        console.error("⚠️ Failed to fetch RAG context from backend:", err);
      }
    }

    // 🧠 2. Construct Dynamic System Prompt
    let dynamicSystemPrompt = systemPrompt;
    if (medicalContext) {
      dynamicSystemPrompt = `${systemPrompt}\n\n[ข้อมูลอ้างอิงทางการแพทย์ตามแนวทางคลินิก (วิเคราะห์ตามหลัก 39 แกน TSPI เท่านั้น ห้ามวินิจฉัยโรคเด็ดขาด)]:\n${medicalContext}`;
    }

    const isMultimodal = hasImage || hasAudio || messages.some((m: any) => m.isImage || m.isAudio);

    if (isMultimodal) {
      // 🚀 Route to Gemini (Multimodal for OCR and Audio Triage)
      const targetModel = activeModel.startsWith("gemini") ? activeModel : "gemini-2.5-flash";
      const model = genAI.getGenerativeModel({ model: targetModel, systemInstruction: dynamicSystemPrompt });
      
      // Convert standard messages to Gemini format (supporting images and audio)
      const geminiMessages = messages.map((m: any) => {
        if (m.isImage && m.imageBase64) {
          const userText = (m.content || "").trim();
          const hintPrompt = userText 
            ? `${userText}\n\n[คำแนะนำสำหรับการอ่านภาพ/OCR]: กรุณาถอดความหมายของคำและผลการวิเคราะห์ในรูปภาพอาการ/ใบตรวจนี้อย่างละเอียด และนำไปประเมินความสอดคล้องตามแนวทางแกน TSPI ของคนไข้ ห้ามสั่งยารักษาหรือวินิจฉัยโรคเด็ดขาด`
            : "กรุณารันระบบ OCR ดึงตัวหนังสือจากรูปภาพผลแล็บ/ภาพอาการชิ้นนี้อย่างละเอียด และทำการคัดกรองอาการเบื้องต้นตามแกนชีวภาพ TSPI";

          return {
            role: "user",
            parts: [
              { text: hintPrompt },
              {
                inlineData: {
                  data: m.imageBase64.split(",")[1], // Remove prefix "data:image/jpeg;base64,"
                  mimeType: m.imageMimeType || "image/jpeg",
                }
              }
            ]
          };
        }

        if (m.isAudio && m.audioBase64) {
          const userText = (m.content || "").trim();
          const hintPrompt = userText && userText !== "[ข้อความเสียง]"
            ? `[คำพูดออดิโอของคนไข้]: "${userText}"\n\n[คำแนะนำสำหรับไฟล์เสียงประกอบ]: กรุณาฟังคลิปเสียงซักประวัติอาการนี้ร่วมด้วย เพื่อถอดความเข้าใจและนำไปร่วมประเมินแนวทางแกน TSPI อย่างแม่นยำ`
            : "กรุณาฟังและถอดเทปเสียงซักประวัติอาการของคนไข้ในไฟล์เสียงประกอบนี้อย่างครบถ้วน และนำไปคัดกรองประเมินแนวแกนระบบชีวภาพ 39 แกน TSPI ของร่างกาย";

          return {
            role: "user",
            parts: [
              { text: hintPrompt },
              {
                inlineData: {
                  data: m.audioBase64.split(",")[1], // Remove prefix "data:audio/webm;base64,"
                  mimeType: m.audioMimeType || "audio/webm",
                }
              }
            ]
          };
        }

        return {
          role: m.role === "user" ? "user" : "model",
          parts: [{ text: m.content }]
        };
      });

      let chatHistory = geminiMessages.slice(0, -1);
      
      // 🚨 Gemini strict rule: The first message in the chat history must be from 'user'.
      if (chatHistory.length > 0 && chatHistory[0].role === "model") {
        chatHistory = chatHistory.slice(1);
      }

      const chat = model.startChat({
        history: chatHistory,
      });

      const lastMessage = geminiMessages[geminiMessages.length - 1];
      const result = await chat.sendMessage(lastMessage.parts);
      const text = result.response.text();

      return NextResponse.json({ 
        role: "assistant", 
        content: text,
        provider: "gemini-" + targetModel
      });

    } else {
      // ⚡ Route based on chosen provider from AI settings
      if (provider === "openai") {
        const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY || "dummy-key" });
        const targetModel = activeModel.startsWith("gpt") ? activeModel : "gpt-4o";
        const response = await openai.chat.completions.create({
          model: targetModel,
          messages: [
            { role: "system", content: dynamicSystemPrompt },
            ...messages.map((m: any) => ({ role: m.role, content: m.content }))
          ],
          temperature: 0.5,
          max_tokens: 1024,
        });

        const aiMessage = response.choices[0].message;
        return NextResponse.json({
          ...aiMessage,
          provider: "openai-" + targetModel
        });

      } else if (provider === "gemini") {
        const targetModel = "gemini-2.5-flash";
        const model = genAI.getGenerativeModel({ model: targetModel, systemInstruction: dynamicSystemPrompt });
        
        const geminiMessages = messages.map((m: any) => ({
          role: m.role === "user" ? "user" : "model",
          parts: [{ text: m.content }]
        }));

        let chatHistory = geminiMessages.slice(0, -1);
        if (chatHistory.length > 0 && chatHistory[0].role === "model") {
          chatHistory = chatHistory.slice(1);
        }

        const chat = model.startChat({
          history: chatHistory,
        });

        const lastMessage = geminiMessages[geminiMessages.length - 1];
        const result = await chat.sendMessage(lastMessage.parts);
        const text = result.response.text();

        return NextResponse.json({ 
          role: "assistant", 
          content: text,
          provider: "gemini-" + targetModel
        });

      } else {
        // Default to Groq Llama (Fast Text Routing)
        const formattedMessages = [
          { role: "system", content: dynamicSystemPrompt },
          ...messages.map((m: any) => ({ role: m.role, content: m.content }))
        ];

        const response = await groq.chat.completions.create({
          model: "llama-3.3-70b-versatile",
          messages: formattedMessages,
          temperature: 0.5,
          max_tokens: 1024,
        });

        const aiMessage = response.choices[0].message;
        return NextResponse.json({
          ...aiMessage,
          provider: "groq-llama3"
        });
      }
    }

  } catch (error: any) {
    console.error("AI Intake Routing Error:", error);
    return NextResponse.json({ error: "AI Connection Failed" }, { status: 500 });
  }
}
