import os
import json
import logging
import asyncio
import httpx
from typing import List, Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
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

@app.get("/api/realtime-token")
async def get_realtime_token():
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OPENAI_API_KEY no encontrada en variables de entorno")
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY no configurada.")

    # Instrucciones estrictas para la voz de OpenAI
    voice_instructions = (
        CIVETTA_BRIDE_PROMPT + 
        "\n\nIMPORTANTE Y REGLAS ESTRICTAS DE VOZ:\n"
        "- Tu voz debe sonar cálida, femenina y 100% como una hablante nativa de Español Latinoamericano.\n"
        "- NUNCA suenes como una extranjera hablando español. Mantén una prosodia natural latina.\n"
        "- Usa siempre español.\n"
        "- Tienes acceso a la herramienta 'consultar_asesor_langgraph'. DEBES llamarla CADA VEZ que el usuario te haga una pregunta sobre productos, bodas, logística, etc. para obtener la respuesta oficial de la base de conocimientos, y luego debes repetir esa respuesta de manera natural conversacional."
    )

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.openai.com/v1/realtime/sessions",
                headers={
                    "Authorization": f"Bearer {openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-realtime-preview-2024-12-17",
                    "voice": "shimmer", # shimmer is a warm feminine voice
                    "instructions": voice_instructions,
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 140 # Barge-in threshold requested: 140ms
                    },
                    "tools": [{
                        "type": "function",
                        "name": "consultar_asesor_langgraph",
                        "description": "Llama a esta herramienta cuando necesites buscar información de Civetta, conocer stock, precios, responder sobre bodas o vestidos, o cualquier pregunta del usuario. Nos pasará la respuesta oficial que debes decir.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "user_query": {"type": "string", "description": "La frase exacta o pregunta que hizo el usuario para consultar en la base de datos."}
                            },
                            "required": ["user_query"]
                        }
                    }],
                    "tool_choice": "auto"
                },
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            return {"client_secret": data["client_secret"]["value"]}
        except httpx.HTTPStatusError as e:
            logger.error(f"Error de API de OpenAI: {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"Error conectando con OpenAI: {e.response.text}")
        except Exception as e:
            logger.error(f"Error creando sesión realtime: {e}")
            raise HTTPException(status_code=500, detail=str(e))

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



