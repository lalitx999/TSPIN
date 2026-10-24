import { GoogleGenerativeAI } from "@google/generative-ai";
import { NextResponse } from "next/server";
import { logAudit } from "@/utils/api/audit";
import { buildAxesPromptText } from "@/lib/axis-definitions";

const genAI = new GoogleGenerativeAI(process.env.GOOGLE_AI_API_KEY || "dummy-key");

export async function POST(req: Request) {
  try {
    const { text, patientId } = await req.json();

    if (!text || text.trim() === "") {
      return NextResponse.json({ error: "No lab text provided" }, { status: 400 });
    }

    // Initialize Gemini 2.5 Flash with JSON response configuration
    const model = genAI.getGenerativeModel({
      model: "gemini-2.5-flash",
      generationConfig: {
        responseMimeType: "application/json"
      }
    });

    const prompt = `
      คุณคือผู้เชี่ยวชาญด้านการวิเคราะห์ผลแล็บและชีววิทยาระดับเซลล์ (Clinical Lab Data and Systems Biology Specialist) ของ TSPI Clinic
      สกัดข้อมูลผลแล็บจากข้อความดิบต่อไปนี้ ให้ออกมาเป็นโครงสร้าง JSON ที่กำหนด
      
      ข้อความผลแล็บ:
      """
      ${text}
      """
      
      ความรู้เรื่อง แกนทางชีววิทยา 39 แกนของ TSPI:
      ${buildAxesPromptText()}

      โปรดวิเคราะห์ว่าค่าแล็บใดที่ผิดปกติ (เช่น สูงกว่าหรือต่ำกว่าช่วงอ้างอิง) ส่งผลกระทบต่อแกนทางชีววิทยาใดใน 39 แกนนี้
      
      โครงสร้าง JSON ที่ต้องส่งกลับ (ห้ามมีข้อความอื่น ให้คืนเป็น JSON เท่านั้น):
      {
        "markers": [
          {
            "name": "ชื่อค่าตรวจ (เช่น HbA1c, ALT, hs-CRP, Cholesterol)",
            "value": "ค่าที่ตรวจได้ (ตัวเลขหรือข้อความ)",
            "unit": "หน่วยการวัด (เช่น mg/dL, U/L, %)",
            "reference": "ค่าอ้างอิงปกติ (เช่น 70-100, < 5.7)",
            "flag": "ใช้คำว่า NORMAL หรือ HIGH หรือ LOW หรือ BORDERLINE"
          }
        ],
        "axes": [
          {
            "id": "A1 (ใส่ตัวอักษร A นำหน้าเบอร์แกน เช่น A1, A3, A24)",
            "name": "ชื่อแกนภาษาอังกฤษ",
            "domain": "ชื่อกลุ่มหมวดหมู่หลักแบบสั้นๆ เช่น Immunity, Metabolism, Oxidation, Hormone, Organ",
            "score": "คะแนนผลกระทบเป็นค่าทศนิยม 0.1 ถึง 1.0 (เช่น 0.8 หมายถึงกระทบ 80%)"
          }
        ],
        "summary": "อธิบายสรุปสั้นๆ เป็นภาษาอังกฤษถึงภาพรวมความผิดปกติของระบบในร่างกาย อิงจากผลแล็บเหล่านี้ (ประมาณ 2-3 ประโยค)"
      }
    `;

    // Generate Content
    const result = await model.generateContent(prompt);
    const response = await result.response;
    const responseText = response.text();

    // Parse response
    const resultData = JSON.parse(responseText.trim());

    // 🕵️‍♂️ Audit Logging
    await logAudit({
      action: "LAB_TEXT_ANALYZED",
      patientId: patientId || undefined,
      details: {
        parameters_found: resultData.markers?.length || 0,
        axis_count: resultData.axes?.length || 0
      },
      metadata: { model: "gemini-2.5-flash", channel: "API" }
    });

    return NextResponse.json(resultData);
  } catch (error: any) {
    console.error("Lab Text Analyzer Error:", error);
    return NextResponse.json({ error: "Text Processing Failed: " + error.message }, { status: 500 });
  }
}