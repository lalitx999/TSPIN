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

async function checkDuplicates() {
  console.log('Fetching modules from tspi_modules...');
  const snapshot = await db.collection('tspi_modules').get();
  console.log(`Total documents fetched: ${snapshot.size}`);

  const idCounts: Record<string, number> = {};
  const codeCounts: Record<string, number> = {};
  const nameCounts: Record<string, number> = {};

  snapshot.docs.forEach(doc => {
    const data = doc.data();
    const id = doc.id;
    const moduleCode = data["PhytoCore Code"] || data.phytocore_code || data.module_code || id;
    const name = data["Product Derived From"] || data.product_derived_from || data.name || id;

    idCounts[id] = (idCounts[id] || 0) + 1;
    codeCounts[moduleCode] = (codeCounts[moduleCode] || 0) + 1;
    nameCounts[name] = (nameCounts[name] || 0) + 1;
  });

  console.log('\n--- Duplicate document IDs (should be 0) ---');
  let duplicateIds = 0;
  for (const [id, count] of Object.entries(idCounts)) {
    if (count > 1) {
      console.log(`ID: "${id}" appears ${count} times`);
      duplicateIds++;
    }
  }
  if (duplicateIds === 0) console.log('None! All Firestore document IDs are perfectly unique.');

  console.log('\n--- Duplicate Module Codes (e.g. H-012) ---');
  let duplicateCodes = 0;
  for (const [code, count] of Object.entries(codeCounts)) {
    if (count > 1) {
      console.log(`Code: "${code}" appears ${count} times`);
      duplicateCodes++;
    }
  }
  console.log(`Total unique codes with duplicates: ${duplicateCodes}`);

  console.log('\n--- Duplicate Names ---');
  let duplicateNames = 0;
  for (const [name, count] of Object.entries(nameCounts)) {
    if (count > 1) {
      // Limit printing to avoid flooding
      if (duplicateNames < 10) {
        console.log(`Name: "${name}" appears ${count} times`);
      }
      duplicateNames++;
    }
  }
  console.log(`Total unique names with duplicates: ${duplicateNames}`);
}

checkDuplicates().catch(console.error);
