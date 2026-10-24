import * as admin from "firebase-admin";

const getDbAdmin = () => {
  if (!admin.apps.length) {
    const projectId = process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID;
    const clientEmail = process.env.FIREBASE_CLIENT_EMAIL;
    const privateKey = process.env.FIREBASE_PRIVATE_KEY?.replace(/\\n/g, "\n");

    if (!projectId || !clientEmail || !privateKey) {
      console.error("❌ Firebase Admin Error: Missing environment variables!");
      // Don't initialize if credentials are missing, return a dummy or let it fail gracefully later
      return null;
    }

    try {
      admin.initializeApp({
        credential: admin.credential.cert({
          projectId,
          clientEmail,
          privateKey,
        }),
      });
      console.log("✅ Firebase Admin Initialized");
    } catch (error) {
      console.error("❌ Firebase Admin Initialization Failed:", error);
      return null;
    }
  }
  return admin.firestore();
};

const dbAdmin = getDbAdmin();
export { dbAdmin, getDbAdmin };
