"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Bot, User } from "lucide-react";

interface ChatPanelProps {
    sessionId: string;
}

interface Message {
    role: "user" | "bot";
    content: string;
}

export default function ChatPanel({ sessionId }: ChatPanelProps) {
    const [messages, setMessages] = useState<Message[]>([
        { role: "bot", content: "¡Hola! Soy Sofía. ¿En qué te puedo ayudar hoy por chat?" }
    ]);
    const [inputText, setInputText] = useState("");
    const [loading, setLoading] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const sendMessage = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!inputText.trim()) return;

        const userMessage = inputText;
        setInputText("");
        setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
        setLoading(true);

        try {
            const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
            const response = await fetch(`${backendUrl}/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: userMessage, session_id: sessionId })
            });

            if (!response.ok) throw new Error("Error en el servidor");

            const data = await response.json();
            setMessages((prev) => [...prev, { role: "bot", content: data.reply }]);
        } catch (err) {
            setMessages((prev) => [...prev, { role: "bot", content: "Disculpa, hubo un problema al contactar el servidor." }]);
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-full bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-6 shadow-[0_8px_32px_0_rgba(31,38,135,0.15)]">
            <h2 className="text-2xl font-semibold tracking-tight mb-6">Chat Integrado</h2>

            <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto pr-2 space-y-6 scrollbar-thin scrollbar-thumb-white/20 hover:scrollbar-thumb-white/30 scrollbar-track-transparent"
            >
                {messages.map((msg, idx) => (
                    <div key={idx} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 
              ${msg.role === "user" ? "bg-indigo-500/20 text-indigo-400" : "bg-fuchsia-500/20 text-fuchsia-400"}`}>
                            {msg.role === "user" ? <User size={16} /> : <Bot size={16} />}
                        </div>

                        <div className={`px-4 py-3 rounded-2xl max-w-[80%] leading-relaxed shadow-sm
              ${msg.role === "user"
                                ? "bg-indigo-500/20 border border-indigo-500/30 text-white rounded-tr-none"
                                : "bg-white/5 border border-white/10 text-white/90 rounded-tl-none"}`}>
                            {msg.content}
                        </div>
                    </div>
                ))}
                {loading && (
                    <div className="flex gap-3 flex-row">
                        <div className="w-8 h-8 rounded-full bg-fuchsia-500/20 text-fuchsia-400 flex items-center justify-center shrink-0">
                            <Bot size={16} />
                        </div>
                        <div className="px-4 py-3 rounded-2xl bg-white/5 border border-white/10 rounded-tl-none flex items-center gap-1.5 h-[46px]">
                            <span className="w-1.5 h-1.5 rounded-full bg-fuchsia-400/60 animate-bounce" style={{ animationDelay: "0ms" }}></span>
                            <span className="w-1.5 h-1.5 rounded-full bg-fuchsia-400/60 animate-bounce" style={{ animationDelay: "150ms" }}></span>
                            <span className="w-1.5 h-1.5 rounded-full bg-fuchsia-400/60 animate-bounce" style={{ animationDelay: "300ms" }}></span>
                        </div>
                    </div>
                )}
            </div>

            <div className="mt-6">
                <form onSubmit={sendMessage} className="relative flex items-center">
                    <input
                        type="text"
                        value={inputText}
                        onChange={(e) => setInputText(e.target.value)}
                        placeholder="Escribe un mensaje..."
                        className="w-full bg-black/10 border border-white/20 rounded-2xl py-4 pl-5 pr-14 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:bg-black/20 transition-all font-medium"
                        disabled={loading}
                    />
                    <button
                        type="submit"
                        disabled={!inputText.trim() || loading}
                        className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-xl bg-indigo-500 text-white hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    >
                        <Send size={18} className={loading || !inputText.trim() ? "opacity-50" : "opacity-100"} />
                    </button>
                </form>
            </div>
        </div>
    );
}
