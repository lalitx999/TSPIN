export type AuditAction = 
    | "AI_INTAKE_REQUEST" 
    | "AI_INTAKE_RESPONSE" 
    | "LAB_OCR_PROCESSED" 
    | "VOICE_TRANSCRIPTION" 
    | "USER_CONSENT_ACCEPTED"
    | "DATA_ACCESS"
    | "ADMIN_ACTION"
    | "AI_ANALYSIS"
    | "AI_VOICE_SOAP_GENERATION"
    | "LAB_TEXT_ANALYZED"
    | "CLINICAL_INTAKE_PROCESSED"
    | "LINE_LIFF_LINKED"
    | "LINE_SECURE_LINKED"
    | "LINE_WEBHOOK_UNLINKED_VISIT"
    | "LINE_WEBHOOK_AI_INTAKE";

/**
 * Recursively cleans undefined values from an object/array, replacing with null.
 */
const cleanUndefined = (obj: any): any => {
    if (obj === null || obj === undefined) return null;
    if (typeof obj !== "object") return obj;
    if (Array.isArray(obj)) return obj.map(cleanUndefined);
    const cleaned: Record<string, any> = {};
    Object.entries(obj).forEach(([key, val]) => {
        if (val !== undefined) {
            cleaned[key] = cleanUndefined(val);
        }
    });
    return cleaned;
};

const DJANGO_API_URL = (process.env.NEXT_PUBLIC_API_URL || 'https://tspi-backend.tanchonhomserverxxx.online') + '/api';

/**
 * Log an action to the Audit Trail in Django PostgreSQL backend.
 */
export const logAudit = async (data: {
    action: AuditAction;
    userId?: string;
    patientId?: string;
    details: any;
    metadata?: {
        model?: string;
        ip?: string;
        channel?: string;
        engine?: string;
    }
}) => {
    try {
        const cleanedData = cleanUndefined(data);
        const logPayload = {
            actor_id: cleanedData.userId || 'system',
            target_id: cleanedData.patientId || 'unknown',
            action: cleanedData.action,
            layer: cleanedData.details?.layer || 'A',
            client_ip: typeof window === "undefined" ? "server-side" : "client-side",
            governance_status: cleanedData.details?.governanceStatus || 'PATIENT_ACCESSIBLE'
        };

        const res = await fetch(`${DJANGO_API_URL}/logs/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(logPayload)
        });
        if (!res.ok) {
            console.warn(`Django logging returned status: ${res.status}`);
        }
    } catch (err) {
        console.error("Failed to log audit to Django:", err);
    }
};

/**
 * Fetch Audit Logs from Django PostgreSQL backend.
 */
export const getAuditLogs = async (limitCount: number = 100) => {
    try {
        const res = await fetch(`${DJANGO_API_URL}/logs/`);
        if (res.ok) {
            const logs = await res.json();
            return logs.map((log: any) => ({
                id: String(log.id),
                userId: log.actor_id,
                patientId: log.target_id,
                action: log.action,
                details: { 
                    layer: log.layer, 
                    governanceStatus: log.governance_status,
                    version: "1.0.0-django"
                },
                timestamp: log.timestamp
            })).slice(0, limitCount);
        }
        return [];
    } catch (err) {
        console.error("Failed to fetch audit logs from Django:", err);
        return [];
    }
};
