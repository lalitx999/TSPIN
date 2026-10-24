
import { initializeApp, cert } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';
import * as dotenv from 'dotenv';
import * as path from 'path';

dotenv.config({ path: path.resolve(process.cwd(), '.env.local') });

const serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT_KEY || '{}');

if (!serviceAccount.project_id) {
  console.error('❌ Service account key not found in environment');
  process.exit(1);
}

initializeApp({
  credential: cert(serviceAccount)
});

const db = getFirestore();

async function countDocs() {
  const snapshot = await db.collection('tspi_knowledge_vectors').count().get();
  console.log(`📊 Documents in tspi_knowledge_vectors: ${snapshot.data().count}`);
}

countDocs().catch(console.error);
