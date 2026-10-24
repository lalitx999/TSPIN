import fs from 'fs';
import path from 'path';
import dotenv from 'dotenv';
import { indexDataFlow } from '../lib/rag-flow';

// Load environment variables from .env.local
dotenv.config({ path: path.resolve(__dirname, '../../.env.local') });

const dataDir = path.resolve(__dirname, '../../../data');

const filesToIndex = [
  { name: 'C เคสคุณสีมาพร', type: 'CaseStudy' },
  { name: 'เพิ่มเติมระบบ AI', type: 'SOP' },
  { name: '36 แกนกลไกชีววิทยา (TSPI Mechanistic Axes) พร้อมแกนย่อย ABC และคำอธิบายแบบสรุปกระชับครับ​.txt', type: 'SOP' },
  { name: 'prompt 20 บท คำสั่งสำหรับออกรายงานสำหรับแพทย์และผู้ป่วยใน tspi platform', type: 'SOP' },
];

async function runIndexing() {
  console.log('🚀 Starting TSPI Knowledge Indexing...');
  
  for (const fileInfo of filesToIndex) {
    const filePath = path.join(dataDir, fileInfo.name);
    if (!fs.existsSync(filePath)) {
      console.warn(`⚠️ File not found: ${filePath}`);
      continue;
    }
    
    console.log(`Processing: ${fileInfo.name}...`);
    const content = fs.readFileSync(filePath, 'utf-8');
    
    try {
      const result = await indexDataFlow({
        text: content,
        source: fileInfo.name,
        type: fileInfo.type as any
      });
      console.log(`✅ Indexed ${result.chunksIndexed} chunks from ${fileInfo.name}`);
    } catch (error) {
      console.error(`❌ Error indexing ${fileInfo.name}:`, error);
    }
  }
  
  console.log('🏁 Indexing completed.');
}

runIndexing();
