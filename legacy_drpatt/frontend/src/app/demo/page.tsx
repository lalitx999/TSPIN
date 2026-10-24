'use client';

import { useState } from 'react';

type DemoStep = 'idle' | 'loading' | 'success' | 'error';

interface DemoResult {
  label: string;
  status: DemoStep;
  data?: any;
  error?: string;
  duration?: number;
}

export default function DemoPage() {
  const [patientId, setPatientId] = useState('');
  const [patientData, setPatientData] = useState<any>(null);
  const [dataStatus, setDataStatus] = useState<DemoStep>('idle');
  const [dataError, setDataError] = useState('');
  const [results, setResults] = useState<DemoResult[]>([]);
  const [loading, setLoading] = useState(false);

  async function loadPatient() {
    if (!patientId.trim()) return;
    setDataStatus('loading');
    setPatientData(null);
    setDataError('');
    setResults([]);

    const start = performance.now();

    try {
      const res = await fetch('/api/ai/patient-data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ patientId: patientId.trim() }),
      });

      const body = await res.json();
      if (!res.ok) throw new Error(body.error || `HTTP ${res.status}`);

      setPatientData(body.data);
      setDataStatus('success');
    } catch (err: any) {
      setDataStatus('error');
      setDataError(err.message);
    }
  }

  async function runScore() {
    if (!patientData) return;
    setLoading(true);
    const start = performance.now();
    try {
      const res = await fetch(
        'https://us-central1-tspi-ee68e.cloudfunctions.net/biologicalScoring',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            data: {
              patientData: {
                labs: patientData.labs,
                symptoms: patientData.symptoms,
                medications: patientData.medications,
                genomics: patientData.genomics,
              },
            },
          }),
        }
      );
      const body = await res.json();
      if (!res.ok) throw new Error(body.error?.message || `HTTP ${res.status}`);
      setResults(prev => [...prev, { label: '🧬 Biological Scoring', status: 'success', data: body.result, duration: Math.round(performance.now() - start) }]);
    } catch (err: any) {
      setResults(prev => [...prev, { label: '🧬 Biological Scoring', status: 'error', error: err.message, duration: Math.round(performance.now() - start) }]);
    }
    setLoading(false);
  }

  async function runSafety() {
    if (!patientData) return;
    setLoading(true);
    const start = performance.now();
    try {
      const res = await fetch(
        'https://us-central1-tspi-ee68e.cloudfunctions.net/safetyAnalysis',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            data: {
              patientId: patientId.trim(),
              genomics: patientData.genomics,
              medications: patientData.medications,
            },
          }),
        }
      );
      const body = await res.json();
      if (!res.ok) throw new Error(body.error?.message || `HTTP ${res.status}`);
      setResults(prev => [...prev, { label: '🛡️ Safety Analysis', status: 'success', data: body.result, duration: Math.round(performance.now() - start) }]);
    } catch (err: any) {
      setResults(prev => [...prev, { label: '🛡️ Safety Analysis', status: 'error', error: err.message, duration: Math.round(performance.now() - start) }]);
    }
    setLoading(false);
  }

  function renderStep(step: DemoResult, i: number) {
    return (
      <div key={i} className={`border rounded-xl p-5 transition-all ${step.status === 'success' ? 'border-green-700/50 bg-green-950/20' : 'border-red-700/50 bg-red-950/20'}`}>
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <span className="text-xl">{step.status === 'success' ? '✅' : '❌'}</span>
            <h3 className="font-semibold">{step.label}</h3>
          </div>
          {step.duration && <span className="text-xs text-gray-500">{step.duration}ms</span>}
        </div>
        {step.error && <pre className="text-xs text-red-300 bg-red-950/50 rounded-lg p-3 whitespace-pre-wrap">{step.error}</pre>}
        {step.data && (
          <>
            <button onClick={() => { const el = document.getElementById(`r-${i}`); if (el) el.classList.toggle('hidden'); }}
              className="text-xs text-gray-500 hover:text-gray-300">📊 ดู Data</button>
            <pre id={`r-${i}`} className="hidden mt-2 bg-gray-950 rounded-lg p-3 text-xs text-gray-300 overflow-auto max-h-48">
              {JSON.stringify(step.data, null, 2).slice(0, 3000)}
            </pre>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
            🏥 TSPI Clinic AI Demo
          </h1>
          <p className="text-gray-400 mt-2">Patient Analysis — ข้อมูลจริงจาก Firestore → AI</p>
        </div>

        {/* Step 1: Patient ID */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-4">
          <h2 className="text-sm text-gray-400 mb-2">👤 ขั้นตอนที่ 1: ป้อน Patient ID</h2>
          <div className="flex gap-3">
            <input type="text" value={patientId} onChange={(e) => setPatientId(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && loadPatient()}
              placeholder="Patient ID จาก Firestore"
              className="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-gray-100 placeholder-gray-500 focus:outline-none focus:border-cyan-500 text-lg font-mono" />
            <button onClick={loadPatient} disabled={dataStatus === 'loading' || !patientId.trim()}
              className="px-6 py-3 bg-cyan-600 rounded-xl font-semibold hover:bg-cyan-500 disabled:opacity-50 transition-all">
              {dataStatus === 'loading' ? '🔄 กำลังโหลด...' : '📥 โหลดข้อมูล'}
            </button>
          </div>
          {dataStatus === 'error' && <p className="text-red-400 text-sm mt-2">❌ {dataError}</p>}
        </div>

        {/* Step 2: Patient Data Preview */}
        {patientData && (
          <div className="border border-green-700/50 bg-green-950/20 rounded-xl p-5 mb-4">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-xl">✅</span>
              <h3 className="font-semibold">{patientData.profile?.name || patientId}</h3>
              <span className="text-xs text-gray-500">
                Labs: {Object.keys(patientData.labs || {}).length} · Symptoms: {(patientData.symptoms || []).length}
              </span>
            </div>
            <div className="flex gap-3 mt-4">
              <button onClick={runScore} disabled={loading}
                className="px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 rounded-lg hover:from-purple-500 hover:to-blue-500 disabled:opacity-50">
                🧬 Score
              </button>
              <button onClick={runSafety} disabled={loading}
                className="px-4 py-2 bg-gradient-to-r from-orange-600 to-red-600 rounded-lg hover:from-orange-500 hover:to-red-500 disabled:opacity-50">
                🛡️ Safety
              </button>
            </div>
          </div>
        )}

        {/* Results */}
        {results.length > 0 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-gray-300">ผลลัพธ์</h2>
            {results.map((step, i) => renderStep(step, i))}
          </div>
        )}

        <div className="mt-8 text-center text-xs text-gray-600 border-t border-gray-800 pt-4">
          TSPI Clinic AI · ข้อมูลจริงจาก Firestore
        </div>
      </div>
    </div>
  );
}
