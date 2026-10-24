import { OpenAI } from "openai";
import { GoogleGenerativeAI } from "@google/generative-ai";
import { NextResponse } from "next/server";
import { logAudit } from "@/utils/api/audit";
import { buildAxesPromptText } from "@/lib/axis-definitions";

// 1. Initialize Engines
const groq = new OpenAI({
  apiKey: process.env.GROQ_API_KEY || "dummy-key",
  baseURL: "https://api.groq.com/openai/v1",
});

const deepseek = new OpenAI({
  apiKey: process.env.DEEPSEEK_API_KEY || "dummy-key",
  baseURL: "https://api.deepseek.com/v1",
});

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY || process.env.GOOGLE_AI_API_KEY || "dummy-key");

// ✅ ลบ AXES_DEFINITIONS ออกทั้งหมด (บรรทัด ~20-31)

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { messages = [], patientId, clinicalContext, engine = "groq", systemInstruction: reqSystemInstruction, options = {} } = body;

    let backendGoogleKey = "";
    let backendGroqKey = "";
    let backendDeepseekKey = "";
    let activeModel = "gemini-2.5-flash";
    let provider = "gemini";
    let dbSystemPrompt = "";

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
          if (config.system_prompt) dbSystemPrompt = config.system_prompt;
          if (config.google_api_key) backendGoogleKey = config.google_api_key;
          if (config.groq_api_key) backendGroqKey = config.groq_api_key;
          if (config.deepseek_api_key) backendDeepseekKey = config.deepseek_api_key;
        }
      }
    } catch (err) {
      console.warn("⚠️ Failed to load dynamic AI settings in Brain Route from EMR backend, falling back to defaults:", err);
    }

    // 🛡️ 1. Prepare initial messages
    const baseMessages = messages.length > 0 ? [...messages] : [{ role: "user", content: "เริ่มการวิเคราะห์คนไข้" }];

    // 🧬 2. Call Django Precision Medicine Engine if patientId is present
    const authHeader = req.headers.get("authorization");
    if (patientId) {
      try {
        let extractedFbs = "";
        let extractedHba1c = "";
        let extractedDoppler = "";

        const lastUserMsg = baseMessages.filter(m => m.role === "user").pop();
        const fullTextForExtraction = `${clinicalContext?.symptoms || ""} ${lastUserMsg ? lastUserMsg.content : ""}`.toLowerCase();

        // Fasting Blood Sugar (FBS) extraction
        const fbsMatch = fullTextForExtraction.match(/(?:fbs|fasting blood sugar|น้ำตาลในเลือด|น้ำตาล)\s*(?:=|:|\s)\s*(\d{2,3})/i);
        if (fbsMatch) extractedFbs = fbsMatch[1];

        // HbA1c extraction
        const hba1cMatch = fullTextForExtraction.match(/(?:hba1c|hb a1c|น้ำตาลสะสม)\s*(?:=|:|\s)\s*(\d+(?:\.\d+)?)/i);
        if (hba1cMatch) extractedHba1c = hba1cMatch[1];

        // Doppler extraction
        if (fullTextForExtraction.includes("doppler") || fullTextForExtraction.includes("plaque") || fullTextForExtraction.includes("stenosis") || fullTextForExtraction.includes("calcification")) {
          extractedDoppler = "Detected arterial plaque / narrowing";
        }

        console.log("🧬 Extracted parameters for Django Precision Medicine calculation:", {
          fbs: extractedFbs,
          hba1c: extractedHba1c,
          doppler: extractedDoppler
        });

        const backendBaseUrl = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";
        const calcRes = await fetch(`${backendBaseUrl}/api/patients/${patientId}/calculate-precision-medicine/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": authHeader || ""
          },
          body: JSON.stringify({
            symptoms: clinicalContext?.symptoms || lastUserMsg?.content || "",
            fbs: extractedFbs,
            hba1c: extractedHba1c,
            doppler: extractedDoppler,
            bowelStatus: "normal"
          })
        });

        if (calcRes.ok) {
          const djangoResult = await calcRes.json();
          if (djangoResult.success) {
            const calculatedScores = djangoResult.calculated_scores || {};
            const insight = djangoResult.insight || "";
            const analysis = djangoResult.analysis || {};

            const axesUpdates: any[] = [];
            const frontendAxes = clinicalContext?.axes || [];

            if (frontendAxes.length > 0) {
              frontendAxes.forEach((ax: any) => {
                const numericId = parseInt(String(ax.axis_id).replace(/[^\d]/g, ''));
                if (calculatedScores[numericId] !== undefined) {
                  axesUpdates.push({
                    axis_id: ax.axis_id,
                    score: calculatedScores[numericId],
                    clinical_note: analysis[numericId] || `ระบบอัตโนมัติคัดกรองตามตรรกะระบบชีวภาพ (${insight})`
                  });
                } else {
                  axesUpdates.push(ax);
                }
              });
              clinicalContext.axes = axesUpdates;
            }
          }
        }
      } catch (calcErr: any) {
        console.warn("⚠️ Django precision analysis failed, falling back to LLM orchestrator:", calcErr.message || calcErr);
      }
    }

    let patientContext = "";

    // 🧬 3. Build Patient Context from Django EMR
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (authHeader) {
      headers["Authorization"] = authHeader;
    }

    if (clinicalContext) {
      patientContext = `
[DIRECT CLINICAL CONTEXT]
Patient: ${clinicalContext.patientName} (HN: ${clinicalContext.hn})
Symptoms: ${clinicalContext.symptoms || "N/A"}
Current Axes: ${JSON.stringify(clinicalContext.axes || {})}
      `.trim();
    }
    else if (patientId) {
      try {
        const backendBaseUrl = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";
        const patientRes = await fetch(`${backendBaseUrl}/api/patients/${patientId}/`, { headers });
        if (patientRes.ok) {
          const patientData = await patientRes.json();
          patientContext = `
[PATIENT CLINICAL RECORD]
Name: ${patientData.first_name || "N/A"} ${patientData.last_name || "N/A"}
Symptoms: ${patientData.chief_complaint || "N/A"}
Axes: ${JSON.stringify(patientData.axes || {})}
          `.trim();
        }
      } catch (err) {
        console.error("Failed to query patient data from Django in AI route:", err);
      }
    }

    // 🧠 3. Final Orchestration
    const systemInstruction = `You are the TSPI Precision Medicine AI Specialist. 
    Analyze using the 39-Axis Framework: ${buildAxesPromptText()}
    
    DIRECTIVES:
    1. PROFESSIONAL THAI ONLY.
    2. NETWORK EFFECT ANALYSIS.
    3. NO HALLUCINATIONS.
    
    ${dbSystemPrompt || ""}
    
    ${reqSystemInstruction || options.systemInstruction || ""}
    `.trim();

    const enhancedMessages = [...baseMessages];
    if (patientContext && enhancedMessages.length > 0) {
      const lastIdx = enhancedMessages.length - 1;
      const userQuery = enhancedMessages[lastIdx].content;
      enhancedMessages[lastIdx].content = `
[CONTEXT]
${patientContext}

[MISSION]
${userQuery}
      `.trim();
    }

    const finalMessages = [{ role: "system", content: systemInstruction }, ...enhancedMessages];

    let responseContent = "";
    let modelName = "";

    // Determine the engine based on user selected provider in DB settings
    let selectedEngine = engine;
    if (engine === "groq" || !engine) {
      if (provider === "openai") {
        selectedEngine = "openai";
      } else if (provider === "gemini" || backendGoogleKey || process.env.GOOGLE_AI_API_KEY || process.env.GEMINI_API_KEY) {
        selectedEngine = activeModel || "gemini-2.5-flash";
      }
    }

    const runGemini = async (): Promise<string> => {
      const apiKey = backendGoogleKey || process.env.GEMINI_API_KEY || process.env.GOOGLE_AI_API_KEY;
      if (!apiKey || apiKey === "dummy-key") {
        throw new Error("Google AI API Key is missing or invalid.");
      }
      const client = new GoogleGenerativeAI(apiKey);
      const targetModel = "gemini-2.5-flash";
      modelName = targetModel;
      const model = client.getGenerativeModel({
        model: targetModel,
        systemInstruction: systemInstruction
      });
      const lastMsg = enhancedMessages[enhancedMessages.length - 1].content;
      const result = await model.generateContent(lastMsg);
      const res = await result.response;
      return res.text();
    };

    const runGroq = async (): Promise<string> => {
      const apiKey = backendGroqKey || process.env.GROQ_API_KEY;
      if (!apiKey || apiKey === "dummy-key") throw new Error("Groq API Key missing");
      modelName = "llama-3.3-70b-versatile";
      const groqClient = new OpenAI({ apiKey, baseURL: "https://api.groq.com/openai/v1" });
      const res = await groqClient.chat.completions.create({
        model: modelName,
        messages: finalMessages,
        ...options
      });
      return res.choices[0].message.content || "";
    };

    const runOpenAI = async (): Promise<string> => {
      const apiKey = process.env.OPENAI_API_KEY;
      if (!apiKey || apiKey === "dummy-key") throw new Error("OpenAI API Key missing");
      modelName = activeModel.startsWith("gpt") ? activeModel : "gpt-4o";
      const openaiClient = new OpenAI({ apiKey });
      const res = await openaiClient.chat.completions.create({
        model: modelName,
        messages: finalMessages,
        ...options
      });
      return res.choices[0].message.content || "";
    };

    const runDeepseek = async (): Promise<string> => {
      const apiKey = backendDeepseekKey || process.env.DEEPSEEK_API_KEY;
      if (!apiKey || apiKey === "dummy-key") throw new Error("DeepSeek API Key missing");
      modelName = "deepseek-chat";
      const dsClient = new OpenAI({ apiKey, baseURL: "https://api.deepseek.com/v1" });
      const res = await dsClient.chat.completions.create({
        model: modelName,
        messages: finalMessages,
        ...options
      });
      return res.choices[0].message.content || "";
    };

    try {
      if (selectedEngine === "openai") {
        responseContent = await runOpenAI();
      } else if (selectedEngine === "groq") {
        responseContent = await runGroq();
      } else if (selectedEngine === "deepseek") {
        responseContent = await runDeepseek();
      } else {
        responseContent = await runGemini();
      }
    } catch (primaryErr: any) {
      console.warn(`⚠️ Primary LLM engine (${selectedEngine}) failed:`, primaryErr.message || primaryErr);
      try {
        responseContent = await runGemini();
      } catch (geminiFallbackErr: any) {
        try {
          responseContent = await runGroq();
        } catch (groqFallbackErr: any) {
          console.error("⚠️ All LLM engines failed:", groqFallbackErr.message || groqFallbackErr);
          modelName = "TSPI Clinical Deterministic Engine";
          responseContent = "ระบบ AI กำลังประมวลผลกลไกชีวภาพผ่านฐานข้อมูลคลินิกย้อนหลังของคนไข้ในระบบ EMR";
        }
      }
    }

    // 💾 TSPI Self-Learning Brain: Log successful training pair to Django PostgreSQL
    if (patientId && responseContent) {
      try {
        let suggestedAxes: Record<string, number> = {};
        const bioMatch = responseContent.match(/:::BIO_UPDATE:::([\s\S]*?)(?::::|$)/);
        if (bioMatch) {
          try {
            const parsed = JSON.parse(bioMatch[1].trim());
            if (parsed.axes) {
              parsed.axes.forEach((a: any) => {
                const axisId = parseInt(String(a.axis_id).replace(/[^\d]/g, ''));
                if (axisId) {
                  suggestedAxes[`AXIS_${axisId}`] = a.severity;
                }
              });
            }
          } catch (pe: any) {
            console.warn("⚠️ Failed to parse BIO_UPDATE for brain logging:", pe.message);
          }
        }

        const backendBaseUrl = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";
        fetch(`${backendBaseUrl}/api/ai/log-brain-training/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": authHeader || ""
          },
          body: JSON.stringify({
            patientId: patientId,
            inputs: {
              labs: clinicalContext || {},
              messages: messages
            },
            output_axes: suggestedAxes,
            output_text: responseContent,
            engine_used: engine
          })
        }).catch(e => console.error("❌ Failed logging TSPI Brain dataset:", e));
      } catch (err) {
        console.error("⚠️ TSPI Brain Logging failed:", err);
      }
    }

    await logAudit({
      action: "AI_ANALYSIS",
      details: { engine, model: modelName, patientId },
      metadata: { model: modelName }
    });

    return NextResponse.json({ content: responseContent, engine, model: modelName });
  } catch (error: any) {
    console.error("AI Brain Critical Error:", error);
    return NextResponse.json({
      error: "AI Brain Coordination Failed",
      details: error.message
    }, { status: 500 });
  }
}