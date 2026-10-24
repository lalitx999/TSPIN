import { OpenAI } from "openai";
import { NextResponse } from "next/server";

const groq = new OpenAI({
  apiKey: process.env.GROQ_API_KEY || "dummy-key",
  baseURL: "https://api.groq.com/openai/v1",
});

export async function POST(req: Request) {
  try {
    const { patientName, symptoms, treatmentPlan, day } = await req.json();

    const response = await groq.chat.completions.create({
      model: "llama-3.3-70b-versatile",
      messages: [
        {
          role: "system",
          content: `คุณคือ TSPI Clinical Assistant หน้าที่ของคุณคือสร้างคำถามติดตามอาการ (Follow-up) สำหรับคนไข้
          
          กฎการสร้างคำถาม:
          1. ใช้ภาษาที่สุภาพ เป็นกันเอง และแสดงความห่วงใย
          2. คำถามต้องสัมพันธ์กับอาการหลัก (${symptoms}) และแผนการรักษา (${treatmentPlan})
          3. สำหรับวันที่ ${day} หลังการรักษา ให้เน้นเรื่องผลข้างเคียงหรือการปรับตัว
          4. ท้ายที่สุด ให้ขอคะแนนความพึงพอใจ (0-10)
          
          รูปแบบการตอบกลับ: ภาษาไทยเท่านั้น`
        },
        { 
          role: "user", 
          content: `สร้างข้อความติดตามอาการสำหรับคุณ ${patientName} วันที่ ${day}` 
        }
      ],
      temperature: 0.7,
      max_tokens: 500,
    });

    return NextResponse.json({
      message: response.choices[0].message.content,
      metadata: {
        generatedAt: new Date().toISOString(),
        day,
        type: "FOLLOW_UP"
      }
    });

  } catch (error: any) {
    console.error("Follow-up API Error:", error);
    return NextResponse.json({ error: "Failed to generate follow-up" }, { status: 500 });
  }
}
