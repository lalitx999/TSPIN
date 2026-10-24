import { NextResponse } from 'next/server';
import { biologicalScoringFlow } from '@/lib/scoring-flow';
import { medicalDb } from '@/lib/medical-data';
import { Timestamp } from 'firebase/firestore';

export async function POST(req: Request) {
  try {
    const { patientId, biomarkers, doctorId } = await req.json();
    
    if (!patientId) {
      return NextResponse.json({ error: 'Patient ID is required' }, { status: 400 });
    }

    // 1. Execute the GenKit Flow (Layer E - Proprietary Logic)
    const result = await biologicalScoringFlow(biomarkers);
    
    // 2. Persist to Firestore
    const axis1Score = {
      axisId: 1,
      axisName: 'Systemic Inflammatory Load',
      score: result.axis1.score,
      updatedAt: Timestamp.now(),
      markers: biomarkers
    };

    await medicalDb.updateBiologicalScores(patientId, {
      '1': axis1Score
    });

    // 3. Log Audit Trail (PDPA Compliance)
    await medicalDb.logAccess(
      doctorId || 'system',
      patientId,
      'CALCULATE_BIOLOGICAL_SCORE',
      'E'
    );
    
    return NextResponse.json({
      ...result,
      persisted: true,
      timestamp: new Date().toISOString()
    });
  } catch (error: any) {
    console.error('Scoring Flow Error:', error);
    return NextResponse.json(
      { error: 'Failed to calculate biological score', details: error.message },
      { status: 500 }
    );
  }
}
