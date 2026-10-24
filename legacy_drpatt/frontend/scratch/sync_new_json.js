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

    console.log('--- Syncing 281 Modules (New Structure) ---');
    const modulesRef = db.collection('tspi_modules_v3');
    
    for (const m of modulesData) {
      const id = m['Code /_Product ID'];
      if (!id) continue;
      
      const cleanM = {};
      for (const key in m) {
        // Replace / and . for Firestore safety
        const cleanKey = key.replace(/\//g, '_').replace(/\./g, '_').trim();
        cleanM[cleanKey] = m[key];
      }
      
      await modulesRef.doc(id).set(cleanM);
      console.log(`Uploaded Module ${id}`);
    }

    console.log('\n✅ UPDATE SUCCESS: 200_module_tspi.json is now live.');
    process.exit(0);
  } catch (err) {
    console.error('SYNC ERROR:', err.message);
    process.exit(1);
  }
}

sync();
