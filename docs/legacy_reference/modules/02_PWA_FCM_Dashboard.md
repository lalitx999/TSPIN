# Module: PWA Patient Portal & FCM Integration

## ทำอะไร
- ยกระดับหน้าจอ **Patient Portal (แผงควบคุมคนไข้)** ให้ดีไซน์ออกมาเป็นสไตล์ Native PWA App บนอุปกรณ์พกพา
- ออกแบบ UI ใหม่โดยใช้หลัก **Noto Sans/Kanit Typography** ผสมกับสี Charcoal เข้ม `#282A29` บนพื้นหลังนุ่มตา `#F6F6F6` และการ์ดมนกลมสไตล์มินิมอล
- เพิ่มปุ่มนำทางด้านล่าง **Bottom Navigation Bar** เมื่อเปิดในมุมมอง Mobile View (ซ่อนเมนู Sidebar ของเดสก์ท็อป)
- เชื่อมต่อระบบแจ้งเตือนด่วน **Firebase Cloud Messaging (FCM)** บน Next.js Client-side คู่กับ Service Worker (`firebase-messaging-sw.js`) และบันทึก Token เข้า PostgreSQL แบบเรียลไทม์ผ่าน API `/api/auth/register-fcm-token/`
- เชื่อมการแจ้งเตือนหน้าจอหมอเวลากดเซฟผลแล็บจากฟิลด์ `patient.extra_data.fcm_token` เพื่อนำส่ง Push Notification ไปยังอุปกรณ์ของคนไข้โดยอัตโนมัติ
- เพิ่มแบบฟอร์มบันทึกค่าวัดระดับชีววิทยาหลัก 4 รายการ (น้ำตาลในเลือด FBS, น้ำตาลสะสม HbA1c, ไขมันเลว LDL, และดัชนีการอักเสบ CRP) เป็นภาษาไทย โดยรองรับการบันทึกประวัติสุขภาพลง `PatientHistory` สำหรับคำนวณแนวโน้มแนวสุขภาพ
- ปรับปรุงหน้าการตั้งค่าส่วนบุคคล (Settings Page) สไตล์เมนูตั้งค่า iOS:
  - รองรับการปรับเปลี่ยนรูปโพรไฟล์คนไข้ผ่าน PWA และบันทึกแบบ Base64 ลงฐานข้อมูล EMR
  - บล็อกฟิลด์ส่วนบุคคลสำคัญ เปิดให้คนไข้แก้ไขได้เฉพาะเบอร์โทรศัพท์ อีเมล และเบอร์ฉุกเฉิน
  - ระบบขอรับรหัส HN จริงถาวร โดยกำหนดให้ขอรับรหัสผ่าน API ได้เพียงครั้งเดียวในประวัติคนไข้เพื่อป้องกันข้อมูลระบบพ่วงกันสับสน
  - แบบฟอร์มเปลี่ยนรหัสผ่าน ทำงานควบคู่กับ API `change-password/` ในฝั่ง Django
  - ระบบยืนยันรหัส OTP 6 หลัก เพื่อจำลองการผูกและเปิดใช้งาน Google Two-Factor Authentication (2FA)
  - หน้าจอข้อมูลเวอร์ชันระบบ **TSPI V.1** และ **TSPI Brain V.1** พร้อมโลโก้ `pwa_logo.jpg` และข้อมูลทางลิขสิทธิ์

## ทำไมถึงทำแบบนี้
- **PWA แทน LINE Bot**: คนไข้จะได้รับประสบการณ์เสมือนกำลังเข้าใช้งานแอปพลิเคชันจริง ๆ บนโทรศัพท์มือถือแบบไม่ต้องติดตั้งผ่าน App Store/Play Store (ผ่านเมนู "Add to Home Screen" บน iOS/Android Safari & Chrome)
- **FCM Web Push API**: เลือกส่งตรงผ่าน Firebase Admin SDK ฝั่งเซิร์ฟเวอร์โดยตรงเพื่อหลีกเลี่ยงการเปิดเผย Private Key/Credentials สู่หน้าบ้าน (Client-side)
- **ทางเลือกอื่นที่เคยคิดไว้**: 
  - การลงทะเบียนเครื่องผ่าน Firebase CLI และ Firestore: ปัดตกเนื่องจากต้องการหลีกเลี่ยง N+1 Query และความยุ่งยากของการดึงข้อมูลข้าม Database (Firestore + PostgreSQL) จึงย้ายมาเก็บบน PostgreSQL EMR โดยตรงภายใต้ฟิลด์ JSON `extra_data`

## โครงสร้างไฟล์
- [dashboard/page.tsx](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/patient/dashboard/page.tsx): หน้าจอหลักคนไข้ แสดงตาราง Biomarkers 2x2, การ์ด Charcoal นัดหมาย, และแท็บระบบพหุมิติ รวมถึงเป็นตัวเริ่มเรียกการตั้งสิทธิ์ FCM และขอติดตั้งแอป PWA ต่อเนื่องกัน
- [settings/page.tsx](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/patient/settings/page.tsx): เมนูการตั้งค่าส่วนตัว ความปลอดภัย รหัสผ่าน และเกี่ยวกับระบบเวอร์ชันแอป
- [layout.tsx](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/patient/layout.tsx): โครงสร้าง Layout หลักสำหรับอุปกรณ์พกพา จัดวางสัดส่วน Bottom Safe Area และ Bottom Navigation Bar
- [firebase-messaging-sw.js](file:///Users/tanchonl/Downloads/drpatt/frontend/public/firebase-messaging-sw.js): พื้นหลัง Service Worker สแตนด์บายดักจับ Web Push Payload เวลาแอปปิดอยู่
- [messaging.ts](file:///Users/tanchonl/Downloads/drpatt/frontend/src/utils/firebase/messaging.ts): ฟังก์ชันสกัด FCM Token บน Client-side
- [admin.ts](file:///Users/tanchonl/Downloads/drpatt/frontend/src/utils/firebase/admin.ts): ตัวตั้งต้นสิทธิ์ผู้ดูแล Firebase Admin SDK ฝั่ง Server-side
- [route.ts](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/api/ai/send-fcm-notification/route.ts): API Endpoint ของเซิร์ฟเวอร์ Next.js ในการ Dispatch push notification
- [views.py](file:///Users/tanchonl/Downloads/drpatt/backend/accounts/views.py): ฟังก์ชัน `register_fcm_token` และ `change_password` บันทึกค่าลง EMR PostgreSQL
- [urls.py](file:///Users/tanchonl/Downloads/drpatt/backend/accounts/urls.py): เชื่อมโยง URL `/api/auth/register-fcm-token/` และ `/api/auth/change-password/`

## จุดที่ต้องระวัง
- **iOS PWA Support**: บนระบบปฏิบัติการ iOS (Safari) จะอนุญาตการเรียกขออนุญาต Web Push ก็ต่อเมื่อคนไข้ได้กดทำ "Add to Home Screen" และเปิดใช้งานแอปในโหมด Standalone เท่านั้น
- **การทดสอบซ้ำ (fcm_prompted / pwa_prompted)**: ค่าสิทธิ์จะถูกบันทึกลงใน Local Storage เพื่อป้องกันการแสดงกล่องซ้ำซาก หากต้องการแสดงป๊อปอัพสอบถามสิทธิ์การแจ้งเตือนและการติดตั้งใหม่อีกครั้งเพื่อทดสอบ ต้องทำการ Clear local storage ก่อน

## อ้างอิง
- [Firebase Cloud Messaging Web SDK Docs](https://firebase.google.com/docs/cloud-messaging/js/client)
- [Django REST Framework ViewSet & Action docs](https://www.django-rest-framework.org/api-guide/viewsets/)
