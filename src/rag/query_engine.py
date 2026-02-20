import os
import re
import pandas as pd
from llama_index.core import VectorStoreIndex, Settings as LlamaSettings
from llama_index.vector_stores.supabase import SupabaseVectorStore
from src.config.settings import settings
from src.config.llm_factory import LLMFactory
from src.config.embeddings_factory import EmbeddingsFactory

def check_stock_status(query_text: str) -> str:
    # ⚠️ AHORA USAMOS UN TOOL O QUERY DIRECTA A LA DB PARA STOCK EN LUGAR DE UN CSV ARCAICO
    # El sistema debe ser dinámico. Por ahora delegaremos la responsabilidad
    # al componente que manejará las tools (Phase 4).
    # Solo dejaremos un placeholder limpio que retorne vacío para no romper la firma.
    return ""

_index_cache = None

def get_index():
    global _index_cache
    if _index_cache:
        return _index_cache

    vector_store = SupabaseVectorStore(
        postgres_connection_string=settings.db_connection_string,
        collection_name="knowledge_base",
        schema_name="public"
    )

    embed_model = EmbeddingsFactory.get_eval_embed_model()
    LlamaSettings.llm = LLMFactory.get_llm()
    LlamaSettings.embed_model = embed_model

    _index_cache = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        embed_model=embed_model
    )
    return _index_cache

def rag_search(query: str, current_product: str = None) -> dict:
    stock_alert = check_stock_status(query)
    print(f"\n🔍 [RAG] Buscando en DB la consulta: '{query}'")

    try:
        index = get_index()

        # 🧠 SI EL USUARIO SOLO PREGUNTA PRECIO → NO BUSCAR EN DB
        if re.search(r"\b(precio|cu[aá]nto cuesta|valor|costo)\b", query.lower()) and current_product:
            retriever = index.as_retriever(similarity_top_k=5)
            nodes = retriever.retrieve(current_product)

            for n in nodes:
                text = n.get_content()
                if current_product.lower() in text.lower():
                    price_match = re.search(r"(?:PRECIO|VALOR|COSTO):\s*([^\n,]+)", text, re.IGNORECASE)
                    if price_match:
                        return {
                            "answer": f"El precio de {current_product} es {price_match.group(1).strip()}.",
                            "context": {"product_name": current_product, "price": price_match.group(1).strip()}
                        }

        retriever = index.as_retriever(similarity_top_k=3)
        nodes = retriever.retrieve(query)

        print(f"📦 [RAG] Documentos encontrados en Supabase: {len(nodes)}")

        if not nodes:
            llm = LLMFactory.get_llm()
            fallback = llm.complete(
                "Eres Sofía, asesora de Civetta. Responde en español de forma natural, gentil y elegante, como una experta en moda y novias."
                f" El usuario dijo: {query}"
            )
            return {"answer": str(fallback).strip(), "context": {}}

        textos_catalogo = "\n\n".join([n.get_content() for n in nodes])
        print(f"📄 [RAG] Contexto:\n{textos_catalogo}\n")

        llm = LLMFactory.get_llm()
        prompt_final = (
            "Eres Sofía, asesora de la marca Civetta.\n"
            f"El usuario preguntó: '{query}'.\n\n"
            "Responde SOLO usando esta información extraída dinámicamente de la base de datos:\n"
            f"{textos_catalogo}\n\n"
            "Si el usuario pregunta por un producto, descríbelo de manera elegante y humana antes de dar el precio si te lo piden. Nunca inventes productos ni precios que no estén aquí."
        )

        final_answer = str(llm.complete(prompt_final)).strip()

        if stock_alert:
            final_answer = f"{stock_alert}\n{final_answer}"

        context = {}
        best_text = nodes[0].get_content() if nodes else ""

        prod_match = re.search(r"(?:PRODUCTO|NOMBRE|ITEM):\s*([^\n,.-]+)", best_text, re.IGNORECASE)
        if prod_match:
            context["product_name"] = prod_match.group(1).strip()

        price_match = re.search(r"(?:PRECIO|VALOR|COSTO):\s*([^\n,]+)", best_text, re.IGNORECASE)
        if price_match:
            context["price"] = price_match.group(1).strip()

        return {"answer": final_answer, "context": context}

    except Exception as e:
        print(f"❌ [RAG] Error crítico: {e}")
        return {
            "answer": "Dame un segundito, tengo un problema técnico al buscar eso.",
            "context": {}
        }