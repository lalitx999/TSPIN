const { initializeApp } = require("firebase/app");
const { getFirestore, collection, getDocs } = require("firebase/firestore");
require("dotenv").config({ path: ".env.local" });

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
  measurementId: process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID,
};

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

async function countModules() {
  const snap = await getDocs(collection(db, "tspi_modules_v4"));
  console.log("Total raw documents in Firestore collection (tspi_modules_v4):", snap.size);

  const seenCodes = new Set();
  const seenNames = new Set();
  let validCount = 0;
  let deDuplicatedCount = 0;

  snap.docs.forEach((d) => {
    const data = d.data();
    const rawName = data["Product Derived From"] || data.product_derived_from || data.name || d.id;
    const rawCode = data["PhytoCore Code"] || data.phytocore_code || data.module_code || d.id;

    if (!rawName || rawName === "Unknown Module" || !rawCode) {
      return;
    }

    validCount++;

    const normalizedName = String(rawName).trim().toUpperCase();
    const normalizedCode = String(rawCode).trim().toUpperCase();

    if (seenCodes.has(normalizedCode) || seenNames.has(normalizedName)) {
      return;
    }

    seenCodes.add(normalizedCode);
    seenNames.add(normalizedName);
    deDuplicatedCount++;
  });

  console.log("Valid modules count:", validCount);
  console.log("De-duplicated modules count (active in UI):", deDuplicatedCount);
  
  // Exit script
  process.exit(0);
}

countModules().catch(err => {
  console.error(err);
  process.exit(1);
});
