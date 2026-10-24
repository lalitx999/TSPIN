/**
 * TSPI Clinical AI Intake Engine
 * มอเตอร์ประมวลผลอาการคนไข้ตาม 39 Biological Axes
 */

export interface AxisScore {
    axis_id: string;
    score: number; // 0-10
    evidence: string[];
}

export const analyzeSymptoms = (text: string, currentScores: Record<string, number>) => {
    const updatedScores = { ...currentScores };
    const findings: string[] = [];

    // ตัวอย่าง Keyword Mapping เบื้องต้น (จะถูกขยายผลด้วย LLM ในภายหลัง)
    const mapping: Record<string, { axes: string[], keywords: string[] }> = {
        "inflammation": {
            axes: ["AXIS_1", "AXIS_9"],
            keywords: ["ปวด", "บวม", "แดง", "ร้อน", "อักเสบ", "ไข้"]
        },
        "immune": {
            axes: ["AXIS_2", "AXIS_3"],
            keywords: ["แพ้", "ผื่น", "คัน", "ติดเชื้อง่าย", "หวัดบ่อย"]
        },
        "circulation": {
            axes: ["AXIS_21", "AXIS_22"],
            keywords: ["มือเท้าเย็น", "ชา", "มึนหัว", "ความดัน", "แน่นหน้าอก"]
        },
        "detox": {
            axes: ["AXIS_15", "AXIS_16"],
            keywords: ["ตับ", "ไต", "ท้องผูก", "ตัวเหลือง", "อ่อนเพลียเรื้อรัง"]
        },
        "neuro": {
            axes: ["AXIS_33", "AXIS_34", "AXIS_35"],
            keywords: ["นอนไม่หลับ", "เครียด", "กังวล", "หลงลืม", "สมาธิสั้น"]
        }
    };

    // ค้นหาความสัมพันธ์
    Object.entries(mapping).forEach(([category, data]) => {
        data.keywords.forEach(kw => {
            if (text.includes(kw)) {
                findings.push(`${category}: พบอาการเกี่ยวข้องกับ "${kw}"`);
                data.axes.forEach(axisId => {
                    updatedScores[axisId] = Math.min((updatedScores[axisId] || 0) + 2, 10);
                });
            }
        });
    });

    return { updatedScores, findings };
};

export const generateNextQuestion = (findings: string[]) => {
    if (findings.length === 0) {
        return "รบกวนช่วยเล่ารายละเอียดของอาการเพิ่มเติมหน่อยครับ เช่น เป็นมานานแค่ไหน หรือมีอาการอื่นร่วมด้วยไหม?";
    }
    
    if (findings.some(f => f.includes("inflammation"))) {
        return "ดูเหมือนจะมีอาการที่เกี่ยวข้องกับการอักเสบนะครับ ไม่ทราบว่ามีอาการปวดบวมแดงร้อนที่จุดไหนเป็นพิเศษไหมครับ?";
    }

    return "ได้รับข้อมูลแล้วครับ แล้วเรื่องการขับถ่ายหรือการนอนหลับในช่วงนี้เป็นอย่างไรบ้างครับ?";
};
