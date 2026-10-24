# Module: RAG Ingestion & Web AI-Intake Grounding

## ทำอะไร
- นำเข้าชุดข้อมูลคู่มือทางการแพทย์และ QA ทางคลินิกจำนวน **10,510 แถว** (`dataset.jsonl`) และเอกสาร **Foundational Medicine** เข้าสู่ตาราง `ClinicalKnowledgeSegment` ใน PostgreSQL
- พัฒนาระบบค้นหาเวกเตอร์ความเร็วสูงด้วยการเก็บข้อมูลในหน่วยความจำของ Django (NumPy Cached Search)
- เชื่อมต่อบริบทความรู้ (RAG Context) เข้ากับแชทบอทซักประวัติฝั่งคนไข้บนหน้าเว็บ (Web AI-Intake Chatbot)
- แก้ไขปัญหาบั๊ก Pagination Crash (`list.map is not a function`) บนหน้าต่างจัดการความรู้ของฝั่งแพทย์

## ทำไมถึงทำแบบนี้
- **Batch Embedding**: ข้อมูลจำนวน 10,000+ รายการ หากทำ Embedding ทีละรายการจะใช้เวลากว่า 50 นาทีและติด Rate Limit 429 การใช้ Batch API ของ Gemini (ส่งทีละ 100 ข้อความ) ช่วยประมวลผลข้อมูลจนเสร็จสิ้นได้ในเวลาไม่ถึง 2 นาที
- **NumPy Vectorized Search**: การวนลูปเปรียบเทียบ Cosine Similarity แบบเดิมใน Python บนข้อมูล 10,000+ ชิ้น จะทำให้ API หน่วงและช้ามาก (หลายร้อยมิลลิวินาที) การโหลดขึ้นหน่วยความจำ (RAM ~32MB) เป็น NumPy Array และคำนวณแบบ C-level Matrix Dot-product ช่วยลดระยะเวลาประมวลผลลงเหลือ **< 5ms**
- **Grounding Chatbot**: การดึงความรู้ RAG แนบเข้าไปใน System Prompt ก่อนยิงหา Groq (Llama 3.3) หรือ Gemini ช่วยควบคุมบอทให้อยู่ในกรอบข้อมูลจริง ป้องกันการวินิจฉัยชี้ขาดโรค และบังคับให้อิงเฉพาะการวิเคราะห์แกนชีวภาพ TSPI อย่างปลอดภัย

## โครงสร้างไฟล์
- **สคริปต์นำเข้าข้อมูล**: [seed_rag_dataset.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/seed_rag_dataset.py)
- **ตัวค้นหาหลังบ้าน (Django)**: [views_ai.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views_ai.py)
- **ระบบแชทหน้าบ้าน (Next.js)**: [route.ts](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/api/patient/chat/route.ts)
- **หน้าจัดการความรู้ฝั่งแพทย์**: [page.tsx](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/doctor/knowledge-rag/page.tsx)

## จุดที่ต้องระวัง
- **API Key Rate Limit**: แม้จะยิงเป็น Batch ละ 100 แถว แต่หากคีย์ติด Limit สคริปต์จะมีระบบ Fallback ค่อยๆ ทยอยรันแบบเดี่ยวจนสำเร็จ
- **Cache Invalidation**: ทุกครั้งที่มีการสร้าง/แก้ไข/ลบหัวข้อความรู้ผ่านหน้าจอแพทย์ ระบบจะทำการสั่ง Invalidate Cache (`RAGCacheManager.clear_cache()`) เสมอเพื่อบังคับให้ดึงข้อมูลใหม่ในรอบถัดไป
- **No Diagnosis**: ตัวแชทบอทจะถูกระบบ Grounding คุมไว้เสมอไม่ให้ทำการวินิจฉัยโรคเพื่อความปลอดภัยทางกฎหมายและการรักษาพยาบาล

## อ้างอิง
- [Gemini Embed Content API Document](https://ai.google.dev/gemini-api/docs/embeddings)
- [Django REST Framework Pagination Guide](https://www.django-rest-framework.org/api-guide/pagination/)
