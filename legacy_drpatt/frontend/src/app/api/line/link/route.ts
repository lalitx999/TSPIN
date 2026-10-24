import { NextResponse } from "next/server";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { token, phone } = body;

    if (!token || !phone) {
      return NextResponse.json({ error: "Token and Phone number are required" }, { status: 400 });
    }

    const backendBaseUrl = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";
    const res = await fetch(`${backendBaseUrl}/api/line/link/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error: any) {
    console.error("❌ Link API Error:", error);
    return NextResponse.json({ error: "Internal Server Error: " + error.message }, { status: 500 });
  }
}
