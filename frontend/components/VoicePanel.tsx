"use client";

import React, { useEffect, useState, useRef } from "react";
import { Phone, PhoneOff, Mic, Loader2, Volume2 } from "lucide-react";

interface VoicePanelProps {
    sessionId: string;
}

export default function VoicePanel({ sessionId }: VoicePanelProps) {
    const [isCalling, setIsCalling] = useState(false);
    const [callStatus, setCallStatus] = useState<"IDLE" | "CONNECTING" | "ACTIVE">("IDLE");
    const [liveTranscript, setLiveTranscript] = useState<string>("");
    const [agentSpeaking, setAgentSpeaking] = useState(false);

    const pcRef = useRef<RTCPeerConnection | null>(null);
    const dcRef = useRef<RTCDataChannel | null>(null);
    const audioElRef = useRef<HTMLAudioElement | null>(null);

    useEffect(() => {
        // Inicializar el elemento de audio
        const audioEl = new Audio();
        audioEl.autoplay = true;
        audioElRef.current = audioEl;

        return () => {
            stopCall();
        };
    }, []);

    const stopCall = () => {
        if (pcRef.current) {
            pcRef.current.close();
            pcRef.current = null;
        }
        if (dcRef.current) {
            dcRef.current.close();
            dcRef.current = null;
        }
        setCallStatus("IDLE");
        setIsCalling(false);
        setAgentSpeaking(false);
        setLiveTranscript("Llamada finalizada.");
    };

    const toggleCall = async () => {
        if (isCalling) {
            stopCall();
            return;
        }

        setIsCalling(true);
        setCallStatus("CONNECTING");
        setLiveTranscript("Conectando con OpenAI Realtime...");

        try {
            // 1. Obtener token efímero del backend
            const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
            const tokenRes = await fetch(`${backendUrl}/api/realtime-token`);
            if (!tokenRes.ok) throw new Error("Error obteniendo el token");
            const tokenData = await tokenRes.json();
            const EPHEMERAL_KEY = tokenData.client_secret;

            // 2. Crear conexión WebRTC
            const pc = new RTCPeerConnection();
            pcRef.current = pc;

            // Escuchar audio del modelo
            pc.ontrack = (e) => {
                if (audioElRef.current) {
                    audioElRef.current.srcObject = e.streams[0];
                }
            };

            // 3. Capturar audio local
            const ms = await navigator.mediaDevices.getUserMedia({ audio: true });
            pc.addTrack(ms.getTracks()[0]);

            // 4. Crear DataChannel para enviar/recibir eventos (Client events + Server events)
            const dc = pc.createDataChannel("oai-events");
            dcRef.current = dc;

            dc.addEventListener("open", () => {
                setCallStatus("ACTIVE");
                setLiveTranscript("Conexión establecida. Di 'Hola' para comenzar.");
            });

            dc.addEventListener("message", async (e) => {
                const event = JSON.parse(e.data);

                // Indicadores visuales de quién habla
                if (event.type === "response.audio.delta") setAgentSpeaking(true);
                if (event.type === "response.done") setAgentSpeaking(false);

                // Actualizar la transcripción
                if (event.type === "conversation.item.input_audio_transcription.completed") {
                    setLiveTranscript(event.transcript);
                }
                if (event.type === "response.audio_transcript.delta") {
                    setLiveTranscript((prev) => prev + event.delta);
                }

                // --- 5. INTERCEPCIÓN DE FUNCTION CALLING PARA LANGGRAPH ---
                if (event.type === "response.function_call_arguments.done") {
                    const callId = event.call_id;
                    const functionName = event.name;
                    const args = JSON.parse(event.arguments);

                    if (functionName === "consultar_asesor_langgraph") {
                        setLiveTranscript("Buscando información de Civetta...");

                        try {
                            // Consultar al backend original (LangGraph)
                            const chatRes = await fetch(`${backendUrl}/chat`, {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({
                                    message: args.user_query,
                                    session_id: sessionId || "voz-web-session"
                                })
                            });

                            const chatData = await chatRes.json();
                            const answer = chatData.reply;

                            // Notificar a OpenAI del resultado de la función
                            const funcResultEvent = {
                                type: "conversation.item.create",
                                item: {
                                    type: "function_call_output",
                                    call_id: callId,
                                    output: JSON.stringify({ success: true, answer: answer })
                                }
                            };
                            dc.send(JSON.stringify(funcResultEvent));

                            // Solicitar al modelo que hable la respuesta
                            const responseCreate = {
                                type: "response.create"
                            };
                            dc.send(JSON.stringify(responseCreate));
                            setLiveTranscript("Asesora respondiendo...");

                        } catch (err) {
                            console.error("Error consultando LangGraph", err);
                            // Notificar error al modelo
                            dc.send(JSON.stringify({
                                type: "conversation.item.create",
                                item: {
                                    type: "function_call_output",
                                    call_id: callId,
                                    output: JSON.stringify({ success: false, error: "Hubo un error interno." })
                                }
                            }));
                            dc.send(JSON.stringify({ type: "response.create" }));
                        }
                    }
                }
            });

            // 6. Crear Offer y conectar por SDP
            const offer = await pc.createOffer();
            await pc.setLocalDescription(offer);

            const baseUrl = "https://api.openai.com/v1/realtime";
            const model = "gpt-4o-realtime-preview-2024-12-17";
            const sdpResponse = await fetch(`${baseUrl}?model=${model}`, {
                method: "POST",
                body: offer.sdp,
                headers: {
                    "Authorization": `Bearer ${EPHEMERAL_KEY}`,
                    "Content-Type": "application/sdp"
                },
            });

            if (!sdpResponse.ok) {
                console.error("SDP fallback failed", await sdpResponse.text());
                throw new Error("Error en negociación SDP con OpenAI");
            }

            const answer: RTCSessionDescriptionInit = {
                type: "answer",
                sdp: await sdpResponse.text()
            };
            await pc.setRemoteDescription(answer);

        } catch (err) {
            console.error("Error al iniciar llamada:", err);
            setCallStatus("IDLE");
            setIsCalling(false);
            setLiveTranscript("Hubo un error al conectar. Verifica tu micrófono o conexión.");
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
