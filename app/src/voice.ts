import { useRef, useState } from "react";
import { toast } from "./components/ui";

/** Web Speech API dictation (Chromium / Edge / Safari). */
export function useSpeech(onFinal: (text: string) => void) {
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const rec = useRef<any>(null);
  const SR: any = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
  const start = () => {
    if (!SR) {
      toast("Voice input isn't available in this window. Open Florist in Edge or Chrome (florist up) to use the mic.", "err");
      return;
    }
    const r = new SR();
    r.lang = navigator.language || "en-US";
    r.interimResults = true;
    r.onresult = (e: any) => {
      let fin = "", mid = "";
      for (let i = e.resultIndex; i < e.results.length; i++) (e.results[i].isFinal ? (fin += e.results[i][0].transcript) : (mid += e.results[i][0].transcript));
      setInterim(mid);
      if (fin) onFinal(fin.trim());
    };
    r.onend = () => { setListening(false); setInterim(""); };
    r.onerror = () => setListening(false);
    rec.current = r;
    r.start();
    setListening(true);
  };
  return { listening, interim, start, stop: () => rec.current?.stop() };
}

export function speak(text: string) {
  try {
    const u = new SpeechSynthesisUtterance(text.replace(/[*_#`>[\]()]/g, "").slice(0, 700));
    speechSynthesis.cancel();
    speechSynthesis.speak(u);
  } catch { /* no TTS */ }
}

/** Spoken commands: "grow", "stop", "pick", "new idea …", "focus on …" */
export function parseVoiceCommand(said: string): { cmd: "grow" | "stop" | "pick" | "idea" | "steer" | "say"; text: string } {
  const s = said.toLowerCase().trim();
  if (/^(grow|keep (exploring|growing)|explore( more)?|run a round)\b/.test(s)) return { cmd: "grow", text: said };
  if (/^(stop|pause)\b/.test(s)) return { cmd: "stop", text: said };
  if (/^pick\b/.test(s)) return { cmd: "pick", text: said };
  const idea = s.match(/^(new idea|what about|also try|idea)[:,]?\s+(.*)/);
  if (idea) return { cmd: "idea", text: said.slice(said.length - idea[2].length) };
  if (/^(steer|focus on|avoid|ignore)\b/.test(s)) return { cmd: "steer", text: said };
  return { cmd: "say", text: said };
}

export function modelLogo(model: string): string {
  const m = model.toLowerCase();
  if (m.startsWith("claude-code")) return "claude";
  if (m.startsWith("codex") || m.startsWith("openai")) return "openai";
  if (m === "mock") return "florist";
  return m.split(/[/:]/)[0];
}

export function modelLabel(model: string): string {
  if (!model) return "Default";
  if (model === "mock") return "Offline demo";
  const [prov, ...rest] = model.split(/[/:]/);
  const name = rest.join("/") || prov;
  const pretty: Record<string, string> = { "claude-code": "Claude Code", codex: "Codex", meta: "Meta", anthropic: "Claude API",
    openai: "OpenAI", gemini: "Gemini", ollama: "Ollama", lm_studio: "LM Studio", openrouter: "OpenRouter", mistral: "Mistral", deepseek: "DeepSeek" };
  if (prov === "claude-code") return `Claude Code · ${name.charAt(0).toUpperCase()}${name.slice(1)}`;
  if (prov === "meta") return name.replace(/^muse-/, "Muse ").replace(/-(\d)/, " $1").replace("spark", "Spark").replace("wonder", "Wonder").replace("-contributor", " · contributor");
  return `${pretty[prov] ?? prov} · ${name.replace(/-Instruct-FP8|-17B-\d+E/g, "")}`;
}
