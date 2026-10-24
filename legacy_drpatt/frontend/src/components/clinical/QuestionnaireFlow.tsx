"use client";

import { useState } from "react";
import { QuestionnaireSession } from "@/types/clinical";
import { getPatient, updatePatient, getTspiAnalysis } from "@/utils/api/services";
import { useRouter } from "next/navigation";
import { Loader2, ArrowRight, CheckCircle2, Sparkles } from "lucide-react";

export default function QuestionnaireFlow({ session }: { session: QuestionnaireSession }) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string | number | boolean>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const router = useRouter();

  if (!session || !session.questions || session.questions.length === 0) {
    return <div className="text-center p-5 text-muted font-kanit">ไม่พบคำถามในเซสชันนี้</div>;
  }

  const currentQuestion = session.questions[currentIndex];
  const totalQuestions = session.questions.length;
  const progress = ((currentIndex) / totalQuestions) * 100;

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setAnswers((prev) => ({ ...prev, [currentQuestion.id]: parseInt(e.target.value, 10) }));
  };

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setAnswers((prev) => ({ ...prev, [currentQuestion.id]: e.target.value }));
  };

  const handleBooleanClick = (value: boolean) => {
    setAnswers((prev) => ({ ...prev, [currentQuestion.id]: value }));
  };

  const handleMultipleChoiceClick = (option: string) => {
    setAnswers((prev) => ({ ...prev, [currentQuestion.id]: option }));
  };

  const currentAnswer = answers[currentQuestion.id];

  const handleNext = async () => {
    // กำหนดค่าเริ่มต้นถ้าคนไข้กดผ่านโดยไม่ตอบ (แล้วแต่ประเภท)
    if (answers[currentQuestion.id] === undefined) {
      if (currentQuestion.type === "slider_0_10") {
        setAnswers((prev) => ({ ...prev, [currentQuestion.id]: 5 }));
      } else if (currentQuestion.type === "text") {
        setAnswers((prev) => ({ ...prev, [currentQuestion.id]: "" }));
      }
    }

    if (currentIndex < totalQuestions - 1) {
      setCurrentIndex((prev) => prev + 1);
    } else {
      await handleSubmit();
    }
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      const responsePayload: any = {
        id: `resp_${Date.now()}`,
        sessionId: session.id,
        patientId: session.patientId,
        submittedAt: new Date().toISOString(),
        answers: Object.entries(answers).map(([questionId, value]) => ({
          questionId,
          value,
        })),
        aiAnalysis: null,
        aiProcessedAt: null
      };

      try {
        // Trigger TSPI Digital Twin analysis on the Django backend
        const result = await getTspiAnalysis(session.patientId);

        if (result) {
          responsePayload.aiAnalysis = result;
          responsePayload.aiProcessedAt = new Date().toISOString();
        }
        console.log("AI Analysis Complete:", result);
      } catch (aiError) {
        console.error("AI Evaluation failed, but response will be saved:", aiError);
      }

      // Update patient profile questionnaire_sessions and questionnaire_responses
      const patient = await getPatient(session.patientId);
      if (patient) {
        const sessionsList = patient.extra_data?.questionnaire_sessions || [];
        const updatedSessions = sessionsList.map((s: any) => 
          s.id === session.id ? { ...s, status: "completed" } : s
        );
        const responsesList = patient.extra_data?.questionnaire_responses || [];
        const updatedResponses = [responsePayload, ...responsesList];

        await updatePatient(session.patientId, {
          extra_data: {
            ...(patient.extra_data || {}),
            questionnaire_sessions: updatedSessions,
            questionnaire_responses: updatedResponses
          }
        });
      }
      
      router.push("/patient/dashboard");
    } catch (error) {
      console.error("Error submitting response:", error);
      alert("เกิดข้อผิดพลาดในการบันทึกข้อมูล กรุณาลองใหม่อีกครั้ง");
      setIsSubmitting(false);
    }
  };

  return (
    <div className="container-fluid p-4 font-kanit d-flex flex-column" style={{ minHeight: 'calc(100vh - 70px)' }}>
      {/* Progress Bar */}
      <div className="mb-4">
        <div className="d-flex justify-content-between align-items-center mb-2">
          <span className="small fw-bold text-muted">
            ข้อที่ {currentIndex + 1} <span className="text-light-muted fw-normal">/ {totalQuestions}</span>
          </span>
          <span className="small fw-bold text-primary-custom">{Math.round(progress)}%</span>
        </div>
        <div className="progress" style={{ height: '6px', borderRadius: '10px', backgroundColor: '#E9ECEF' }}>
          <div 
            className="progress-bar bg-primary-custom" 
            role="progressbar" 
            style={{ width: `${progress}%`, transition: 'width 0.4s ease' }} 
          />
        </div>
      </div>

      {/* Question Card */}
      <div className="bg-white rounded-4 shadow-sm border border-light p-4 mb-4 flex-grow-1 d-flex flex-column justify-content-center animate-fade-in position-relative">
        {currentQuestion.isAiGenerated && (
          <div className="d-flex align-items-center gap-2 mb-3 bg-purple bg-opacity-10 text-purple px-3 py-1 rounded-pill" style={{ width: 'fit-content' }}>
            <Sparkles size={14} />
            <span className="fw-bold" style={{ fontSize: '11px' }}>AI Follow-up: {currentQuestion.aiContext}</span>
          </div>
        )}
        
        <h3 className="fw-bold text-dark mb-4 lh-base" style={{ fontSize: '1.4rem' }}>
          {currentQuestion.text}
        </h3>

        {/* Input Types */}
        <div className="mt-2 mb-2 w-100">
           
           {/* TYPE: Slider 0-10 */}
           {currentQuestion.type === "slider_0_10" && (
             <div className="text-center">
               <div className="d-flex align-items-center justify-content-center mx-auto rounded-circle bg-light border border-2 border-white shadow-sm mb-4" style={{ width: '80px', height: '80px' }}>
                  <span className="fw-black text-primary-custom" style={{ fontSize: '2.5rem' }}>
                    {currentAnswer ?? 5}
                  </span>
               </div>
               <input 
                 type="range" className="form-range custom-range-slider mb-2"
                 min="0" max="10" step="1"
                 value={(currentAnswer as number) ?? 5}
                 onChange={handleSliderChange}
               />
               <div className="d-flex justify-content-between px-1">
                 <span className="small fw-semibold text-muted">0 (แย่มาก)</span>
                 <span className="small fw-semibold text-muted">10 (ดีเยี่ยม)</span>
               </div>
             </div>
           )}

           {/* TYPE: Boolean (Yes/No) */}
           {currentQuestion.type === "boolean" && (
             <div className="row g-3">
               <div className="col-6">
                 <button 
                   className={`btn w-100 py-3 rounded-4 fw-bold shadow-sm ${currentAnswer === true ? 'btn-primary-custom text-white' : 'btn-light border text-muted'}`}
                   onClick={() => handleBooleanClick(true)}
                 >
                   มี / ใช่
                 </button>
               </div>
               <div className="col-6">
                 <button 
                   className={`btn w-100 py-3 rounded-4 fw-bold shadow-sm ${currentAnswer === false ? 'btn-danger text-white' : 'btn-light border text-muted'}`}
                   onClick={() => handleBooleanClick(false)}
                 >
                   ไม่มี / ไม่ใช่
                 </button>
               </div>
             </div>
           )}

           {/* TYPE: Multiple Choice */}
           {currentQuestion.type === "multiple_choice" && currentQuestion.options && (
             <div className="d-flex flex-column gap-3">
               {currentQuestion.options.map((opt, idx) => (
                 <button 
                   key={idx}
                   className={`btn w-100 py-3 rounded-4 fw-bold shadow-sm text-start px-4 ${currentAnswer === opt ? 'btn-primary-custom text-white border-primary-custom' : 'btn-light border border-light text-dark'}`}
                   onClick={() => handleMultipleChoiceClick(opt)}
                 >
                   {opt}
                 </button>
               ))}
             </div>
           )}

           {/* TYPE: Text (Subjective) */}
           {currentQuestion.type === "text" && (
             <div className="form-group">
               <textarea 
                 className="form-control rounded-4 p-3 bg-light border-0 shadow-inner"
                 rows={5}
                 placeholder="พิมพ์คำตอบของคุณที่นี่..."
                 value={(currentAnswer as string) || ""}
                 onChange={handleTextChange}
                 style={{ resize: 'none' }}
               />
             </div>
           )}

        </div>
      </div>

      {/* Control Buttons */}
      <div className="mt-auto">
         <button 
           onClick={handleNext}
           disabled={isSubmitting || (currentQuestion.type === "multiple_choice" && currentAnswer === undefined) || (currentQuestion.type === "boolean" && currentAnswer === undefined)}
           className="btn btn-dark w-100 rounded-pill py-3 fw-bold shadow d-flex align-items-center justify-content-center gap-2"
           style={{ fontSize: '1.1rem' }}
         >
           {isSubmitting ? (
              <><Loader2 className="animate-spin" size={20} /> กำลังบันทึกข้อมูล...</>
           ) : currentIndex === totalQuestions - 1 ? (
              <><CheckCircle2 size={20} /> บันทึกและส่งข้อมูล</>
           ) : (
              <>ถัดไป <ArrowRight size={20} /></>
           )}
         </button>
      </div>

      <style jsx>{`
        .text-light-muted { color: #adb5bd; }
        .bg-purple { background-color: rgba(111, 66, 193, 1); }
        .text-purple { color: #6f42c1; }
        .shadow-inner { box-shadow: inset 0 2px 4px 0 rgb(0 0 0 / 0.05); }
        .custom-range-slider {
           -webkit-appearance: none; width: 100%; height: 8px; border-radius: 5px; background: #e9ecef; outline: none;
        }
        .custom-range-slider::-webkit-slider-thumb {
           -webkit-appearance: none; appearance: none; width: 28px; height: 28px; border-radius: 50%;
           background: #2563eb; cursor: pointer; border: 4px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.2); transition: transform 0.1s;
        }
        .custom-range-slider::-webkit-slider-thumb:active { transform: scale(1.1); }
      `}</style>
    </div>
  );
}
