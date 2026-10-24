import { initializeApp, cert } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const serviceAccount = require('../../service-account.json');

initializeApp({
  credential: cert(serviceAccount)
});

const db = getFirestore();

async function main() {
  const snapshot = await db.collection('modules').limit(2).get();
  snapshot.forEach(doc => {
    console.log(doc.id, '=>', doc.data());
  });
  
  const axesSnap = await db.collection('axes').limit(2).get();
  axesSnap.forEach(doc => {
     console.log('Axis:', doc.id, '=>', doc.data());
  });
}
main();
