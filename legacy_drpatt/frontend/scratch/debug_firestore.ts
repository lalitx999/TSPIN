import { db } from "./src/utils/firebase/client";
import { collection, getDocs, limit, query } from "firebase/firestore";

async function debugData() {
    console.log("--- DEBUGGING FIRESTORE DATA ---");
    
    // Check Axes
    const axesSnap = await getDocs(query(collection(db, "axes"), limit(2)));
    console.log("Axes Example:", axesSnap.docs.map(d => ({ id: d.id, ...d.data() })));
    
    // Check Modules
    const modulesSnap = await getDocs(query(collection(db, "modules"), limit(2)));
    console.log("Modules Example:", modulesSnap.docs.map(d => ({ id: d.id, ...d.data() })));
}

debugData();
