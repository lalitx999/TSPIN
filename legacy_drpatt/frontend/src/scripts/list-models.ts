import './init-env';

async function listModels() {
  console.log('📋 Fetching available models for your API Key...');

  const apiKey = process.env.GOOGLE_AI_API_KEY || process.env.GOOGLE_API_KEY;

  if (!apiKey) {
    console.error('❌ Missing API_KEY in .env.local');
    return;
  }

  const url = `https://generativelanguage.googleapis.com/v1beta/models?key=${apiKey}`;

  try {
    const response = await fetch(url);
    const data = await response.json();

    if (data.models) {
      console.log('\n✨ โมเดลที่หมอใช้งานได้ตอนนี้:');
      data.models.forEach((m: any) => {
        // กรองเอาเฉพาะรุ่นที่รองรับการสร้างเนื้อหา
        if (m.supportedGenerationMethods.includes('generateContent')) {
          console.log(`- ${m.name.replace('models/', '')} (${m.displayName})`);
        }
      });
      console.log('\n💡 ให้เลือกเอาชื่อข้างหน้า (เช่น gemini-1.5-flash) ไปใส่ในโค้ดได้เลยครับ');
    } else {
      console.error('❌ ไม่พบรายชื่อโมเดล:', JSON.stringify(data, null, 2));
    }
  } catch (error: any) {
    console.error('❌ Error:', error.message || error);
  }
}

listModels();
