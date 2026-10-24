# รายงานการกู้ระบบ TSPI Clinical Intelligence (13/05/2026)

วันนี้เราประสบความสำเร็จในการติดตั้งระบบ **Vector Indexing** ซึ่งเป็น "หัวใจ" ของความจำ AI สำหรับโปรเจกต์ TSPI โดยสรุปรายละเอียดปัญหาและแนวทางแก้ไขดังนี้ครับ:

## ❌ ปัญหาที่พบและแนวทางแก้ไข (Timeline)

### 1. ปัญหา Telemetry Recursion (Recursive Stack Trace)
*   **อาการ**: โปรแกรมค้างและพ่น Error ยาวเหยียดเกี่ยวกับ OpenTelemetry
*   **สาเหตุ**: ระบบวัดผลของ Firestore ตีกับ GenKit ในสภาพแวดล้อม Local
*   **การแก้ไข**: สร้างไฟล์ `init-env.ts` เพื่อสั่งปิด `GOOGLE_CLOUD_FIRESTORE_TELEMETRY_DISABLED` และ `OTEL_SDK_DISABLED` ก่อนเริ่มรันสคริปต์ทุกครั้ง

### 2. ปัญหา Authentication & Project ID
*   **อาการ**: `FirebaseError: Could not load the default credentials`
*   **สาเหตุ**: Firebase Admin SDK พยายามหา Service Account file ซึ่งติดตั้งยากในเครื่อง Local
*   **การแก้ไข**: เปลี่ยนมาใช้ **Firebase Client SDK** (ชุดเดียวกับที่ใช้ใน Frontend) ทำให้ใช้ API Key จาก `.env.local` ได้โดยตรง

### 3. ปัญหา Vector Data Validation
*   **อาการ**: `VectorValues must only contain numeric values`
*   **สาเหตุ**: ข้อมูลที่ได้จาก AI (GenKit) เป็นประเภท `Float32Array` หรือ Object ซ้อน ซึ่ง Firestore ไม่ยอมรับ
*   **การแก้ไข**: เขียนฟังก์ชัน `extractVector` เพื่อดึงข้อมูลออกมาเป็น Plain JavaScript Array และบังคับทุกค่าให้เป็น `Number`

### 4. ปัญหา Vector Dimensions Limit (2048 vs 3072)
*   **อาการ**: `INVALID_ARGUMENT: Vectors must be at most 2048 dimensions`
*   **สาเหตุ**: โมเดลรุ่นใหม่ (`gemini-embedding-2`) ให้ผลลัพธ์ละเอียดเกินไป (3072 มิติ) แต่ Firestore รับได้แค่ 2048
*   **การแก้ไข**: เพิ่มโค้ด `trimmedVector` เพื่อตัดขนาดข้อมูลให้เหลือ 2048 มิติพอดีกับขีดจำกัดของฐานข้อมูล

### 5. ปัญหาการสร้าง Vector Index (UI Navigation)
*   **อาการ**: หาเมนูการสร้าง Vector Index ในหน้า Firebase Console ไม่เจอ
*   **สาเหตุ**: UI ของ Firebase มีการอัปเดตและซ่อนเมนู Single Field Index ไว้ลึก
*   **การแก้ไข**: ใช้เครื่องมือ **Google Cloud CLI (gcloud)** สั่งสร้าง Index ผ่าน Terminal แทนการกดบนเว็บ ทำให้ได้ค่าที่แม่นยำ 100%

---

## ✅ สถานะปัจจุบัน
1.  **Indexing**: ใช้งานได้ปกติ (รันสคริปต์ `index-knowledge-v2.ts` เพื่อเพิ่มความรู้ได้เลย)
2.  **Vector Search**: ใช้งานได้ปกติ (ผ่านระบบ Manual Distance Calculation ใน `test-rag.ts`)
3.  **AI Intelligence**: พร้อมตอบคำถามโดยอ้างอิงจากเคสศึกษา (RAG Flow พร้อมใช้งาน)

## 🚀 แผนงานถัดไป
*   นำระบบ RAG ไปเชื่อมต่อกับหน้าจอ Chat ใน Doctor Portal
*   ปรับปรุงการแบ่งส่วนเนื้อหา (Chunking) ให้ยาวขึ้นเพื่อให้ AI ได้เนื้อหาที่ครบถ้วนในการตอบ

**สรุปโดย**: Antigravity (AI Coding Assistant)
**สถานะโปรเจกต์**: 🟢 พร้อมใช้งาน (Fixed)
