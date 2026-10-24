import dotenv from "dotenv";
dotenv.config({ path: ".env.local" });

import { precisionMedicineFlow } from "./src/lib/precision-medicine-flow";

async function test() {
  try {
    console.log("Running precisionMedicineFlow directly...");
    const result = await precisionMedicineFlow({
      patientId: "1",
      rawInput: "เหนื่อยง่าย เพลีย และท้องผูก",
      labData: { fbs: 105.0, hba1c: 5.9 }
    });
    console.log("Success! Result keys:", Object.keys(result));
    console.log("NSS calculated:", result.axesState ? "Present" : "Missing");
  } catch (e: any) {
    console.error("Error executing flow:", e);
  }
}

test();
