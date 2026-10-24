const admin = require("firebase-admin");
const fs = require("fs");
const serviceAccount = require("/media/tanchon-lita/Data/Pr/dr_pat/backend_engine_v-twin/tspi-ee68e-firebase-adminsdk-fbsvc-4d7ec1a2d3.json");

if (!admin.apps.length) {
  admin.initializeApp({
    credential: admin.credential.cert(serviceAccount),
    projectId: "tspi-ee68e",
  });
}

const db = admin.firestore();
const dataPath = "/media/tanchon-lita/Data/Pr/dr_pat/data/extracted_admins.json";
const admins = JSON.parse(fs.readFileSync(dataPath, "utf8"));

async function run() {
  console.log(`Starting migration for ${admins.length} admins/doctors...`);
  let batch = db.batch();
  let count = 0;

  for (const a of admins) {
    // Use userID as ID (e.g., A0001)
    const docId = String(a.userID || a.id);
    const ref = db.collection("doctors").doc(docId);
    
    const cleanData = {
      uid: a.userID,
      username: a.username,
      fname: a.fname,
      lname: a.lname,
      email: a.email,
      phone: a.phone,
      position: a.positionID === "1" ? "Owner/Admin" : (a.positionID === "3" ? "Doctor" : "Staff"),
      branchId: a.branchID,
      role: a.positionID === "3" ? "doctor" : "admin",
      status: "active",
      updatedAt: a.update_at || new Date().toISOString(),
      createdAt: a.create_at || new Date().toISOString(),
      profile: {
        fname_en: a.fname_en || null,
        lname_en: a.lname_en || null,
        address: a.address || null
      }
    };

    batch.set(ref, cleanData, { merge: true });
    count++;
  }

  await batch.commit();
  console.log("Admin migration finished successfully!");
}

run().catch(console.error);
