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
    const rawData = JSON.parse(fs.readFileSync('/media/tanchon-lita/Data/Pr/dr_pat/data/200_module_tspi.json', 'utf8'));
    const modulesData = rawData.data;

    console.log('--- Syncing Modules (Strict ID Check) ---');
    const modulesRef = db.collection('tspi_modules_v3');
    let count = 0;
    
    for (const m of modulesData) {
      const id = m['Code /_Product ID'];
      if (!id || String(id).trim() === '') {
        console.warn('Skipping record with empty ID');
        continue;
      }
      
      const cleanM = {};
      for (const key in m) {
        const cleanKey = key.replace(/\//g, '_').replace(/\./g, '_').trim();
        cleanM[cleanKey] = m[key];
      }
      
      await modulesRef.doc(String(id).trim()).set(cleanM);
      count++;
    }

    console.log(`\n✅ UPDATE SUCCESS: ${count} modules are now live.`);
    process.exit(0);
  } catch (err) {
    console.error('SYNC ERROR:', err.message);
    process.exit(1);
  }
}

sync();
