import './init-env';

async function createIndex() {
  console.log('🏗️  Attempting to CREATE Vector Index via REST API...');

  const projectId = process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID;
  const apiKey = process.env.GOOGLE_AI_API_KEY || process.env.GOOGLE_API_KEY;

  if (!projectId || !apiKey) {
    console.error('❌ Missing PROJECT_ID or API_KEY in .env.local');
    return;
  }

  // ตัวอย่างโครงสร้าง Index สำหรับ Vector
  const indexConfig = {
    queryScope: "COLLECTION",
    fields: [
      {
        fieldPath: "embedding",
        vectorConfig: {
          dimension: 2048,
          flat: {}
        }
      }
    ]
  };

  const url = `https://firestore.googleapis.com/v1beta1/projects/${projectId}/databases/(default)/collectionGroups/tspi_knowledge_vectors/indexes?key=${apiKey}`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(indexConfig),
    });

    const data = await response.json();

    if (response.ok) {
      console.log('✅ ส่งคำสั่งสร้าง Index สำเร็จแล้วครับ!');
      console.log('สถานะ:', data.name);
      console.log('กรุณารอระบบประมวลผลประมาณ 5-10 นาทีนะครับ');
    } else {
      console.error('❌ ไม่สามารถสร้างผ่าน API ได้โดยตรง (อาจติดเรื่องสิทธิ์ OAuth):');
      console.error(JSON.stringify(data, null, 2));
      console.log('\n💡 แนะนำให้คุณหมอใช้คำสั่ง gcloud ในเครื่อง (ถ้ามี) หรือคลิกลิงก์จากสคริปต์ trigger-index ตัวก่อนหน้านี้ครับ');
    }
  } catch (error: any) {
    console.error('❌ Error:', error.message || error);
  }
}

createIndex();
