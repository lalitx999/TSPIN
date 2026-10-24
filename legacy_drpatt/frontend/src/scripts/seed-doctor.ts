import { initializeApp } from "firebase/app";
import { getFirestore, doc, setDoc } from "firebase/firestore";
import { getAuth, createUserWithEmailAndPassword } from "firebase/auth";
import * as dotenv from 'dotenv';

dotenv.config({ path: '.env.local' });

const firebaseConfig = {
    apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
    authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
    projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
    storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
    messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
    appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID
};

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);
const auth = getAuth(app);

async function seedDoctor() {
    const email = "doctor@tspi.com";
    const password = "Tspi123456";
    
    console.log(`🚀 Creating doctor account: ${email}...`);
    
    try {
        const userCredential = await createUserWithEmailAndPassword(auth, email, password);
        const user = userCredential.user;
        
        await setDoc(doc(db, "doctors", user.uid), {
            email: email,
            role: "doctor",
            displayName: "Dr. TSPI Specialist",
            createdAt: new Date().toISOString()
        });
        
        console.log("✅ Doctor account created successfully!");
        console.log("Login with:");
        console.log(`Email: ${email}`);
        console.log(`Password: ${password}`);
        process.exit(0);
    } catch (error: any) {
        if (error.code === 'auth/email-already-in-use') {
            console.log("ℹ️ Account already exists, skipping creation.");
            process.exit(0);
        } else {
            console.error("❌ Failed to create account:", error);
            process.exit(1);
        }
    }
}

seedDoctor();
