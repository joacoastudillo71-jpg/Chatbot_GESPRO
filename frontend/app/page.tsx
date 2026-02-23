import React from "react";
import VoicePanel from "@/components/VoicePanel";
import ChatPanel from "@/components/ChatPanel";
import { Sparkles } from "lucide-react";

export default function Home() {
  // Generar un Session ID unificado para el cliente
  // En Next.js App Router (Server Component), podríamos usar cookies o generar uno estático para la demo.
  // Como esto se hidrata en el cliente, generaremos uno simple o lo pasaremos estático para pruebas.
  const sessionId = "demo-session-gespro-001";

  return (
    <main className="min-h-screen p-4 md:p-8 flex flex-col items-center justify-center relative overflow-hidden">
      {/* Decorative Blur Backgrounds */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-500/30 rounded-full mix-blend-multiply filter blur-[128px] opacity-70 animate-blob"></div>
      <div className="absolute top-[20%] right-[-10%] w-[30%] h-[30%] bg-fuchsia-500/30 rounded-full mix-blend-multiply filter blur-[128px] opacity-70 animate-blob animation-delay-2000"></div>
      <div className="absolute bottom-[-20%] left-[20%] w-[40%] h-[40%] bg-sky-500/30 rounded-full mix-blend-multiply filter blur-[128px] opacity-70 animate-blob animation-delay-4000"></div>

      <div className="w-full max-w-7xl relative z-10 flex flex-col h-[90vh] p-2 sm:p-4 lg:p-0">
        <header className="mb-4 lg:mb-8 flex items-center justify-between px-6 py-4 bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-fuchsia-500 flex items-center justify-center text-white shadow-lg">
              <Sparkles size={20} />
            </div>
            <div>
              <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-100 to-slate-400">Civetta AI Assistant</h1>
              <p className="text-xs text-slate-400 font-medium tracking-wide uppercase">Sofía - Demo Multimodal</p>
            </div>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10">
            <span className="w-2 h-2 rounded-full bg-green-400 shadow-[0_0_8px_rgba(74,222,128,0.8)]"></span>
            <span className="text-xs font-semibold text-slate-300">Sistemas Operativos</span>
          </div>
        </header>

        <div className="flex-1 flex flex-col lg:flex-row gap-4 lg:gap-6 min-h-0">
          {/* Panel Izquierdo: Voz */}
          <section className="h-[35vh] lg:h-full lg:w-1/2 shrink-0 lg:shrink">
            <VoicePanel sessionId={sessionId} />
          </section>

          {/* Panel Derecho: Texto */}
          <section className="h-[50vh] lg:h-full lg:w-1/2 flex flex-col shrink-0 lg:shrink">
            <ChatPanel sessionId={sessionId} />
          </section>
        </div>
      </div>
    </main>
  );
}
