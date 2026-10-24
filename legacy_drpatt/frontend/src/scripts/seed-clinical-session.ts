import { initializeApp } from "firebase/app";
import { getFirestore, doc, setDoc, serverTimestamp } from "firebase/firestore";
import * as dotenv from "dotenv";

// โหลด .env.local เพื่อใช้ public keys 
dotenv.config({ path: ".env.local" });

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

// ใช้ Client SDK แทน Admin SDK เพื่อหลีกเลี่ยงปัญหา Private Key หาย
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

async function seed() {
  const sessionId = "TEST_SESSION_001";
  console.log("🌱 กำลังบันทึกข้อมูลของจริงลง Firestore ที่ Collection: questionnaireSessions ...");

  const sessionData = {
    patientId: "PAT_DEMO_999",
    createdAt: serverTimestamp(),
    status: "pending",
    questions: [
      {
        id: "core_sleep_01",
        text: "สัปดาห์ที่ผ่านมา คุณภาพการนอนหลับของคุณเป็นอย่างไร?",
        type: "slider_0_10",
        linkedAxes: ["Sleep/Circadian Biology"],
        isAiGenerated: false
      },
      {
        id: "core_energy_01",
        text: "ระดับพลังงานของคุณในระหว่างวัน อยู่ในระดับใด?",
        type: "slider_0_10",
        linkedAxes: ["Mitochondrial Function"],
        isAiGenerated: false
      },
      {
        id: "ai_joint_pain_01",
        text: "เมื่อสัปดาห์ก่อนคุณมีอาการปวดข้อเข่า สัปดาห์นี้ความปวดลดลงบ้างไหม?",
        type: "slider_0_10",
        linkedAxes: ["Inflammatory Load"],
        isAiGenerated: true,
        aiContext: "ติดตามอาการปวดข้อเข่าจากสัปดาห์ก่อน"
      }
    ]
  };

  try {
    await setDoc(doc(db, "questionnaireSessions", sessionId), sessionData);
    console.log("✅ Seed completed. บันทึกลงฐานข้อมูลจริงแล้ว!");
    console.log("👉 คุณสามารถเปิดทดสอบ UI ได้ที่ URL: http://localhost:3000/patient/checkin/TEST_SESSION_001");
    process.exit(0);
  } catch (err) {
    console.error("❌ Error:", err);
    process.exit(1);
  }
}

seed();
