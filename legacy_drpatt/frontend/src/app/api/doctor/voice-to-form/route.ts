import { GoogleGenerativeAI } from "@google/generative-ai";
import { NextResponse } from "next/server";
import { logAudit } from "@/utils/api/audit";

const genAI = new GoogleGenerativeAI(process.env.GOOGLE_AI_API_KEY || "dummy-key");

export async function POST(req: Request) {
  const startTime = Date.now();
  try {
    const contentType = req.headers.get("content-type") || "";
    let transcription = "";
    let uploadedFile: Blob | null = null;
    let patientId = "";
    let doctorId = "";

    if (contentType.includes("application/json")) {
      const body = await req.json();
      transcription = body.text || "";
      patientId = body.patientId || "";
      doctorId = body.doctorId || "";
    } else {
      const formData = await req.formData();
      uploadedFile = formData.get("file") as Blob | null;
      transcription = formData.get("text") as string || "";
      patientId = formData.get("patientId") as string || "";
      doctorId = formData.get("doctorId") as string || "";
    }

    if (!process.env.GOOGLE_AI_API_KEY) {
      return NextResponse.json({ error: "Google AI API Key not configured" }, { status: 500 });
    }

    const model = genAI.getGenerativeModel({
      model: "gemini-2.5-flash",
      generationConfig: {
        responseMimeType: "application/json"
      }
    });

    const prompt = `
      คุณคือผู้เชี่ยวชาญด้านเวชระเบียนและระบบชีววิทยา (Precision Clinical Scribe & Systemic Health Specialist) ของ TSPI Clinic พูดภาษาไทยเป็นหลัก
      หน้าที่: วิเคราะห์ข้อมูลผู้ป่วยที่ส่งมา (ซึ่งอาจเป็น เสียงบันทึกการซักประวัติ, ภาพถ่ายอาการ, ผลแล็บ หรือ ข้อความ) 
      แล้วทำการสกัดและวิเคราะห์จัดกลุ่มเป็นรูปเล่มข้อมูล SOAP Note JSON ที่สมบูรณ์ มีระเบียบ และเรียบร้อยที่สุด

      โครงสร้าง JSON ที่ต้องส่งกลับ (ห้ามมีคำพูดเกริ่นนำหรือปิดท้าย ให้คืนเป็น JSON เท่านั้น):
      {
        "subjective": "สรุปข้อมูลที่ผู้ป่วยบอกเล่า อาการ ความรู้สึก ประวัติครอบครัว ประวัติการเจ็บป่วย (เขียนสรุปเป็นภาษาไทยอย่างเป็นระเบียบ เรียบร้อย อ่านง่าย)",
        "objective": "ข้อมูลทางคลินิกที่สังเกตหรือตรวจวัดได้ เช่น สัญญาณชีพ ผลการตรวจร่างกาย ผลแล็บ หรือลักษณะรูปภาพที่เห็นชัดเจนทางการแพทย์ (ถ้าไม่มีให้ใส่ '-')",
        "assessment": "การประเมินวิเคราะห์สภาวะของผู้ป่วยเบื้องต้น ความเสี่ยง หรือประเด็นทางชีวภาพหลักที่ต้องระวัง (ภาษาไทย)",
        "plan": "แผนการจัดการและการติดตามผล แนะนำการปรับพฤติกรรม อาหารเสริม ยา หรือการตรวจเพิ่มเติม (เขียนเป็นข้อๆ ภาษาไทยอย่างเป็นระเบียบเรียบร้อย)",
        "key_symptoms": ["อาการหลักที่พบ 1", "อาการหลักที่พบ 2"],
        "severity": "mild หรือ moderate หรือ severe (เลือกระดับความรุนแรง)",
        "summary_short": "สรุปใจความสำคัญสั้นๆ 1 ประโยคของสภาวะคนไข้รายนี้ (ภาษาไทย)"
      }
    `;

    let structuredContent: Record<string, any> = {};

    if (uploadedFile) {
      const buffer = Buffer.from(await uploadedFile.arrayBuffer());
      const base64Data = buffer.toString("base64");
      const fileMime = uploadedFile.type || "application/octet-stream";

      if (fileMime.startsWith("image/")) {
        // Handle medical image analysis
        const result = await model.generateContent([
          prompt + "\n\nโปรดวิเคราะห์ลักษณะทางคลินิกและอาการของโรคจากรูปภาพที่แนบมานี้ด้วย",
          {
            inlineData: {
              data: base64Data,
              mimeType: fileMime
            }
          }
        ]);
        
        const text = result.response.text();
        structuredContent = JSON.parse(text.trim());
        transcription = `[วิเคราะห์รูปภาพ: ${(uploadedFile as any).name || "medical_image.png"}]\n\nคำบรรยายภาพทางคลินิก:\n${structuredContent.subjective}`;
      } else if (fileMime.startsWith("audio/") || fileMime.includes("webm") || fileMime.includes("octet-stream")) {
        // Handle audio transcription and analysis via Gemini directly
        // Note: webm recording is often sent as application/octet-stream or audio/webm
        const targetMime = fileMime.includes("octet-stream") ? "audio/webm" : fileMime;
        const result = await model.generateContent([
          prompt + "\n\nโปรดถอดเสียงจากไฟล์เสียงที่บันทึกการซักประวัติที่แนบมานี้ และสรุปผลเข้าระบบ SOAP Note",
          {
            inlineData: {
              data: base64Data,
              mimeType: targetMime
            }
          }
        ]);
        
        const text = result.response.text();
        structuredContent = JSON.parse(text.trim());
        transcription = structuredContent.subjective || "ไม่สามารถถอดความเสียงได้";
      } else {
        // Text-based files (PDF/txt)
        const fileContent = buffer.toString("utf-8");
        const result = await model.generateContent([
          prompt + `\n\nโปรดวิเคราะห์เนื้อหาเอกสารทางการแพทย์ต่อไปนี้:\n\n${fileContent}`
        ]);
        
        const text = result.response.text();
        structuredContent = JSON.parse(text.trim());
        transcription = `[เอกสารแนบ: ${(uploadedFile as any).name || "medical_document.txt"}]\n\n${structuredContent.subjective}`;
      }
    } else if (transcription) {
      // Manual text intake processing
      const result = await model.generateContent([
        prompt + `\n\nวิเคราะห์และสรุปจากคำบอกเล่าของคนไข้และประวัติอาการต่อไปนี้:\n\n${transcription}`
      ]);
      const text = result.response.text();
      structuredContent = JSON.parse(text.trim());
    } else {
      return NextResponse.json({ error: "No voice transcription or file content provided" }, { status: 400 });
    }

    // Audit Logging
    try {
      await logAudit({
        action: "CLINICAL_INTAKE_PROCESSED",
        userId: doctorId || undefined,
        patientId: patientId || undefined,
        details: {
          inputRaw: transcription.slice(0, 500),
          outputStructured: structuredContent,
          is_file: !!uploadedFile,
          mime_type: uploadedFile?.type,
          executionTimeMs: Date.now() - startTime,
          success: true
        },
        metadata: { 
          model: "gemini-2.5-flash",
          channel: uploadedFile ? "file_upload" : "manual_text"
        },
      });
    } catch (auditErr) {
      console.warn("⚠️ Audit log skipped:", auditErr);
    }

    return NextResponse.json({
      text: transcription,
      summary: structuredContent.summary_short || structuredContent.subjective,
      structured: structuredContent,
    });
  } catch (error: any) {
    console.error("Clinical Intake Error:", error);
    return NextResponse.json(
      { error: "Intake Analysis Failed", details: error.message },
      { status: 500 }
    );
  }
}
