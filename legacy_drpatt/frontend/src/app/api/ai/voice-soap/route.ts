import { OpenAI } from "openai";
import { NextResponse } from "next/server";
import { logAudit } from "@/utils/api/audit";

const groq = new OpenAI({
  apiKey: process.env.GROQ_API_KEY || "dummy-key",
  baseURL: "https://api.groq.com/openai/v1",
});

const SYSTEM_PROMPT = `
คุณคือ "TSPI Clinical Intelligence Assistant" ผู้เชี่ยวชาญด้านชีววิทยาเชิงลึกและการเขียนบันทึกทางการแพทย์ (Clinical SOAP Notes)
หน้าที่ของคุณคือรับข้อความบรรยายอาการหรือผลการตรวจ (Transcript) และแปลงเป็นรูปแบบ SOAP Note ที่เป็นโครงสร้าง JSON พร้อมระบุแกนชีววิทยา (TSPI 39 Biological Axes) ที่เกี่ยวข้อง

โปรดคืนค่าเป็น JSON เท่านั้น โดยมีโครงสร้างดังนี้:
{
  "S": "Subjective - อาการที่ผู้ป่วยบอก",
  "O": "Objective - ผลการตรวจร่างกายหรือแล็บที่พบ",
  "A": "Assessment - การประเมินกลไกของโรค",
  "P": "Plan - แผนการรักษาหรือการให้คำแนะนำ",
  "axes": ["ชื่อแกนที่ 1", "ชื่อแกนที่ 2"]
}

ห้ามใส่ข้อความอธิบายใดๆ นอกเหนือจาก JSON
`;

export async function POST(req: Request) {
  try {
    const { text } = await req.json();

    if (!text) {
      return NextResponse.json({ error: "No text provided" }, { status: 400 });
    }

    const response = await groq.chat.completions.create({
      model: "llama-3.3-70b-versatile",
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user", content: `Transcript:\n\n${text}` }
      ],
      temperature: 0.3, // Low temperature for more structured output
      max_tokens: 1024,
      response_format: { type: "json_object" }
    });

    const aiMessage = response.choices[0].message.content || "{}";
    const soapResult = JSON.parse(aiMessage);

    // 🕵️‍♂️ Audit Logging
    await logAudit({
      action: "AI_VOICE_SOAP_GENERATION",
      details: { 
        text_length: text.length,
      },
      metadata: { model: "llama-3.3-70b-versatile" }
    });

    return NextResponse.json(soapResult);
  } catch (error: any) {
    console.error("Groq API Error:", error);
    return NextResponse.json({ error: "AI Connection Failed" }, { status: 500 });
  }
}
