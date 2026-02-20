"use client";

import React, { useEffect, useState } from "react";
import { RetellWebClient } from "retell-client-js-sdk";
import { Phone, PhoneOff, Mic, Loader2, Volume2 } from "lucide-react";

interface VoicePanelProps {
    sessionId: string;
}

const retellWebClient = new RetellWebClient();

export default function VoicePanel({ sessionId }: VoicePanelProps) {
    const [isCalling, setIsCalling] = useState(false);
    const [callStatus, setCallStatus] = useState<"IDLE" | "CONNECTING" | "ACTIVE">("IDLE");
    const [liveTranscript, setLiveTranscript] = useState<string>("");
    const [agentSpeaking, setAgentSpeaking] = useState(false);

    useEffect(() => {
        // Escuchar eventos del SDK de Retell
        retellWebClient.on("call_started", () => {
            setCallStatus("ACTIVE");
            setLiveTranscript("Conexión establecida. Di 'Hola' para comenzar.");
        });

        retellWebClient.on("call_ended", () => {
            setCallStatus("IDLE");
            setIsCalling(false);
            setLiveTranscript("Llamada finalizada.");
        });

        retellWebClient.on("agent_start_talking", () => setAgentSpeaking(true));
        retellWebClient.on("agent_stop_talking", () => setAgentSpeaking(false));

        retellWebClient.on("update", (update) => {
            if (update.transcript && update.transcript.length > 0) {
                // Obtenemos solo el contenido del último evento para dar feedback en vivo
                const latestTranscript = update.transcript[update.transcript.length - 1].content;
                setLiveTranscript(latestTranscript);
            }
        });

        return () => {
            retellWebClient.removeAllListeners();
        };
    }, []);

    const toggleCall = async () => {
        if (isCalling) {
            retellWebClient.stopCall();
            setIsCalling(false);
        } else {
            setIsCalling(true);
            setCallStatus("CONNECTING");
            try {
                // Pedimos el web call token al backend de FastAPI
                const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
                // Usamos nuestro Agent ID de Retell
                // En producción idealmente se enviaría también un session_id para unificar la DB
                const response = await fetch(`${backendUrl}/api/retell/create-web-call`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ agent_id: "agent_d78b94f1f844fb36ff54ef312c" }) // Ejemplo de agentId estático (Ajustar)
                });

                if (!response.ok) {
                    throw new Error("Error obteniendo el token de llamada web segura.");
                }

                const data = await response.json();

                await retellWebClient.startCall({
                    accessToken: data.access_token,
                    sampleRate: 16000,
                });

            } catch (err) {
                console.error("Error al iniciar llamada:", err);
                setCallStatus("IDLE");
                setIsCalling(false);
                setLiveTranscript("Hubo un error al conectar. Intenta nuevamente.");
            }
        }
    };

    return (
        <div className="flex flex-col h-full bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-6 shadow-[0_8px_32px_0_rgba(31,38,135,0.15)] transition-all duration-300">
            <div className="flex items-center justify-between mb-8">
                <h2 className="text-2xl font-semibold tracking-tight">Voz en Vivo</h2>
                <div className="flex items-center gap-2">
                    {callStatus === "ACTIVE" && (
                        <span className="flex h-3 w-3 relative">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                        </span>
                    )}
                    <span className="text-sm font-medium opacity-70">
                        {callStatus === "IDLE" ? "Desconectado" : callStatus === "CONNECTING" ? "Conectando..." : "Conectado"}
                    </span>
                </div>
            </div>

            <div className="flex-1 flex flex-col items-center justify-center space-y-8">
                {/* Visualizer Circle */}
                <div className="relative flex items-center justify-center group">
                    <div className={`absolute w-48 h-48 rounded-full transition-all duration-500 ease-in-out blur-xl 
            ${agentSpeaking ? "bg-indigo-500/40 scale-125" : callStatus === "ACTIVE" ? "bg-blue-400/20 scale-110 animate-pulse" : "bg-gray-400/10 scale-100"}`}>
                    </div>

                    <button
                        onClick={toggleCall}
                        disabled={callStatus === "CONNECTING"}
                        className={`relative z-10 w-32 h-32 rounded-full flex items-center justify-center transition-all duration-300 shadow-xl border-4
              ${callStatus === "ACTIVE"
                                ? "bg-red-500/20 hover:bg-red-500/30 border-red-500/50 text-red-500"
                                : "bg-indigo-500/20 hover:bg-indigo-500/30 border-indigo-500/50 text-indigo-400"
                            }
              ${callStatus === "CONNECTING" ? "opacity-70 cursor-not-allowed" : "hover:scale-105 active:scale-95"}
            `}
                    >
                        {callStatus === "CONNECTING" ? (
                            <Loader2 className="w-12 h-12 animate-spin" />
                        ) : callStatus === "ACTIVE" ? (
                            <PhoneOff className="w-12 h-12" />
                        ) : (
                            <Phone className="w-12 h-12" />
                        )}
                    </button>
                </div>

                {/* Live Transcript Panel */}
                <div className="w-full h-32 mt-6 overflow-hidden relative rounded-2xl bg-black/5 border border-white/10 p-4">
                    <div className="flex items-start gap-3">
                        {agentSpeaking ? <Volume2 className="w-5 h-5 text-indigo-400 mt-0.5" /> : <Mic className="w-5 h-5 opacity-40 mt-0.5" />}
                        <p className={`text-lg font-medium tracking-wide transition-opacity duration-300 leading-relaxed
                ${liveTranscript ? "opacity-100" : "opacity-40 italic"}
             `}>
                            {liveTranscript || "Presiona el botón para iniciar la conversación..."}
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
