# แผนงานปรับปรุงระบบ (Project TODO List)

ตารางแผนงานปรับปรุงระบบ Dr. Pat เรียงลำดับความสำคัญจากเร่งด่วนที่สุดไปจนถึงคุณสมบัติเพิ่มเติมทั่วไป:

---

## 📅 ระยะที่ 1: การแก้ไขข้อผิดพลาดวิกฤต (ความปลอดภัยและเสถียรภาพ) — **ต้องดำเนินการทันที**

* [ ] **แก้ไขนิยามแกนชีววิทยาให้ตรงกัน (Ontology Mismatch)**
  * **เป้าหมาย**: ลบสตริง `AXES_DEFINITIONS` ใน [brain/route.ts](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/api/ai/brain/route.ts#L19) และ [lab-text-analyzer/route.ts](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/api/doctor/lab-text-analyzer/route.ts#L7)
  * **แนวทาง**: นำข้อมูลคำอธิบายจาก [39_last_x.json](file:///Users/tanchonl/Downloads/drpatt/frontend/src/data/39_last_x.json) ไปโหลดใช้งานในการสตรีม LLM เพื่อความสอดคล้องทางการแพทย์
* [ ] **ย้ายพาธดิเรกทอรีแบบฮาร์ดโค้ดเป็น Relative Path (Django Paths)**
  * **เป้าหมาย**: แก้ไขพาธใน [views.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views.py#L190) และ [tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py#L73) ให้พึ่งพิงตำแหน่ง `settings.BASE_DIR`
* [ ] **เปลี่ยนการเรียก API จาก `localhost:8000` เป็นตัวแปรสภาพแวดล้อม (Frontend API URLs)**
  * **เป้าหมาย**: เปลี่ยนเส้นทาง Fetch ในหน้า [login/page.tsx](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/patient/login/page.tsx#L48) และ [settings/page.tsx](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/patient/settings/page.tsx#L133) ให้ดึงค่าจากตัวแปร `process.env.NEXT_PUBLIC_API_URL`
* [ ] **เพิ่มการตรวจสอบค่าความปลอดภัยในขั้นตอนฝึกฝนสมองกล (Float Cast protection)**
  * **เป้าหมาย**: ครอบตัวแปลงค่าแล็บประวัติใน `train_brain_model` ด้วย `try/except` ดักจับกรณีผู้ใช้ใส่หน่วยตรวจวัดหรือข้อมูลผิดพลาดเข้ามา

---

## 📅 ระยะที่ 2: ปรับปรุงประสิทธิภาพของระบบ (Optimization & Refactoring)

* [ ] **รวมศูนย์ตรรกะการประเมินคะแนนแกนและจับคู่สมุนไพร (Scoring Engine Consolidation)**
  * **เป้าหมาย**: ลบตรรกะคำนวณในหน้าบ้าน Next.js และอิงคำตอบประเมินจากฝั่ง Django REST API เป็นหลักเพื่อไม่ให้คำนวณไม่ตรงกัน
* [ ] **ปรับปรุงประสิทธิภาพประวัติตารางคนไข้หน้าแรกแพทย์ (List Lightweight Pagination)**
  * **เป้าหมาย**: ขยายความสามารถการกรองผลตรวจ N+1 Queries ในหน้ารายงานของระบบให้ทำงานผ่าน Query ที่เหมาะสมที่สุด
* [ ] **เพิ่มดักจับเหตุผลการตรวจ (Audit Log Compliance)**
  * **เป้าหมาย**: บันทึกข้อมูล Audit Log สำหรับส่วนการเข้าถึงประวัติเวชระเบียนของผู้ป่วยผ่านบอท LINE OA ให้ปลอดภัยตามกฎกระทรวงสาธารณสุขและ พ.ร.บ. คุ้มครองข้อมูลส่วนบุคคล (PDPA)

---

## 📅 ระยะที่ 3: การเพิ่มขีดความสามารถใหม่ (Future Feature Extensions)

* [ ] **พัฒนาแผนภูมิแสดงแนวโน้มสุขภาพคนไข้ (Lab Trend Dashboard Widget)**
  * **เป้าหมาย**: เพิ่มกราฟแสดงประวัติความเปลี่ยนแปลงย้อนหลังของค่า HbA1c, FBS, LDL เพื่อประเมินผลการรักษาในหน้าหลักแดชบอร์ด
* [ ] **ทำหน้าจอสำหรับแพทย์ปรับปรุงเกณฑ์คัดกรองสัญญาณภัยของโรคศีรษะ (Headache Red-Flags Registry Editor)**
  * **เป้าหมาย**: สร้างหน้าตัวเลือกเพื่อให้แพทย์กำหนดอาการอันตรายในหมวด Red-Flags ของคลินิกได้เองแทนการใช้เกณฑ์ดิบในโค้ด
* [ ] **ทำระบบประเมินค่าความแม่นยำของโมเดลสมองกลจำลอง (AI Brain Training Metrics)**
  * **เป้าหมาย**: เพิ่มกราฟวัดค่าประสิทธิภาพ R-squared หรือ Mean Absolute Error (MAE) ของ OLS Ridge ในหน้าจัดการระบบ AI
