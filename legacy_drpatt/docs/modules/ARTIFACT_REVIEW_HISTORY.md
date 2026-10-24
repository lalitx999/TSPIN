# Module: Artifact review history

## ทำอะไร

เพิ่ม ArtifactReviewEvent และ internal record_artifact_review service
เก็บ actor, เวลา, เหตุผล, decision และ exact artifact integrity hash
รองรับ REVIEWED_NOT_APPROVED, REQUEST_CHANGES, REJECT เท่านั้น
ไม่ถือเป็น physician signoff และไม่เปลี่ยน release readiness

## ทำไมถึงทำแบบนี้

ทางเลือกแก้สถานะเดิมทับง่ายกว่า แต่สูญเสียลำดับตรวจร่าง
ใช้ append-only events เพื่อเก็บประวัติและผูกฉบับที่ผู้ตรวจเห็น
การตรวจร่างแยกจากการยืนยันใบอนุญาตและการอนุมัติทางคลินิก

## โครงสร้างไฟล์

- backend/patients/models.py: ArtifactReviewEvent
- backend/patients/artifact_review.py: atomic service, permissions, artifact integrity
- backend/patients/migrations/0030_artifact_review_event.py
- backend/patients/tests_artifact_review.py

## จุดที่ต้องระวัง

มี API GET/POST /api/patients/{patient_id}/agentic-artifacts/{artifact_id}/reviews/
แต่ยังไม่มี UI สำหรับบันทึกนี้
ต้อง clinical reviewer access และ explicit add_artifactreviewevent/view_agenticartifact permissions
ไม่กำหนดผู้ยืนยันใบอนุญาตแทนคลินิก ไม่เปิด APPROVE หรือส่ง PDF/LINE
append-only บังคับระดับ Django model/queryset ไม่ใช่ DB trigger ป้องกัน raw SQL
การตรวจ historical artifact ไม่รับรองความสดของข้อมูลปัจจุบัน
การเรียกซ้ำสร้าง event ใหม่ ยังไม่มี idempotency contract สำหรับ HTTP retry
ผู้ใช้ต้อง review และรัน migration ใน staging/production เอง

## ผลตรวจ 19 October 2026

- ชุด review history + physician preflight + legacy release security: 21 tests ผ่าน
- SQLite test database เท่านั้น; ไม่ทดสอบ PostgreSQL concurrency
- makemigrations patients --check --dry-run: No changes detected
- ตรวจ consistency ของ migration history จริงไม่ได้ เพราะ postgres_server resolve ไม่ได้
- ไม่ deploy/push หรือรัน production migration

## API integration

POST รับเฉพาะ expected_artifact_hash, decision, reason (ไม่เกิน 4000 ตัวอักษร)
actor/เวลา/hash ที่บันทึกมาจาก server; ห้ามส่ง actor หรือ APPROVE จาก client
GET ต้อง view_artifactreviewevent + view_agenticartifact และ clinical reviewer access
POST ต้อง add_artifactreviewevent + view_agenticartifact และ clinical reviewer access
ตรวจ patient/artifact scope และ integrity; ไม่อนุญาต PATCH/DELETE
GET ส่งครั้งละไม่เกิน 50 รายการพร้อม next_before_id; หน้าถัดไปใช้ ?before_id=...
success response เป็น Cache-Control: no-store และ send_allowed=false
ไม่มี automatic retry/idempotency; ต้องอ่านประวัติก่อนลอง POST ซ้ำเมื่อ response ขาดหาย
ชุด API tests ครอบคลุม permission, scope, malformed payload, forged actor,
approval attempt, stale hash, pagination และ forbidden mutation

ผลชุดรวมหลังเชื่อม API: review history + physician preflight + release security +
agentic service ผ่าน 44 tests บน SQLite test database; ไม่มี production migration

## Discovery API

GET /api/patients/artifact-review-patients/?q=... ค้น HN/ชื่อ เฉพาะคนที่มีร่าง
ต้อง clinical reviewer + view_agenticartifact; ส่งชื่อ/HN/ID สูงสุด 50 และ truncated
GET /api/patients/{id}/artifact-review-list/ ส่ง metadata ร่างสูงสุด 50 ไม่ส่ง payload
cursor before_id เป็น UUID และเรียง UUID descending (ไม่ใช่ chronological order)
ทั้งสอง endpoint เป็น no-store และไม่ได้ยืนยัน integrity จนเปิด artifact ด้วย endpoint เดิม
