import { OpenAI } from "openai";
import { NextResponse } from "next/server";
import { logAudit } from "@/utils/api/audit";

const groq = new OpenAI({
  apiKey: process.env.GROQ_API_KEY || "dummy-key",
  baseURL: "https://api.groq.com/openai/v1",
});

const SYSTEM_PROMPT = `
คุณคือ "TSPI Clinical Intelligence Assistant" ผู้เชี่ยวชาญด้านการซักประวัติทางการแพทย์แผนไทยประยุกต์และชีววิทยาเชิงลึก
หน้าที่ของคุณคือซักประวัติคนไข้เบื้องต้นเพื่อประเมินความผิดปกติผ่าน "39 Biological Axes" ของ TSPI Clinic

แนวทางการซักประวัติ:
1. เริ่มต้นด้วยการถามอาการหลัก (Chief Complaint) และประวัติสุขภาพปัจจุบัน
2. ซักถามเพื่อประเมินแกนชีววิทยาหลัก (Axis 1, 2, 9, 15, 21, 33)
3. ตรวจสอบความครบถ้วน (QC): ถามจนกว่าจะได้ข้อมูลชัดเจนเรื่อง อาการ, ระยะเวลา, ปัจจัยกระตุ้น

รูปแบบการตอบกลับ:
- ให้คำแนะนำและถามคำถามอย่างสุภาพ
- ท้ายข้อความของคุณ (บรรทัดสุดท้าย) ให้ใส่ JSON Block เสมอในรูปแบบ:
  [[{"scores": {"AXIS_1": 0, "AXIS_9": 0, ...}, "status": "active|completed", "findings": ["..."]}]]

กฎเหล็ก: ห้ามวินิจฉัยโรคเอง ให้สรุปข้อมูลเพื่อส่งต่อแพทย์เท่านั้น
`;

export async function POST(req: Request) {
  try {
    const { messages } = await req.json();

    const response = await groq.chat.completions.create({
      model: "llama-3.3-70b-versatile",
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        ...messages
      ],
      temperature: 0.7,
      max_tokens: 1024,
    });

    const aiMessage = response.choices[0].message;

    // 🕵️‍♂️ Audit Logging
    await logAudit({
      action: "AI_INTAKE_RESPONSE",
      details: { 
        message_count: messages.length,
        response_preview: aiMessage.content?.slice(0, 200)
      },
      metadata: { model: "llama3-70b-8192" }
    });

    return NextResponse.json(aiMessage);
  } catch (error: any) {
    console.error("Groq API Error:", error);
    return NextResponse.json({ error: "AI Connection Failed" }, { status: 500 });
  }
}
