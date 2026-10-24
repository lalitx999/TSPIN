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
const dataPath = "/media/tanchon-lita/Data/Pr/dr_pat/data/extracted_patients.json";
const patients = JSON.parse(fs.readFileSync(dataPath, "utf8"));

async function run() {
  console.log(`Starting migration for ${patients.length} patients...`);
  let batch = db.batch();
  let count = 0;

  for (const p of patients) {
    const docId = String(p.userHN || p.userID || p.id);
    const ref = db.collection("patients").doc(docId);
    
    const cleanData = {
      hn: p.userHN || null,
      fname: p.fname || "",
      lname: p.lname || "",
      phone: p.phone || "",
      age: p.age || null,
      sex: p.sex || "",
      status: "active",
      clinical_profile: {
        disease: p.disease || "",
        smoking: p.smoking || "no",
        drink: p.drink || "no",
        symptoms: p.symptoms || ""
      }
    };

    batch.set(ref, cleanData, { merge: true });
    count++;

    if (count % 400 === 0) {
      await batch.commit();
      batch = db.batch();
      console.log(`Progress: ${count}/${patients.length}`);
    }
  }

  await batch.commit();
  console.log("Migration finished successfully!");
}

run().catch(console.error);
