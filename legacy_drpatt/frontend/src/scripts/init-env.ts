import * as dotenv from 'dotenv';
import path from 'path';

// Load environment variables immediately
dotenv.config({ path: path.resolve(process.cwd(), '.env.local') });

// Disable Firestore internal telemetry to prevent recursion with GenKit OTEL
// This must be set before Firestore/GenKit modules are loaded
process.env.GOOGLE_CLOUD_FIRESTORE_TELEMETRY_DISABLED = 'true';
process.env.OTEL_SDK_DISABLED = 'true';
process.env.GENKIT_ENV = 'prod'; // Disable dev UI/telemetry in genkit

// Set GCLOUD_PROJECT so firebase-admin can find the project ID
if (process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID) {
  process.env.GCLOUD_PROJECT = process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID;
  process.env.GOOGLE_CLOUD_PROJECT = process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID;
}

console.log('🔧 Environment initialized. Project:', process.env.GCLOUD_PROJECT);
