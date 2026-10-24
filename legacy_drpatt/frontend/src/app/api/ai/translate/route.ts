import { NextRequest, NextResponse } from "next/server";
import { ai } from "@/lib/genkit";

export async function POST(req: NextRequest) {
   try {
      const { text, targetLang } = await req.json();

      if (!text || !targetLang) {
         return NextResponse.json({ error: "Missing text or targetLang" }, { status: 400 });
      }

      const langName = targetLang === "th" ? "Thai" : "English";

      const translationResult = await ai.generate({
         model: "groq/llama-3.3-70b-versatile",
         system: `You are a professional medical translator. Translate the given medical text into ${langName}. 
                  Maintain all medical terminology accurately, keeping English terms in parentheses if necessary when translating to Thai. 
                  Do not add any conversational filler, only return the translated text.`,
         prompt: `Translate this to ${langName}:\n\n${text}`
      });

      return NextResponse.json({ translatedText: translationResult.text });
   } catch (error: any) {
      console.error("Translation API Error:", error);
      return NextResponse.json({ error: error.message || "Failed to translate" }, { status: 500 });
   }
}
