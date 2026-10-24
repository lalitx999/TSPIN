const { GoogleGenerativeAI } = require("@google/generative-ai");
const dotenv = require("dotenv");
const path = require("path");

// Load env
dotenv.config({ path: path.join(__dirname, "../.env.local") });

const genAI = new GoogleGenerativeAI(process.env.GOOGLE_AI_API_KEY || "");

const AXES_DEFINITIONS = `
1: Systemic Inflammatory Load, 2: Immune Homeostasis, 3: Viral/Bacterial Governance, 
4: Detoxification, 5: Biotransformation, 6: Oxidative Burden,
7: Glycemic Regulation, 8: Lipid Dynamics, 9: Energy/Mitochondrial Health,
10: Hormonal Balance, 11: Thyroid Economy, 12: Adrenal Reserve,
13: Gut Barrier Integrity, 14: Digestive Efficiency, 15: Microbiome Ecosystem,
16: Neuro-Chemical Balance, 17: Cognitive Reserve, 18: Sleep/Circadian Biology,
19: Cardiovascular Strength, 20: Microvascular Flow, 21: Endothelial Health,
22: Respiratory Dynamics, 23: Renal/Fluid Balance, 24: Hepatic Architecture,
25: Musculoskeletal Integrity, 26: Bone Density/Mineral, 27: Connective Tissue,
28: Skin Barrier, 29: Visual Health, 30: Auditory Function,
31: Lymphatic Drainage, 32: Cellular Cycle/Autophagy, 33: Epigenetic Resilience,
34: Longevity/Senescence, 35: Stem Cell Vitality, 36: Bio-Energetic Flow,
37: Clinical Context A, 38: Clinical Context B, 39: Precision Outcome
`.trim();

async function testHandler() {
  try {
    const patientId = "Mn98e7NhY5WlgD6nEaFROqJbQJs2";
    const clinicalContext = {
      patientName: "Test Patient",
      hn: "HN12345",
      axes: { "AXIS_1": 65, "AXIS_2": 45 },
      weights: { "AXIS_1": 1.0, "AXIS_2": 1.0 }
    };
    const reqSystemInstruction = `คุณคือ 'TSPI™ Systems Biology Intelligence' ปัญญาประดิษฐ์ทางการแพทย์ระดับสูงของคณะแพทยศาสตร์คลินิก 
    โปรดประเมินแผนผังดิจิทัลทวิน (39-Axis Digital Twin) ของคนไข้รายนี้ตามหลักวิชาชีพแพทย์
    1. ตอบเป็นภาษาไทยระดับเป็นทางการ (Professional Clinical Thai) เพื่อให้แพทย์อ่านประเมินก่อนเข้าปรึกษา
    2. ระบุหัวข้อหลักอย่างชัดเจน: [Clinical Impression], [Mechanistic Pathophysiology Pathways], [Biomarker Burden Interlinkage]
    3. นำเสนอโครงสร้างการรักษาเป็นลำดับขั้นตอน (Step-by-step therapeutic advice)
    4. ปิดท้ายบทวิเคราะห์ด้วย JSON block เสมอ เพื่อแนะนำการคาลิเบรตค่าแกนชีวภาพตามโครงสร้างต่อไปนี้เท่านั้น:
    :::BIO_UPDATE:::
    {
      "axes": [
        { "axis_id": "AXIS_X", "severity": 50, "insight": "เหตุผลเชิงลึกทางสรีรวิทยาการแพทย์" }
      ]
    }
    :::`;

    const baseMessages = [{ role: "user", content: "เริ่มการวิเคราะห์คนไข้" }];
    const patientContext = `
[DIRECT CLINICAL CONTEXT]
Patient: ${clinicalContext.patientName} (HN: ${clinicalContext.hn})
Symptoms: ${clinicalContext.symptoms || "N/A"}
Current Axes: ${JSON.stringify(clinicalContext.axes || {})}
    `.trim();

    const systemInstruction = `You are the TSPI Precision Medicine AI Specialist. 
    Analyze using the 39-Axis Framework: ${AXES_DEFINITIONS}
    
    DIRECTIVES:
    1. PROFESSIONAL THAI ONLY.
    2. NETWORK EFFECT ANALYSIS.
    3. NO HALLUCINATIONS.
    
    ${reqSystemInstruction}
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

    console.log("Using modelName: gemini-2.5-flash");
    const model = genAI.getGenerativeModel({ 
      model: "gemini-2.5-flash",
      systemInstruction: systemInstruction
    });

    const lastMsg = enhancedMessages[enhancedMessages.length - 1].content;
    console.log("Sending prompt to Gemini...");
    const result = await model.generateContent(lastMsg);
    const res = await result.response;
    const responseContent = res.text();
    console.log("SUCCESS! Response content length:", responseContent.length);
    console.log("Response starts with:\n", responseContent.substring(0, 500));
  } catch (error) {
    console.error("FAILED with error:", error);
  }
}

testHandler();
