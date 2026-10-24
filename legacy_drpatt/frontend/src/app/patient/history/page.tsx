"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Search,
  ChevronRight,
  Download,
  Database,
  Microscope,
  Zap,
  Shield,
  Layers,
  Lock,
  ArrowLeft,
  Loader2,
  Clock
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine
} from "recharts";
import Swal from "sweetalert2";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Biomarker limit metadata
const BIOMARKER_META = {
   FBS: { label: "น้ำตาลในเลือด (FBS)", unit: "mg/dL", limit: 100, color: "#0A5C8E", description: "ระดับปกติขณะอดอาหารควรน้อยกว่า 100 mg/dL" },
   HbA1c: { label: "น้ำตาลสะสม (HbA1c)", unit: "%", limit: 5.7, color: "#10B981", description: "ระดับน้ำตาลสะสมไตรมาสปกติควรน้อยกว่า 5.7%" },
   LDL: { label: "ไขมันเลว (LDL)", unit: "mg/dL", limit: 130, color: "#F43F5E", description: "คอเลสเตอรอลชนิดไม่ดี LDL ควรน้อยกว่า 130 mg/dL" },
   CRP: { label: "ดัชนีการอักเสบ (CRP)", unit: "mg/L", limit: 1.0, color: "#F59E0B", description: "ดัชนีการตอบสนองความอักเสบ CRP ควรน้อยกว่า 1.0 mg/L" }
};

export default function MedicalHistoryPage() {
  const [activeTab, setActiveTab] = useState<"history" | "download" | "trends">("history");
  const [historyItems, setHistoryItems] = useState<any[]>([]);
  const [userData, setUserData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedBiomarker, setSelectedBiomarker] = useState<"FBS" | "HbA1c" | "LDL" | "CRP">("FBS");
  
  // New States for Detail modal & download category selector
  const [selectedItem, setSelectedItem] = useState<any>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>("เวชระเบียน");
  const [isInjectingDemo, setIsInjectingDemo] = useState(false);

  const fetchHistoryData = async () => {
    if (typeof window === "undefined") return;
    const token = localStorage.getItem("patient_access_token");
    if (!token) {
      window.location.href = "/";
      return;
    }

    try {
      const meRes = await fetch(`${API_BASE}/api/auth/me/`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!meRes.ok) {
        localStorage.removeItem("patient_access_token");
        window.location.href = "/";
        return;
      }
      const profile = await meRes.json();
      
      const mappedUser = {
        id: profile.id,
        hn: profile.hn,
        first_name: profile.first_name,
        last_name: profile.last_name,
        id_card: profile.id_card,
        phone: profile.phone,
        email: profile.email,
        birth_date: profile.birth_date,
        extra_data: profile.extra_data,
        axes: {} as Record<string, any>,
        ...profile
      };

      if (profile.axes_records && profile.axes_records.length > 0) {
        const latestRecord = profile.axes_records[0];
        const axesScores: Record<string, number> = {};
        for (let i = 1; i <= 39; i++) {
           axesScores[`AXIS_${i}`] = latestRecord[`axis_${i}`] ?? 50;
        }
        mappedUser.axes = axesScores;
      }
      setUserData(mappedUser);
      
      const histRes = await fetch(`${API_BASE}/api/history/?patient=${profile.id}`);
      if (histRes.ok) {
        const rawHist = await histRes.json();
        const mappedHist = rawHist.map((h: any) => ({
          id: String(h.id),
          type: h.type || "General",
          content: h.content || "",
          title: h.title || "ประวัติการรักษา",
          createdAt: h.created_at
        }));
        setHistoryItems(mappedHist);
      }
    } catch (err) {
      console.error("Error loading history from Django:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistoryData();
  }, []);

  const formatDate = (dateValue: any) => {
     if (!dateValue) return "ไม่ระบุวันที่";
     const date = new Date(dateValue);
     return date.toLocaleDateString("th-TH", { year: "numeric", month: "short", day: "numeric" });
  };
  
  const formatTime = (dateValue: any) => {
     if (!dateValue) return "";
     const date = new Date(dateValue);
     return date.toLocaleTimeString("th-TH", { hour: "2-digit", minute: "2-digit" });
  };

  const getIconAndColor = (type: string) => {
      switch(type?.toLowerCase()) {
         case "ai assessment": return { icon: "🤖", bg: "bg-primary-custom bg-opacity-10" };
         case "lab result": return { icon: "🔬", bg: "bg-success bg-opacity-10" };
         case "doctor visit": return { icon: "🩺", bg: "bg-info bg-opacity-10" };
         case "prescription": return { icon: "💊", bg: "bg-warning bg-opacity-10" };
         default: return { icon: "📝", bg: "bg-secondary bg-opacity-10" };
      }
  };

  // Lab content parser utilizing regex to extract values
  const parseLabsFromContent = (content: string) => {
     const fbsMatch = content.match(/FBS:\s*([\d.]+)/i);
     const hba1cMatch = content.match(/HbA1c:\s*([\d.]+)/i);
     const ldlMatch = content.match(/LDL:\s*([\d.]+)/i);
     const crpMatch = content.match(/CRP:\s*([\d.]+)/i);
     
     return {
        FBS: fbsMatch && fbsMatch[1] ? parseFloat(fbsMatch[1]) : null,
        HbA1c: hba1cMatch && hba1cMatch[1] ? parseFloat(hba1cMatch[1]) : null,
        LDL: ldlMatch && ldlMatch[1] ? parseFloat(ldlMatch[1]) : null,
        CRP: crpMatch && crpMatch[1] ? parseFloat(crpMatch[1]) : null,
     };
  };

  const getChartData = () => {
     const labHistory = historyItems
        .filter((h: any) => h.type?.toLowerCase() === "lab result")
        .map((h: any) => {
           const parsed = parseLabsFromContent(h.content);
           const date = new Date(h.createdAt);
           return {
              formattedDate: date.toLocaleDateString("th-TH", { month: "short", day: "numeric" }),
              rawDate: date,
              ...parsed
           };
        })
        .filter((d: any) => d[selectedBiomarker] !== null);
        
     // Sort oldest to newest for chronological graph line direction
     return labHistory.sort((a: any, b: any) => a.rawDate.getTime() - b.rawDate.getTime());
  };

  const chartData = getChartData();

  // Inject chronological demo data for graph visualization
  const handleInjectDemoData = async () => {
    if (!userData?.id) return;
    setIsInjectingDemo(true);
    const token = localStorage.getItem("patient_access_token");

    const demoRecords = [
      {
        patient: userData.id,
        type: "Lab Result",
        title: "บันทึกผลแล็บทางการแพทย์ (แพทย์)",
        content: "ผลแล็บได้รับการอัปเดตเข้าระบบ EMR:\n- น้ำตาลในเลือด FBS: 125 mg/dL\n- น้ำตาลสะสม HbA1c: 6.8 %\n- ไขมันเลว LDL: 155 mg/dL\n- ดัชนีการอักเสบ CRP: 2.1 mg/L",
        created_at: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString()
      },
      {
        patient: userData.id,
        type: "Lab Result",
        title: "บันทึกผลแล็บทางการแพทย์ (แพทย์)",
        content: "ผลแล็บได้รับการอัปเดตเข้าระบบ EMR:\n- น้ำตาลในเลือด FBS: 110 mg/dL\n- น้ำตาลสะสม HbA1c: 6.1 %\n- ไขมันเลว LDL: 140 mg/dL\n- ดัชนีการอักเสบ CRP: 1.5 mg/L",
        created_at: new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString()
      },
      {
        patient: userData.id,
        type: "Lab Result",
        title: "บันทึกค่าวัดชีวภาพโดยคนไข้",
        content: "คนไข้บันทึกค่าวัดชีวภาพผ่านแอป:\n- น้ำตาลในเลือด FBS: 98 mg/dL\n- น้ำตาลสะสม HbA1c: 5.6 %\n- ไขมันเลว LDL: 125 mg/dL\n- ดัชนีการอักเสบ CRP: 0.9 mg/L",
        created_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString()
      },
      {
        patient: userData.id,
        type: "Lab Result",
        title: "บันทึกผลแล็บทางการแพทย์ (แพทย์)",
        content: "ผลแล็บได้รับการอัปเดตเข้าระบบ EMR:\n- น้ำตาลในเลือด FBS: 88 mg/dL\n- น้ำตาลสะสม HbA1c: 5.2 %\n- ไขมันเลว LDL: 112 mg/dL\n- ดัชนีการอักเสบ CRP: 0.4 mg/L",
        created_at: new Date().toISOString()
      }
    ];

    try {
      for (const r of demoRecords) {
        await fetch(`${API_BASE}/api/history/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify(r)
        });
      }

      await fetchHistoryData();
      Swal.fire({
        title: "โหลดข้อมูลสาธิตสำเร็จ!",
        text: "ระบบได้จำลองประวัติแล็บ 4 ช่วงเวลาเพื่อใช้พล็อตกราฟเส้นแนวโน้มเรียบร้อยแล้ว",
        icon: "success",
        confirmButtonColor: "#282A29"
      });
    } catch (err) {
      console.error(err);
      Swal.fire("เกิดข้อผิดพลาด", "ไม่สามารถสร้างข้อมูลทดสอบได้", "error");
    } finally {
      setIsInjectingDemo(false);
    }
  };

  // Generate Custom Printable HTML Medical Dossier
  const generateHTMLReport = (category: string) => {
    const patientName = `${userData?.first_name || ""} ${userData?.last_name || ""}`;
    const hn = userData?.hn || "ไม่ระบุ";
    const birth = userData?.birth_date ? new Date(userData.birth_date).toLocaleDateString("th-TH") : "ไม่ระบุ";
    const idCard = userData?.id_card || "ไม่ระบุ";
    
    let title = "";
    let reportContent = "";
    
    if (category === "เวชระเบียน") {
       title = "รายงานเวชระเบียนผู้ป่วยหลัก (Electronic Medical Record)";
       reportContent = `
          <h3>ข้อมูลทั่วไปผู้เข้ารับการรักษา</h3>
          <table class="report-table">
             <tr><th>ชื่อ - นามสกุล</th><td>${patientName}</td></tr>
             <tr><th>รหัสประวัติ (HN)</th><td>${hn}</td></tr>
             <tr><th>เลขประจำตัวประชาชน</th><td>${idCard}</td></tr>
             <tr><th>วันเดือนปีเกิด</th><td>${birth}</td></tr>
             <tr><th>เบอร์โทรศัพท์ติดต่อ</th><td>${userData?.phone || "ไม่ระบุ"}</td></tr>
             <tr><th>เบอร์โทรติดต่อฉุกเฉิน</th><td>${userData?.extra_data?.emergency_phone || "ไม่ระบุ"}</td></tr>
          </table>
          
          <h3>คะแนนประเมินภาระโรคพหุมิติ 39 แกนชีววิทยา</h3>
          <p style="font-size:12px; color:#555;">(ประเมินโดยโมเดลปัญญาประดิษฐ์สรีรวิทยาเพื่อหาสมดุลธาตุ Prakati)</p>
          <table class="report-table">
             <thead>
                <tr>
                   <th>ระบบ/แกนชีววิทยา</th>
                   <th>ภาระโรคจำลอง (Burden Score)</th>
                   <th>สถานะการวิเคราะห์</th>
                </tr>
             </thead>
             <tbody>
                ${Object.keys(userData?.axes || {}).length > 0 ? 
                   Object.entries(userData.axes).map(([key, val]: any) => {
                      const num = key.replace("AXIS_", "");
                      const score = typeof val === 'object' ? (val.score ?? 50) : val;
                      const status = score > 70 ? "<span class='text-danger font-bold'>วิกฤต (Critical)</span>" 
                                   : score >= 40 ? "<span style='color:#d97706; font-weight:bold;'>เฝ้าระวัง (Warning)</span>" 
                                   : "<span style='color:#059669; font-weight:bold;'>ปกติ (Optimal)</span>";
                      return `<tr><td>แกนชีววิทยาที่ ${num}</td><td>${score}%</td><td>${status}</td></tr>`;
                   }).join("")
                   : "<tr><td colspan='3' class='text-center'>ไม่พบประวัติคะแนนแกนชีววิทยาในระบบ EMR</td></tr>"
                }
             </tbody>
          </table>
       `;
    } else if (category === "ผลตรวจ Lab") {
       title = "รายงานผลตรวจชีววิทยาและตัวชี้วัดสุขภาพ (Lab Report)";
       const labs = getChartData();
       reportContent = `
          <h3>ตารางเปรียบเทียบค่าระดับชีววิทยาห้องปฏิบัติการย้อนหลัง</h3>
          <table class="report-table">
             <thead>
                <tr>
                   <th>วันที่ตรวจ</th>
                   <th>น้ำตาลในเลือด FBS (mg/dL)</th>
                   <th>น้ำตาลสะสม HbA1c (%)</th>
                   <th>ไขมันเลว LDL (mg/dL)</th>
                   <th>การอักเสบ CRP (mg/L)</th>
                </tr>
             </thead>
             <tbody>
                ${labs.length > 0 ? 
                   labs.map((l: any) => `
                      <tr>
                         <td>${l.formattedDate}</td>
                         <td class="${l.FBS > 100 ? 'text-danger font-bold' : ''}">${l.FBS ?? "--"}</td>
                         <td class="${l.HbA1c > 5.7 ? 'text-danger font-bold' : ''}">${l.HbA1c ?? "--"} %</td>
                         <td class="${l.LDL > 130 ? 'text-danger font-bold' : ''}">${l.LDL ?? "--"}</td>
                         <td class="${l.CRP > 1.0 ? 'text-danger font-bold' : ''}">${l.CRP ?? "--"}</td>
                      </tr>
                   `).join("")
                   : "<tr><td colspan='5' class='text-center'>ไม่พบประวัติผลตรวจแล็บบันทึกอยู่ในระบบ</td></tr>"
                }
             </tbody>
          </table>
          <p style="font-size:12px; color:#6B7280; line-height:1.4;">
            * เกณฑ์อ้างอิงความเสี่ยงทางสรีรวิทยา: FBS ปกติ &lt; 100 mg/dL, HbA1c ปกติ &lt; 5.7%, LDL ปกติ &lt; 130 mg/dL, CRP ปกติ &lt; 1.0 mg/L
          </p>
       `;
    } else if (category === "ประวัติยา") {
       title = "รายงานการสั่งยาสมุนไพรและใบสั่งแผนฟื้นฟู (Prescriptions)";
       const prescriptions = historyItems.filter((h: any) => h.type?.toLowerCase() === "prescription");
       reportContent = `
          <h3>ประวัติการจัดยาสมุนไพรสัญชาตญาณเซลล์และเวชภัณฑ์</h3>
          <table class="report-table">
             <thead>
                <tr>
                   <th style="width:20%">วันที่ออกใบสั่ง</th>
                   <th style="width:30%">รายการแพทย์/ยา</th>
                   <th style="width:50%">วิธีรับประทานและข้อแนะนำฟื้นฟู</th>
                </tr>
             </thead>
             <tbody>
                ${prescriptions.length > 0 ? 
                   prescriptions.map((p: any) => `
                      <tr>
                         <td>${formatDate(p.createdAt)}</td>
                         <td><strong>${p.title}</strong></td>
                         <td style="white-space: pre-wrap;">${p.content}</td>
                      </tr>
                   `).join("")
                   : "<tr><td colspan='3' class='text-center'>ไม่พบประวัติการสั่งจ่ายยาในระบบ EMR ของคนไข้</td></tr>"
                }
             </tbody>
          </table>
       `;
    } else if (category === "สรุปผล AI") {
       title = "รายงานการประเมินปัญญาประดิษฐ์และ AI Triage (AI Clinical Insights)";
       const assessments = historyItems.filter((h: any) => h.type?.toLowerCase() === "ai assessment");
       const latestInsight = userData?.extra_data?.latest_precision_insight || "ยังไม่มีข้อมูลบทวิเคราะห์สรีรวิทยาฉบับปัจจุบัน";
       
       reportContent = `
          <h3>บทวิเคราะห์สรีรวิทยาและแผนพฤกษเคมี (Latest AI Clinical Report)</h3>
          <div class="insight-box" style="white-space: pre-wrap; font-family:inherit;">
             ${latestInsight}
          </div>
          
          <h3>ประวัติประเมินการคัดกรองอาการอัจฉริยะย้อนหลัง (AI Intake History)</h3>
          <table class="report-table">
             <thead>
                <tr>
                   <th style="width:20%">วันที่บันทึก</th>
                   <th style="width:30%">หัวข้อการคัดกรอง</th>
                   <th style="width:50%">บทสรุปวิเคราะห์ของระบบ</th>
                </tr>
             </thead>
             <tbody>
                ${assessments.length > 0 ? 
                   assessments.map((a: any) => `
                      <tr>
                         <td>${formatDate(a.createdAt)}</td>
                         <td><strong>${a.title}</strong></td>
                         <td style="white-space: pre-wrap;">${a.content}</td>
                      </tr>
                   `).join("")
                   : "<tr><td colspan='3' class='text-center'>ไม่พบประวัติประเมินอาการ AI ย้อนหลังในเวชระเบียน</td></tr>"
                }
             </tbody>
          </table>
       `;
    }

    const htmlDocument = `
       <!DOCTYPE html>
       <html>
       <head>
          <meta charset="utf-8">
          <title>${title}</title>
          <style>
             body { font-family: 'Sarabun', 'Helvetica Neue', Arial, sans-serif; padding: 40px; color: #282A29; line-height: 1.6; }
             .header { text-align: center; border-bottom: 3px double #282A29; padding-bottom: 18px; margin-bottom: 25px; }
             .logo { font-size: 22px; font-weight: bold; letter-spacing: 0.5px; }
             .report-title { font-size: 18px; font-weight: bold; margin-top: 8px; color: #111; }
             .meta-info { display: flex; justify-content: space-between; margin-bottom: 25px; font-size: 12.5px; color: #4B5563; border-bottom: 1px solid #E5E7EB; padding-bottom: 10px; }
             .report-table { width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 25px; }
             .report-table th, .report-table td { border: 1px solid #E5E7EB; padding: 10px; text-align: left; font-size: 12.5px; }
             .report-table th { background-color: #F9FAFB; font-weight: bold; color: #1F2937; }
             .text-danger { color: #DC2626; }
             .font-bold { font-weight: bold; }
             .insight-box { background-color: #F9FAFB; border-left: 4px solid #282A29; padding: 18px; border-radius: 6px; font-size: 12.5px; line-height: 1.65; margin-bottom: 25px; color: #374151; }
             .print-btn { display: block; width: 100%; text-align: center; margin-top: 35px; padding: 11px; background-color: #282A29; color: white; border: none; border-radius: 6px; font-weight: bold; font-size: 13.5px; cursor: pointer; }
             @media print {
                .print-btn { display: none; }
                html, body {
                   height: auto !important;
                   overflow: visible !important;
                }
                body { padding: 0; }
             }
          </style>
       </head>
       <body>
          <div class="header">
             <div class="logo">TSPI CLINICAL E-PORTAL</div>
             <div class="report-title">${title}</div>
          </div>
          
          <div class="meta-info">
             <div>
                <strong>HN:</strong> ${hn} &nbsp;|&nbsp; <strong>ชื่อคนไข้:</strong> ${patientName}
             </div>
             <div>
                <strong>วันที่จัดพิมพ์:</strong> ${new Date().toLocaleDateString("th-TH")}
             </div>
          </div>
          
          ${reportContent}
          
          <button class="print-btn" onclick="window.print()">พิมพ์เอกสารออกรายงาน / สั่งบันทึกเป็น PDF</button>
       </body>
       </html>
    `;
    
    return htmlDocument;
  };

  const handleConfirmDownload = () => {
    const docString = generateHTMLReport(selectedCategory);
    
    // Open in a new tab/window to bypass Safari and LINE Webview download limits
    const previewWindow = window.open("", "_blank");
    if (previewWindow) {
      previewWindow.document.write(docString);
      previewWindow.document.close();
      
      Swal.fire({
         title: "เปิดหน้าต่างพิมพ์รายงานสำเร็จ",
         text: `ระบบได้เปิดตัวอย่างรายงาน ${selectedCategory} ในแท็บใหม่เรียบร้อยแล้ว ท่านสามารถสั่งพิมพ์หรือบันทึกเป็น PDF ได้ทันที`,
         icon: "success",
         confirmButtonColor: "#282A29",
         confirmButtonText: "ตกลง"
      });
    } else {
      // Fallback download if popup is blocked
      Swal.fire({
         title: "บล็อกหน้าต่างป๊อปอัพ",
         text: "เบราว์เซอร์ของท่านทำการบล็อกป๊อปอัพ กรุณาอนุญาตการเปิดป๊อปอัพ หรือเลือกดาวน์โหลดไฟล์ HTML โดยตรง",
         icon: "warning",
         showCancelButton: true,
         confirmButtonColor: "#282A29",
         confirmButtonText: "ดาวน์โหลดไฟล์โดยตรง",
         cancelButtonText: "ยกเลิก"
      }).then((result) => {
         if (result.isConfirmed) {
            const blob = new Blob([docString], { type: "text/html" });
            const url = URL.createObjectURL(blob);
            
            const link = document.createElement("a");
            link.href = url;
            
            const fileLabel = selectedCategory === "เวชระเบียน" ? "medical_record" 
                           : selectedCategory === "ผลตรวจ Lab" ? "lab_results"
                           : selectedCategory === "ประวัติยา" ? "prescription_history"
                           : "ai_summary";
                            
            link.download = `tspi_${fileLabel}_${userData?.hn || "report"}.html`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            Swal.fire({
               title: "ดาวน์โหลดไฟล์สำเร็จ",
               text: "ท่านสามารถเปิดไฟล์ HTML และสั่งบันทึกเป็น PDF ได้เช่นกัน",
               icon: "success",
               confirmButtonColor: "#282A29"
            });
         }
      });
    }
  };

  return (
    <div className="bg-light min-vh-100 font-kanit pb-5 text-start">
      {/* Mini Header */}
      <div className="bg-white px-3 py-3 d-flex align-items-center gap-3 shadow-sm sticky-top border-bottom border-light">
        <Link href="/patient/dashboard" className="text-dark"><ArrowLeft size={24} /></Link>
        <div>
          <h5 className="fw-bold mb-0 text-dark">ข้อมูลสุขภาพ</h5>
          <p className="tiny text-muted mb-0">ประวัติการรักษาและเอกสาร</p>
        </div>
      </div>

      <div className="container-fluid p-3 max-w-md mx-auto">
        {/* Apple Health Style Segmented Control */}
        <div className="bg-secondary bg-opacity-10 rounded-3 p-1 d-flex mb-4">
           <button 
              onClick={() => setActiveTab("history")}
              className={`flex-grow-1 py-2 rounded-2 border-0 small fw-bold transition-all ${activeTab === 'history' ? 'bg-white text-dark shadow-sm' : 'bg-transparent text-muted'}`}
           >
              ประวัติการรักษา
           </button>
           <button 
              onClick={() => setActiveTab("trends")}
              className={`flex-grow-1 py-2 rounded-2 border-0 small fw-bold transition-all ${activeTab === 'trends' ? 'bg-white text-dark shadow-sm' : 'bg-transparent text-muted'}`}
           >
              แนวโน้มชีวภาพ
           </button>
           <button 
              onClick={() => setActiveTab("download")}
              className={`flex-grow-1 py-2 rounded-2 border-0 small fw-bold transition-all ${activeTab === 'download' ? 'bg-white text-dark shadow-sm' : 'bg-transparent text-muted'}`}
           >
              ศูนย์ดาวน์โหลด
           </button>
        </div>

        {/* Tab 1: Medical History List */}
        {activeTab === 'history' && (
           <div className="text-start animate-fade-in">
              <div className="position-relative mb-4">
                 <Search className="position-absolute top-50 start-0 translate-middle-y ms-3 text-muted" size={18} />
                 <input type="text" className="form-control rounded-4 ps-5 bg-white border-light shadow-sm py-3 small fw-medium text-dark" placeholder="ค้นหาประวัติการรักษา..." />
              </div>

              <h6 className="fw-bold text-dark mb-3 ps-1">รายการล่าสุด</h6>
              {loading ? (
                <div className="py-5 text-center">
                   <Loader2 className="animate-spin text-primary-custom mx-auto mb-3" size={32} />
                   <p className="small text-muted">กำลังโหลดประวัติ...</p>
                </div>
              ) : historyItems.length === 0 ? (
                 <div className="text-center py-5">
                    <div className="bg-white rounded-circle d-inline-flex align-items-center justify-content-center mb-3 shadow-sm" style={{width: '64px', height: '64px'}}>
                       <Database size={32} className="text-muted opacity-50" />
                    </div>
                    <h6 className="fw-bold text-dark mb-1">ไม่มีประวัติการรักษา</h6>
                    <p className="small text-muted mb-0">เมื่อมีข้อมูลการรักษาจะแสดงที่นี่</p>
                 </div>
              ) : (
                 <div className="d-grid gap-3">
                    {historyItems.map((item) => {
                       const styling = getIconAndColor(item.type);
                       return (
                       <div 
                         key={item.id} 
                         onClick={() => setSelectedItem(item)}
                         className="bg-white rounded-4 p-3 shadow-sm border border-light d-flex align-items-center gap-3 transition hover-shadow cursor-pointer"
                       >
                          <div className={`${styling.bg} rounded-circle d-flex align-items-center justify-content-center`} style={{width: '48px', height: '48px', fontSize: '24px'}}>
                             {styling.icon}
                          </div>
                          <div className="flex-grow-1 overflow-hidden">
                             <h6 className="fw-bold text-dark mb-1 text-truncate" style={{ fontSize: '13.5px' }}>{item.title || "การบันทึกประวัติ"}</h6>
                             <div className="d-flex align-items-center gap-2">
                                <span className="tiny text-muted" style={{ fontSize: '10px' }}>{formatDate(item.createdAt)} • {formatTime(item.createdAt)}</span>
                                <span className="badge bg-light text-dark border tiny px-2" style={{ fontSize: '9px' }}>{item.type || "ทั่วไป"}</span>
                             </div>
                             <p className="text-muted mb-0 small text-truncate mt-1.5" style={{ fontSize: '11px' }}>{item.content}</p>
                          </div>
                          <ChevronRight size={20} className="text-muted opacity-50" />
                       </div>
                    )})}
                 </div>
              )}
           </div>
        )}

        {/* Tab 2: Health Trends Chart (Recharts) */}
        {activeTab === 'trends' && (
           <div className="text-start animate-fade-in">
              <div className="bg-white rounded-4 p-3 shadow-sm border border-light mb-4">
                 <h6 className="fw-bold text-dark mb-3" style={{ fontFamily: 'Kanit, sans-serif', fontSize: '13.5px' }}>วิเคราะห์กราฟเส้นแนวโน้มสุขภาพระดับพหุมิติ</h6>
                 
                 {/* Biomarker Pill Selector */}
                 <div className="d-flex gap-1.5 overflow-auto pb-3 mb-3 border-bottom no-scrollbar">
                    {(["FBS", "HbA1c", "LDL", "CRP"] as const).map((bm) => (
                       <button
                          key={bm}
                          onClick={() => setSelectedBiomarker(bm)}
                          className={`btn btn-sm rounded-pill px-3 py-1.5 fw-bold text-nowrap transition-all border-0 ${
                             selectedBiomarker === bm 
                                ? "text-white" 
                                : "bg-light text-muted"
                          }`}
                          style={{ 
                             fontSize: '11px',
                             backgroundColor: selectedBiomarker === bm ? "#282A29" : "",
                          }}
                       >
                          {BIOMARKER_META[bm].label}
                       </button>
                    ))}
                 </div>

                 <div className="mb-2">
                    <span className="tiny text-muted d-block uppercase tracking-wider mb-0.5" style={{ fontSize: '10px' }}>ค่าวัดล่าสุดของคุณ (Current Value)</span>
                    <strong className="fs-5 text-dark" style={{ fontFamily: 'Kanit, sans-serif' }}>
                       {chartData.length > 0 ? `${chartData[chartData.length - 1][selectedBiomarker]} ${BIOMARKER_META[selectedBiomarker].unit}` : "--"}
                    </strong>
                    <p className="text-muted mt-1.5 mb-0" style={{ fontSize: '11.5px', lineHeight: '1.4' }}>{BIOMARKER_META[selectedBiomarker].description}</p>
                 </div>

                 {/* Recharts Canvas Container */}
                 <div className="w-100 mt-4" style={{ height: "240px", fontSize: "11px" }}>
                    {chartData.length === 0 ? (
                       <div className="h-100 d-flex flex-column align-items-center justify-content-center border border-dashed rounded-4 p-4 text-center">
                          <Microscope size={36} className="text-muted opacity-40 mb-2" />
                          <p className="small text-muted mb-0">ยังไม่มีข้อมูลบันทึกในระบบ EMR สำหรับผลแล็บนี้</p>
                          
                          <button
                            onClick={handleInjectDemoData}
                            disabled={isInjectingDemo}
                            className="btn btn-sm btn-outline-dark rounded-pill px-3 py-1.5 mt-3 fw-bold"
                            style={{ fontSize: '11px' }}
                          >
                             {isInjectingDemo ? "กำลังโหลด..." : "ทดลองโหลดข้อมูลสาธิตแล็บย้อนหลัง (Demo) 🧪"}
                          </button>
                       </div>
                    ) : (
                       <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={chartData} margin={{ top: 15, right: 15, left: -25, bottom: 0 }}>
                             <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                             <XAxis dataKey="formattedDate" stroke="#9CA3AF" />
                             <YAxis stroke="#9CA3AF" />
                             <Tooltip 
                                contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 4px 20px rgba(0,0,0,0.08)", fontFamily: "Kanit, sans-serif" }} 
                                labelStyle={{ fontWeight: "bold", color: "#374151" }}
                             />
                             <ReferenceLine 
                                y={BIOMARKER_META[selectedBiomarker].limit} 
                                stroke="#EF4444" 
                                strokeDasharray="4 4" 
                                label={{ value: `เกณฑ์ปกติ (${BIOMARKER_META[selectedBiomarker].limit})`, fill: '#EF4444', position: 'top', fontSize: 10, fontFamily: 'Kanit, sans-serif' }} 
                             />
                             <Line 
                                type="monotone" 
                                dataKey={selectedBiomarker} 
                                stroke={BIOMARKER_META[selectedBiomarker].color} 
                                strokeWidth={3} 
                                dot={{ r: 5, strokeWidth: 2 }} 
                                activeDot={{ r: 8 }} 
                             />
                          </LineChart>
                       </ResponsiveContainer>
                    )}
                 </div>
              </div>

              {/* Guide Card */}
              <div className="bg-white rounded-4 p-3 border border-light">
                 <span className="tiny text-muted d-block uppercase tracking-wider mb-1.5" style={{ fontSize: '10px' }}>คำชี้แจงการประมวลผลระบบ EMR</span>
                 <p className="mb-0 text-muted" style={{ fontSize: "11px", lineHeight: "1.4" }}>
                    * การอัปเดตข้อมูลแนวโน้มนี้จะเชื่อมต่อข้อมูลจากประวัติสุขภาพ EMR โดยอัตโนมัติ ซึ่งบันทึกได้ทั้งจากการพิมพ์บันทึกด้วยตนเองและผลวิเคราะห์ทางการแพทย์จากการเข้ารับบริการที่คลินิกจริง
                 </p>
              </div>
           </div>
        )}

        {/* Tab 3: Downloads Portal */}
        {activeTab === 'download' && (
           <div className="text-start animate-fade-in">
              <div className="bg-white rounded-4 p-4 shadow-sm border border-light mb-4">
                 <h6 className="fw-bold text-dark mb-3 d-flex align-items-center gap-2" style={{ fontFamily: 'Kanit, sans-serif', fontSize: '14px' }}>
                    <Layers size={20} className="text-primary-custom" /> เลือกประเภทเอกสารประวัติสุขภาพ
                 </h6>
                 
                 {/* Multi-category select Grid */}
                 <div className="row g-3">
                    {[
                       { title: "เวชระเบียน", icon: Database, color: "text-info" },
                       { title: "ผลตรวจ Lab", icon: Microscope, color: "text-primary-custom" },
                       { title: "ประวัติยา", icon: Shield, color: "text-success" },
                       { title: "สรุปผล AI", icon: Zap, color: "text-warning" },
                    ].map((c, i) => (
                       <div key={i} className="col-6">
                          <div 
                             onClick={() => setSelectedCategory(c.title)}
                             className={`p-3 border rounded-4 bg-light h-100 cursor-pointer transition d-flex flex-column align-items-center text-center ${
                                selectedCategory === c.title ? 'border-dark shadow-sm bg-white border-2' : 'border-light opacity-75'
                             }`}
                          >
                             <div className={`${c.color} mb-2 bg-white rounded-circle p-2 shadow-sm`}><c.icon size={24} /></div>
                             <p className="small fw-bold text-dark mb-0 mt-2">{c.title}</p>
                          </div>
                       </div>
                    ))}
                 </div>
              </div>

              {/* Format selection */}
              <div className="bg-white rounded-4 p-4 shadow-sm border border-light mb-4">
                 <h6 className="fw-bold text-dark mb-2.5" style={{ fontSize: '13.5px' }}>หัวข้อรายงานที่จะส่งออก</h6>
                 <div className="p-3 bg-light rounded-4 border mb-4">
                    <span className="tiny text-muted d-block uppercase tracking-wider mb-1">หมวดหมู่เอกสาร:</span>
                    <strong className="text-dark small">{selectedCategory}</strong>
                 </div>
                 
                 <button 
                   onClick={handleConfirmDownload}
                   className="btn btn-dark rounded-pill w-100 py-3 fw-bold d-flex align-items-center justify-content-center gap-2 shadow border-0" 
                   style={{ backgroundColor: '#282A29', fontSize: '14px' }}
                 >
                    <Download size={18} /> ยืนยันดาวน์โหลดเอกสาร PDF (HTML)
                 </button>
              </div>

              <div className="bg-dark rounded-4 p-4 text-center shadow">
                 <Lock size={22} className="text-success mb-2" />
                 <p className="tiny text-white text-opacity-75 mb-0" style={{ fontSize: '11px' }}>
                    ข้อมูลส่วนบุคคลของคุณถูกเข้ารหัสด้วยมาตรฐานความปลอดภัยระดับสูง (AES-256) ปลอดภัย 100%
                 </p>
              </div>
           </div>
        )}
      </div>

      {/* History Item Detail Modal Overlay */}
      {selectedItem && (
         <div className="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center bg-dark bg-opacity-50" style={{ zIndex: 1050, backdropFilter: "blur(4px)" }}>
            <div className="bg-white rounded-4 p-4 max-w-sm w-100 mx-3 shadow-lg border border-light animate-fade-in text-start">
               
               {/* Modal Header */}
               <div className="d-flex justify-content-between align-items-start border-bottom pb-3 mb-3">
                  <div>
                     <span className="badge bg-light text-dark border mb-1.5" style={{ fontSize: '10px' }}>{selectedItem.type}</span>
                     <h6 className="fw-bold text-dark mb-0" style={{ fontFamily: 'Kanit, sans-serif', fontSize: '15px' }}>{selectedItem.title}</h6>
                  </div>
                  <button type="button" className="btn-close" onClick={() => setSelectedItem(null)}></button>
               </div>

               {/* Modal Body */}
               <div className="mb-4" style={{ maxHeight: '300px', overflowY: 'auto', paddingRight: '5px' }}>
                  
                  {/* Timestamp Card */}
                  <div className="d-flex align-items-center gap-2.5 bg-light p-2.5 rounded-3 border mb-3">
                     <Clock size={15} className="text-muted" />
                     <div>
                        <span className="text-muted tiny d-block">วันและเวลาที่บันทึกข้อมูล</span>
                        <strong className="text-dark" style={{ fontSize: '11px' }}>
                           {formatDate(selectedItem.createdAt)} เวลา {formatTime(selectedItem.createdAt)} น.
                        </strong>
                     </div>
                  </div>

                  <label className="tiny text-muted uppercase tracking-wider mb-1.5 d-block">รายละเอียดเวชระเบียน:</label>
                  <div className="p-3 bg-light rounded-3 text-dark small leading-relaxed border" style={{ whiteSpace: 'pre-wrap', fontSize: '12px' }}>
                     {selectedItem.content}
                  </div>
               </div>

               {/* Modal Footer */}
               <div className="d-grid gap-2">
                  <button
                     type="button"
                     onClick={() => setSelectedItem(null)}
                     className="btn btn-dark rounded-pill py-2.5 fw-bold border-0"
                     style={{ backgroundColor: "#282A29", fontSize: "13px" }}
                  >
                     ปิดหน้าต่างเวชระเบียน
                  </button>
               </div>

            </div>
         </div>
      )}

      <style jsx>{`
        .bg-primary-custom, .btn-primary-custom { background-color: #0A5C8E; color: white; border: none; }
        .text-primary-custom { color: #0A5C8E; }
        .hover-shadow:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important; }
        .hover-border-primary:hover { border-color: #0A5C8E !important; }
        .transition { transition: all 0.2s ease; }
        
        .animate-fade-in { animation: fadeIn 0.35s ease-out; }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
      `}</style>
    </div>
  );
}
