// frontend/src/lib/axis-definitions.ts

import axesData from '@/data/39_last_x.json';

// กำหนด Type สำหรับข้อมูลแกน (ดึงเฉพาะที่จำเป็น)
export interface SubAxis {
    name: string;
    description: string;
}

export interface Axis {
    axis_id: number;
    name: string;
    sub_axes: {
        A?: SubAxis;
        B?: SubAxis;
        C?: SubAxis;
        D?: SubAxis;
    };
    modules: string[];
    modules_by_context: Partial<Record<string, string[]>>;
}

export interface Domain {
    domain_id: number;
    title: string;
    axes: Axis[];
}

// ฟังก์ชันหลัก: ดึงข้อมูลแกนทั้งหมด
export function getAxesDefinitions(): Axis[] {
    // axesData เป็น array ของ Domain แต่ละ Domain มี axes
    const allAxes: Axis[] = [];

    axesData.domains.forEach((domain: Domain) => {
        if (domain.axes && domain.axes.length > 0) {
            allAxes.push(...domain.axes);
        }
    });

    return allAxes;
}

// ฟังก์ชัน: ดึงข้อมูลแกนตาม ID
export function getAxisById(axisId: number): Axis | undefined {
    const axes = getAxesDefinitions();
    return axes.find(axis => axis.axis_id === axisId);
}

// ฟังก์ชัน: ดึงชื่อแกนตาม ID
export function getAxisName(axisId: number): string {
    const axis = getAxisById(axisId);
    return axis?.name || `Axis ${axisId} (ไม่พบข้อมูล)`;
}

// ฟังก์ชัน: สร้างข้อความสำหรับ AI Prompt (รูปแบบเดียวกับที่เคย Hardcode)
export function buildAxesPromptText(): string {
    const axes = getAxesDefinitions();
    return axes
        .map(axis => `AXIS_${axis.axis_id}: ${axis.name}`)
        .join('\n');
}

// ฟังก์ชัน: สร้างข้อความแบบมีรายละเอียด (ใช้ตอนต้องการข้อมูลเพิ่ม)
export function buildDetailedAxesPrompt(): string {
    const axes = getAxesDefinitions();
    let result = '';

    axes.forEach(axis => {
        result += `\n### AXIS_${axis.axis_id}: ${axis.name}\n`;

        // เพิ่ม sub-axes ถ้ามี
        if (axis.sub_axes) {
            const subKeys = ['A', 'B', 'C', 'D'] as const;
            subKeys.forEach(key => {
                const sub = axis.sub_axes[key as keyof typeof axis.sub_axes];
                if (sub) {
                    result += `  - ${key}. ${sub.name}: ${sub.description}\n`;
                }
            });
        }
    });

    return result;
}

// Export default สำหรับสะดวก
export default {
    getAxesDefinitions,
    getAxisById,
    getAxisName,
    buildAxesPromptText,
    buildDetailedAxesPrompt,
};
