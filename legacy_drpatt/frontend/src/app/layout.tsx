import type { Metadata } from "next";
import { Inter, Sarabun } from "next/font/google";
import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap-icons/font/bootstrap-icons.css";
import "./globals.css";
import BootstrapClient from "@/components/BootstrapClient";
import { LiffProvider } from "@/components/providers/LiffProvider";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const sarabun = Sarabun({
  variable: "--font-sarabun",
  subsets: ["thai"],
  weight: ["300", "400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: "TSPI Clinic | Clinical Intelligence Platform",
  description: "Next-generation AI engine for patient care and precision medicine — วิเคราะห์เชิงลึกด้วยกลไกชีววิทยา 39 แกน",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "TSPI คลินิก",
  },
  icons: {
    icon: "/drp.ico",
    apple: "/logo_tspi.jpg",
    shortcut: "/drp.ico",
  },
  other: {
    "mobile-web-app-capable": "yes",
    "apple-mobile-web-app-capable": "yes",
    "apple-mobile-web-app-status-bar-style": "default",
    "apple-mobile-web-app-title": "TSPI คลินิก",
    "application-name": "TSPI Clinic",
    "msapplication-TileColor": "#0A5C8E",
    "msapplication-TileImage": "/logo_tspi.jpg",
    "theme-color": "#0A5C8E",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${sarabun.variable}`}>
      <body>
        <LiffProvider>
          <BootstrapClient />
          {children}
        </LiffProvider>
      </body>
    </html>
  );
}
