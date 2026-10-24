/**
 * TSPI Medical Data Schema (PDPA & Clinical Intelligence Compliant)
 * Connected exclusively to Django + PostgreSQL Backend.
 */

export interface BiologicalScore {
  axisId: number;
  axisName: string;
  score: number; // 0-100
  updatedAt: any;
  markers: Record<string, any>;
  insight?: string;
}

export interface PatientProfile {
  id: string;
  firstName: string;
  lastName: string;
  name?: string;
  fname?: string;
  lname?: string;
  hn?: string;
  id_card?: string;
  phone?: string;
  symptoms?: string;
  birthDate: string;
  gender: string;
  bloodType?: string;
  allergies?: string[];
  lastClinicalUpdate: any;
  axes: Record<string, BiologicalScore>; // Key is Axis ID
  reports?: string[]; // IDs of ClinicalReport
  caseSummary?: string; // AI generated case summary
  labs?: any;
  genomics?: any;
  microbiome?: any;
  proteomics?: any;
  extra_data?: any;
}

const DJANGO_API_URL = (process.env.NEXT_PUBLIC_API_URL || 'https://tspi-backend.tanchonhomserverxxx.online') + '/api';

// Read JWT from localStorage (set by doctor login flow)
const getAuthHeaders = (): Record<string, string> => {
  if (typeof window === 'undefined') return {};
  const token = localStorage.getItem('doctor_access_token') || localStorage.getItem('patient_access_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
};

const djangoGet = (url: string) =>
  fetch(url, { headers: { 'Content-Type': 'application/json', ...getAuthHeaders() } });

// Map Django API output to Next.js Medical Profile schema
const transformPatientFromDjango = (djangoPatient: any): PatientProfile => {
  const latestRecord = djangoPatient.axes_records && djangoPatient.axes_records.length > 0 
    ? djangoPatient.axes_records[0] 
    : null;
  
  const axes: Record<string, BiologicalScore> = {};
  if (latestRecord) {
    for (let i = 1; i <= 39; i++) {
      axes[`AXIS_${i}`] = {
        axisId: i,
        axisName: `Axis ${i}`,
        score: latestRecord[`axis_${i}`] ?? 50,
        updatedAt: latestRecord.record_date,
        insight: latestRecord.notes,
        markers: {}
      };
    }
  } else {
    // Fill defaults if record doesn't exist
    for (let i = 1; i <= 39; i++) {
      axes[`AXIS_${i}`] = {
        axisId: i,
        axisName: `Axis ${i}`,
        score: 50,
        updatedAt: new Date().toISOString(),
        insight: 'No clinical records found.',
        markers: {}
      };
    }
  }

  return {
    id: String(djangoPatient.id),
    firstName: djangoPatient.first_name,
    lastName: djangoPatient.last_name,
    name: `${djangoPatient.first_name} ${djangoPatient.last_name}`,
    fname: djangoPatient.first_name,
    lname: djangoPatient.last_name,
    hn: djangoPatient.hn,
    id_card: djangoPatient.id_card,
    birthDate: djangoPatient.birth_date,
    gender: djangoPatient.gender === 'M' ? 'Male' : (djangoPatient.gender === 'F' ? 'Female' : 'Other'),
    phone: djangoPatient.phone,
    axes: axes,
    lastClinicalUpdate: latestRecord ? latestRecord.record_date : null,
    // Fallback static mock or mapping from patient record fields
    labs: djangoPatient.labs || {
      hba1c: 7.8,
      fbs: 152,
      crp: 4.5,
      ldl: 165,
      alt: 45,
      ggt: 55
    },
    genomics: djangoPatient.genomics || {},
    microbiome: djangoPatient.microbiome || {},
    proteomics: djangoPatient.proteomics || {}
  };
};

export const medicalDb = {
  // --- Patient Management ---
  async getPatient(id: string): Promise<PatientProfile | null> {
    try {
      const res = await djangoGet(`${DJANGO_API_URL}/patients/${id}/`);
      if (res.ok) {
        const djangoPatient = await res.json();
        return transformPatientFromDjango(djangoPatient);
      }
      return null;
    } catch (err) {
      console.error("Error fetching patient from Django:", err);
      throw err;
    }
  },

  async updateBiologicalScores(patientId: string, scores: Record<string, BiologicalScore>) {
    try {
      const payload: any = {
        patient: parseInt(patientId),
        record_date: new Date().toISOString(),
      };
      for (let i = 1; i <= 39; i++) {
        payload[`axis_${i}`] = scores[`AXIS_${i}`]?.score ?? 50;
      }
      // Extract note/insight if available
      payload.notes = scores['AXIS_1']?.insight || scores['AXIS_5']?.insight || 'Updated via Next.js Frontend';
      
      const res = await fetch(`${DJANGO_API_URL}/records/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }
      console.log("Successfully stored biological scores record in PostgreSQL database via Django.");
    } catch (err) {
      console.error("Failed to write scores to Django:", err);
      throw err;
    }
  },

  // --- Audit Logging ---
  async logAccess(actorId: string, targetId: string, action: string, layer: 'A' | 'B' | 'C' | 'D' | 'E') {
    const logData = {
      actor_id: actorId,
      target_id: targetId,
      action: action,
      layer: layer,
      client_ip: typeof window === "undefined" ? "server-side" : "client-side",
      governance_status: layer === 'E' ? 'RESTRICTED_INTERNAL' : 'PATIENT_ACCESSIBLE'
    };

    try {
      const res = await fetch(`${DJANGO_API_URL}/logs/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify(logData)
      });
      if (!res.ok) {
        console.warn(`Audit logging returned status: ${res.status}`);
      }
    } catch (err) {
      console.warn("Failed to write access log to Django:", err);
    }
  },

  async getPatientList(): Promise<any[]> {
    try {
      const res = await djangoGet(`${DJANGO_API_URL}/patients/?no_pagination=true`);
      if (res.ok) {
        const djangoPatients = await res.json();
        const patientsArray = Array.isArray(djangoPatients) ? djangoPatients : (djangoPatients.results || []);
        return patientsArray.map((dp: any) => transformPatientFromDjango(dp));
      }
      return [];
    } catch (err) {
      console.error("Error fetching patients list from Django:", err);
      throw err;
    }
  },

  async getPatientDataLayer(patientId: string, layer: 'A' | 'B' | 'C' | 'D' | 'E', actorId: string = 'ai-copilot'): Promise<any> {
    await this.logAccess(actorId, patientId, `READ_LAYER_${layer}`, layer);
    
    const patient = await this.getPatient(patientId);
    if (!patient) return null;
    
    switch (layer) {
      case 'A':
        return {
          id: patient.id,
          firstName: patient.firstName,
          lastName: patient.lastName,
          name: patient.name,
          fname: patient.fname,
          lname: patient.lname,
          birthDate: patient.birthDate,
          gender: patient.gender,
          bloodType: patient.bloodType,
          allergies: patient.allergies,
          labs: patient.labs || null,
        };
      case 'B':
        return {
          id: patient.id,
          caseSummary: patient.caseSummary,
        };
      case 'C':
        return {
          id: patient.id,
          genomics: patient.genomics || null,
          microbiome: patient.microbiome || null,
          proteomics: patient.proteomics || null,
        };
      case 'D':
        return {
          id: patient.id,
          axes: patient.axes,
          lastClinicalUpdate: patient.lastClinicalUpdate,
        };
      case 'E':
        return {
          id: patient.id,
          message: "Layer E is restricted internal governance logic.",
        };
      default:
        return patient;
    }
  }
};
