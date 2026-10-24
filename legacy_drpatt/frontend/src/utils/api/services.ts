import { encryptMessage } from "../crypto";
import axesData from "../../data/39_last_x.json";
import modulesData from "../../data/modules_db.json";

/**
 * ⚠️ ARCHITECTURAL NOTICE (MIGRATION TO DJANGO):
 * Although this file is named services.ts in the utils/firebase directory for legacy reasons,
 * ALL data access methods (patients, EMR records, biological scores, weights) have been fully 
 * migrated to the Django/PostgreSQL REST API backend at http://localhost:8000.
 * Firebase is only used for client auth and analytics.
 */

// Helper utilities for Django backend API adapter
const getAuthHeaders = (): Record<string, string> => {
    if (typeof window === "undefined") return {};
    const token = localStorage.getItem("doctor_access_token") || localStorage.getItem("patient_access_token");
    return token ? { "Authorization": `Bearer ${token}` } : {};
};

const djangoFetch = async (endpoint: string, options: RequestInit = {}) => {
    const headers = {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
        ...(options.headers || {}),
    };
    const apiBase = typeof window !== "undefined"
        ? (process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online")
        : (process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online");
        
    const base = apiBase.replace(/\/+$/, "").replace(/\/api$/, "");
    const response = await fetch(`${base}${endpoint}`, {
        ...options,
        headers,
    });
    
    // 🔑 Auto-Redirect when JWT Token is Unauthorized/Expired (401)
    if (response.status === 401) {
        if (typeof window !== "undefined") {
            localStorage.removeItem("doctor_access_token");
            localStorage.removeItem("patient_access_token");
            window.location.href = window.location.pathname.startsWith("/doctor") 
                ? "/doctor/login" 
                : "/patient/login";
        }
        throw new Error("Session expired. Redirecting to login...");
    }

    if (!response.ok) {
        throw new Error(`Django API Error: ${response.statusText}`);
    }
    const resData = await response.json();
    if (resData && typeof resData === "object" && Array.isArray(resData.results)) {
        return resData.results;
    }
    return resData;
};

// ==================== PATIENTS ====================

export const getPatient = async (uid: string) => {
    try {
        const data = await djangoFetch(`/api/patients/${uid}/`);
        if (data && Array.isArray(data.axes_records)) {
            data.digitalTwinHistory = data.axes_records.map((rec: any) => {
                const axesState: Record<string, any> = {};
                for (let i = 1; i <= 39; i++) {
                    axesState[`AXIS_${i}`] = {
                        score: rec[`axis_${i}`] !== undefined ? rec[`axis_${i}`] : 50,
                        axisId: i,
                        axisName: `Axis ${i}`
                    };
                }
                return {
                    id: String(rec.id),
                    timestamp: rec.record_date,
                    axesState
                };
            });
        } else {
            data.digitalTwinHistory = [];
        }
        return data;
    } catch (e) {
        console.error(`Failed to get patient ${uid} from Django:`, e);
        return null;
    }
};

export const getAllPatients = async () => {
    try {
        const data = await djangoFetch("/api/patients/list-lightweight/");
        return data;
    } catch (e) {
        console.error("Failed to get all patients from Django:", e);
        return [];
    }
};

export const createPatient = async (uid: string, data: any) => {
    try {
        const payload = { ...data };
        if (data.name && !data.first_name) {
            const parts = data.name.trim().split(" ");
            payload.first_name = parts[0];
            payload.last_name = parts.slice(1).join(" ");
        }
        if (!payload.hn) {
            payload.hn = `HN-${new Date().getFullYear()}-${Math.floor(1000 + Math.random() * 9000)}`;
        }
        if (!payload.legacy_id) {
            payload.legacy_id = payload.id_card || payload.hn;
        }
        await djangoFetch("/api/patients/", {
            method: "POST",
            body: JSON.stringify(payload)
        });
    } catch (e) {
        console.error("Failed to create patient in Django:", e);
    }
};

export const updatePatient = async (uid: string, data: any) => {
    try {
        await djangoFetch(`/api/patients/${uid}/`, {
            method: "PATCH",
            body: JSON.stringify(data)
        });
    } catch (e) {
        console.error(`Failed to update patient ${uid} in Django:`, e);
    }
};

// ==================== DOCTORS ====================

export const getDoctor = async (uid: string) => {
    return { id: uid, name: "Dr. Patt", email: "obsidianzx.m123@gmail.com" };
};

export const getAllDoctors = async () => {
    return [{ id: "doc1", name: "Dr. Patt", email: "obsidianzx.m123@gmail.com" }];
};

// ==================== APPOINTMENTS ====================

export const getAppointments = async (date?: string) => {
    try {
        const data = await djangoFetch("/api/appointments/?no_pagination=true");
        const mapped = data.map((appt: any) => ({
            ...appt,
            id: String(appt.id),
            date: appt.date_meet,
            time: appt.time_meet,
            name: appt.userid,
            patientName: appt.userid,
            type: appt.symptom || "ตรวจวินิจฉัยทั่วไป",
            status: appt.status || "pending",
            urgencyScore: appt.time_id || 0,
            expectedDuration: 30
        }));

        if (date) {
            return mapped.filter((a: any) => a.date === date);
        }
        return mapped;
    } catch (e) {
        console.error("Failed to get appointments from Django:", e);
        return [];
    }
};

export const createAppointment = async (data: any) => {
    try {
        const payload = {
            userid: data.patientName || data.name || "unknown",
            date_meet: data.date || new Date().toISOString().split("T")[0],
            time_meet: data.time || "09:00",
            symptom: data.type || "ตรวจวินิจฉัยทั่วไป",
            status: data.status || "pending",
            time_id: data.urgencyScore || 0
        };
        const res = await djangoFetch("/api/appointments/", {
            method: "POST",
            body: JSON.stringify(payload)
        });
        
        const appointmentId = String(res.id);

        // 🤖 Automate Clinical Tasks in Django EMR
        try {
            const apptDate = new Date(`${payload.date_meet}T${payload.time_meet}`);
            
            // 1. No-show check (1 hour after appt)
            const noShowTime = new Date(apptDate.getTime() + 60 * 60 * 1000);
            await createAutomationTask({
                type: "NO_SHOW_CHECK",
                status: "pending",
                patientName: payload.userid,
                patientHn: "",
                scheduledFor: noShowTime.toISOString()
            });

            // 2. Follow-up (3 days after appt)
            const followUpTime = new Date(apptDate.getTime() + 3 * 24 * 60 * 60 * 1000);
            await createAutomationTask({
                type: "FOLLOW_UP",
                status: "pending",
                patientName: payload.userid,
                patientHn: "",
                scheduledFor: followUpTime.toISOString()
            });
        } catch (autoErr) {
            console.error("Failed to automate task schedule:", autoErr);
        }

        return appointmentId;
    } catch (e) {
        console.error("Failed to create appointment in Django:", e);
        return "temp-id";
    }
};

export const updateAppointment = async (id: string, data: any) => {
    try {
        const payload: any = {};
        if (data.patientName) payload.userid = data.patientName;
        if (data.date) payload.date_meet = data.date;
        if (data.time) payload.time_meet = data.time;
        if (data.type) payload.symptom = data.type;
        if (data.status) payload.status = data.status;
        if (data.urgencyScore !== undefined) payload.time_id = data.urgencyScore;

        await djangoFetch(`/api/appointments/${id}/`, {
            method: "PATCH",
            body: JSON.stringify(payload)
        });
    } catch (e) {
        console.error(`Failed to update appointment ${id} in Django:`, e);
    }
};


// ==================== LAB RESULTS ====================

export const getLabResults = async (patientId?: string) => {
    try {
        if (patientId) {
            const patient = await getPatient(patientId);
            if (patient && patient.extra_data && Array.isArray(patient.extra_data.lab_results)) {
                return patient.extra_data.lab_results;
            }
            return [];
        } else {
            const allResults = await djangoFetch("/api/patients/all-lab-results/");
            return allResults.sort((a: any, b: any) => {
                const dateA = a.createdAt ? new Date(a.createdAt).getTime() : 0;
                const dateB = b.createdAt ? new Date(b.createdAt).getTime() : 0;
                return dateB - dateA;
            });
        }
    } catch (e) {
        console.error("Failed to get lab results from Django EMR:", e);
        return [];
    }
};

export const saveLabResult = async (data: any) => {
    try {
        const patientId = data.patientId;
        if (!patientId) return "client-created-temp-id";

        const patient = await getPatient(patientId);
        if (patient) {
            const labResults = patient.extra_data?.lab_results || [];
            let updatedList = [...labResults];
            let resultId = data.id;

            if (resultId) {
                const index = updatedList.findIndex((r: any) => r.id === resultId);
                if (index !== -1) {
                    updatedList[index] = {
                        ...updatedList[index],
                        ...data,
                        updatedAt: new Date().toISOString()
                    };
                } else {
                    updatedList.push({
                        ...data,
                        updatedAt: new Date().toISOString()
                    });
                }
            } else {
                resultId = `lab_${Date.now()}`;
                updatedList.push({
                    ...data,
                    id: resultId,
                    createdAt: new Date().toISOString(),
                    updatedAt: new Date().toISOString()
                });
            }

            await updatePatient(patientId, {
                extra_data: {
                    ...(patient.extra_data || {}),
                    lab_results: updatedList
                }
            });
            return resultId;
        }
    } catch (e) {
        console.error("Failed to save lab result in Django EMR:", e);
    }
    return data.id || "client-created-temp-id";
};

// ==================== ENGINE RESULTS ====================

export const getEngineResults = async () => {
    try {
        const patients = await djangoFetch("/api/patients/?no_pagination=true");
        const list = Array.isArray(patients) ? patients : (patients.results || []);
        if (list.length > 0) {
            return list.map((p: any) => {
                const latestRecord = p.axes_records && p.axes_records[0];
                
                // Calculate average biological severity score (nss) from the 39 axes
                let totalScore = 0;
                let axisCount = 0;
                if (latestRecord) {
                    for (let i = 1; i <= 39; i++) {
                        const val = latestRecord[`axis_${i}`];
                        if (val !== undefined && val !== null) {
                            totalScore += Number(val);
                            axisCount++;
                        }
                    }
                }
                const burdenScore = axisCount > 0 ? Math.round(totalScore / axisCount) : 50;
                const status = burdenScore > 70 ? "In Review" : "Verified";
                
                return {
                    id: `eng_${p.id}_${latestRecord?.id || 'default'}`,
                    patient_id: p.id,
                    patient_name: p.name || `${p.first_name} ${p.last_name}`.trim(),
                    patient_hn: p.hn,
                    burden_score: burdenScore,
                    status: status,
                    createdAt: latestRecord?.record_date || p.created_at || new Date().toISOString()
                };
            });
        }
    } catch (e) {
        console.error("Failed to get engine results from Django, falling back to local storage:", e);
    }

    if (typeof window === "undefined") return [];
    const local = localStorage.getItem("tspi_engine_results");
    return local ? JSON.parse(local) : [];
};

export const createEngineResult = async (data: any) => {
    if (typeof window === "undefined") return "temp-id";
    const results = await getEngineResults();
    const newId = `eng_${Date.now()}`;
    const item = { ...data, id: newId, createdAt: new Date().toISOString() };
    localStorage.setItem("tspi_engine_results", JSON.stringify([item, ...results]));
    return newId;
};

// ==================== AXES / MODULES ====================

export const getAxes = async () => {
    const domains = (axesData as any).domains || [];
    const flatAxes = domains.flatMap((d: any) => 
        (d.axes || []).map((a: any) => ({
            ...a,
            domain_id: d.domain_id,
            domain_title: d.title
        }))
    );
    return flatAxes.map((d: any) => ({
        ...d,
        id: d.axis_id || d.id,
        name: d.name,
        axis_id: d.axis_id,
        domain_title: d.domain_title
    }));
};

export const getModules = async () => {
    if (typeof window === "undefined") {
        return modulesData.map((d: any) => ({
            ...d,
            id: d.id,
            name: d.name || d.product_derived_from || d["Product Derived From"],
            module_code: d.module_code || d.phytocore_code || d["PhytoCore Code"],
            tspi_axis_mapping: d.tspi_axis_mapping || d["TSPI Axis Mapping"] || ""
        }));
    }

    // 1. Fetch static fallback modules
    const staticModules = modulesData.map((d: any) => ({
        ...d,
        id: d.id,
        name: d.name || d.product_derived_from || d["Product Derived From"],
        module_code: d.module_code || d.phytocore_code || d["PhytoCore Code"],
        tspi_axis_mapping: d.tspi_axis_mapping || d["TSPI Axis Mapping"] || ""
    }));

    // 2. Load deleted IDs
    const deletedRaw = localStorage.getItem("tspi_modules_deleted") || "[]";
    const deletedIds = new Set<string>(JSON.parse(deletedRaw));

    // 3. Load edited modules dictionary
    const editedRaw = localStorage.getItem("tspi_modules_edited") || "{}";
    const editedMap = JSON.parse(editedRaw);

    // 4. Load custom created modules
    const customRaw = localStorage.getItem("tspi_modules_custom") || "[]";
    const customModules = JSON.parse(customRaw);

    // 5. Merge static modules with edits & filter deleted
    const processedStatic = staticModules
        .filter((m: any) => !deletedIds.has(String(m.id)))
        .map((m: any) => {
            const idStr = String(m.id);
            if (editedMap[idStr]) {
                return { ...m, ...editedMap[idStr] };
            }
            return m;
        });

    // 6. Merge custom modules (filter deleted as well)
    const processedCustom = customModules
        .filter((m: any) => !deletedIds.has(String(m.id)))
        .map((m: any) => {
            const idStr = String(m.id);
            if (editedMap[idStr]) {
                return { ...m, ...editedMap[idStr] };
            }
            return m;
        });

    return [...processedStatic, ...processedCustom];
};

// ==================== ANALYTICS / STATS ====================

export const getDashboardStats = async () => {
    try {
        const stats = await djangoFetch("/api/dashboard-stats/");
        return stats;
    } catch (e) {
        console.error("Failed to get dashboard stats from Django:", e);
        return {
            total_patients: 0,
            urgent_cases: 0,
            active_now: 0,
            completion_rate: "0%",
            total_axes: 39,
            total_modules: 271
        };
    }
};

// ==================== REAL-TIME SUBSCRIPTIONS ====================

export const subscribePatients = (
    callback: (data: any[]) => void
) => {
    return () => {};
};

export const subscribeAppointments = (
    date: string,
    callback: (data: any[]) => void
) => {
    return () => {};
};

// ==================== ALGORITHM WEIGHTS ====================

export const getAxesWeightConfig = async () => {
    try {
        const data = await djangoFetch("/api/settings/axes_weight_config/");
        return typeof data.setting_value === "string" 
            ? JSON.parse(data.setting_value) 
            : data.setting_value;
    } catch (e) {
        console.error("Failed to get axes weight config from Django EMR:", e);
        return null;
    }
};

export const updateAxesWeightConfig = async (weights: Record<string, number>) => {
    try {
        await djangoFetch("/api/settings/axes_weight_config/", {
            method: "PUT",
            body: JSON.stringify({
                setting_key: "axes_weight_config",
                setting_value: JSON.stringify(weights),
                category: "weights"
            })
        });
    } catch (e) {
        console.error("Failed to update axes weight config in Django EMR:", e);
    }
};

// ==================== AI ENGINE SETTINGS ====================

export const getAISettings = async () => {
    try {
        const data = await djangoFetch("/api/settings/ai_settings/");
        return typeof data.setting_value === "string" 
            ? JSON.parse(data.setting_value) 
            : data.setting_value;
    } catch (e) {
        console.error("Failed to get AI settings from Django EMR:", e);
        return null;
    }
};

export const updateAISettings = async (settings: any) => {
    try {
        await djangoFetch("/api/settings/ai_settings/", {
            method: "PUT",
            body: JSON.stringify({
                setting_key: "ai_settings",
                setting_value: JSON.stringify(settings),
                category: "AI"
            })
        });
    } catch (e) {
        console.error("Failed to update AI settings in Django EMR:", e);
    }
};

// ==================== CLINIC SETTINGS ====================

export const getClinicSettings = async () => {
    try {
        const data = await djangoFetch("/api/settings/clinic_info/");
        return typeof data.setting_value === "string" 
            ? JSON.parse(data.setting_value) 
            : data.setting_value;
    } catch (e) {
        console.error("Failed to get clinic settings from Django EMR:", e);
        return null;
    }
};

export const updateClinicSettings = async (settings: any) => {
    try {
        await djangoFetch("/api/settings/clinic_info/", {
            method: "PUT",
            body: JSON.stringify({
                setting_key: "clinic_info",
                setting_value: JSON.stringify(settings),
                category: "Clinic"
            })
        });
    } catch (e) {
        console.error("Failed to update clinic settings in Django EMR:", e);
    }
};

// ==================== OUTCOMES ====================

export const getOutcomes = async () => {
    if (typeof window === "undefined") return [];
    const local = localStorage.getItem("tspi_outcomes");
    return local ? JSON.parse(local) : [];
};

export const createOutcome = async (data: any) => {
    if (typeof window === "undefined") return "temp-id";
    const outcomes = await getOutcomes();
    const newId = `out_${Date.now()}`;
    const item = { ...data, id: newId, createdAt: new Date().toISOString() };
    localStorage.setItem("tspi_outcomes", JSON.stringify([item, ...outcomes]));
    return newId;
};

// ==================== VALIDATIONS ====================

export const getValidations = async () => {
    if (typeof window === "undefined") return [];
    const local = localStorage.getItem("tspi_validations");
    if (local) return JSON.parse(local);
    const mock = [
        { id: "val_1", patientName: "แทนชล วรรณวงศ์", type: "Clinical Review", status: "pending", createdAt: new Date().toISOString() }
    ];
    localStorage.setItem("tspi_validations", JSON.stringify(mock));
    return mock;
};

export const updateValidationStatus = async (id: string, status: string) => {
    if (typeof window === "undefined") return;
    const validations = await getValidations();
    const idx = validations.findIndex((v: any) => v.id === id);
    if (idx !== -1) {
        validations[idx].status = status;
        validations[idx].updatedAt = new Date().toISOString();
        localStorage.setItem("tspi_validations", JSON.stringify(validations));
    }
};

// ==================== MODULES ====================

export const createModule = async (data: any) => {
    if (typeof window === "undefined") return "temp-id";
    const local = localStorage.getItem("tspi_modules_custom") || "[]";
    const list = JSON.parse(local);
    const newId = `mod_${Date.now()}`;
    const item = { 
        ...data, 
        id: newId, 
        module_code: data.module_code || `P-${Date.now().toString().slice(-4)}`,
        createdAt: new Date().toISOString() 
    };
    list.push(item);
    localStorage.setItem("tspi_modules_custom", JSON.stringify(list));
    return newId;
};

export const updateModule = async (id: string, data: any) => {
    if (typeof window === "undefined") return;
    
    // Save to edited overrides map
    const editedRaw = localStorage.getItem("tspi_modules_edited") || "{}";
    const editedMap = JSON.parse(editedRaw);
    
    editedMap[String(id)] = {
        ...editedMap[String(id)],
        ...data,
        updatedAt: new Date().toISOString()
    };
    localStorage.setItem("tspi_modules_edited", JSON.stringify(editedMap));
};

export const deleteModule = async (id: string) => {
    if (typeof window === "undefined") return;
    
    const deletedRaw = localStorage.getItem("tspi_modules_deleted") || "[]";
    const deletedList = JSON.parse(deletedRaw);
    
    if (!deletedList.includes(String(id))) {
        deletedList.push(String(id));
        localStorage.setItem("tspi_modules_deleted", JSON.stringify(deletedList));
    }
};

// ==================== GENERATED CLINICAL REPORTS ====================

export const saveGeneratedReport = async (
    patientId: string,
    patientName: string,
    patientHn: string,
    reportType: "physician" | "patient" | "multi-omics",
    inputsUsed: { symptoms: string; labResults: any; history: string },
    reportData: Array<{ chapterTitle: string; content: string }>,
    analysisRecordId?: string | null
) => {
    const patient = await getPatient(patientId);
    if (!patient) {
        throw new Error(`ไม่พบข้อมูลคนไข้ (${patientId}) — ไม่สามารถบันทึกรายงานได้`);
    }

    const reports = patient.extra_data?.generated_reports || [];
    const newId = `report_${Date.now()}`;
    const newReport = {
        id: newId,
        patientId,
        patientName,
        patientHn,
        reportType,
        inputsUsed,
        report: reportData,
        createdAt: new Date().toISOString(),
        approvalStatus: "PENDING_REVIEW",
        // P0-C: the immutable Django AnalysisRecord this report was generated from, so PDF
        // export can render the same gated axis table instead of re-pulling raw DB values
        // (ans.txt problem #9/#11 — see backend/patients/views_ai.py generate_report_pdf_view).
        analysisRecordId: analysisRecordId ?? null
    };
    await updatePatient(patientId, {
        extra_data: {
            ...(patient.extra_data || {}),
            generated_reports: [newReport, ...reports]
        }
    });
    return newId;
};

// Marks a generated report as physician-approved. Must be called explicitly by a
// signed-in doctor action — reports default to PENDING_REVIEW until this is called.
export const approveGeneratedReport = async (patientId: string, reportId: string, approvedBy: string) => {
    const patient = await getPatient(patientId);
    if (!patient) {
        throw new Error(`ไม่พบข้อมูลคนไข้ (${patientId}) — ไม่สามารถอนุมัติรายงานได้`);
    }

    const reports = patient.extra_data?.generated_reports || [];
    const updatedReports = reports.map((r: any) =>
        r.id === reportId
            ? { ...r, approvalStatus: "APPROVED", approvedBy, approvedAt: new Date().toISOString() }
            : r
    );

    await updatePatient(patientId, {
        extra_data: {
            ...(patient.extra_data || {}),
            generated_reports: updatedReports
        }
    });

    return updatedReports.find((r: any) => r.id === reportId);
};

export const getGeneratedReports = async (patientId: string) => {
    try {
        const patient = await getPatient(patientId);
        if (patient && patient.extra_data && Array.isArray(patient.extra_data.generated_reports)) {
            return patient.extra_data.generated_reports;
        }
    } catch (e) {
        console.error("Failed to get generated reports:", e);
    }
    return [];
};

export const deleteGeneratedReport = async (reportId: string, patientId?: string) => {
    try {
        if (!patientId) return;
        const patient = await getPatient(patientId);
        if (patient && patient.extra_data && Array.isArray(patient.extra_data.generated_reports)) {
            const updated = patient.extra_data.generated_reports.filter((r: any) => r.id !== reportId);
            await updatePatient(patientId, {
                extra_data: {
                    ...patient.extra_data,
                    generated_reports: updated
                }
            });
        }
    } catch (e) {
        console.error("Failed to delete generated report:", e);
    }
};

// ==================== INTAKE CHAT SESSIONS ====================

export const getIntakeSessions = async () => {
    try {
        const activeSessions = await djangoFetch("/api/patients/active-intake-sessions/");
        return activeSessions || [];
    } catch (e) {
        console.error("Failed to get active intake sessions:", e);
        return [];
    }
};

export const saveIntakeSessionMessage = async (
    patientId: string, 
    sessionId: string, 
    message: any, 
    aiActive?: boolean,
    systemMessage?: any
) => {
    try {
        const payload: Record<string, any> = {
            session_id: sessionId,
            message: message
        };
        if (aiActive !== undefined) {
            payload.ai_active = aiActive;
        }
        if (systemMessage !== undefined) {
            payload.system_message = systemMessage;
        }
        
        await djangoFetch(`/api/patients/${patientId}/save-intake-message/`, {
            method: "POST",
            body: JSON.stringify(payload)
        });
    } catch (e) {
        console.error("Failed to save intake session message:", e);
    }
};

export const updateIntakeSessionStatus = async (patientId: string, sessionId: string, aiActive: boolean) => {
    try {
        await djangoFetch(`/api/patients/${patientId}/update-intake-status/`, {
            method: "POST",
            body: JSON.stringify({
                session_id: sessionId,
                ai_active: aiActive
            })
        });
    } catch (e) {
        console.error("Failed to update intake session status:", e);
    }
};

export const getIntakeSession = async (patientId: string, sessionId: string) => {
    try {
        const patient = await getPatient(patientId);
        if (patient && patient.extra_data?.intake_sessions) {
            return patient.extra_data.intake_sessions[sessionId] || null;
        }
    } catch (e) {
        console.error("Failed to get intake session:", e);
    }
    return null;
};

export const createIntakeSession = async (patientId: string, sessionId: string, initialMsg: any) => {
    try {
        const patient = await getPatient(patientId);
        if (patient) {
            const sessions = patient.extra_data?.intake_sessions || {};
            sessions[sessionId] = {
                status: "active",
                aiActive: true,
                startedAt: new Date().toISOString(),
                messages: [initialMsg]
            };
            await updatePatient(patientId, {
                extra_data: {
                    ...(patient.extra_data || {}),
                    intake_sessions: sessions
                }
            });
        }
    } catch (e) {
        console.error("Failed to create intake session:", e);
    }
};


// ==================== CLINICAL AUTOMATIONS ====================

export const getAutomations = async () => {
    try {
        return await djangoFetch("/api/automations/?no_pagination=true");
    } catch (e) {
        console.error("Failed to fetch automations:", e);
        return [];
    }
};

export const createAutomationTask = async (task: any) => {
    try {
        const payload = {
            type: task.type,
            status: task.status || "pending",
            patientName: task.patientName,
            patientHn: task.patientHn || "",
            scheduledFor: task.scheduledFor || new Date().toISOString(),
            logs: task.logs || ["Task initialized in queue"]
        };
        const res = await djangoFetch("/api/automations/", {
            method: "POST",
            body: JSON.stringify(payload)
        });
        return String(res.id);
    } catch (e) {
        console.error("Failed to create automation task:", e);
        return "temp-id";
    }
};

export const updateAutomationTask = async (id: string, data: any) => {
    try {
        // Map keys to API format
        const payload: any = {};
        if (data.type) payload.type = data.type;
        if (data.status) payload.status = data.status;
        if (data.patientName) payload.patientName = data.patientName;
        if (data.patientHn) payload.patientHn = data.patientHn;
        if (data.scheduledFor) payload.scheduledFor = data.scheduledFor;
        if (data.logs) payload.logs = data.logs;

        await djangoFetch(`/api/automations/${id}/`, {
            method: "PATCH",
            body: JSON.stringify(payload)
        });
    } catch (e) {
        console.error("Failed to update automation task:", e);
    }
};

export const runBackendWorkers = async () => {
    try {
        return await djangoFetch("/api/automations/run-workers/", {
            method: "POST"
        });
    } catch (e) {
        console.error("Failed to trigger backend workers:", e);
        return { success: false, error: String(e) };
    }
};

export const getAppointment = async (id: string) => {
    try {
        const appt = await djangoFetch(`/api/appointments/${id}/`);
        return {
            ...appt,
            id: String(appt.id),
            date: appt.date_meet,
            time: appt.time_meet,
            name: appt.userid,
            patientName: appt.userid,
            type: appt.symptom || "ตรวจวินิจฉัยทั่วไป",
            status: appt.status || "pending",
            urgencyScore: appt.time_id || 0,
            expectedDuration: 30
        };
    } catch (e) {
        console.error(`Failed to get appointment ${id} from Django:`, e);
        return null;
    }
};


export const analyzeLabOcr = async (patientId: string, mimeType: string, base64Data: string) => {
    try {
        return await djangoFetch("/api/ai/analyze-lab-ocr/", {
            method: "POST",
            body: JSON.stringify({ patientId, mimeType, base64Data })
        });
    } catch (e) {
        console.error("Failed to analyze lab OCR:", e);
        throw e;
    }
};

export const getTspiAnalysis = async (patientId: string, bowelStatus: string = 'normal') => {
    try {
        return await djangoFetch(`/api/patients/${patientId}/tspi-analysis/?bowel_status=${bowelStatus}`);
    } catch (e) {
        console.error(`Failed to get TSPI analysis for patient ${patientId}:`, e);
        return null;
    }
};

export const getClinicalAnalyses = async (patientId: string) => {
    try {
        const patient = await getPatient(patientId);
        if (patient && patient.extra_data && Array.isArray(patient.extra_data.clinical_analyses)) {
            return patient.extra_data.clinical_analyses;
        }
    } catch (e) {
        console.error("Failed to get clinical analyses:", e);
    }
    return [];
};

export const saveClinicalAnalysis = async (patientId: string, analysis: any) => {
    try {
        const patient = await getPatient(patientId);
        if (patient) {
            const analyses = patient.extra_data?.clinical_analyses || [];
            const newId = `analysis_${Date.now()}`;
            const newAnalysis = {
                id: newId,
                patientId,
                patientName: `${patient.first_name} ${patient.last_name}`,
                timestamp: new Date().toISOString(),
                ...analysis
            };
            await updatePatient(patientId, {
                extra_data: {
                    ...(patient.extra_data || {}),
                    clinical_analyses: [newAnalysis, ...analyses]
                }
            });
            return newId;
        }
    } catch (e) {
        console.error("Failed to save clinical analysis:", e);
    }
    return "client-created-analysis-id";
};

export const getDoctorProfile = async () => {
    try {
        return await djangoFetch("/api/auth/doctor/me/");
    } catch (e) {
        console.error("Failed to get doctor profile:", e);
        return null;
    }
};

export const updateDoctorProfile = async (profileData: { first_name: string; last_name: string }) => {
    try {
        return await djangoFetch("/api/auth/doctor/me/", {
            method: "PUT",
            body: JSON.stringify(profileData)
        });
    } catch (e) {
        console.error("Failed to update doctor profile:", e);
        throw e;
    }
};

export const changePassword = async (passwordData: any) => {
    try {
        return await djangoFetch("/api/auth/change-password/", {
            method: "POST",
            body: JSON.stringify(passwordData)
        });
    } catch (e) {
        console.error("Failed to change password:", e);
        throw e;
    }
};




