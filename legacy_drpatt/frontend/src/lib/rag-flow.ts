import { z } from 'zod';
import { ai, embedder } from './genkit';
import { getFirestore, FieldValue } from 'firebase-admin/firestore';
import { initializeApp, getApps, cert } from 'firebase-admin/app';
import { defineFirestoreRetriever } from '@genkit-ai/firebase';

// Initialize Firebase Admin for script/backend usage
if (getApps().length === 0) {
  initializeApp();
}

// Fix: Disable Firestore internal telemetry to prevent recursion with GenKit OTEL
process.env.GOOGLE_CLOUD_FIRESTORE_TELEMETRY_DISABLED = 'true';

const db = getFirestore();
const collectionName = 'tspi_knowledge_vectors';

/**
 * TSPI Vector Retriever
 * Fetches relevant scientific context based on clinical queries
 */
export const tspiRetriever = defineFirestoreRetriever(ai, {
  name: 'tspiRetriever',
  firestore: db,
  collection: collectionName,
  embedder: embedder,
  vectorField: 'embedding',
  contentField: 'text',
});

/**
 * Index Data Flow
 * Manual implementation of indexing using Firestore Admin SDK
 * because defineFirestoreIndexer might not be available in this version.
 */
export const indexDataFlow = ai.defineFlow(
  {
    name: 'indexDataFlow',
    inputSchema: z.object({
      text: z.string(),
      source: z.string(),
      axis: z.string().optional(),
      type: z.enum(['SOP', 'Research', 'CaseStudy', 'Module']).optional(),
    }),
  },
  async (input) => {
    // Simple chunking logic
    const chunks = input.text.split('\n\n').filter(c => c.length > 50);
    console.log(`Chunking ${input.source} into ${chunks.length} segments...`);

    for (const chunk of chunks) {
      // 1. Generate embedding
      const embedResult = await ai.embed({
        embedder: embedder,
        content: chunk,
      });

      if (embedResult && embedResult.length > 0) {
        // 2. Save to Firestore
        await db.collection(collectionName).add({
          text: chunk,
          embedding: FieldValue.vector(embedResult[0].embedding),
          source: input.source,
          axis: input.axis || null,
          type: input.type || null,
          indexedAt: FieldValue.serverTimestamp(),
        });
      }
    }
    
    return { status: 'success', chunksIndexed: chunks.length };
  }
);
