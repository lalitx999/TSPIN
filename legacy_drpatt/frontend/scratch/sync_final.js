const admin = require('firebase-admin');
const fs = require('fs');

const serviceAccount = require('/media/tanchon-lita/Data/Pr/dr_pat/backend_engine_v-twin/tspi-ee68e-firebase-adminsdk-fbsvc-4d7ec1a2d3.json');

if (!admin.apps.length) {
  admin.initializeApp({
    credential: admin.credential.cert(serviceAccount)
  });
}

const db = admin.firestore();

async function sync() {
  try {
    const axesData = JSON.parse(fs.readFileSync('/media/tanchon-lita/Data/Pr/dr_pat/data/TSPI_36_axes.json', 'utf8'));
    const modulesData = JSON.parse(fs.readFileSync('/media/tanchon-lita/Data/Pr/dr_pat/data/200_last.json', 'utf8'));

    console.log('--- Syncing 36 Axes ---');
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

    console.log('\n--- Syncing 200 Modules ---');
    const modulesRef = db.collection('tspi_modules_v3');
    const actualModules = modulesData.slice(1); // Skip header
    for (const m of actualModules) {
      const id = m['Code /'] || m['Product ID'];
      if (!id || id === 'Product ID') continue;
      
      const cleanM = {};
      for (const key in m) {
        const cleanKey = key.replace(/\//g, '_').replace(/\./g, '_').trim();
        cleanM[cleanKey] = m[key];
      }
      
      await modulesRef.doc(id).set(cleanM);
      console.log(`Uploaded Module ${id}`);
    }

    console.log('\n✅ MISSION ACCOMPLISHED! Data is now live on Firestore.');
    process.exit(0);
  } catch (err) {
    console.error('SYNC ERROR:', err.message);
    process.exit(1);
  }
}

sync();
