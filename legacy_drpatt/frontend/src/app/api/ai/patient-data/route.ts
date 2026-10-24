import { NextResponse } from 'next/server';
import { getFirestore, Timestamp } from 'firebase-admin/firestore';
import { getApps, initializeApp } from 'firebase-admin/app';

// Init Admin SDK (if not already)
if (getApps().length === 0) {
  const projectId = process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || 'tspi-ee68e';
  const saKey = process.env.FIREBASE_SERVICE_ACCOUNT_KEY;
  if (saKey) {
    initializeApp({
      credential: JSON.parse(saKey),
      projectId,
    });
  } else {
    initializeApp({ projectId });
  }
}

const db = getFirestore();

export async function POST(req: Request) {
  try {
    const { patientId } = await req.json();

    if (!patientId) {
      return NextResponse.json({ error: 'Patient ID is required' }, { status: 400 });
    }

    console.log(`📡 Fetching patient: ${patientId}`);

    // Fetch patient from Firestore
    const patientDoc = await db.collection('patients').doc(patientId).get();
    if (!patientDoc.exists) {
      return NextResponse.json({ error: `Patient ${patientId} not found` }, { status: 404 });
    }

    const data = patientDoc.data()!;

    // Fetch omics if available
    let omics: any = {};
    try {
      const omicsDoc = await db.collection('patient_omics').doc(patientId).get();
      if (omicsDoc.exists) omics = omicsDoc.data() || {};
    } catch {}

    // Fetch scores if available
    let scores: any = {};
    try {
      const scoresDoc = await db.collection('patient_scores').doc(patientId).get();
      if (scoresDoc.exists) scores = scoresDoc.data() || {};
    } catch {}

    // Return clean patient data
    const patientData = {
      profile: {
        name: `${data.firstName || ''} ${data.lastName || ''}`.trim() || patientId,
        gender: data.gender || 'unknown',
        birthDate: data.birthDate,
        bloodType: data.bloodType,
        allergies: data.allergies || [],
      },
      labs: data.labs || {},
      symptoms: data.symptoms || [],
      medications: data.medications || [],
      genomics: omics.genomics || {},
      microbiome: omics.microbiome || {},
      proteomics: omics.proteomics || {},
      biologicalScores: scores.axes || data.axes || {},
    };

    return NextResponse.json({
      patientId,
      patientName: patientData.profile.name,
      data: patientData,
      timestamp: new Date().toISOString(),
    });
  } catch (error: any) {
    console.error('❌ Patient fetch error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
