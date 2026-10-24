import axesData from '@/data/39_last_x.json';
import modulesDb from '@/data/200_module_tspi.json';
import labMapping from '@/data/lab_mapping.json';
import clinicalRules from '@/data/clinical_rules.json';

// Removed Firebase dbAdmin import. Connected to Django PostgreSQL.

export interface AxisScore {
  axisId: string;
  score: number;
  severity: 'Low' | 'Moderate' | 'High' | 'Critical';
  reasoning: string;
  evidence: string[];
  suggestedModules: any[];
}

export interface PrecisionAnalysisResult {
  patientId: string;
  timestamp: string;
  axesScores: Record<string, AxisScore>;
  domainIndices: Record<string, number>;
  topPriorities: string[];
}

export class PrecisionEngine {
  axes: any[];
  modules: any[];
  labMap: any[];

  constructor() {
    // Flatten all axes from 12 domains (39_last_x.json)
    this.axes = (axesData as any).domains
      .filter((d: any) => d.axes && d.axes.length > 0)
      .flatMap((d: any) => d.axes.map((a: any) => ({ ...a, domain_id: d.domain_id, domain_title: d.title })));

    // 200 modules from 200_module_tspi.json (uses .data array)
    this.modules = (modulesDb as any).data || [];

    // Lab mapping
    this.labMap = ((labMapping as any).mappings) || [];
  }

  async analyzeAxis(axisId: string, patientData: any, customWeights?: Record<string, number>): Promise<AxisScore> {
    const numericId = parseInt(axisId.replace('AXIS_', ''));
    const axisDef = this.axes.find(a => a.axis_id === numericId);

    // Dynamic weight override for this axis (defaults to 1.0)
    const weightOverride = customWeights && customWeights[axisId] !== undefined ? customWeights[axisId] : 1.0;

    let score = 50;
    const evidence: string[] = [];

    // 🧪 Lab Scoring
    const relevantLabs = this.labMap.filter((m: any) => m.axisId === axisId);
    if (relevantLabs.length > 0 && patientData.labs) {
      let labTotalScore = 0;
      let totalWeight = 0;
      relevantLabs.forEach((m: any) => {
        const val = patientData.labs[m.marker];
        if (val !== undefined) {
          let contribution = 0;
          if (val > m.criticalRange.min) contribution = 100;
          else if (val > m.optimalRange.max) contribution = 70;
          else contribution = 20;

          // Apply biomarker base weight and engine override weight
          const finalBiomarkerWeight = m.weight * weightOverride;

          labTotalScore += contribution * finalBiomarkerWeight;
          totalWeight += finalBiomarkerWeight;
          evidence.push(`Lab: ${m.marker} = ${val} (${contribution > 70 ? 'Critical' : 'Suboptimal'})`);
        }
      });
      if (totalWeight > 0) score = labTotalScore / totalWeight;
    }

    // 🩺 Symptom Adjustment
    if (patientData.symptoms && patientData.symptoms.length > 0) {
      score = Math.min(100, score + patientData.symptoms.length * 5 * weightOverride);
    }

    const severity = this.getSeverity(score);

    // 🌿 Match modules via "TSPI Axis Mapping" field
    // Use 'Axis N ' (with space) to prevent Axis 1 matching Axis 10, 15, etc.
    const axisTag = `Axis ${numericId} `;
    const suggestedModules = this.modules
      .filter((m: any) => (m['TSPI Axis Mapping'] || '').includes(axisTag))
      .slice(0, 3)
      .map((m: any) => ({
        id: m['Code /_Product ID'],
        name: m['Product Derived From'],
        mechanism: m['Main Key Mechanism_(3 Pillars)'] || ''
      }));

    return {
      axisId,
      score: Math.round(score),
      severity,
      reasoning: evidence.length > 0
        ? `Analysis based on: ${evidence.join(', ')}`
        : `Baseline analysis for ${axisDef?.name ?? axisId}.`,
      evidence,
      suggestedModules
    };
  }

  recommendModules(axesScores: Record<string, AxisScore>): any[] {
    const criticalAxes = Object.values(axesScores).filter(a => a.score > 70);
    const scoreMap: Record<string, { name: string; synergyScore: number; coveredAxes: string[]; mechanism: string }> = {};

    this.modules.forEach((module: any) => {
      const mapping = module['TSPI Axis Mapping'] || '';
      const id = module['Code /_Product ID'];
      if (!id) return;

      criticalAxes.forEach(ax => {
        const numericId = ax.axisId.replace('AXIS_', '');
        if (mapping.includes(`Axis ${numericId} `)) {
          if (!scoreMap[id]) {
            scoreMap[id] = {
              name: module['Product Derived From'] || id,
              synergyScore: 0,
              coveredAxes: [],
              mechanism: module['Main Key Mechanism_(3 Pillars)'] || ''
            };
          }
          scoreMap[id].synergyScore += ax.score / 100;
          scoreMap[id].coveredAxes.push(ax.axisId);
        }
      });
    });

    return Object.entries(scoreMap)
      .map(([id, data]) => ({ id, ...data }))
      .sort((a, b) => b.synergyScore - a.synergyScore);
  }

  getSeverity(score: number): AxisScore['severity'] {
    if (score >= 85) return 'Critical';
    if (score >= 70) return 'High';
    if (score >= 35) return 'Moderate';
    return 'Low';
  }

  async runFullAnalysis(patientId: string, patientData: any): Promise<PrecisionAnalysisResult> {
    const results: Record<string, AxisScore> = {};

    // 1. Fetch custom weights from Django settings dynamically
    let customWeights: Record<string, number> = {};
    try {
      const backendBaseUrl = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";
      const res = await fetch(`${backendBaseUrl}/api/settings/axes_weight_config/`);
      if (res.ok) {
        const data = await res.json();
        // setting_value stores stringified json
        const parsed = JSON.parse(data.setting_value || '{}');
        customWeights = parsed.weights || {};
        console.log("⚙️ Precision Engine: Loaded custom axes weights override from Django PostgreSQL:", Object.keys(customWeights).length, "weights");
      }
    } catch (e: any) {
      console.warn("⚠️ Failed to load custom weights from Django, using default weights (1.0):", e.message);
    }

    for (const axis of this.axes) {
      const axisId = `AXIS_${axis.axis_id}`;
      results[axisId] = await this.analyzeAxis(axisId, patientData, customWeights);
    }

    const domainIndices: Record<string, number> = {};
    (axesData as any).domains
      .filter((d: any) => d.axes && d.axes.length > 0)
      .forEach((domain: any) => {
        const scores = domain.axes.map((a: any) => results[`AXIS_${a.axis_id}`]?.score ?? 50);
        const avg = scores.reduce((a: number, b: number) => a + b, 0) / scores.length;
        domainIndices[`DOMAIN_${domain.domain_id}`] = Math.round(avg);
      });

    return {
      patientId,
      timestamp: new Date().toISOString(),
      axesScores: results,
      domainIndices,
      topPriorities: Object.keys(results)
        .filter(id => results[id].score > 75)
        .sort((a, b) => results[b].score - results[a].score)
    };
  }

  evaluateRules(axesScores: Record<string, AxisScore>): any[] {
    const triggeredRules: any[] = [];
    (clinicalRules as any).rules?.forEach((rule: any) => {
      if (this.parseCondition(rule.condition, axesScores)) {
        triggeredRules.push(rule);
      }
    });
    return triggeredRules;
  }

  parseCondition(condition: string, scores: Record<string, AxisScore>): boolean {
    return condition.split(' AND ').every(part => {
      const [key, op, val] = part.trim().split(' ');
      const axisScore = scores[key]?.score ?? 0;
      const targetVal = parseInt(val);
      if (op === '>') return axisScore > targetVal;
      if (op === '<') return axisScore < targetVal;
      return false;
    });
  }

  getAxisDef(axisId: string) {
    const numericId = parseInt(axisId.replace('AXIS_', ''));
    return this.axes.find(a => a.axis_id === numericId);
  }
}

export const precisionEngine = new PrecisionEngine();
