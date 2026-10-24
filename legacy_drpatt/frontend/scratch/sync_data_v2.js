const admin = require('firebase-admin');
const fs = require('fs');

// Attempt to use environment variables for Firebase
if (!admin.apps.length) {
  try {
    admin.initializeApp({
      credential: admin.credential.applicationDefault(),
      projectId: 'dr-pat-tspi' // Adjust if project ID is different
    });
  } catch (e) {
    console.log('Default initialization failed, trying service account...');
    const saPath = '/media/tanchon-lita/Data/Pr/dr_pat/frontend/service-account.json';
    if (fs.existsSync(saPath)) {
      admin.initializeApp({ credential: admin.credential.cert(require(saPath)) });
    } else {
      console.error('CRITICAL: No Firebase credentials found!');
      process.exit(1);
    }
  }
}

const db = admin.firestore();

async function sync() {
  try {
    const axesData = JSON.parse(fs.readFileSync('/media/tanchon-lita/Data/Pr/dr_pat/data/TSPI_36_axes.json', 'utf8'));
    const modulesData = JSON.parse(fs.readFileSync('/media/tanchon-lita/Data/Pr/dr_pat/data/200_last.json', 'utf8'));

    console.log('Syncing Axes...');
    const axesRef = db.collection('tspi_axes_v3');
    for (const domain of axesData.domains) {
      for (const axis of domain.axes) {
        await axesRef.doc(`AXIS_${axis.axis_id}`).set({
          ...axis,
          domain_id: domain.domain_id,
          domain_title: domain.title
        });
      }
    }
    console.log('Axes Synced.');

    console.log('Syncing Modules...');
    const modulesRef = db.collection('tspi_modules_v3');
    const actualModules = modulesData.slice(1);
    for (const m of actualModules) {
      const id = m['Code /'] || m['Product ID'];
      if (!id || id === 'Product ID') continue;
      
      // Clean keys for Firestore (no / allowed in some cases, though usually fine, let's be safe)
      const cleanM = {};
      for (const key in m) {
        const cleanKey = key.replace(/\//g, '_').replace(/\./g, '_').trim();
        cleanM[cleanKey] = m[key];
      }
      
      await modulesRef.doc(id).set(cleanM);
    }
    console.log('Modules Synced.');
    process.exit(0);
  } catch (err) {
    console.error('SYNC ERROR:', err.message);
    process.exit(1);
  }
}

sync();
