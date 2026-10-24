# EP 7: Patient Portal & Verified LINE OA Integration (พอร์ทัลคนไข้และการเชื่อมต่อ LINE OA แบบยืนยันตัวตน)

## 1. ภาพรวมโมดูล (Module Overview)
โมดูลนี้ทำหน้าที่เป็นระบบพอร์ทัลสำหรับผู้รับบริการ (Patient Portal) และช่องทางการสื่อสารสองทางผ่าน **LINE Official Account (LINE OA)** สำหรับ TSPI Clinic โดยออกแบบเน้นประสบการณ์ผู้ใช้บนอุปกรณ์พกพา (Mobile-First Wellness Aesthetic) ควบคู่กับมาตรฐานความปลอดภัยระดับสูงสุด:
1. **Patient Portal Dashboard:** แสดงผลสรุปสมดุล 12 โดเมนชีววิทยา ตารางนัดหมายแพทย์ และรายงานการแพทย์แม่นยำฉบับผู้ป่วย (Patient Edition)
2. **LINE OA Cryptographic Webhook:** ตรวจสอบลายเซ็น HMAC-SHA256 จาก LINE Developers แบบ Exact-byte และ Fail-Closed 100%
3. **One-Time Nonce Account Binding:** ระบบเชื่อมโยงบัญชีผู้ป่วย (HN) เข้ากับ LINE User ID ด้วยโทเค็นสุ่มความปลอดภัยสูงและหมดอายุตามเวลา ป้องกันการสวมรอยบัญชีและ Replay Attack
4. **Automated Clinical Flex Messages:** ส่งการ์ดแจ้งเตือนใบนัดหมายแพทย์ และการ์ดแจ้งเตือนเมื่อแพทย์ลงนามอนุมัติรายงานการแพทย์แม่นยำ

---

## 2. Security Pillars & Iron Rules ที่ควบคุม
- **Pillar 1 (Unified Identity & Session Architecture):** รองรับการเข้าสู่ระบบพอร์ทัลทั้งด้วยรหัสประจำตัวผู้ป่วย (HN) ควบคู่กับเบอร์โทรศัพท์ที่ลงทะเบียนไว้ หรือผ่านบัญชีผู้ใช้ Role Patient
- **Pillar 2 (Strict RBAC & IDOR Prevention):**
  - **Insecure Direct Object Reference (IDOR) Protection:** คนไข้แต่ละคนจะสามารถเข้าถึงได้เฉพาะข้อมูลและรายงานของตนเองเท่านั้น หากมีความพยายามเข้าดู URL รายงานของคนไข้ท่านอื่น ระบบจะตัดสิทธิ์ด้วย `403 Forbidden` ทันที และบันทึก `SUSPICIOUS_IDOR_ATTEMPT` ลงใน `AuditLog`
- **Pillar 8 (Immutable Audit Trail):**
  - บันทึกทุกเหตุการณ์: `PATIENT_PORTAL_LOGIN_SUCCESS`, `PATIENT_PORTAL_LOGIN_FAILED`, `PATIENT_PORTAL_REPORT_VIEW`, `LINE_USER_FOLLOW`, `LINE_ACCOUNT_BOUND`, `SUSPICIOUS_IDOR_ATTEMPT`
- **Pillar 14 (Zero-Trust External APIs - LINE Webhook Security):**
  - **Exact-byte HMAC Verification:** ตรวจสอบ `X-Line-Signature` ด้วย `hmac.compare_digest` เทียบกับ Raw Request Bytes ก่อน decode ป้องกัน Unicode Manipulation
  - **Fail-Closed Policy:**
    - หากเซิร์ฟเวอร์ไม่ได้ตั้งค่า `LINE_CHANNEL_SECRET` &rarr; คืนค่า `503 Service Unavailable`
    - หากขาด Signature หรือ Signature ผิดพลาด &rarr; คืนค่า `401 Unauthorized`
    - หาก Payload JSON ผิดโครงสร้าง &rarr; คืนค่า `400 Bad Request`
    - Probe events เปล่าจาก LINE Console &rarr; คืนค่า `200 OK`
- **Pillar 15 (Human-in-the-Loop & Safety Gate):**
  - **Draft Reports Isolation:** คนไข้สามารถเข้าดูได้เฉพาะรายงานที่แพทย์ลงนามอนุมัติแล้วเท่านั้น (`status in ['approved', 'released']`) หากรายงานยังอยู่ในสถานะร่าง (`draft`) ระบบจะตอบกลับ `404 Not Found` แก่คนไข้ เพื่อป้องกันการนำข้อมูลที่ยังไม่ผ่านการตรวจทานไปใช้อย่างเด็ดขาด

---

## 3. สถาปัตยกรรม & Data Flow

```
[LINE Official Account User]
       │
       ├─ (1) เพิ่มเพื่อน / ส่งข้อความเข้ามา (POST /line/webhook/) ──────────────────┐
       │                                                                             ▼
       │                                                                  [line_webhook_view]
       │                                                                             │
       │                                                                  [LineSecurity.verify_signature]
       │                                                                  (Exact HMAC-SHA256 Match)
       │                                                                             │
       │ ◀── ตอบกลับ Flex Message ต้อนรับ / ใบนัดหมาย ────────────────────────────────┤
       │                                                                             │
       ├─ (2) ขอผูกบัญชี HN กับ LINE (GET /patient/line/bind/)                      │
       │                                                                             ▼
       │                                                                  [PatientLinkingToken.create_token]
       │                                                                  (Generate One-Time Nonce)
       │                                                                             │
       ├─ (3) ยืนยันการผูกบัญชี (POST /patient/line/confirm/?token=...) ─────────────┤
       │                                                                             ▼
       │                                                                  [อัปเดต Patient.line_user_id]
       │                                                                  [ทำเครื่องหมาย Token ว่า is_used=True]
       │                                                                  [บันทึก AuditLog: LINE_ACCOUNT_BOUND]
       │
[Patient Web Browser / Mobile View]
       │
       ├─ (4) ล็อกอินเข้า Patient Portal (POST /patient/login/)
       │                                  │
       │                                  ▼
       │                    [ตรวจสอบ HN + Phone Match & สร้าง Session]
       │                                  │
       ├─ (5) หน้าแดชบอร์ดคนไข้ (GET /patient/dashboard/)
       │                                  │
       │                                  ▼
       │                    - แสดงภาพรวม 12 โดเมนชีววิทยา (Radar Chart)
       │                    - แสดงนัดหมายแพทย์ที่กำลังจะมาถึง
       │                    - แสดงเฉพาะรายงานที่สถานะ 'approved' (Pillar 15)
       │                                  │
       └─ (6) เปิดดูรายงานฉบับคนไข้ (GET /patient/reports/<id>/)
                                          │
                                          ▼
                            [ตรวจสอบ IDOR: analysis.patient == current_patient]
                            [บันทึก AuditLog: PATIENT_PORTAL_REPORT_VIEW]
                            [ส่งออก Patient-Edition View & PDF Download Link]
```

---

## 4. โครงสร้างไฟล์ที่สร้างและพัฒนา

| ตำแหน่งไฟล์ | คำอธิบายหน้าที่ |
|---|---|
| `apps/patients/models.py` | เพิ่มฟิลด์ `user` บน `Patient` และโมเดล `PatientLinkingToken` (One-Time Nonce & Expiry) |
| `apps/patients/line_service.py` | Service Layer: `LineSecurity` (HMAC verify), `LineFlexMessageBuilder` (Rich Cards), `LineMessagingService` |
| `apps/patients/views_line.py` | Controller: Webhook Handler (Fail-closed rules) และ Account Binding Confirmation Callback |
| `apps/patients/views_portal.py` | Controller: Patient Portal Login, Logout, Dashboard, Report Detail (IDOR safe), Appointments |
| `apps/portal_patient/urls.py` | กำหนด URL routing สำหรับ `portal_patient` ทั้งหมด พร้อม namespace |
| `config/urls.py` | เชื่อมต่อ URL endpoints ทั้งระดับพอร์ทัลและ Direct LINE Webhook |
| `templates/portal/base_portal.html` | โครงร่าง Mobile-First Wellness สำหรับคนไข้ พร้อม Sarabun typography |
| `templates/portal/portal_login.html` | หน้าล็อกอิน 2 รูปแบบ: HN+Phone หรือ Username/Password |
| `templates/portal/portal_dashboard.html` | แดชบอร์ดคนไข้: ข้อมูลส่วนตัว, สถานะ LINE, ใบนัดหมาย, เรดาร์ 12 โดเมน, รายงานอนุมัติแล้ว |
| `templates/portal/portal_report_detail.html` | หน้ารายงานการแพทย์แม่นยำฉบับคนไข้ พร้อมปุ่มดาวน์โหลด PDF |
| `templates/portal/portal_appointments.html` | รายการตารางนัดหมายแพทย์ทั้งหมดของผู้ป่วย |
| `templates/portal/portal_line_binding.html` | หน้าแนะนำและแสดงโทเค็นสำหรับเชื่อมต่อ LINE OA |
| `templates/portal/binding_confirm.html` | หน้าฟอร์มยืนยันการผูก LINE User ID กับ HN |
| `templates/portal/binding_result.html` | หน้าแสดงผลลัพธ์การเชื่อมต่อบัญชีสำเร็จหรือผิดพลาด |
| `apps/portal_patient/tests.py` | ชุดทดสอบ 14 ข้อ ครอบคลุม Webhook Security, Token Expiry, IDOR Prevention, และ Approved Gate |

---

## 5. ผลการทดสอบ (Verification Checklist)
- [x] ตรวจสอบ LINE Webhook Signature: คำขอไม่มี Signature หรือปลอมแปลงลายเซ็น คืนค่า `401 Unauthorized` ทันที
- [x] ตรวจสอบ Server Secret: หากไม่มี Secret คืนค่า `503 Service Unavailable` ทันที (Fail-Closed)
- [x] ตรวจสอบ Empty Probe Event: คืนค่า `200 OK`
- [x] ตรวจสอบ Malformed JSON: คืนค่า `400 Bad Request`
- [x] ตรวจสอบ One-Time Token Binding: โทเค็นใช้ได้ครั้งเดียว มีอายุจำกัด ป้องกันการผูก LINE ID ซ้ำซ้อนกับผู้ป่วยอื่น
- [x] ตรวจสอบ Patient Portal Login: ยืนยันตัวตนด้วย HN + เบอร์โทรศัพท์ และบันทึก AuditLog
- [x] ตรวจสอบ IDOR Prevention: ผู้ป่วยไม่สามารถเปิดดูรายงานของผู้อื่นได้ (`403 Forbidden` พร้อมบันทึก `SUSPICIOUS_IDOR_ATTEMPT`)
- [x] ตรวจสอบ Approved Gate (Pillar 15): รายงานสถานะร่าง (Draft) ถูกซ่อนจากพอร์ทัลคนไข้ 100% (`404 Not Found`)
- [x] ตรวจสอบการดาวน์โหลด PDF ฉบับคนไข้: รองรับทั้งแพทย์และคนไข้เจ้าของรายงาน พร้อมบันทึก AuditLog
- [x] ชุดทดสอบทั้งหมด 52/52 tests ผ่าน 100% (Pass Rate 100%)
