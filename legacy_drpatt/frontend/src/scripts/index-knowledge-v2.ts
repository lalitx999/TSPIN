import './init-env';
import fs from 'fs';
import path from 'path';
import { genkit } from 'genkit';
import { googleAI } from '@genkit-ai/google-genai';
import { initializeApp } from 'firebase/app';
import { getFirestore, collection, addDoc, serverTimestamp, vector } from 'firebase/firestore';

const apiKey = process.env.GOOGLE_AI_API_KEY || process.env.GOOGLE_API_KEY;

if (!apiKey) {
  console.error('❌ Error: API Key not found in .env.local');
  process.exit(1);
}

// 1. Initialize Firebase Client SDK
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

// 2. Initialize GenKit
const ai = genkit({
  plugins: [googleAI({ apiKey })],
  model: 'googleai/gemini-2.0-flash',
});

const embedder = 'googleai/gemini-embedding-001';
const collectionName = 'tspi_knowledge_vectors';

// ฟังก์ชันสำหรับดึง Vector ออกมาให้ถูกต้อง (Robust Vector Extraction)
function extractVector(data: any): number[] | null {
  if (!data) return null;

  // Case 1: Array of { embedding: [...] } — GenKit ai.embed() returns this structure
  if (Array.isArray(data) && data.length > 0 && data[0].embedding) {
    const emb = data[0].embedding;
    if (Array.isArray(emb)) {
      const nums = emb.map(v => Number(v)).filter(v => !isNaN(v));
      return nums.length > 0 ? nums : null;
    }
  }

  // Case 2: Direct number[] (some GenKit versions)
  if (Array.isArray(data)) {
    const nums = data.map(v => Number(v)).filter(v => !isNaN(v));
    return nums.length > 0 ? nums : null;
  }

  // Case 3: Nested structures like { values: [...] } or { embedding: { values: [...] } }
  const raw = data.values || (data.embedding && data.embedding.values) || data.embedding;

  if (Array.isArray(raw)) {
    const nums = raw.map(v => Number(v)).filter(v => !isNaN(v));
    return nums.length > 0 ? nums : null;
  }

  return null;
}

async function runIndexing() {
  console.log('🚀 Starting TSPI Knowledge Indexing (v2.1 Robust Mode)...');

  const dataDir = path.resolve(process.cwd(), '../data');
  const filesToIndex = [
    { name: 'C เคสคุณสีมาพร', type: 'CaseStudy' },
    { name: 'เพิ่มเติมระบบ AI', type: 'SOP' },
  ];

  for (const fileInfo of filesToIndex) {
    const filePath = path.join(dataDir, fileInfo.name);
    if (!fs.existsSync(filePath)) {
      console.warn(`⚠️ File not found: ${filePath}`);
      continue;
    }

    console.log(`Processing: ${fileInfo.name}...`);
    const content = fs.readFileSync(filePath, 'utf-8');
    const chunks = content.split('\n\n').filter(c => c.trim().length > 50);

    for (const chunk of chunks) {
      try {
        await new Promise(resolve => setTimeout(resolve, 1000));

        const embeddingResponse = await ai.embed({
          embedder: embedder,
          content: chunk,
        });

        const numericVector = extractVector(embeddingResponse);

        if (!numericVector || numericVector.length === 0) {
          console.error('❌ Failed to extract numeric vector from response:', JSON.stringify(embeddingResponse).substring(0, 100));
          continue;
        }

        // Firestore vector search supports max 2048 dimensions
        // Truncate if needed (e.g., text-embedding-004 outputs 3072)
        const MAX_DIM = 2048;
        const trimmedVector = numericVector.length > MAX_DIM
          ? numericVector.slice(0, MAX_DIM)
          : numericVector;

        console.log(`✅ Vector Extracted: [${trimmedVector.slice(0, 3)}...] (Dim: ${trimmedVector.length})`);

        await addDoc(collection(db, collectionName), {
          text: chunk,
          embedding: vector(trimmedVector),
          source: fileInfo.name,
          type: fileInfo.type,
          indexedAt: serverTimestamp(),
        });

        console.log(`✨ Saved chunk to Firestore`);
      } catch (error) {
        console.error(`❌ Error in chunk processing:`, error);
      }
    }
  }
  console.log('🏁 Indexing complete.');
}

runIndexing().catch(console.error);
