from typing import TypedDict, Annotated, Literal
import operator
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

from src.rag.query_engine import rag_search

# 1. Definir el estado (Memoria Contextual y de Hilo)
class AgentState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], operator.add]
    company_id: str
    lopdp_consent: bool
    current_product_context: dict  # Campo obligatorio para evitar Amnesia Conversacional

# 2. Nodos
def check_consent(state: AgentState):
    """Verifica si el consentimiento fue otorgado. Si no, lo solicita."""
    if state.get("lopdp_consent"):
        return {"messages": []}
    
    last_message = state["messages"][-1] if state.get("messages") else None
    
    if last_message and isinstance(last_message, HumanMessage) and "acepto" in last_message.content.lower():
        return {
            "lopdp_consent": True,
            "messages": [AIMessage(content="Gracias por su confirmación. ¿En qué le puedo ayudar hoy?")]
        }
    
    return {
        "messages": [AIMessage(content="Buen día, para continuar, por favor responda 'Acepto' para autorizar el tratamiento de datos.")]
    }

async def consult_knowledge(state: AgentState):
    """Nodo que utiliza RAG para responder preguntas extrayendo datos del catálogo."""
    messages = state.get("messages", [])
    if not messages:
        return {"messages": []}

    last_message = messages[-1]
    
    if isinstance(last_message, HumanMessage):
        raw_query = last_message.content
        current_context = state.get("current_product_context", {})
        if not isinstance(current_context, dict):
            current_context = {}

        # --- Limpieza del input (Websocket manda historial acumulado) ---
        import re
        parts = [p.strip() for p in re.split(r'[.?!]', raw_query) if p.strip()]
        query = parts[-1] if parts else raw_query

        greetings = ["hola", "buenos días", "buenas tardes", "buenas", "qué tal", "hello"]
        if query.lower().strip() in greetings or len(query.split()) <= 2 and "hola" in query.lower():
            return {
                "messages": [AIMessage(content="¡Hola! Qué gusto saludarte, soy Sofía de Civetta. ¿En qué puedo ayudarte hoy?")],
                "current_product_context": current_context # Mantenemos el contexto por si acaso
            }

        # --- Detección de Cambio de Tema (Drop the Anchor) ---
        release_keywords = ["otro", "otra", "diferente", "qué más", "aparte", "tienes pijama", "tienes lencería", "quiero ver"]
        is_theme_change = any(word in query.lower() for word in release_keywords)

        if is_theme_change:
            # Lógica de reseteo
            current_context = {}
            product_name = None
        else:
            product_name = current_context.get("product_name")

        # --- FASE 1: Resolución de Pronombres y Slot Filling ---
        implicit_keywords = ["precio", "cuesta", "vale", "talle", "talla", "color", "tela", "material", "descripción", "ese", "esa", "este", "este", "tienes", "batas", "medias"]
        is_implicit = any(word in query.lower() for word in implicit_keywords)
        
        search_query = query

        if is_implicit and product_name and not is_theme_change:
            # Simplificamos la query para que el buscador encuentre el producto exacto
            search_query = f"{query} (producto: {product_name})"

        # --- FASE 2: Búsqueda RAG ASÍNCRONA (LATENCIA < 100MS) ---
        # Enviamos SOLO la intención de búsqueda pura a la base de datos de manera asíncrona.
        rag_result = await rag_search(search_query, current_product=product_name)       
        
        # Manejo seguro por si el RAG devuelve string o diccionario
        if isinstance(rag_result, dict):
            raw_context = rag_result.get("answer", "No se encontró información.")
            new_context = rag_result.get("context", {})
        else:
            raw_context = str(rag_result)
            new_context = {}

        # --- FASE 2.5: Generación de Respuesta con LLM (Para que "Sofía" no entregue fragmentos crudos) ---
        from src.config.llm_factory import LLMFactory
        from llama_index.core.llms import ChatMessage, MessageRole
        
        system_prompt = (
            "Eres Sofía de Civetta, una asesora de boutique de lujo. "
            "Solo preséntate si es el inicio de la conversación o si el usuario te saluda directamente. "
            "Si la conversación ya está en curso, responde directamente a la pregunta sin repetir el saludo ni tu nombre. "
            "ACTITUD (REGLAS ESTRICTAS):\n"
            "- Sé directa, humana y elegante. NUNCA uses frases de relleno ni te disculpes por demoras (ej. 'Lamento la espera', 'Gracias por preguntar').\n"
            "- No repitas frases de cierre genéricas como '¿Te puedo ayudar en algo más?'. Varía o simplemente no las uses si la respuesta ya es clara.\n"
            "- Limita tus respuestas a lo ESENCIAL (máximo 2 a 3 oraciones), a menos que el usuario pida detalles específicos como la tela o botones.\n"
            "FORMATO DE PRODUCTOS:\n"
            "- NUNCA listes productos con el formato crudo (ej: 'PRODUCTO: x, TELA: y').\n"
            "- Si hay varias opciones, menciónalas en un párrafo fluido y conversacional. Ejemplo: 'Tenemos la Pijama Luna en satín ($34.99) y el Conjunto Encanto en seda ($49.99). Ambas son hermosas, ¿alguna te llama la atención?'.\n"
            "- Responde SIEMPRE basándote en el contexto suministrado. Nunca inventes precios ni productos."
        )
        
        user_prompt = f"Pregunta del usuario: {query}\n\n[CONTEXTO:\n{raw_context}\n]"
        
        try:
            llm = LLMFactory.get_llm()
            chat_messages = [
                ChatMessage(role=MessageRole.SYSTEM, content=system_prompt)
            ]
            
            # Incorporar el historial de chat para que Sofía tenga contexto
            # Tomamos los últimos mensajes relevantes (excluyendo el actual)
            recent_msgs = messages[-5:-1] if isinstance(messages, list) else []
            for msg in recent_msgs:
                if isinstance(msg, HumanMessage):
                    chat_messages.append(ChatMessage(role=MessageRole.USER, content=msg.content)) # type: ignore
                elif isinstance(msg, AIMessage):
                    chat_messages.append(ChatMessage(role=MessageRole.ASSISTANT, content=msg.content)) # type: ignore
                    
            chat_messages.append(ChatMessage(role=MessageRole.USER, content=user_prompt))
            
            response = await llm.achat(chat_messages)
            answer = str(response.message.content)
        except Exception as e:
            print(f"Error en LLM generador de respuesta: {e}")
            answer = "Permíteme un momento, estoy verificando esa información para ti..."

        # --- FASE 3: Lógica de Persistencia (Anti-Amnesia) ---
        final_context = current_context.copy()
        
        if new_context and "product_name" in new_context:
            final_context = new_context
        elif new_context:
            final_context.update(new_context)

        return {
            "messages": [AIMessage(content=answer)],
            "current_product_context": final_context
        }
        
    return {"messages": []}

# 3. Lógica condicional de ruteo
def should_continue(state: AgentState) -> Literal["consult_knowledge", "wait_for_input"]:
    if state.get("lopdp_consent"):
        return "consult_knowledge"
    else:
        return "wait_for_input"

# 4. Construcción del grafo
builder = StateGraph(AgentState)

builder.add_node("check_consent", check_consent)
builder.add_node("consult_knowledge", consult_knowledge)

builder.add_edge(START, "check_consent")

builder.add_conditional_edges(
    "check_consent",
    should_continue,
    {
        "consult_knowledge": "consult_knowledge",
        "wait_for_input": END
    }
)

builder.add_edge("consult_knowledge", END)

graph = builder.compile()

