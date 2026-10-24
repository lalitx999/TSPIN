# Module: Audit Trail

## ทำอะไร

เก็บ audit event ของ HTTP traffic และ event สำคัญด้านบัญชี เช่น สมัครสมาชิก, login, ลงทะเบียนแพทย์ และเปลี่ยนรหัสผ่าน ใน `patient_audit_logs`.

## ข้อมูลที่เก็บ

เวลา, actor, target ที่ระบุจาก URL, action/event type, IP, HTTP method/path/status, user-agent, request ID และรายชื่อ query parameter เท่านั้น

## ความเป็นส่วนตัว

ไม่บันทึก request body, password, JWT/refresh token, cookies หรือ clinical payload. IP และ user-agent เป็นข้อมูลส่วนบุคคล ต้องกำหนดผู้เข้าถึงและ retention policy ก่อน production.

## R0

Migration `0020_expand_audit_log.py` ขยายตาราง log เดิมโดยไม่ลบข้อมูล.
