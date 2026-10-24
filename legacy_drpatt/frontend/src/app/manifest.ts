import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "TSPI Clinic | Patient Portal",
    short_name: "TSPI คลินิก",
    description: "ระบบดูแลสุขภาพแม่นยำส่วนบุคคล ขับเคลื่อนด้วย AI วิเคราะห์ 39 แกนสรีรวิทยา",
    start_url: "/patient/dashboard",
    display: "standalone",
    orientation: "portrait",
    background_color: "#F6F6F6",
    theme_color: "#0A5C8E",
    categories: ["health", "medical", "lifestyle"],
    lang: "th",
    icons: [
      {
        src: "/logo_tspi.jpg",
        sizes: "192x192",
        type: "image/jpeg",
        purpose: "any",
      },
      {
        src: "/logo_tspi.jpg",
        sizes: "512x512",
        type: "image/jpeg",
        purpose: "maskable",
      },
      {
        src: "/pwa_logo.jpg",
        sizes: "512x512",
        type: "image/jpeg",
        purpose: "any",
      },
    ],
    shortcuts: [
      {
        name: "ซักประวัติอาการ AI",
        short_name: "AI Chat",
        description: "เริ่มการซักประวัติอาการกับ AI",
        url: "/patient/ai-intake",
      },
      {
        name: "ตารางนัดหมาย",
        short_name: "นัดหมาย",
        description: "ดูตารางนัดหมายแพทย์",
        url: "/patient/appointments",
      },
      {
        name: "ประวัติสุขภาพ",
        short_name: "ประวัติ",
        description: "ดูประวัติการรักษาและผลตรวจ",
        url: "/patient/history",
      },
    ],
  };
}
