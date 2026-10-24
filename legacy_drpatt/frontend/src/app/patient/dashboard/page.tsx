"use client";

import { useState, useEffect } from "react";
import {
   Activity,
   Calendar,
   Clock,
   Info,
   Moon,
   Scale,
   User as UserIcon,
   AlertCircle,
   ClipboardList,
   Heart,
   Droplet,
   Shield,
   Sparkles,
   Bell,
   FileText,
   Zap,
   History,
   Loader2,
   ChevronRight,
   LogOut,
   CheckCircle2,
   Download,
   BookOpen
} from "lucide-react";
import Link from "next/link";
import Swal from "sweetalert2";
import { getFCMToken } from "@/utils/pwa/messaging";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// 6 Dimensions Configuration
const DIMENSIONS = [
   {
      id: 1,
      name: "ภูมิคุ้มกัน & การอักเสบ",
      englishName: "Immune & Inflammation",
      icon: Shield,
      color: "#0A5C8E",
      axes: [1, 2, 3, 4],
      description: "ความแข็งแกร่งของเกราะป้องกันเซลล์ การตอบสนองต่อการติดเชื้อ และการอักเสบเรื้อรังซ่อนเร้น"
   },
   {
      id: 2,
      name: "เมตาบอลิซึม & พลังงาน",
      englishName: "Metabolism & Energy Core",
      icon: Zap,
      color: "#0A5C8E",
      axes: [5, 6, 7, 8, 9, 10],
      description: "ระบบเผาผลาญ ความไวต่ออินซูลิน คาร์โบไฮเดรต/ไขมันสะสม และการสร้างพลังงาน ATP ในระดับเซลล์"
   },
   {
      id: 4,
      name: "ระบบย่อย & การล้างพิษ",
      englishName: "Detox & Gut Ecosystem",
      icon: Droplet,
      color: "#0A5C8E",
      axes: [15, 16, 17, 18, 19],
      description: "ความสมบูรณ์ของจุลชีพในลำไส้ การซึมผ่านสารอาหาร และกระบวนการขับล้างสารพิษของตับและไต"
   },
   {
      id: 5,
      name: "ระบบหมุนเวียน & หลอดเลือด",
      englishName: "Vascular & Circulation",
      icon: Heart,
      color: "#0A5C8E",
      axes: [20, 21, 22, 23],
      description: "ความยืดหยุ่นของผนังหลอดเลือดฝอย การขนส่งออกซิเจน และความสมดุลของการไหลเวียนเลือด"
   },
   {
      id: 7,
      name: "ระบบโครงสร้าง & กระดูก",
      englishName: "Musculoskeletal & Structural",
      icon: Scale,
      color: "#0A5C8E",
      axes: [28, 29, 30],
      description: "ความหนาแน่นมวลกระดูก ความแข็งแรงของข้อต่อ กล้ามเนื้อ และโครงสร้างทางกายวิภาคโดยรวม"
   },
   {
      id: 9,
      name: "ระบบประสาท & ความเครียด",
      englishName: "Neuro & Sleep Quality",
      icon: Moon,
      color: "#0A5C8E",
      axes: [34],
      description: "สมดุลเคมีสมอง คุณภาพการนอนหลับ และการฟื้นฟูของระบบประสาทอัตโนมัติจากความตึงเครียด"
   }
];

// Fallback Lifestyle Advice based on worst dimension
const LIFESTYLE_ADVICE: Record<number, { title: string; nutrition: string; exercise: string; sleep: string; herbs: string }> = {
   1: {
      title: "เน้นปรับสมดุลภูมิคุ้มกันและลดภาระการอักเสบเรื้อรัง",
      nutrition: "รับประทานอาหารต้านอักเสบ (Anti-inflammatory Diet) เพิ่มกรดไขมันโอเมก้า-3 จากปลาทะเล ผักใบเขียว และขมิ้นชัน เลี่ยงน้ำตาลและไขมันทรานส์",
      exercise: "ออกกำลังกายระดับปานกลาง เช่น เดินเร็ว โยคะ หรือแกว่งแขน 30 นาทีต่อวัน หลีกเลี่ยงการหักโหมเพราะจะกระตุ้นสารอักเสบเพิ่มขึ้น",
      sleep: "นอนก่อน 22.00 น. เพื่อให้ร่างกายหลั่งโกรทฮอร์โมน (Growth Hormone) เข้ามาฟื้นฟูและยุติวงจรการอักเสบระดับเซลล์อย่างเต็มที่",
      herbs: "ดื่มชาเขียวอุ่นๆ หรือชาขิงเข้มข้นสม่ำเสมอเพื่อรับสารต้านอนุมูลอิสระธรรมชาติ"
   },
   2: {
      title: "เน้นปรับความไวอินซูลินและฟื้นฟูการเผาผลาญพลังงาน",
      nutrition: "ทานอาหารคาร์โบไฮเดรตต่ำ ดัชนีน้ำตาลต่ำ (Low-Glycemic Diet) เน้นโปรตีนสะอาดและใยอาหารสูง ทำ Intermittent Fasting (16/8)",
      exercise: "เน้นสร้างมวลกล้ามเนื้อด้วย Resistance Training (บอดี้เวท/ยกน้ำหนัก) ร่วมกับการคาร์ดิโอเบาๆ เพื่อเปิดรับกลูโคสเข้าเซลล์โดยตรง",
      sleep: "นอนหลับลึกอย่างน้อย 7-8 ชั่วโมง การอดนอนจะทำให้ระดับฮอร์โมนความหิวเพิ่มขึ้นและดื้อต่ออินซูลินในวันรุ่งนี้อย่างมีนัยสำคัญ",
      herbs: "พริกไทยดำ มะระขี้นก หรืออบเชย ช่วยปรับความไวต่อการจัดการคาร์โบไฮเดรต"
   },
   4: {
      title: "เน้นฟื้นฟูเยื่อบุลำไส้รั่วและจุลชีพสุขภาพดี",
      nutrition: "เพิ่มกลุ่ม Prebiotics เช่น หอมใหญ่ กระเทียม กล้วยน้ำว้าดิบ และ Probiotics จากโยเกิร์ตแท้ธรรมชาติ ลดอาหารแปรรูปและแอลกอฮอล์",
      exercise: "ออกกำลังกายเบาๆ เช่น การเดินหลังอาหาร 15-20 นาที เพื่อกระตุ้นการเคลื่อนตัวและการบีบตัวที่เป็นจังหวะของลำไส้อย่างเหมาะสม",
      sleep: "รักษารูปแบบเวลาการนอนหลับให้คงที่ เนื่องจากระบบจุลชีพในลำไส้ (Gut Microbiome) ทำงานสัมพันธ์อย่างลึกซึ้งกับนาฬิกาชีวิต",
      herbs: "ทานกล้วยน้ำว้าดิบตากแห้งชงดื่ม หรือขมิ้นชันเพื่อช่วยลดกรดสมานแผลเยื่อบุทางเดินอาหาร"
   },
   5: {
      title: "เน้นฟื้นฟูความยืดหยุ่นหลอดเลือดและการส่งเลือดฝอย",
      nutrition: "ทานอาหารโซเดียมต่ำ เพิ่มกลุ่มโพแทสเซียม เช่น มะเขือเทศ อะโวคาโด และอาหารที่มี ไนเตรตธรรมชาติ เช่น บีทรูท ผักโขม เพื่อขยายเส้นเลือด",
      exercise: "เน้นการออกกำลังกายแบบคาร์ดิโออย่างต่อเนื่อง (Zone 2 Cardiorespiratory Exercise) เช่น ว่ายน้ำ ปั่นจักรยาน วันละ 30-45 นาที",
      sleep: "จัดท่านอนให้หัวใจและระบบหายใจทำงานได้สะดวก หลีกเลี่ยงห้องนอนที่หนาวเกินไปเพื่อป้องกันไม่ให้หลอดเลือดส่วนปลายบีบรัดตัว",
      herbs: "เกสรดอกไม้โบราณ หรือตำรับพฤกษเวชขยายหลอดเลือดตามแพทย์แนะนำ"
   },
   7: {
      title: "เน้นเสริมสร้างความแข็งแกร่งของกระดูก ข้อต่อ และกล้ามเนื้อแกนกลาง",
      nutrition: "ทานอาหารแคลเซียมสูง คู่กับวิตามิน D3 และ K2 (พบในปลา นม นัตโตะ หรือไข่แดง) เพื่อส่งเสริมการดึงแคลเซียมเข้าสู่มวลกระดูกตรงจุด",
      exercise: "ฝึกท่าต้านแรงดึงดูด (Weight-bearing exercise) เพื่อกระตุ้นการสร้างความหนาแน่นมวลกระดูก เสริมสร้างกล้ามเนื้อแกนกลางลำตัว",
      sleep: "เลือกที่นอนที่ไม่นิ่มหรือแข็งเกินไปเพื่อประคองแนวกระดูกสันหลังให้สมบูรณ์ ลดอาการปวดเกร็งขณะสลับวงจรหลับฝัน",
      herbs: "ตำรับเบญจกูล หรือสารสกัดสมุนไพรที่มีสรรพคุณบำรุงเส้นเอ็นตามแพทย์สั่ง"
   },
   9: {
      title: "เน้นปรับสมดุลคลื่นสมอง คลายระบบประสาท และฟื้นฟูอาการหลับยาก",
      nutrition: "ลดเครื่องดื่มคาเฟอีนหลังเวลาเที่ยงวัน ทานอาหารที่มีแมกนีเซียมสูง เช่น กล้วย ถั่วอัลมอนด์ ผักปวยเล้ง และชาดอกคาโมมายล์อุ่นๆ",
      exercise: "ออกกำลังกายผ่อนคลายกล้ามเนื้อ เช่น ยืดเหยียด พิลาทิส หลีกเลี่ยงการออกกำลังกายหนักก่อนเวลานอนหลับอย่างน้อย 4 ชั่วโมง",
      sleep: "งดใช้หน้าจอมือถือ/แท็บเล็ตก่อนเข้านอน 1 ชั่วโมง จัดห้องนอนให้มืดสนิท เงียบ และอุณหภูมิเย็นพอเหมาะเพื่อกระตุ้นเมลาโทนินธรรมชาติ",
      herbs: "น้ำมันหอมระเหย ลาเวนเดอร์ หรือการดื่มน้ำอัญชันดอกไม้คลายอารมณ์"
   }
};

export default function PatientDashboard() {
   const [greeting, setGreeting] = useState("สวัสดีตอนเช้า");
   const [patient, setPatient] = useState<any>(null);
   const [reports, setReports] = useState<any[]>([]);
   const [selectedReport, setSelectedReport] = useState<any>(null);
   const [loading, setLoading] = useState(true);
   const [activeTab, setActiveTab] = useState<"hud" | "lifestyle" | "reports">("hud");
   
   // PWA & Edit States
   const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
   const [showEditModal, setShowEditModal] = useState(false);
   const [editFBS, setEditFBS] = useState("");
   const [editHbA1c, setEditHbA1c] = useState("");
   const [editLDL, setEditLDL] = useState("");
   const [editCRP, setEditCRP] = useState("");
   const [isSavingLabs, setIsSavingLabs] = useState(false);

   // Intercept PWA Installation Prompt
   useEffect(() => {
      const handleBeforeInstall = (e: any) => {
         e.preventDefault();
         setDeferredPrompt(e);
      };
      window.addEventListener("beforeinstallprompt", handleBeforeInstall);
      return () => window.removeEventListener("beforeinstallprompt", handleBeforeInstall);
   }, []);

   // Fetch data
   useEffect(() => {
      const hour = new Date().getHours();
      if (hour < 12) setGreeting("สวัสดีตอนเช้า");
      else if (hour < 18) setGreeting("สวัสดีตอนบ่าย");
      else setGreeting("สวัสดีตอนเย็น");

      const fetchDashboardData = async () => {
         if (typeof window === "undefined") return;
         const token = localStorage.getItem("patient_access_token");
         if (!token) {
            window.location.href = "/";
            return;
         }

         try {
            const res = await fetch(`${API_BASE}/api/auth/me/`, {
               headers: {
                  "Authorization": `Bearer ${token}`
               }
            });
            if (res.ok) {
               const data = await res.json();
               const mappedPatient = {
                  id: data.id,
                  hn: data.hn,
                  fname: data.first_name,
                  lname: data.last_name,
                  email: data.email,
                  phone: data.phone,
                  gender: data.gender,
                  birth_date: data.birth_date,
                  axes: {} as Record<string, number>,
                  ...data
               };
               
               if (data.axes_records && data.axes_records.length > 0) {
                  const latestRecord = data.axes_records[0];
                  const axesScores: Record<string, number> = {};
                  for (let i = 1; i <= 39; i++) {
                     axesScores[`AXIS_${i}`] = latestRecord[`axis_${i}`] ?? 50;
                  }
                  mappedPatient.axes = axesScores;
               }
               
               setPatient(mappedPatient);
               
               // Fetch reports history if available
               setReports([]);
            } else {
               localStorage.removeItem("patient_access_token");
               window.location.href = "/";
            }
         } catch (err) {
            console.error("Error loading patient dashboard data from Django:", err);
            window.location.href = "/";
         } finally {
            setLoading(false);
         }
      };

      fetchDashboardData();
   }, []);

   const handleLogout = async () => {
      const result = await Swal.fire({
         title: "ยืนยันการออกจากระบบ?",
         text: "คุณต้องการออกจากแผงควบคุมคนไข้ใช่หรือไม่?",
         icon: "question",
         showCancelButton: true,
         confirmButtonColor: "#DC2626",
         cancelButtonColor: "#6B7280",
         confirmButtonText: "ออกจากระบบ",
         cancelButtonText: "ยกเลิก"
      });

      if (result.isConfirmed) {
         localStorage.removeItem("patient_access_token");
         localStorage.removeItem("patient_refresh_token");
         window.location.href = "/patient/login";
      }
   };

   // FCM registration flow and PWA Installation promotion chain
   useEffect(() => {
      const registerFCM = async () => {
         if (typeof window === "undefined" || !patient?.id) return;

         const triggerPWAPrompt = async () => {
            const hasInstalledPrompted = localStorage.getItem("pwa_prompted");
            if (hasInstalledPrompted) return;
            
            if (deferredPrompt) {
               localStorage.setItem("pwa_prompted", "true");
               const result = await Swal.fire({
                  title: "ติดตั้งแอป TSPI บนมือถือของคุณ 📲",
                  text: "เข้าใช้งานได้รวดเร็วทันใจผ่านหน้าจอหลักเหมือนแอปพลิเคชันจริงโดยไม่ต้องติดตั้งผ่าน App Store/Play Store",
                  imageUrl: "/pwa_logo.jpg",
                  imageWidth: 80,
                  imageHeight: 80,
                  imageAlt: "TSPI Logo",
                  showCancelButton: true,
                  confirmButtonColor: "#282A29",
                  cancelButtonColor: "#9CA3AF",
                  confirmButtonText: "ติดตั้งแอป",
                  cancelButtonText: "ไว้ทีหลัง"
               });
               if (result.isConfirmed) {
                  deferredPrompt.prompt();
                  deferredPrompt.userChoice.then((choiceResult: any) => {
                     if (choiceResult.outcome === "accepted") {
                        console.log("User accepted the install prompt");
                     }
                     setDeferredPrompt(null);
                  });
               }
            }
         };

         if (!("Notification" in window)) {
            await triggerPWAPrompt();
            return;
         }
         
         const hasPrompted = localStorage.getItem("fcm_prompted");
         if (hasPrompted) {
            await triggerPWAPrompt();
            return;
         }
         
         localStorage.setItem("fcm_prompted", "true");
         
         const result = await Swal.fire({
            title: "เปิดรับการแจ้งเตือนข่าวด่วน 🦾",
            text: "คุณต้องการเปิดรับแจ้งเตือนผลแล็บและแผนฟื้นฟูสรีรวิทยาเจาะจงบุคคลจากคลินิกโดยตรงหรือไม่?",
            imageUrl: "/pwa_logo.jpg",
            imageWidth: 80,
            imageHeight: 80,
            imageAlt: "TSPI Logo",
            showCancelButton: true,
            confirmButtonColor: "#282A29",
            cancelButtonColor: "#9CA3AF",
            confirmButtonText: "เปิดรับข่าวสาร",
            cancelButtonText: "ไว้ทีหลัง"
         });
         
         if (result.isConfirmed) {
            try {
               const permission = await Notification.requestPermission();
               if (permission === "granted") {
                  const vapidKey = process.env.NEXT_PUBLIC_FIREBASE_VAPID_KEY || "";
                  if (vapidKey) {
                     const token = await getFCMToken(vapidKey);
                     if (token) {
                        console.log("FCM Token retrieved successfully:", token);
                        const accessToken = localStorage.getItem("patient_access_token");
                        await fetch(`${API_BASE}/api/auth/register-fcm-token/`, {
                           method: "POST",
                           headers: {
                              "Content-Type": "application/json",
                              "Authorization": `Bearer ${accessToken}`
                           },
                           body: JSON.stringify({ fcm_token: token })
                        });
                     }
                  }
                  
                  await Swal.fire({
                     title: "ลงทะเบียนสำเร็จ!",
                     text: "คุณจะได้รับการแจ้งเตือนผลการรักษาจากคลินิกทันที",
                     icon: "success",
                     confirmButtonColor: "#282A29"
                  });
               }
            } catch (err) {
               console.error("FCM Registration Failed:", err);
            }
         }
         await triggerPWAPrompt();
      };
      
      if (patient) {
         registerFCM();
      }
   }, [patient, deferredPrompt]);

   const openEditModal = () => {
      setEditFBS(patient?.labs?.FBS ? String(patient.labs.FBS) : "");
      setEditHbA1c(patient?.labs?.HbA1c ? String(patient.labs.HbA1c) : "");
      setEditLDL(patient?.labs?.LDL ? String(patient.labs.LDL) : "");
      setEditCRP(patient?.labs?.CRP ? String(patient.labs.CRP) : "");
      setShowEditModal(true);
   };

   const handleSaveLabs = async (e: React.FormEvent) => {
      e.preventDefault();
      setIsSavingLabs(true);
      
      const token = localStorage.getItem("patient_access_token");
      if (!token || !patient?.id) return;
      
      const updatedLabs = {
         ...(patient.labs || {}),
         FBS: editFBS ? parseFloat(editFBS) : null,
         HbA1c: editHbA1c ? parseFloat(editHbA1c) : null,
         LDL: editLDL ? parseFloat(editLDL) : null,
         CRP: editCRP ? parseFloat(editCRP) : null,
      };
      
      try {
         const res = await fetch(`${API_BASE}/api/patients/${patient.id}/`, {
            method: "PATCH",
            headers: {
               "Content-Type": "application/json",
               "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ labs: updatedLabs })
         });
         
         if (res.ok) {
            // Save to PatientHistory for health trends summary
            await fetch(`${API_BASE}/api/history/`, {
               method: "POST",
               headers: {
                  "Content-Type": "application/json",
                  "Authorization": `Bearer ${token}`
               },
               body: JSON.stringify({
                  patient: patient.id,
                  type: "Lab Result",
                  title: "บันทึกค่าวัดชีวภาพโดยคนไข้",
                  content: `คนไข้บันทึกค่าวัดชีวภาพผ่านแอป:\n- น้ำตาลในเลือด FBS: ${editFBS || "--"} mg/dL\n- น้ำตาลสะสม HbA1c: ${editHbA1c || "--"} %\n- ไขมันเลว LDL: ${editLDL || "--"} mg/dL\n- ดัชนีการอักเสบ CRP: ${editCRP || "--"} mg/L`
               })
            });
            
            setPatient({
               ...patient,
               labs: updatedLabs
            });
            
            setShowEditModal(false);
            
            Swal.fire({
               title: "บันทึกข้อมูลเรียบร้อย!",
               text: "ข้อมูลค่าวัดชีวภาพได้รับการบันทึกเข้าสู่ระบบ EMR แล้ว",
               icon: "success",
               confirmButtonColor: "#282A29"
            });
         } else {
            const errData = await res.json();
            Swal.fire({
               title: "เกิดข้อผิดพลาด",
               text: errData.error || "ไม่สามารถบันทึกข้อมูลได้",
               icon: "error",
               confirmButtonColor: "#282A29"
            });
         }
      } catch (err) {
         console.error("Error saving labs:", err);
         Swal.fire({
            title: "เกิดข้อผิดพลาด",
            text: "โปรดตรวจสอบการเชื่อมต่ออินเทอร์เน็ต",
            icon: "error",
            confirmButtonColor: "#282A29"
         });
      } finally {
         setIsSavingLabs(false);
      }
   };

   // Calculate dimension scores
   const computeDimensionScore = (axesList: number[]) => {
      if (!patient || !patient.axes) return 30;

      let totalScore = 0;
      let count = 0;

      axesList.forEach(id => {
         const axisKey = `AXIS_${id}`;
         const scoreItem = patient.axes[axisKey];
         if (scoreItem !== undefined) {
            const score = typeof scoreItem === 'object' ? (scoreItem.score ?? 50) : scoreItem;
            totalScore += score;
            count++;
         }
      });

      return count > 0 ? Math.round(totalScore / count) : 35;
   };

   // Identify the highest burden dimension to give targeted fallback advice
   const getHighestBurdenDimension = () => {
      let maxScore = -1;
      let worstDimId = 1;

      DIMENSIONS.forEach(dim => {
         const score = computeDimensionScore(dim.axes);
         if (score > maxScore) {
            maxScore = score;
            worstDimId = dim.id;
         }
      });

      return worstDimId;
   };

   const highestBurdenId = getHighestBurdenDimension();
   const dynamicAdvice = LIFESTYLE_ADVICE[highestBurdenId] || LIFESTYLE_ADVICE[1];

   if (loading) {
      return (
         <div className="d-flex flex-column align-items-center justify-content-center" style={{ minHeight: "80vh", gap: "16px" }}>
            <Loader2 className="animate-spin text-primary" size={40} style={{ color: "#0A5C8E" }} />
            <div style={{ fontSize: "14px", fontWeight: 600, color: "#4B5563" }}>กำลังโหลดข้อมูลพหุมิติสุขภาพของคุณ...</div>
         </div>
      );
   }

   // Extracted biomarker values for the 2x2 grid (wait for real EMR data from doctor)
   const fbsVal = patient?.labs?.FBS;
   const hba1cVal = patient?.labs?.HbA1c;
   const ldlVal = patient?.labs?.LDL;
   const crpVal = patient?.labs?.CRP;

   return (
      <div className="min-vh-100 font-sans pb-5" style={{ backgroundColor: '#F6F6F6' }}>
         <div className="container max-w-md mx-auto px-4 pt-3">
            
            {/* Header Section (Mockup style) */}
            <div className="d-flex justify-content-between align-items-center mb-4 pt-3">
               <div>
                  <h4 className="fw-bold mb-0 text-dark" style={{ letterSpacing: '-0.3px', color: '#282A29' }}>
                     Hello, {patient?.fname || patient?.firstName || "Jasmin"}
                  </h4>
                  <p className="text-muted mb-0 small" style={{ fontSize: '12px' }}>How are you feeling today?</p>
               </div>
               <div className="d-flex align-items-center gap-3">
                  <button
                     onClick={handleLogout}
                     className="btn btn-sm btn-light border rounded-pill d-flex align-items-center gap-1 px-3 py-1.5 fw-bold"
                     style={{ fontSize: "11px", color: '#6B7280' }}
                  >
                     <LogOut size={12} /> ออก
                  </button>
                  <div className="position-relative" style={{ width: '42px', height: '42px', borderRadius: '50%', backgroundColor: '#E5E7EB', overflow: 'hidden', border: '2px solid white', boxShadow: '0 4px 10px rgba(0,0,0,0.05)' }}>
                     <img 
                        src="https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&q=80&w=120&h=120"
                        alt="Profile"
                        className="w-100 h-100 object-fit-cover"
                     />
                  </div>
               </div>
            </div>

            {/* 2x2 Biomarker Grid Header with Edit Trigger */}
            <div className="d-flex justify-content-between align-items-center mb-3">
               <span className="fw-bold text-dark" style={{ fontSize: '13px', fontFamily: 'Kanit, sans-serif' }}>
                  ค่าวัดระดับชีววิทยาหลัก (EMR Labs)
               </span>
               <button
                  onClick={openEditModal}
                  className="btn btn-sm btn-dark rounded-pill px-3 py-1.5 fw-bold d-flex align-items-center gap-1 shadow-xs border-0"
                  style={{ fontSize: "11px", backgroundColor: "#282A29" }}
               >
                  <Activity size={12} /> บันทึกค่าวัดด้วยตนเอง
               </button>
            </div>

            {/* 2x2 Biomarker Grid */}
            <div className="row g-3 mb-4">
               {[
                  { 
                     label: "น้ำตาลในเลือด (FBS)", 
                     value: fbsVal ? `${fbsVal} mg/dL` : "-- mg/dL", 
                     status: fbsVal ? (fbsVal > 100 ? "กลุ่มเสี่ยง (Warning)" : "ปกติ (Optimal)") : "รอผลจากแพทย์", 
                     icon: Droplet, 
                     iconBg: fbsVal ? (fbsVal > 100 ? '#FEE2E2' : '#ECFDF5') : '#F3F4F6', 
                     iconColor: fbsVal ? (fbsVal > 100 ? '#EF4444' : '#10B981') : '#9CA3AF' 
                  },
                  { 
                     label: "น้ำตาลสะสม (HbA1c)", 
                     value: hba1cVal ? `${hba1cVal} %` : "-- %", 
                     status: hba1cVal ? (hba1cVal > 5.7 ? "กลุ่มเสี่ยง (Warning)" : "ปกติ (Optimal)") : "รอผลจากแพทย์", 
                     icon: Activity, 
                     iconBg: hba1cVal ? (hba1cVal > 5.7 ? '#FEE2E2' : '#ECFDF5') : '#F3F4F6', 
                     iconColor: hba1cVal ? (hba1cVal > 5.7 ? '#EF4444' : '#10B981') : '#9CA3AF' 
                  },
                  { 
                     label: "ไขมันเลว (LDL)", 
                     value: ldlVal ? `${ldlVal} mg/dL` : "-- mg/dL", 
                     status: ldlVal ? (ldlVal > 130 ? "กลุ่มเสี่ยง (Warning)" : "ปกติ (Optimal)") : "รอผลจากแพทย์", 
                     icon: Heart, 
                     iconBg: ldlVal ? (ldlVal > 130 ? '#FEE2E2' : '#ECFDF5') : '#F3F4F6', 
                     iconColor: ldlVal ? (ldlVal > 130 ? '#EF4444' : '#10B981') : '#9CA3AF' 
                  },
                  { 
                     label: "ดัชนีการอักเสบ (CRP)", 
                     value: crpVal ? `${crpVal} mg/L` : "-- mg/L", 
                     status: crpVal ? (crpVal > 1.0 ? "กลุ่มเสี่ยง (Warning)" : "ปกติ (Optimal)") : "รอผลจากแพทย์", 
                     icon: Zap, 
                     iconBg: crpVal ? (crpVal > 1.0 ? '#FEE2E2' : '#ECFDF5') : '#F3F4F6', 
                     iconColor: crpVal ? (crpVal > 1.0 ? '#EF4444' : '#10B981') : '#9CA3AF' 
                  },
               ].map((marker, idx) => (
                  <div key={idx} className="col-6">
                     <div className="card p-3 border-0 bg-white shadow-xs rounded-4 text-start h-100" style={{ boxShadow: '0 4px 20px rgba(0,0,0,0.012)' }}>
                        <div className="d-flex align-items-center gap-2 mb-3">
                           <div className="rounded-circle d-flex align-items-center justify-content-center" style={{ width: '34px', height: '34px', backgroundColor: marker.iconBg }}>
                              <marker.icon size={15} style={{ color: marker.iconColor }} />
                           </div>
                           <span className="text-muted" style={{ fontSize: '11px', fontWeight: 600 }}>{marker.label}</span>
                        </div>
                        <h5 className="fw-bold mb-1" style={{ color: '#282A29', fontSize: '18px' }}>{marker.value}</h5>
                        <span style={{ fontSize: '10px', color: marker.iconColor, fontWeight: 600 }}>{marker.status}</span>
                     </div>
                  </div>
               ))}
            </div>

            {/* Next Appointment Card (Placeholder mockup style) */}
            <div className="card p-4 border-0 mb-4 rounded-4" style={{ backgroundColor: '#282A29', color: '#FFFFFF', boxShadow: '0 8px 30px rgba(40,42,41,0.12)' }}>
               <div className="d-flex justify-content-between align-items-start mb-2">
                  <div>
                     <span className="text-white-50 small uppercase tracking-wider d-block mb-1" style={{ fontSize: '9px', fontWeight: 700, letterSpacing: '0.5px' }}>
                        นัดหมายแพทย์ถัดไป (NEXT APPOINTMENT)
                     </span>
                     <h5 className="fw-bold mb-0 text-white" style={{ fontSize: '16px' }}>ยังไม่มีการนัดหมายแพทย์ในขณะนี้</h5>
                  </div>
                  <span className="badge rounded-pill px-2.5 py-1 bg-secondary bg-opacity-20 text-white border border-white border-opacity-10 fw-bold" style={{ fontSize: '10px' }}>ไม่มีนัด</span>
               </div>
               
               <div className="d-flex align-items-center gap-3 border-top border-white border-opacity-10 pt-3">
                  <div className="flex-grow-1 text-start">
                     <p className="mb-0 text-white-50 small" style={{ fontSize: '11.5px', lineHeight: 1.5 }}>
                        *(ข้อมูลจำลอง: รอการยืนยันวันนัดหมายจริงและการบันทึกข้อมูลตารางเวลายืนยันจากฝั่งแพทย์ผู้ดูแลของคุณเข้าระบบ EMR)*
                     </p>
                  </div>
                  <Link href="/patient/appointments" className="btn btn-sm btn-light rounded-pill px-3 py-1.5 fw-bold text-dark border-0" style={{ fontSize: '11px' }}>
                     ตารางนัดทั้งหมด
                  </Link>
               </div>
            </div>

            {/* Tab navigation (Charcoal style) */}
            <div className="d-flex p-1 bg-white border border-light rounded-4 mb-4 gap-1 shadow-xs" style={{ fontFamily: 'Kanit, sans-serif' }}>
               {[
                  { id: "hud", label: "ดัชนี 6 มิติ", icon: Activity },
                  { id: "lifestyle", label: "คำแนะนำฟื้นฟู", icon: Sparkles },
                  { id: "reports", label: "รายงานแพทย์", icon: BookOpen }
               ].map(tab => (
                  <button
                     key={tab.id}
                     onClick={() => setActiveTab(tab.id as any)}
                     className={`flex-grow-1 py-2.5 rounded-3 border-0 fw-bold small transition ${
                        activeTab === tab.id ? "text-white" : "bg-transparent text-muted"
                     }`}
                     style={{ 
                        backgroundColor: activeTab === tab.id ? "#282A29" : "transparent",
                        transition: 'all 0.2s'
                     }}
                  >
                     <tab.icon size={14} className="me-1 d-inline" />
                     {tab.label}
                  </button>
               ))}
            </div>

            {/* ================= TAB 1: 6 DIMENSIONS HEALTH HUD ================= */}
            {activeTab === "hud" && (
               <div className="animate-fade-in">
                  <div className="bg-white rounded-4 p-3 border mb-4 shadow-sm">
                     <div className="d-flex align-items-center gap-2 mb-2">
                        <Info size={16} style={{ color: "#0A5C8E" }} />
                        <span className="fw-bold text-dark" style={{ fontSize: "13px", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                           สภาวะความตึงเครียดของเซลล์ (Cellular Burden HUD)
                        </span>
                     </div>
                     <p className="text-muted mb-0" style={{ fontSize: "11.5px", lineHeight: "1.4" }}>
                        ค่าร้อยละจำลองภาระโรค (Burden) ยิ่งระดับเปอร์เซ็นต์ต่ำ สุขภาพยิ่งมั่นคงและเข้าสู่จุดสมดุลสากล (Prakati)
                     </p>
                  </div>

                  {/* Dimension Cards */}
                  <div className="row g-3">
                     {DIMENSIONS.map((dim) => {
                        const score = computeDimensionScore(dim.axes);
                        const Icon = dim.icon;

                        let stateText = "ระดับผ่านเกณฑ์ (Optimal)";
                        let badgeColor = "#059669";
                        if (score > 70) {
                           stateText = "ระดับวิกฤต (Critical Risk)";
                           badgeColor = "#DC2626";
                        } else if (score >= 40) {
                           stateText = "ระดับเฝ้าระวัง (Moderate)";
                           badgeColor = "#D97706";
                        }

                        return (
                           <div key={dim.id} className="col-12">
                              <div 
                                 className="card border-0 p-3 bg-white shadow-sm hover-translate-y-2 cursor-pointer"
                                 style={{ borderLeft: `5px solid ${badgeColor}` }}
                              >
                                 <div className="d-flex justify-content-between align-items-start mb-2">
                                    <div className="d-flex align-items-center gap-2.5">
                                       <div className="p-2 rounded bg-light d-flex align-items-center justify-content-center">
                                          <Icon size={18} style={{ color: "#0A5C8E" }} />
                                       </div>
                                       <div>
                                          <h6 className="fw-bold text-dark mb-0" style={{ fontSize: "13.5px" }}>{dim.name}</h6>
                                          <span className="text-muted" style={{ fontSize: "10px" }}>{dim.englishName}</span>
                                       </div>
                                    </div>
                                    
                                    <div className="text-end">
                                       <span className="fs-4 fw-900 mb-0 d-block" style={{ color: badgeColor, lineHeight: "1" }}>
                                          {score}%
                                       </span>
                                       <span className="badge mt-1 text-white border-0" style={{ backgroundColor: badgeColor, fontSize: "9px" }}>
                                          {stateText}
                                       </span>
                                    </div>
                                 </div>
                                 
                                 <div className="progress mb-2" style={{ height: "6px", backgroundColor: "#F3F4F6" }}>
                                    <div 
                                       className="progress-bar"
                                       style={{ 
                                          width: `${score}%`, 
                                          backgroundColor: badgeColor,
                                          borderRadius: "100px"
                                       }}
                                    />
                                 </div>

                                 <p className="text-muted mb-0" style={{ fontSize: "11px", lineHeight: "1.4" }}>
                                    {dim.description}
                                 </p>
                              </div>
                           </div>
                        );
                     })}
                  </div>
               </div>
            )}

            {/* ================= TAB 2: LIFESTYLE MODIFICATIONS ================= */}
            {activeTab === "lifestyle" && (
               <div className="animate-fade-in">
                  
                  <div className="card border-0 p-4 bg-white shadow-sm mb-4">
                     <div className="d-flex align-items-center gap-2 mb-3">
                        <Sparkles size={20} style={{ color: "#D4AF37" }} />
                        <h5 className="fw-bold text-dark mb-0">แผนใบสั่งสรีรวิทยาเจาะจงบุคคล</h5>
                     </div>
                     
                     <div className="p-3 rounded-4 mb-4" style={{ backgroundColor: "rgba(10, 92, 142, 0.05)", borderLeft: "4px solid #0A5C8E" }}>
                        <span className="tiny text-muted d-block uppercase tracking-wider mb-1">จุดฟื้นฟูเร่งด่วนที่สุดในปัจจุบันของคุณ</span>
                        <strong style={{ fontSize: "14px", color: "#1F2937" }}>{dynamicAdvice.title}</strong>
                     </div>

                     <div className="d-flex flex-column gap-3">
                        <div className="d-flex gap-3">
                           <div className="p-2 rounded bg-light text-primary-custom d-flex align-items-center justify-content-center flex-shrink-0" style={{ width: "36px", height: "36px", color: "#0A5C8E" }}>
                              🥗
                           </div>
                           <div>
                              <strong className="d-block small text-dark">อาหารฟื้นฟู (Nutrition Strategy)</strong>
                              <p className="text-muted mb-0 small" style={{ lineHeight: "1.4" }}>{dynamicAdvice.nutrition}</p>
                           </div>
                        </div>

                        <div className="d-flex gap-3 border-top pt-3">
                           <div className="p-2 rounded bg-light text-primary-custom d-flex align-items-center justify-content-center flex-shrink-0" style={{ width: "36px", height: "36px", color: "#0A5C8E" }}>
                              🏃
                           </div>
                           <div>
                              <strong className="d-block small text-dark">การออกกำลังกาย (Therapeutic Exercise)</strong>
                              <p className="text-muted mb-0 small" style={{ lineHeight: "1.4" }}>{dynamicAdvice.exercise}</p>
                           </div>
                        </div>

                        <div className="d-flex gap-3 border-top pt-3">
                           <div className="p-2 rounded bg-light text-primary-custom d-flex align-items-center justify-content-center flex-shrink-0" style={{ width: "36px", height: "36px", color: "#0A5C8E" }}>
                              🛌
                           </div>
                           <div>
                              <strong className="d-block small text-dark">การพักผ่อน (Restorative Sleep)</strong>
                              <p className="text-muted mb-0 small" style={{ lineHeight: "1.4" }}>{dynamicAdvice.sleep}</p>
                           </div>
                        </div>

                        <div className="d-flex gap-3 border-top pt-3">
                           <div className="p-2 rounded bg-light text-primary-custom d-flex align-items-center justify-content-center flex-shrink-0" style={{ width: "36px", height: "36px", color: "#0A5C8E" }}>
                              🍃
                           </div>
                           <div>
                              <strong className="d-block small text-dark">สารสกัดธรรมชาติซิงก์โมเลกุล (Phytochemical Harmony)</strong>
                              <p className="text-muted mb-0 small" style={{ lineHeight: "1.4" }}>{dynamicAdvice.herbs}</p>
                           </div>
                        </div>
                     </div>
                  </div>

                  <div className="p-3 bg-white border rounded-4 d-flex align-items-start gap-2 shadow-xs">
                     <AlertCircle size={16} className="text-warning flex-shrink-0 mt-0.5" />
                     <p className="mb-0 text-muted" style={{ fontSize: "11px", lineHeight: "1.4" }}>
                        * แผนการฟื้นฟูสัญชาตญาณเซลล์จัดทำขึ้นตามค่าน้ำตาล ผลแล็บ และดัชนีชีววิทยาระบบ 39 แกนหลักของคุณที่เชื่อมอยู่ในฐานข้อมูล EMR ของคลินิกแพทย์ผู้รักษา
                     </p>
                  </div>
               </div>
            )}

            {/* ================= TAB 3: CLINICAL REPORTS (PATIENT EDITION) ================= */}
            {activeTab === "reports" && (
               <div className="animate-fade-in">
                  
                  {reports.length === 0 ? (
                     <div className="text-center py-5 bg-white border rounded-4 shadow-sm">
                        <FileText size={40} className="text-muted mb-2.5" />
                        <h6 className="fw-bold text-dark">ยังไม่มีรายงานสุขภาพฉบับคนไข้</h6>
                        <p className="text-muted mb-0 small px-4">
                           แพทย์ผู้รักษาจะทำการสรุปรายงานสุขภาพฉบับเข้าใจง่าย (Patient Edition) และส่งเข้าระบบ EMR ของท่านทันทีหลังวิเคราะห์สำเร็จ
                        </p>
                     </div>
                  ) : (
                     <>
                        <div className="bg-white rounded-4 p-3 border mb-4 shadow-sm">
                           <label className="tiny fw-bold text-muted text-uppercase mb-2.5 d-block tracking-wide">
                              เลือกดูประวัติรายงานผู้ป่วย (Patient Edition History)
                           </label>
                           <div className="d-flex flex-column gap-2">
                              {reports.map((rep) => (
                                 <button
                                    key={rep.id}
                                    onClick={() => setSelectedReport(rep)}
                                    className={`w-100 p-2.5 rounded-3 border text-start bg-transparent transition d-flex align-items-center justify-content-between ${
                                       selectedReport?.id === rep.id 
                                          ? "border-primary bg-primary bg-opacity-5" 
                                          : "border-light"
                                    }`}
                                    style={{ borderColor: selectedReport?.id === rep.id ? "#0A5C8E" : "#E5E7EB" }}
                                 >
                                    <div className="d-flex align-items-center gap-2.5">
                                       <FileText size={16} style={{ color: "#0A5C8E" }} />
                                       <div>
                                          <strong className="d-block small text-dark">รายงานฟื้นฟูสุขภาพฉบับคนไข้</strong>
                                          <span className="text-muted" style={{ fontSize: "10.5px" }}>
                                             สร้างเมื่อ: {new Date(rep.createdAt).toLocaleDateString("th-TH", { year: "numeric", month: "short", day: "numeric" })}
                                          </span>
                                       </div>
                                    </div>
                                    <ChevronRight size={16} className="text-muted" />
                                 </button>
                              ))}
                           </div>
                        </div>

                        {selectedReport && (
                           <div className="card border-0 p-4 bg-white shadow-sm mb-4">
                              <div className="d-flex justify-content-between align-items-center border-bottom pb-3 mb-3">
                                 <div>
                                    <h5 className="fw-bold text-dark mb-0">รายงานสุขภาพสำหรับคนไข้</h5>
                                    <span className="text-muted" style={{ fontSize: "10.5px" }}>
                                       ฉบับลงวันที่: {new Date(selectedReport.createdAt).toLocaleDateString("th-TH", { year: "numeric", month: "long", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                                    </span>
                                 </div>
                              </div>

                              <div className="d-flex flex-column gap-3.5" style={{ maxHeight: "500px", overflowY: "auto", paddingRight: "5px" }}>
                                 {selectedReport.report && Array.isArray(selectedReport.report) ? (
                                    selectedReport.report.map((chapter: any, index: number) => (
                                       <div key={index} className="p-3 bg-light rounded-4 border">
                                          <h6 className="fw-bold text-dark mb-2" style={{ fontSize: "13.5px" }}>
                                             {chapter.chapterTitle}
                                          </h6>
                                          <div 
                                             className="text-muted small leading-relaxed"
                                             style={{ whiteSpace: "pre-wrap" }}
                                          >
                                             {chapter.content}
                                          </div>
                                       </div>
                                    ))
                                 ) : (
                                    <p className="text-muted small">โครงสร้างรายงานไม่สมบูรณ์</p>
                                 )}
                              </div>
                           </div>
                        )}
                     </>
                  )}
               </div>
            )}
         </div>

         {/* Edit Biomarkers Modal */}
         {showEditModal && (
            <div className="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center bg-dark bg-opacity-50" style={{ zIndex: 1050, backdropFilter: "blur(4px)" }}>
               <div className="bg-white rounded-4 p-4 max-w-sm w-100 mx-3 shadow-lg border border-light animate-fade-in text-start">
                  <div className="d-flex justify-content-between align-items-center mb-3">
                     <h5 className="fw-bold mb-0 text-dark" style={{ fontFamily: 'Kanit, sans-serif', fontSize: '16px' }}>บันทึกตัวบ่งชี้ชีวภาพ</h5>
                     <button type="button" className="btn-close" onClick={() => setShowEditModal(false)}></button>
                  </div>
                  <form onSubmit={handleSaveLabs}>
                     <div className="mb-3">
                        <label className="form-label text-muted small fw-bold mb-1">น้ำตาลในเลือด FBS (mg/dL)</label>
                        <input
                           type="number"
                           step="any"
                           className="form-control rounded-pill border-light bg-light text-dark py-2 px-3"
                           style={{ fontSize: "14px" }}
                           placeholder="เช่น 95"
                           value={editFBS}
                           onChange={(e) => setEditFBS(e.target.value)}
                        />
                     </div>
                     <div className="mb-3">
                        <label className="form-label text-muted small fw-bold mb-1">น้ำตาลสะสม HbA1c (%)</label>
                        <input
                           type="number"
                           step="any"
                           className="form-control rounded-pill border-light bg-light text-dark py-2 px-3"
                           style={{ fontSize: "14px" }}
                           placeholder="เช่น 5.6"
                           value={editHbA1c}
                           onChange={(e) => setEditHbA1c(e.target.value)}
                        />
                     </div>
                     <div className="mb-3">
                        <label className="form-label text-muted small fw-bold mb-1">ไขมันเลว LDL (mg/dL)</label>
                        <input
                           type="number"
                           step="any"
                           className="form-control rounded-pill border-light bg-light text-dark py-2 px-3"
                           style={{ fontSize: "14px" }}
                           placeholder="เช่น 120"
                           value={editLDL}
                           onChange={(e) => setEditLDL(e.target.value)}
                        />
                     </div>
                     <div className="mb-4">
                        <label className="form-label text-muted small fw-bold mb-1">ดัชนีการอักเสบ CRP (mg/L)</label>
                        <input
                           type="number"
                           step="any"
                           className="form-control rounded-pill border-light bg-light text-dark py-2 px-3"
                           style={{ fontSize: "14px" }}
                           placeholder="เช่น 1.1"
                           value={editCRP}
                           onChange={(e) => setEditCRP(e.target.value)}
                        />
                     </div>
                     <div className="d-grid gap-2">
                        <button
                           type="submit"
                           disabled={isSavingLabs}
                           className="btn btn-dark rounded-pill py-2.5 fw-bold d-flex align-items-center justify-content-center gap-2 border-0"
                           style={{ backgroundColor: "#282A29", fontSize: "14px" }}
                        >
                           {isSavingLabs ? (
                              <>
                                 <Loader2 className="animate-spin" size={16} /> กำลังบันทึก...
                              </>
                           ) : (
                              "บันทึกข้อมูลเข้า EMR"
                           )}
                        </button>
                        <button
                           type="button"
                           onClick={() => setShowEditModal(false)}
                           className="btn btn-light rounded-pill py-2.5 text-muted border border-light"
                           style={{ fontSize: "14px" }}
                        >
                           ยกเลิก
                        </button>
                     </div>
                  </form>
               </div>
            </div>
         )}

         {/* Bottom spacing helper */}
         <div style={{ height: "40px" }} />
      </div>
   );
}
