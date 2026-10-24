import { NextResponse } from 'next/server';
import { clinicalCopilotFlow } from '@/lib/clinical-copilot';

export async function POST(req: Request) {
  try {
    const { patientId, message, history } = await req.json();

    if (!patientId || !message) {
      return NextResponse.json({ error: 'Missing patientId or message' }, { status: 400 });
    }

    const result = await clinicalCopilotFlow({
      patientId,
      message,
      history
    });

    return NextResponse.json(result);
  } catch (error: any) {
    console.error('Copilot API Error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
