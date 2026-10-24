import './init-env';
import { genkit } from 'genkit';
import { googleAI } from '@genkit-ai/google-genai';
import { initializeApp } from 'firebase/app';
import { getFirestore, collection, getDocs, limit, query } from 'firebase/firestore';

const apiKey = process.env.GOOGLE_AI_API_KEY || process.env.GOOGLE_API_KEY;

// 1. Setup
const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID
};
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

const ai = genkit({
  plugins: [googleAI({ apiKey })],
  model: 'googleai/gemini-2.5-flash',
});

// ฟังก์ชันคำนวณ Cosine Similarity แบบ Manual
function cosineSimilarity(vecA: number[], vecB: number[]) {
  let dotProduct = 0;
  let normA = 0;
  let normB = 0;
  for (let i = 0; i < Math.min(vecA.length, vecB.length); i++) {
    dotProduct += vecA[i] * vecB[i];
    normA += vecA[i] * vecA[i];
    normB += vecB[i] * vecB[i];
  }
  return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
}

async function testRAG(userQuery: string) {
  console.log(`\n🔍 คำถามจากคุณหมอ: "${userQuery}"`);
  console.log('🧪 (โหมดคำนวณความแม่นยำสูง - Manual Mode)');
  console.log('---');

  try {
    // 2. แปลงคำถามเป็น Vector
    const embeddingResponse = await ai.embed({
      embedder: 'googleai/gemini-embedding-2',
      content: userQuery,
    });
    
    // @ts-ignore
    const rawVector = embeddingResponse[0]?.embedding || (embeddingResponse as any).values || (embeddingResponse.embedding && (embeddingResponse.embedding as any).values);
    const queryVector = Array.from(rawVector);

    // 3. ดึงข้อมูลจาก Firestore มาเปรียบเทียบ (Manual Retrieval)
    const colRef = collection(db, 'tspi_knowledge_vectors');
    const snapshot = await getDocs(query(colRef, limit(50))); // ดึงมา 50 ชุดมาหาตัวที่ใกล้ที่สุด
    
    if (snapshot.empty) {
      console.log('❌ ไม่พบข้อมูลในฐานข้อมูลครับ');
      return;
    }

    const matches = snapshot.docs.map(doc => {
      const data = doc.data();
      const docVector = data.embedding?._values || data.embedding?.values || data.embedding || [];
      const score = cosineSimilarity(queryVector, docVector);
      return { id: doc.id, ...data, score };
    });

    // เรียงลำดับตัวที่คะแนนสูงสุด
    matches.sort((a, b) => b.score - a.score);
    const topMatches = matches.slice(0, 2);

    console.log('✨ พบข้อมูลที่ใกล้เคียงที่สุด:');
    topMatches.forEach((m: any) => {
      console.log(`\n📄 Source: ${m.source} (Score: ${m.score.toFixed(4)})`);
      console.log(`📝 Content: ${m.text.substring(0, 200)}...`);
    });

    // 4. ให้ AI สรุปคำตอบ
    const context = topMatches.map((m: any) => m.text).join('\n\n');
    const { text } = await ai.generate({
      prompt: `คุณคือผู้ช่วยอัจฉริยะ TSPI Clinical Intelligence
      จงตอบคำถามโดยใช้ข้อมูลอ้างอิง (Context) ที่ให้มาเท่านั้น
      หากในข้อมูลไม่มีคำตอบที่ตรงเป๊ะ ให้พยายามสรุปจากข้อมูลที่ใกล้เคียงที่สุด
      
      Context: ${context}
      
      คำถาม: ${userQuery}`,
    });

    console.log('\n🤖 AI สรุปคำตอบ:');
    console.log(text);

  } catch (error: any) {
    console.error('❌ Error during RAG test:', error.message || error);
  }
}

testRAG("สรุปผลการรักษาเคสคุณสีมาพรให้หน่อยครับ");
