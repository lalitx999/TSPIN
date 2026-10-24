// Scripts for Firebase App and Messaging compatibility inside Web Service Worker
importScripts('https://www.gstatic.com/firebasejs/10.7.1/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.7.1/firebase-messaging-compat.js');

// ⚠️ ใส่ข้อมูล Firebase API Credentials ของคุณหมอที่นี่ครับ
// (สามารถเปิดดูค่าเหล่านี้ได้ในไฟล์ .env.local หรือก๊อปปี้จากหน้าเว็บ Firebase Console ของคุณหมอได้เลยครับ)
firebase.initializeApp({
  apiKey: "AIzaSyCFfGv2TmXw1ycM_zmPBgBEogmOQx2WQdA",
  authDomain: "diabesteslab.firebaseapp.com",
  projectId: "diabesteslab",
  storageBucket: "diabesteslab.firebasestorage.app",
  messagingSenderId: "772808065283",
  appId: "1:772808065283:web:d3e1bbe0dee9cfaa482936",
  measurementId: "G-F1L0FH83B1"
});

const messaging = firebase.messaging();

// ตรวจจับข้อความด่วนเมื่อคนไข้ปิดแอป/ล็อกหน้าจออยู่ (Background Notification Handler)
messaging.onBackgroundMessage((payload) => {
  console.log('[firebase-messaging-sw.js] ได้รับข้อความเบื้องหลัง: ', payload);

  const notificationTitle = payload.notification?.title || 'TSPI Clinic';
  const notificationOptions = {
    body: payload.notification?.body || 'คุณหมอได้ทำการอัปเดตผลการตรวจหรือเวชระเบียนใหม่ของคุณแล้ว',
    icon: '/logo_tspi.jpg', // นำรูปโลโก้มาแสดงประกอบการแจ้งเตือน
    badge: '/logo_tspi.jpg',
  };

  self.registration.showNotification(notificationTitle, notificationOptions);
});
