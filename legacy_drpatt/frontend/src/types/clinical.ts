// ตัวแทนของ 39 Axes ทางชีววิทยาระบบ (ใส่ชื่อแกนชั่วคราวบางส่วน ต้องนำ 39 แกนจริงมาใส่ภายหลัง)
export type SystemAxis = 
  | "Sleep/Circadian Biology" 
  | "Cognitive Reserve" 
  | "Inflammatory Load" 
  | "Gut Barrier Integrity"
  | "Mitochondrial Function"
  | "Hormonal Balance"
  | "Immune Resilience"
  | "Cardiometabolic Health"
  | "Detoxification Capacity"
  | "Autonomic Nervous System"; // ตัวอย่างเพิ่มเติม

// รูปแบบคำตอบของคำถาม
export type QuestionType = "slider_0_10" | "boolean" | "multiple_choice" | "text";

/**
 * โครงสร้างของคำถาม 1 ข้อ (รองรับทั้งคำถามหลัก และคำถามเสริมจาก AI)
 */
export interface QuestionItem {
  id: string;               // รหัสคำถาม เช่น 'core_sleep_01' หรือ 'ai_followup_01'
  text: string;             // ข้อความคำถาม เช่น "คุณภาพการนอนสัปดาห์นี้เป็นอย่างไร?"
  type: QuestionType;       // รูปแบบคำตอบ
  options?: string[];       // (สำหรับ multiple_choice) ตัวเลือกคำตอบ
  linkedAxes: SystemAxis[]; // คำถามนี้ส่งผลต่อแกนชีววิทยาใดบ้าง (สำหรับการวิเคราะห์แนวโน้ม)
  isAiGenerated: boolean;   // แฟล็กบอกว่า AI เป็นคนสร้างข้อนี้ขึ้นมาสดๆ ใช่หรือไม่ (false = คำถามหลักประจำสัปดาห์)
  aiContext?: string;       // (เฉพาะ AI) บริบทหรือเหตุผลที่ AI สร้างคำถามนี้ เช่น "สัปดาห์ที่แล้วมีอาการปวดหัว"
}

/**
 * ชุดแบบสอบถามประจำสัปดาห์ (เปิดให้คนไข้ทำ)
 * ระบบจะสร้าง 1 Session ต่อ 1 รอบการทำแบบสอบถาม
 */
export interface QuestionnaireSession {
  id: string;               // Session ID
  patientId: string;        // รหัสคนไข้
  createdAt: Date;          // วันเวลาที่สร้างชุดคำถามนี้
  status: "pending" | "completed" | "expired"; // สถานะของการทำแบบสอบถาม
  questions: QuestionItem[];// รายการคำถามทั้งหมด (เช่น Core 7 ข้อ + AI เจนมา 5 ข้อ)
}

/**
 * คำตอบของคนไข้ที่จะถูกบันทึกกลับเข้าสู่ Firestore
 */
export interface QuestionnaireResponse {
  sessionId: string;        // อ้างอิงกลับไปยัง QuestionnaireSession
  patientId: string;
  submittedAt: Date;        // วันเวลาที่ส่งคำตอบ
  answers: {
    questionId: string;     // อ้างอิง ID ของ QuestionItem
    value: number | boolean | string; // คำตอบ (ส่วนใหญ่เป็นตัวเลข 0-10 ตามที่ออกแบบไว้)
  }[];
}
