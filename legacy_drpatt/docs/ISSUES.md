# สรุปจุดบกพร่องที่พบในระบบและข้อแนะนำการแก้ไข (Critique of Technical Issues & Vulnerabilities)

เอกสารฉบับนี้รวบรวมข้อผิดพลาดเชิงโครงสร้าง (Vulnerabilities/Bugs) ที่ตรวจพบจากการสแกนโปรเจกต์เชิงลึก เพื่อให้นักพัฒนานำไปปรับปรุงก่อนนำระบบขึ้นสภาพแวดล้อมจริง:

---

## 🔴 1. ความขัดแย้งของคำนิยามแกนชีววิทยา (Ontology Inconsistency)

* **ไฟล์ปัญหา**:
  * [frontend/src/app/api/ai/brain/route.ts](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/api/ai/brain/route.ts#L23) (มีสตริงนิยาม `AXES_DEFINITIONS`)
  * [frontend/src/app/api/doctor/lab-text-analyzer/route.ts](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/api/doctor/lab-text-analyzer/route.ts#L11)
  * [frontend/src/app/doctor/knowledge-rag/page.tsx](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/doctor/knowledge-rag/page.tsx#L23) (ตารางตัวเลือกระบบ RAG)
* **รายละเอียดปัญหา**:
  * นิยามของแกน `AXIS_11` และ `AXIS_12` ขัดแย้งกันระหว่าง หน้าบ้าน Next.js และ หลังบ้าน Django:
    * **หลังบ้าน Django (รวมถึง JSON Source)**: นิยามว่า `AXIS_11 = DNA Repair & Genomic Stability` และ `AXIS_12 = Epigenetic-Gene Regulation`
    * **หน้าบ้าน Next.js**: ฮาร์ดโค้ดเป็น `AXIS_11 = Thyroid Economy` (การคุมระบบไทรอยด์) และ `AXIS_12 = Adrenal Reserve` (กำลังสำรองต่อมหมวกไต)
* **ผลกระทบ**: ข้อมูลที่แพทย์วิเคราะห์โรคของคนไข้จะผิดเพี้ยนไปจากความจริง (เช่น คนไข้มี DNA เสียหายจากสารเคมีทำลายไต หลังบ้านประเมินคะแนนแกน 11 สูง แต่หน้าบ้านสรุปผลว่าเป็นโรคต่อมไทรอยด์ทำงานเสื่อม)
* **แนวทางแก้ไข**:
  * ให้ลบสตริง `AXES_DEFINITIONS` ที่ฝังอยู่ออกทั้งหมด
  * เปลี่ยนมาเรียกนำเข้าและอ้างอิงคำนิยามจากจุดตรวจสอบจุดเดียว (Single Source of Truth) คือไฟล์ [39_last_x.json](file:///Users/tanchonl/Downloads/drpatt/frontend/src/data/39_last_x.json) ผ่านฟังก์ชัน `precisionEngine.getAxisDef(id)` หรือเรียก API ขอข้อมูลจากฝั่ง Backend

---

## 🔴 2. การฮาร์ดโค้ด URL โลคัลในโค้ดฝั่ง Client (Hardcoded Localhost API URLs)

* **ไฟล์ปัญหา**:
  * [frontend/src/app/patient/login/page.tsx](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/patient/login/page.tsx#L48)
  * [frontend/src/app/patient/settings/page.tsx](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/patient/settings/page.tsx#L133)
  * [frontend/src/app/patient/appointments/page.tsx](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/patient/appointments/page.tsx#L33)
* **รายละเอียดปัญหา**:
  * โค้ดส่วนนี้รันอยู่ในเบราว์เซอร์ของคนไข้จริง แต่มีการเขียน URL แบบฝังคงที่ เช่น `fetch("http://localhost:8000/api/auth/me/")`
* **ผลกระทบ**: เมื่อคนไข้เข้าใช้เว็บผ่านโทรศัพท์มือถือ เบราว์เซอร์จะพยายามค้นหา API ที่ตัวเครื่องผู้ใช้เอง (`localhost`) ส่งผลให้เบราว์เซอร์รายงานล้มเหลวเชื่อมต่อระบบ (Connection Refused) ไม่สามารถล็อกอินหรือดึงโปรไฟล์ตัวเองได้
* **แนวทางแก้ไข**:
  * ดึงค่าตัวแปรสภาพแวดล้อมที่ตั้งไว้ในระบบมาใช้งานเสมอ:
    ```typescript
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const res = await fetch(`${apiBase}/api/auth/me/`, { ... });
    ```

---

## 🟡 3. เส้นทางไดเรกทอรีคงที่บนเครื่องนักพัฒนาหลังบ้าน (Hardcoded Server Absolute Paths)

* **ไฟล์ปัญหา**:
  * [backend/patients/views.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views.py#L190) (พาธน้ำหนักสมองกล `weights_path`)
  * [backend/patients/views_ai.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views_ai.py#L459) (พาธไฟล์ข้อมูลแกน)
  * [backend/patients/tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py#L73) (พาธสมุนไพร)
* **รายละเอียดปัญหา**:
  * มีการป้อนพาธของตำแหน่งผู้ใช้ในเครื่อง Mac ของนักพัฒนาแบบสมบูรณ์ เช่น `/Users/tanchonl/Downloads/drpatt/...` เพื่อเปิดอ่านไฟล์
* **ผลกระทบ**: หากนำไปติดตั้งรันบนเครื่องคอมพิวเตอร์เครื่องอื่น หรือบนคลาวด์โปรดักชัน แอปจะขัดข้องและหยุดทำงานทันทีเพราะหาที่อยู่ไดเรกทอรีนี้ไม่พบ
* **แนวทางแก้ไข**:
  * นำเข้า settings และทำที่อยู่สัมพัทธ์อ้างอิงตำแหน่งติดตั้งโปรเจกต์จริง:
    ```python
    from django.conf import settings
    weights_path = os.path.join(settings.BASE_DIR, '..', 'data', 'tspi_brain_weights.json')
    ```

---

## 🟡 4. ความเสี่ยงการล่มจากข้อความไม่ใช่ตัวเลขในขั้นตอนฝึกฝน AI (OLS Ridge Float Casting Crash Risk)

* **ไฟล์ปัญหา**:
  * [backend/patients/views_ai.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views_ai.py#L936) (ในฟังก์ชัน `train_brain_model`)
* **รายละเอียดปัญหา**:
  * โค้ดดึงประวัติแล็บดิบของเคสมาฝึกฝนโมเดลจำลอง แล้วเรียก `float(...)` ตรงๆ เพื่อสร้างค่า Input
* **ผลกระทบ**: ถ้ามีข้อมูลที่แพทย์บันทึกข้อความผิดพลาดเป็นสตริงคำอธิบาย (เช่น ป้อนว่า `"90 mg/dL"` แทนที่จะเป็นตัวเลข `"90"`) ระบบ OLS Ridge จะแจ้งขัดข้องด้วยข้อผิดพลาด `ValueError` และทำระบบประมวลผลล่ม 500 ทันที
* **แนวทางแก้ไข**:
  * ปรับแต่งด้วยการครอบตัวดักข้อผิดพลาดสำหรับการแปลงทศนิยม:
    ```python
    def safe_float(val, default):
        try:
            if val not in (None, ""):
                return float(val)
        except ValueError:
            pass
        return default
    ```

---

## 🟡 5. ระบบคำนวณและประเมินโรคทับซ้อนกันสองแห่ง (Duplicate CDSS Engine Logic)

* **ไฟล์ปัญหา**:
  * หลังบ้าน: [backend/patients/tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py)
  * หน้าบ้าน: [frontend/src/lib/tspi-engine.ts](file:///Users/tanchonl/Downloads/drpatt/frontend/src/lib/tspi-engine.ts)
* **รายละเอียดปัญหา**:
  * ตรรกะการประเมินคะแนน NSS/SPS การจับคู่โมดูลยาสมุนไพร และการคัดกรองความปลอดภัย (Safety Gate) มีโค้ดสองภาษาคู่ขนานกัน
* **ผลกระทบ**: เพิ่มอัตราเสี่ยงที่จะอัปเดตเกณฑ์คะแนนหรือเพิ่มเกรดยาสมุนไพรไม่ตรงกัน (Desynchronization) ในอนาคต ทำให้ข้อมูลในหน้าจอรายงานเบราว์เซอร์ไม่ตรงกับข้อมูลในเอกสาร PDF
* **แนวทางแก้ไข**:
  * ยกเลิกตรรกะประเมินคะแนนใน Next.js (`tspi-engine.ts`)
  * กำหนดให้ Next.js เรียก API ร้องขอคำนวณจากหลังบ้าน Django แหล่งเดียว แล้วนำผลลัพธ์ JSON ที่คำนวณเสร็จสิ้นไปพรีวิวแสดงผลเท่านั้น
