const admin = require("firebase-admin");
const fs = require("fs");
const path = require("path");
const serviceAccount = require("/media/tanchon-lita/Data/Pr/dr_pat/backend_engine_v-twin/tspi-ee68e-firebase-adminsdk-fbsvc-4d7ec1a2d3.json");

if (!admin.apps.length) {
  admin.initializeApp({
    credential: admin.credential.cert(serviceAccount),
    projectId: "tspi-ee68e",
  });
}

const db = admin.firestore();
const sourceDir = "/media/tanchon-lita/Data/Pr/dr_pat/data/extracted_tables/";

async function bulkMigrate() {
  const files = fs.readdirSync(sourceDir).filter(f => f.endsWith(".json"));
  console.log(`🚀 Found ${files.length} collections to migrate...`);

  for (const file of files) {
    const collectionName = path.basename(file, ".json");
    const data = JSON.parse(fs.readFileSync(path.join(sourceDir, file), "utf8"));

    if (data.length === 0) {
      console.log(`⚪ Creating empty collection: ${collectionName}`);
      await db.collection(collectionName).doc("_status").set({
        initialized: true,
        migratedAt: new Date().toISOString(),
        info: "Empty table from SQL"
      });
      continue;
    }

    console.log(`📦 Migrating collection: ${collectionName} (${data.length} rows)`);

    // Batch upload (Firestore limit 500 per batch)
    const batchSize = 500;
    for (let i = 0; i < data.length; i += batchSize) {
      const batch = db.batch();
      const chunk = data.slice(i, i + batchSize);

      chunk.forEach((item, index) => {
        // Use 'id' as docId if exists, otherwise let Firestore generate it
        const docId = item.id ? String(item.id) : null;
        const ref = docId ? db.collection(collectionName).doc(docId) : db.collection(collectionName).doc();
        batch.set(ref, item, { merge: true });
      });

      await batch.commit();
    }
    console.log(`✅ Finished ${collectionName}`);
  }

  console.log("🏁 ALL TABLES MIGRATED SUCCESSFULLY!");
}

bulkMigrate().catch(console.error);
