/* ==========================================================================
   Shared helpers for TSPI AI Chat (/ai/ & /patient/assistant/)
   ========================================================================== */
window.TspiAssistantUtils = (function () {
    const GENERAL_HEADING = 'ข้อมูลทั่วไปเพิ่มเติม';

    function parseParts(m) {
        const text = (m && m.content ? String(m.content) : '').replace(/\*\*/g, '').trim();
        if (m && m.kind === 'general') {
            return { clinic: '', general: text.replace(/ข้อมูลทั่วไปเพิ่มเติม[^:\n]*:\s*/, '').trim() };
        }
        const at = text.indexOf(GENERAL_HEADING);
        if (at < 0) return { clinic: text, general: '' };
        return {
            clinic: text.slice(0, at).trim(),
            general: text.slice(at).replace(/^[^:\n]*:?\s*/, '').trim(),
        };
    }

    function parseBlocks(text) {
        const segs = (line) => line.split(/(\[\d+\])/).filter(Boolean)
            .map((t) => (/^\[\d+\]$/.test(t) ? { cite: Number(t.slice(1, -1)) } : { t }));
        const out = [];
        for (const raw of (text || '').split('\n')) {
            const line = raw.trim();
            if (!line) continue;
            const li = line.match(/^(?:[-•*]|\d+[.)])\s+(.*)$/);
            if (li) {
                const last = out[out.length - 1];
                if (last && last.type === 'ul') last.items.push(segs(li[1]));
                else out.push({ type: 'ul', items: [segs(li[1])] });
            } else {
                out.push({ type: 'p', items: [segs(line)] });
            }
        }
        return out;
    }

    function autoGrow(el) {
        if (!el) return;
        el.style.height = 'auto';
        el.style.height = Math.min(el.scrollHeight, 180) + 'px';
    }

    async function copyText(text) {
        if (!text) return false;
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (e) {
            return false;
        }
    }

    function supportsSpeech() {
        return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
    }

    function createSpeechRecognizer(onText, onState) {
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SR) return null;
        const rec = new SR();
        rec.lang = 'th-TH';
        rec.interimResults = true;
        rec.continuous = false;
        let finalBuf = '';
        rec.onstart = () => { finalBuf = ''; onState(true, ''); };
        rec.onresult = (ev) => {
            let interim = '';
            for (let i = ev.resultIndex; i < ev.results.length; i++) {
                const t = ev.results[i][0].transcript;
                if (ev.results[i].isFinal) finalBuf += t;
                else interim += t;
            }
            onText((finalBuf + interim).trim(), !!finalBuf);
        };
        rec.onerror = (ev) => { onState(false, ev.error === 'not-allowed' ? 'กรุณาอนุญาตการใช้ไมโครโฟนในเบราว์เซอร์' : ''); };
        rec.onend = () => { onState(false, ''); };
        return rec;
    }

    return { parseParts, parseBlocks, autoGrow, copyText, supportsSpeech, createSpeechRecognizer };
})();

