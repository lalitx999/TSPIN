import fs from 'fs';
import path from 'path';
import { initializeApp } from "firebase/app";
import { getFirestore, collection, getDocs, doc, writeBatch } from "firebase/firestore";
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

async function clearCollection(colName: string) {
    console.log(`🧹 Clearing collection: ${colName}...`);
    const colRef = collection(db, colName);
    const snapshot = await getDocs(colRef);
    const batch = writeBatch(db);
    snapshot.docs.forEach((d) => batch.delete(d.ref));
    await batch.commit();
}

async function migrateDetailedAxes() {
    console.log("🚀 Starting Refined Axes Migration (v5)...");
    const txtPath = path.join(process.cwd(), '../data/39 แกนทางชีววิทยา tspi.txt');
    const content = fs.readFileSync(txtPath, 'utf8');
    
    const lines = content.split('\n');
    let currentAxis: any = null;
    const axesMap = new Map();

    // Much more flexible regex for axes
    const axisHeaderRegex = /(?:Axis|AXIS)\s*(\d+)/i;

    for (let line of lines) {
        const trimmed = line.trim();
        const match = trimmed.match(axisHeaderRegex);
        
        // Ensure it's a header (short line or starts with emoji/Axis)
        const isHeader = match && (trimmed.length < 100) && (trimmed.startsWith('Axis') || trimmed.startsWith('AXIS') || trimmed.match(/^[^\w\s]/));

        if (isHeader) {
            const axisNum = match![1];
            const axisId = `AXIS_${axisNum}`;
            if (!axesMap.has(axisId)) {
                currentAxis = {
                    axis_id: axisId,
                    name: trimmed.replace(/Axis\s*\d+/i, '').replace(/^[:\- \t🧩🧠]+/, '').trim() || `Axis ${axisNum}`,
                    sub_axes: { A: "", B: "", C: "" },
                    modules: [],
                    description: ""
                };
                axesMap.set(axisId, currentAxis);
            } else {
                currentAxis = axesMap.get(axisId);
            }
        } else if (currentAxis) {
            if (trimmed.startsWith('A:')) currentAxis.sub_axes.A = trimmed.substring(2).trim();
            else if (trimmed.startsWith('B:')) currentAxis.sub_axes.B = trimmed.substring(2).trim();
            else if (trimmed.startsWith('C:')) currentAxis.sub_axes.C = trimmed.substring(2).trim();
            else if (trimmed.startsWith('Module :') || trimmed.startsWith('Modules :')) {
                const parts = trimmed.split(':');
                if (parts[1]) {
                    const mods = parts[1].split(/[, ]+/).filter(m => m.length > 1);
                    currentAxis.modules = [...new Set([...currentAxis.modules, ...mods])];
                }
            }
        }
    }

    const finalAxes = Array.from(axesMap.values());
    const batch = writeBatch(db);
    finalAxes.forEach(axis => {
        const ref = doc(db, "axes", axis.axis_id);
        batch.set(ref, { ...axis, updatedAt: new Date().toISOString() });
    });
    await batch.commit();
    console.log(`✅ Migrated ${finalAxes.length} Unique Axes successfully!`);
}

async function migrateAllModules() {
    console.log("🚀 Starting Global Modules Migration (v5)...");
    const dataDir = path.join(process.cwd(), '../data');
    const files = fs.readdirSync(dataDir).filter(f => f.endsWith('.csv'));
    
    const modulesMap = new Map();
    const colMap = [
        "id", "phytocoreCode", "name", "botanicalComposition", "mechanisticFunction",
        "bioactiveMarkers", "axisMapping", "cytotoxicity", "ld50", "proteomicsMarker",
        "peakRatio", "nodeDiseases", "mainMechanism", "drugInteraction", "biomarkerResponse",
        "recommendedDose", "healthCategory", "tasteEnergy", "ic50Data", "interpretation",
        "cancerCytotoxicity", "selectivityNormalCells", "regenerativeOncology", "safetyProfile",
        "researchStatus", "summaryBiologicalActivity", "antioxidantActivity", "selectivityIndex",
        "gutMetabolicConcept", "hematologicOncology"
    ];

    for (const file of files) {
        console.log(`...Reading ${file}`);
        const fileContent = fs.readFileSync(path.join(dataDir, file), 'utf8');
        const lines = fileContent.split('\n');
        let currentModule: any = null;

        for (let i = 2; i < lines.length; i++) {
            const line = lines[i].trim();
            if (!line) continue;

            const matchId = line.match(/^([A-Z0-9-]{2,20})\s*,/i);
            if (matchId) {
                if (currentModule) {
                    const existing = modulesMap.get(currentModule.key);
                    if (!existing || currentModule.mechanisticFunction.length > existing.mechanisticFunction.length) {
                        modulesMap.set(currentModule.key, currentModule);
                    }
                }
                
                const cols = line.split(/,(?=(?:(?:[^"]*"){2})*[^"]*$)/); 
                currentModule = { key: matchId[1].trim() + "_" + (cols[1] || cols[2] || "").trim() };
                colMap.forEach((key, idx) => {
                    currentModule[key] = (cols[idx] || "").replace(/^"|"$/g, '').trim();
                });
                currentModule.id = matchId[1].trim();
            } else if (currentModule) {
                currentModule["mechanisticFunction"] += " " + line;
            }
        }
        if (currentModule) {
            const existing = modulesMap.get(currentModule.key);
            if (!existing || currentModule.mechanisticFunction.length > existing.mechanisticFunction.length) {
                modulesMap.set(currentModule.key, currentModule);
            }
        }
    }

    const finalModules = Array.from(modulesMap.values());
    let batch = writeBatch(db);
    let count = 0;
    for (const mod of finalModules) {
        const docId = mod.key.replace(/[/\\#? ]/g, '_').substring(0, 100);
        try {
            const docRef = doc(db, "modules", docId);
            batch.set(docRef, { ...mod, updatedAt: new Date().toISOString() });
            count++;
            if (count % 400 === 0) {
                await batch.commit();
                batch = writeBatch(db);
            }
        } catch (e) {
            console.error(`❌ Error with docId: ${docId}`, e);
        }
    }
    await batch.commit();
    console.log(`✅ Migrated ${count} Total Unique Modules successfully!`);
}

async function runUltimateVerifiedMigration() {
    try {
        await clearCollection("axes");
        await clearCollection("modules");
        await migrateDetailedAxes();
        await migrateAllModules();
        console.log("🎊 FULL DATA RE-MIGRATION COMPLETED SUCCESSFULLY!");
        process.exit(0);
    } catch (error) {
        console.error("❌ Migration failed:", error);
        process.exit(1);
    }
}

runUltimateVerifiedMigration();
