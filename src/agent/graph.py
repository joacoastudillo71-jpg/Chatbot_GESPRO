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
            answer = rag_result.get("answer", "Dame un segundito para verificar eso...")
            new_context = rag_result.get("context", {})
        else:
            answer = str(rag_result)
            new_context = {}

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

