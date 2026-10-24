import { z } from 'zod';
import { ai, models } from './genkit';
import { biologicalScoringFlow } from './scoring-flow';
import * as fs from 'fs';
import * as path from 'path';

// --- Structured Clinical Summary Schema ---
const ClinicalSummarySchema = z.object({
  clinicalImpression: z.object({
    summary: z.string(),
    keyFindings: z.array(z.string()),
  }),
  rootCauseAnalysis: z.object({
    primaryDriver: z.string(),
    contributingFactors: z.array(z.string()),
  }),
  recommendedActionsForPhysician: z.array(z.object({
    priority: z.string(),
    action: z.string(),
    rationale: z.string(),
  })),
  lifestyleAndDietaryAdviceForPatient: z.array(z.string()),
  physicianNotes: z.string(),
});

const ReportInputSchema = z.object({
  patientId: z.union([z.string(), z.number()]).transform(val => String(val)),
  patientData: z.object({
    profile: z.any(), labs: z.any(), symptoms: z.any(), medications: z.any(),
    genomics: z.any(), microbiome: z.any(), proteomics: z.any(),
    biologicalScores: z.any(),
  }),
  reportType: z.enum(['Physician', 'Patient']).default('Physician'),
});

const ChapterOutputSchema = z.object({
  chapterNumber: z.number(), title: z.string(), content: z.string(), summary: z.string(),
});

/**
 * ✍️ Writing Engine: Powered by Claude (Anthropic)
 */
export const clinicalReportFlow = ai.defineFlow(
  {
    name: 'clinicalReportFlow',
    inputSchema: ReportInputSchema,
    outputSchema: z.object({
      reportId: z.string(), fullReport: z.string(), chapters: z.record(z.any()),
      biologicalScores: z.any().optional(),
    }),
  },
  async (input) => {
    let chapters: Record<string, any> = {};
    let fullReport = `# TSPI ${input.reportType} Precision Medicine Analysis\n\n`;
    let scores = input.patientData?.biologicalScores;

    if (!scores || Object.keys(scores).length === 0) {
      scores = await biologicalScoringFlow({
        patientData: input.patientData
      });
    }

    const chapterConfigs = [
      { num: 1, title: 'Executive Clinical Synopsis & Strategic Roadmap' },
      { num: 5, title: 'Laboratory Systems Analysis' },
      { num: 9, title: 'Mitochondrial Function' },
      { num: 18, title: 'Lifestyle Prescription' },
      { num: 19, title: 'Clinical Summary' },
      // ... (other chapters omitted for brevity in demo, but system can run all 20)
    ];

    for (const config of chapterConfigs) {
      try {
          if (config.num === 1) {
              const summaryResponse = await ai.generate({
                model: models.writer, // ✍️ Use Claude for high-level summary
                prompt: `
                  คุณคือ TSPI Chief Medical Officer. วิเคราะห์ข้อมูลผู้ป่วยระดับ Systems Biology.
                  สร้าง "Executive Clinical Summary" ที่คมชัดที่สุดตามโครงสร้างที่กำหนด.
                  ข้อมูลผู้ป่วย: ${JSON.stringify(input.patientData, null, 2)}
                  คะแนน Biological Axes: ${JSON.stringify(scores, null, 2)}
                `,
                output: { schema: ClinicalSummarySchema }
              });

              const summaryData = summaryResponse.output;
              if (summaryData) {
                  chapters["1"] = summaryData;
                  let md = `### 1.1 Clinical Impression\n> ${summaryData.clinicalImpression.summary}\n\n`;
                  md += `**Key Findings:**\n${summaryData.clinicalImpression.keyFindings.map(f => `- ${f}`).join('\n')}\n\n`;
                  md += `### 1.2 Root Cause Analysis\n- **Primary Driver:** ${summaryData.rootCauseAnalysis.primaryDriver}\n`;
                  md += `**Contributing Factors:**\n${summaryData.rootCauseAnalysis.contributingFactors.map(f => `- ${f}`).join('\n')}\n\n`;
                  md += `### 1.3 Recommended Actions\n`;
                  md += summaryData.recommendedActionsForPhysician.map(a => `**[${a.priority}] ${a.action}**\n*Rationale:* ${a.rationale}`).join('\n\n');
                  fullReport += `## ${config.title}\n\n${md}\n\n`;
              }
          } else {
              const response = await ai.generate({
                model: models.writer, // ✍️ Use Claude for detailed writing
                prompt: `
                  Generate Chapter ${config.num}: "${config.title}" for a ${input.reportType} report.
                  Patient Data: ${JSON.stringify(input.patientData, null, 2)}
                  Axis Scores: ${JSON.stringify(scores, null, 2)}
                `,
                output: { schema: ChapterOutputSchema }
              });

              const content = response.output?.content || response.text || "Analysis not available.";
              chapters[config.num.toString()] = content;
              fullReport += `## Chapter ${config.num}: ${config.title}\n\n${content}\n\n`;
          }
          console.log(`✅ Chapter ${config.num} (Claude) generated.`);
      } catch (err) {
          console.error(`❌ Chapter ${config.num} Error:`, err);
      }
    }

    // Save to local file
    try {
        const reportsDir = path.join(process.cwd(), 'reports');
        if (!fs.existsSync(reportsDir)) fs.mkdirSync(reportsDir, { recursive: true });
        const filename = `REP-${input.patientId}-${Date.now()}.md`;
        fs.writeFileSync(path.join(reportsDir, filename), fullReport, 'utf8');
    } catch (e) {}

    return { reportId: `REP-${Date.now()}`, fullReport, chapters, biologicalScores: scores };
  }
);
