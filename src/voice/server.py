import json
import logging
import asyncio
from typing import List, Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage
from src.agent.graph import graph
from src.voice.interruption_handler import InterruptionHandler
from src.voice.prompts import CIVETTA_BRIDE_PROMPT

print("🔥 SERVER VOZ ULTRA-LOW LATENCY CARGADO 🔥")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice_server")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],
)

from src.voice.health import router as health_router
app.include_router(health_router)

class ChatRequest(BaseModel):
    message: str
    session_id: str

text_sessions: Dict[str, dict] = {}

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

manager = ConnectionManager()
interruption_handler = InterruptionHandler()

def extract_text(transcript):
    """Convierte transcript de Retell a string plano"""
    if isinstance(transcript, str):
        return transcript
    if isinstance(transcript, list):
        texts = [item["content"] for item in transcript if isinstance(item, dict) and "content" in item]
        return " ".join(texts)
    return ""

async def process_user_message(agent_state: dict, user_text: str) -> (dict, str):
    agent_state["messages"].append(HumanMessage(content=user_text))
    
    logger.info("🧠 Invoking LangGraph...")
    # Idealmente en el futuro pasaremos esto a astream() para token-by-token.
    final_state = await graph.ainvoke(agent_state)

    all_messages = final_state.get("messages", [])
    if all_messages and isinstance(all_messages[-1], AIMessage):
        ai_response_text = all_messages[-1].content
    else:
        ai_response_text = "Disculpa, dame un segundo para revisar eso."

    return final_state, ai_response_text

@app.post("/chat")
async def chat_text(req: ChatRequest):
    session_id = req.session_id
    user_text = req.message

    if session_id not in text_sessions:
        text_sessions[session_id] = {
            "messages": [SystemMessage(content=CIVETTA_BRIDE_PROMPT + "\n\nIMPORTANTE: Responde SIEMPRE en español. Nunca uses inglés.")],
            "lopdp_consent": True,
            "current_product_context": {}
        }

    agent_state = text_sessions[session_id]
    final_state, ai_response_text = await process_user_message(agent_state, user_text)
    text_sessions[session_id] = final_state

    return {"reply": ai_response_text}

# ===============================
# VOZ (RETELL + CARTESIA OPTIMIZADO)
# ===============================
@app.websocket("/llm-websocket/{call_id}")
async def websocket_endpoint(websocket: WebSocket, call_id: str):
    await manager.connect(websocket)
    logger.info(f"✅ Connected to call: {call_id} | Voice ID: Cartesia-Sofia | Temp: 0.5")

    agent_state = {
        "messages": [SystemMessage(content=CIVETTA_BRIDE_PROMPT + "\n\nIMPORTANTE: Tono calmado, humano, usa modismos latinos. Responde en español.")],
        "lopdp_consent": True,
        "current_product_context": {}
    }

    try:
        while True:
            raw_data = await websocket.receive_text()
            event = json.loads(raw_data)

            interaction_type = event.get("interaction_type")

            if interaction_type == "ping_pong":
                await websocket.send_text(json.dumps({
                    "interaction_type": "ping_pong",
                    "timestamp": event.get("timestamp")
                }))
                continue

            # --- OPTIMIZACIÓN BARGE-IN (Interrupción < 140ms) ---
            if interaction_type == "update_only":
                transcript = extract_text(event.get("transcript", ""))
                
                # VAD y filtro semántico (Ignora "ajá", "mm-hmm")
                if transcript and interruption_handler.should_interrupt(transcript):
                    logger.info(f"🛑 INTERRUPTION DETECTED: {transcript}")
                    # Comando NATIVO de Retell para detener audio inmediatamente
                    await websocket.send_text(json.dumps({
                        "interaction_type": "clear" 
                    }))
                continue
            # --------------------------------------------

            if interaction_type == "response_required":
                transcript = extract_text(event.get("transcript", ""))
                response_id = event.get("response_id")
                logger.info(f"🗣 User said: {transcript}")

                if not transcript.strip():
                    await websocket.send_text(json.dumps({
                        "response_id": response_id,
                        "content": "¿Hola? ¿Sigues ahí?",
                        "content_complete": True,
                        "end_call": False
                    }))
                    continue

                # --- TRUCO DE LATENCIA CERO (Filler Words Sin Muletillas) ---
                # Enviamos un marcador conversacional de inmediato para que la voz empiece a sonar (100ms)
                # mientras LangGraph procesa por detrás (800ms). Eliminado el "Mmm".
                if "por favor" in transcript.lower() or "podrías" in transcript.lower() or "quiero" in transcript.lower():
                    filler_word = "Claro... " 
                elif any(q in transcript.lower() for q in ["precio", "cuánto", "talla", "stock"]):
                    filler_word = "Permíteme verificarlo... "
                else:
                    filler_word = "Entiendo... "
                
                await websocket.send_text(json.dumps({
                    "response_id": response_id,
                    "content": filler_word,
                    "content_complete": False,
                    "end_call": False
                }))

                # Procesamiento real (El RAG)
                agent_state, ai_response_text = await process_user_message(agent_state, transcript)

                # STREAMING OPTIMIZADO PARA VOZ (Fragmentación Inteligente)
                # Separamos por comas y puntos para que Cartesia procese la prosodia correctamente
                chunks = ai_response_text.replace(",", ",|").replace(".", ".|").split("|")
                
                for chunk in chunks:
                    clean_chunk = chunk.strip()
                    if not clean_chunk:
                        continue
                        
                    await websocket.send_text(json.dumps({
                        "response_id": response_id,
                        "content": clean_chunk + " ",
                        "content_complete": False,
                        "end_call": False
                    }))
                    # Pequeña pausa asíncrona para no saturar el buffer del socket
                    await asyncio.sleep(0.01)

                # Finalizar respuesta
                await websocket.send_text(json.dumps({
                    "response_id": response_id,
                    "content": "",
                    "content_complete": True,
                    "end_call": False
                }))
                logger.info(f"🤖 Sent complete response for id {response_id}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"🔌 Call {call_id} disconnected")
    except Exception as e:
        logger.error(f"❌ Error in call {call_id}: {e}")
        manager.disconnect(websocket)

