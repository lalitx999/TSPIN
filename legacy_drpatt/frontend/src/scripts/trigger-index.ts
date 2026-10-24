import './init-env';
import { initializeApp } from 'firebase/app';
import { getFirestore, collection, query, where, orderBy, getDocs } from 'firebase/firestore';

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

async function triggerIndex() {
  console.log('🔍 Triggering Composite Index link (to find the menu)...');
  
  const colRef = collection(db, 'tspi_knowledge_vectors');
  
  try {
    // สร้าง Query ที่ "ต้องมี Index" (Composite)
    // วิธีนี้จะทำให้ Firebase คายลิงก์ "Create Index" ออกมาใน Error แน่นอนครับ
    const q = query(
      colRef,
      where('type', '==', 'CaseStudy'),
      orderBy('indexedAt', 'desc')
    );
    
    await getDocs(q);
    console.log('✅ Index already exists!');
  } catch (error: any) {
    if (error.message && error.message.includes('https://console.firebase.google.com')) {
      console.log('\n📌 เจอลิงก์แล้วครับ! คลิกตัวนี้เลย:');
      const link = error.message.match(/https:\/\/console\.firebase\.google\.com[^\s]*/);
      if (link) {
        console.log('\n🔗 ' + link[0] + '\n');
        console.log('พอกดเข้าไปแล้ว คุณหมอจะเห็นหน้าสร้าง Index ให้สังเกตที่แถบด้านบนจะมีคำว่า "Single field" ให้คลิกตรงนั้นครับ!');
      } else {
        console.log(error.message);
      }
    } else {
      console.error('❌ Error:', error.message || error);
    }
  }
}

triggerIndex();
