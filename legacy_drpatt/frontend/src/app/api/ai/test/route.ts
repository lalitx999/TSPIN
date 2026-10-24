
import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({ status: "ok", message: "API GET is working" });
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    return NextResponse.json({ status: "ok", message: "API POST is working", received: body });
  } catch (e) {
    return NextResponse.json({ status: "error", message: "POST failed to parse body" }, { status: 400 });
  }
}
