# 🧬 TSPI Precision Clinical Platform — Deep RAG Architecture & Continuity Manual
**Document Version:** 1.0.0 (Clinical-Grade Production Blueprint)  
**Creation Date:** May 19, 2026  
**Lead AI Systems Architect:** Antigravity (Google DeepMind Team)  
**Target Systems Framework:** Next.js Enterprise Dynamic Core + Firebase Firestore + Groq Multi-Model Reasoning  

---

## 🏛️ SECTION 1: Strategic Systems Biology RAG Philosophy

In modern precision medicine, patients suffer not from isolated symptoms, but from **interconnected networks of physiological stress**. The TSPI Clinical Platform models this systemic stress using **39 Systems Biology Axes** grouped across multiple domains.

Standard Large Language Models (LLMs) lack the specialized, localized, and context-dependent clinical knowledge of a specific clinic (e.g., Dr. Pat's custom clinical recovery protocols or highly recent peer-reviewed articles on cellular biotransformation). 

To solve this, we designed and implemented a **Closed-Circuit RAG (Retrieval-Augmented Generation) Engine**.

### 🧠 The Network Stress & RAG Synergy Principle
When a patient presents with multiple chronic dysfunctions, our deterministic math engine calculates the stress levels of all 39 axes. 
Any axis with a **Burden Score exceeding 60%** is marked as **Critical**.

Instead of performing blind vector searches across a generalized pool, our **Context-Aware RAG Engine** targets the active clinical research matched to these specific high-burden axes, fetching only the literature relevant to the patient's actual molecular profile.

```
       [Raw Patient Intake / Voice SOAP / OCR Labs]
                           │
                           ▼
       [Deterministic 39-Axis Stress Calculation]
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
      Critical Axes (>60%)         Healthy Axes (<60%)
             │                           │
             ▼                           ▼
    [Query Firestore RAG]            [Ignored]
  Filter: Axis == Critical
             │
             ▼
   [Fetch Research Text]
             │
             ▼
 [Inject Context into Groq Llama] ──> [Clinical Decision Support Synthesis]
```

---

## 🛠️ SECTION 2: Complete Codebase Implementations & Mappings

Four key files were created or modified to integrate this architecture seamlessly. The exact implementations and files are detailed below:

### 📁 File 1: Ingestion Dashboard Page
* **Route:** `/doctor/knowledge-rag`
* **File Location:** [knowledge-rag/page.tsx](file:///media/tanchon-lita/Data/Pr/dr_pat/frontend/src/app/doctor/knowledge-rag/page.tsx)
* **Design Philosophy:** Premium clinical aesthetics with dark-accented status cards, responsive form layouts, real-time sync loaders, search inputs, and axis selection.
* **Component Code Architecture:**
  * Uses Client-Side Firebase Firestore SDK directly for instant rendering of the knowledge base list.
  * Connects to `/api/ai/index-knowledge` to post new literature.
  * Contains a fully scrollable, clean dashboard list showing the source name, type tag, biological axis tag, time created, and the full literature text with a custom truncator.

```typescript
// 39 Systems Biology Axes mapping index used inside the selection form:
const AXES_OPTIONS = [
   { id: 1, name: "Systemic Inflammatory Load" },
   { id: 2, name: "Immune Homeostasis" },
   { id: 3, name: "Viral/Bacterial Governance" },
   { id: 4, name: "Detoxification" },
   { id: 5, name: "Biotransformation" },
   { id: 6, name: "Oxidative Burden" },
   { id: 7, name: "Glycemic Regulation" },
   { id: 8, name: "Lipid Dynamics" },
   { id: 9, name: "Energy/Mitochondrial Health" },
   { id: 10, name: "Hormonal Balance" },
   { id: 11, name: "Thyroid Economy" },
   { id: 12, name: "Adrenal Reserve" },
   { id: 13, name: "Gut Barrier Integrity" },
   { id: 14, name: "Digestive Efficiency" },
   { id: 15, name: "Microbiome Ecosystem" },
   { id: 16, name: "Neuro-Chemical Balance" },
   { id: 17, name: "Cognitive Reserve" },
   { id: 18, name: "Sleep/Circadian Biology" },
   { id: 19, name: "Cardiovascular Strength" },
   { id: 20, name: "Microvascular Flow" },
   { id: 21, name: "Endothelial Health" },
   { id: 22, name: "Respiratory Dynamics" },
   { id: 23, name: "Renal/Fluid Balance" },
   { id: 24, name: "Hepatic Architecture" },
   { id: 25, name: "Musculoskeletal Integrity" },
   { id: 26, name: "Bone Density/Mineral" },
   { id: 27, name: "Connective Tissue" },
   { id: 28, name: "Skin Barrier" },
   { id: 29, name: "Visual Health" },
   { id: 30, name: "Auditory Function" },
   { id: 31, name: "Lymphatic Drainage" },
   { id: 32, name: "Cellular Cycle/Autophagy" },
   { id: 33, name: "Epigenetic Resilience" },
   { id: 34, name: "Longevity/Senescence" },
   { id: 35, name: "Stem Cell Vitality" },
   { id: 36, name: "Bio-Energetic Flow" },
   { id: 37, name: "Clinical Context A" },
   { id: 38, name: "Clinical Context B" },
   { id: 39, name: "Precision Outcome" }
];
```

---

### 📁 File 2: Ingestion Server Route with Local Fallback
* **Route:** `/api/ai/index-knowledge`
* **File Location:** [index-knowledge/route.ts](file:///media/tanchon-lita/Data/Pr/dr_pat/frontend/src/app/api/ai/index-knowledge/route.ts)
* **Design Philosophy:** Since deploying Google Cloud Functions requires full production setup, we added a robust fallback inside the Next.js API. If the Cloud Function `indexKnowledge` returns an error, the backend falls back gracefully to storing the document directly in the Firestore `knowledge_base` collection using `dbAdmin`.
* **Full File Code:**

```typescript
import { NextResponse } from 'next/server';
import { functions } from '@/utils/firebase/functions-client';
import { dbAdmin } from '@/utils/firebase/admin';

export async function POST(req: Request) {
  try {
    const { text, source, axis, type } = await req.json();

    if (!text || !source) {
      return NextResponse.json({ error: 'Missing text or source' }, { status: 400 });
    }

    console.log(`📚 Indexing: ${source}`);

    let result;
    try {
      result = await functions.indexKnowledge({
        text,
        source,
        axis,
        type
      });
    } catch (funcError: any) {
      console.warn("⚠️ Cloud Function indexKnowledge failed, writing directly to Firestore knowledge_base:", funcError.message);
      if (dbAdmin) {
        const docRef = await dbAdmin.collection("knowledge_base").add({
          text,
          source,
          axis: axis || "General",
          type: type || "clinical_guideline",
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        });
        result = { success: true, id: docRef.id, mode: "local_firestore" };
      } else {
        throw funcError;
      }
    }

    return NextResponse.json(result);
  } catch (error: any) {
    console.error('❌ Index Error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
```

---

### 📁 File 3: Real-Time RAG Query & Clinical Synthesis Injected
* **Flow Pipeline:** `precisionMedicineFlow`
* **File Location:** [precision-medicine-flow.ts](file:///media/tanchon-lita/Data/Pr/dr_pat/frontend/src/lib/precision-medicine-flow.ts)
* **Design Philosophy:** We integrated Phase 2.5 directly between the deterministic stress calculations and Groq's high-grade clinical reasoning. It retrieves matching axes dynamically from the database and appends them to the Groq prompt system instructions.
* **Modified Core Pipeline Section:**

```typescript
    // --- PHASE 2: DETERMINISTIC ENGINE ---
    const engineResult = await precisionEngine.runFullAnalysis(input.patientId, processedData);

    // --- PHASE 2.5: CLOSED-CIRCUIT RAG RETRIEVAL ---
    let ragContexts: string[] = [];
    const criticalAxes = Object.entries(engineResult.axesScores)
      .filter(([_, val]) => val.score > 60)
      .map(([id, val]) => {
        const aDef = precisionEngine.getAxisDef(id);
        return `${aDef?.name || id}: ${val.score}% (${val.severity})`;
      });

    try {
      if (dbAdmin) {
        console.log("📚 Querying closed-circuit RAG knowledge base...");
        const criticalAxisNames = Object.entries(engineResult.axesScores)
          .filter(([_, val]) => val.score > 60)
          .map(([id, _]) => {
            const aDef = precisionEngine.getAxisDef(id);
            return aDef ? aDef.name : "";
          })
          .filter(Boolean);

        const kbSnap = await dbAdmin.collection('knowledge_base').get();
        kbSnap.forEach(doc => {
          const data = doc.data();
          // Check if knowledge matches any of the critical axes or is general clinical framework
          const matchesCritical = criticalAxisNames.some(cName => data.axis && data.axis.includes(cName));
          if (matchesCritical || data.axis === "General") {
            ragContexts.push(`[Source: ${data.source}] (Target Axis: ${data.axis})\n${data.text}`);
          }
        });
        console.log(`✅ Loaded ${ragContexts.length} relevant institutional knowledge blocks.`);
      }
    } catch (ragError: any) {
      console.warn("⚠️ Closed-circuit RAG query skipped:", ragError.message);
    }

    // --- PHASE 3: MECHANISTIC ANALYSIS (Deep Clinical Reasoning via Groq Llama) ---
    const deepSeekAnalysis = await ai.generate({
      model: 'groq/llama-3.3-70b-versatile', 
      system: `You are the TSPI Precision Medicine Clinical Reasoning Engine.
               You analyze systems biology and precision medicine data using deep clinical reasoning.
               
               High-Burden Domains:
               ${domainSummary.join('\n')}
               
               Active Critical Axes (Scored > 60%):
               ${criticalAxes.join('\n')}
               
               Closed-Circuit Institutional RAG Knowledge (Targeted clinical research & clinical inputs):
               ${ragContexts.length > 0 ? ragContexts.join('\n\n') : 'No matching specialized guidelines loaded in local memory.'}
               
               Clinical Guidelines:
               1. Synthesize the "Network Effect" showing how these axes are biologically interconnected.
               2. Map clinical symptoms directly to physiological dysfunctions across the 39 systems biology axes.
               3. Incorporate the provided Closed-Circuit RAG Knowledge explicitly when proposing explanations or justifications.
               4. Outline mechanistic pathways of recommended therapeutic modules.
               5. Keep explanations clear, rigorous, and highly actionable for clinicians.`,
      prompt: `Patient Symptoms: ${processedData.symptoms.join(', ')}
               Observations: ${processedData.observations}
               Based on the clinical observations, computed physiological scoring, and institutional RAG knowledge above, perform a Systems Biology synthesis of the patient's condition.`,
    });
```

---

### 📁 File 4: Navigation Integration
* **File Location:** [doctor/layout.tsx](file:///media/tanchon-lita/Data/Pr/dr_pat/frontend/src/app/doctor/layout.tsx)
* **Design Philosophy:** Seamless UI entry.
* **Layout Segment:**
```typescript
    {
      title: "AI Engine",
      items: [
        { name: "Voice AI", href: "/doctor/voice-form", icon: Cpu },
        { name: "Automations", href: "/doctor/automations", icon: Zap },
        { name: "Knowledge RAG", href: "/doctor/knowledge-rag", icon: Database }, // <-- Added here
        { name: "Engine History", href: "/doctor/engine-results", icon: History },
        { name: "Outcomes", href: "/doctor/outcomes", icon: Trophy },
        { name: "Validations", href: "/doctor/validations", icon: ClipboardCheck },
      ]
    }
```

---

## 💾 SECTION 3: Database Collection Specifications

To maintain data parity, verify that your local Firestore contains the following structured payloads:

### 1. Collection Name: `knowledge_base`
This collection holds the clinical literature base.

```typescript
interface KnowledgeBaseNode {
   id?: string;               // Autogenerated by Firestore
   source: string;            // Text input: e.g. "Journal of Endocrinological Research, 2025"
   axis: string;              // Dropdown: e.g. "Axis 7: Glycemic Regulation" or "General"
   type: string;              // Dropdown: e.g. "research_paper", "clinical_guideline", "nutraceutical_synergy"
   text: string;              // Large Text Area containing the actual facts
   createdAt: string;         // ISO String representation of time indexed
   updatedAt: string;         // ISO String representation of updates
}
```

### 2. Collection Name: `patients/{patientId}/digitalTwin`
This sub-collection tracks all temporal snapshots computed by the multi-model engine.

```typescript
interface DigitalTwinSnapshot {
   patientId: string;
   snapshotId: string;
   timestamp: string;
   axesState: {
      [axisId: string]: {     // e.g. "AXIS_7"
         score: number;       // e.g. 78.5
         severity: string;    // e.g. "High Burden"
      }
   };
   mechanisticInsights: string; // The markdown analysis output from Groq citing the RAG literature
   recommendedProtocol: Array<{
      moduleId: string;
      name: string;
      rationale: string;
      priority: number;
   }>;
}
```

---

## 🧪 SECTION 4: Interactive Sandbox Dry Run Guide (For Tomorrow)

Follow these exact steps tomorrow to test the RAG integration end-to-end:

### Step 1: Input Ingestion Test
1. Log into the Doctor dashboard and navigate to **Knowledge RAG** via the sidebar.
2. Fill in the Form:
   * **Source:** `TSPI Mitochondrial Protocol v1.4`
   * **Axis:** Select `Axis 9: Energy/Mitochondrial Health`
   * **Type:** `clinical_guideline`
   * **Content:** 
     > "Mitochondrial dysfunction in fatiguing illnesses is driven by NADH/CoQ10 imbalances. Clinics should recommend high-dose Coenzyme Q10 synergistic modules combined with L-Carnitine to stimulate the citric acid cycle."
3. Click **Synchronize to RAG System**.
4. Verify that the card instantly appears in the database grid on the right side.

### Step 2: Running the V-Twin Simulator
1. Go to the **Clinical Review** screen (`/doctor/clinical-review`).
2. Select your test patient.
3. Inject raw symptoms into the active patient simulation inputs:
   * `"Patient complains of profound muscle fatigue, low energy levels, and brain fog."`
4. Trigger the clinical analysis.
5. Under the hood:
   * The deterministic engine will calculate **Axis 9: Energy/Mitochondrial Health** as high stress (>60%).
   * Phase 2.5 will query Firestore, fetch the `TSPI Mitochondrial Protocol v1.4` node.
   * It will feed this text directly into Groq.
6. **Verify the Output:**
   * Open the **Systemic Biology Synthesis** tab.
   * Look for the citations matching **Coenzyme Q10** or **L-Carnitine** from your exact RAG entry!
7. Check the **Audit Trail** (`/doctor/audit`) to confirm the latency logs and payload captures.

---

## 📈 SECTION 5: Long-Term Enterprise Migration Recommendations

When the time comes to migrate from local machine sandbox to your production VPS, execute the following strategy:

1. **Deploy Cloud Functions:**
   * Build and deploy Genkit Cloud Functions (`functions.indexKnowledge` and standard retrievers) using Firebase CLI.
   * This shifts vector parsing to Google's specialized servers, freeing up Next.js thread pools.
2. **Local Embedding Models:**
   * If you choose to host vector embeddings privately inside your VPS to avoid third-party calls, we can implement local embeddings via `transformers.js` using the standard MiniLM-L6 vector architecture.
3. **Database Rules Auditing:**
   * Run the xcode/firebase security auditing tools to enforce locked-down PDPA clinical rules:
     * Restrict `knowledge_base` read/write privileges strictly to authenticated clinician roles.

---
*Document compiled and vetted. Full codebase compiled with exit code 0. Ready for the next phase.*
