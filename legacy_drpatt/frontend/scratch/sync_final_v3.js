const admin = require('firebase-admin');
const fs = require('fs');

const sa = require('/media/tanchon-lita/Data/Pr/dr_pat/backend_engine_v-twin/tspi-ee68e-firebase-adminsdk-fbsvc-4d7ec1a2d3.json');
if (!admin.apps.length) admin.initializeApp({ credential: admin.credential.cert(sa) });
const db = admin.firestore();

async function sync() {
  // --- 1. SYNC 39 AXES ---
  const axesRaw = JSON.parse(fs.readFileSync('/media/tanchon-lita/Data/Pr/dr_pat/data/39_last_x.json', 'utf8'));
  const axesRef = db.collection('tspi_axes_v4');
  let axisCount = 0;

  for (const domain of axesRaw.domains) {
    if (!domain.axes || domain.axes.length === 0) continue;
    for (const axis of domain.axes) {
      await axesRef.doc(`AXIS_${axis.axis_id}`).set({
        ...axis,
        domain_id: domain.domain_id,
        domain_title: domain.title
      });
      axisCount++;
    }
  }
  console.log(`✅ Axes synced: ${axisCount} axes`);

  // --- 2. SYNC 200 MODULES ---
  const modRaw = JSON.parse(fs.readFileSync('/media/tanchon-lita/Data/Pr/dr_pat/data/200_module_tspi.json', 'utf8'));
  const modRef = db.collection('tspi_modules_v4');
  let modCount = 0;

  for (const m of modRaw.data) {
    const id = m['Code /_Product ID'];
    if (!id || String(id).trim() === '') continue;
    const clean = {};
    for (const key in m) {
      clean[key.replace(/\//g, '_').replace(/\./g, '_').trim()] = m[key];
    }
    await modRef.doc(String(id).trim()).set(clean);
    modCount++;
  }
  console.log(`✅ Modules synced: ${modCount} modules`);
  console.log('🏆 ALL DONE — tspi_axes_v4 & tspi_modules_v4 are live!');
  process.exit(0);
}

sync().catch(err => { console.error('ERROR:', err.message); process.exit(1); });
