const admin = require('firebase-admin');
const fs = require('fs');
const path = require('path');

// Initialize Firebase Admin (Using local credentials if available or environment)
if (!admin.apps.length) {
  // Try to find the service account key
  const serviceAccountPath = '/media/tanchon-lita/Data/Pr/dr_pat/frontend/service-account.json';
  if (fs.existsSync(serviceAccountPath)) {
    const serviceAccount = require(serviceAccountPath);
    admin.initializeApp({
      credential: admin.credential.cert(serviceAccount)
    });
  } else {
    // Fallback to default
    admin.initializeApp();
  }
}

const db = admin.firestore();

async function syncData() {
  const axesData = JSON.parse(fs.readFileSync('/media/tanchon-lita/Data/Pr/dr_pat/data/TSPI_36_axes.json', 'utf8'));
  const modulesData = JSON.parse(fs.readFileSync('/media/tanchon-lita/Data/Pr/dr_pat/data/200_last.json', 'utf8'));

  console.log('--- Syncing Axes ---');
  const axesRef = db.collection('tspi_axes_v3');
  for (const domain of axesData.domains) {
    for (const axis of domain.axes) {
      const docId = `AXIS_${axis.axis_id}`;
      await axesRef.doc(docId).set({
        ...axis,
        domain_id: domain.domain_id,
        domain_title: domain.title
      });
      console.log(`Uploaded ${docId}`);
    }
  }

  console.log('\n--- Syncing Modules ---');
  const modulesRef = db.collection('tspi_modules_v3');
  // Skip the first element (header)
  const actualModules = modulesData.slice(1);
  for (const module of actualModules) {
    const docId = module['Code /'] || module['Product ID'];
    if (docId && docId !== 'Product ID') {
      await modulesRef.doc(docId).set(module);
      console.log(`Uploaded Module ${docId}`);
    }
  }

  console.log('\n✅ ALL DONE! Data synced to Firestore.');
  process.exit(0);
}

syncData().catch(err => {
  console.error(err);
  process.exit(1);
});
