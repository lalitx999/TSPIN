import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  try {
    const { text, source, axis, type } = await req.json();

    if (!text || !source) {
      return NextResponse.json({ error: 'Missing text or source' }, { status: 400 });
    }

    // Extract axis_id from axis string (e.g. "Axis 12: Adrenal Reserve" -> 12)
    let axisId = 0;
    if (axis && axis !== "General") {
      const match = axis.match(/Axis\s+(\d+)/i);
      if (match) {
        axisId = parseInt(match[1], 10);
      }
    }

    console.log(`📚 Indexing Knowledge Base to Django PostgreSQL: ${source} (Axis ID: ${axisId})`);

    const authHeader = req.headers.get("Authorization");

    let result;
    try {
      // Proxy request to Django knowledge-segments endpoint (which computes embeddings)
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";
      const res = await fetch(`${apiBase}/api/knowledge-segments/`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          ...(authHeader ? { "Authorization": authHeader } : {})
        },
        body: JSON.stringify({
          title: source,
          content: text,
          source: source,
          axis_id: axisId
        })
      });

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`Django backend returned status ${res.status}: ${errorText}`);
      }

      const data = await res.json();
      result = { success: true, id: String(data.id), mode: "django_postgres" };
    } catch (apiError: any) {
      console.error("❌ Django indexing failed:", apiError.message);
      throw apiError;
    }

    return NextResponse.json(result);
  } catch (error: any) {
    console.error('❌ Index Error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
