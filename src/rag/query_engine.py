import os
import re
import asyncio
from typing import Dict, Optional
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from src.config.settings import settings
from src.config.embeddings_factory import EmbeddingsFactory

# Connection pool global
pool = None

async def init_pool():
    global pool
    if pool is None:
        pool = AsyncConnectionPool(
            conninfo=settings.db_connection_string,
            min_size=1,
            max_size=5,
            kwargs={"row_factory": dict_row},
            open=False
        )
        await pool.open()

async def get_db_pool() -> AsyncConnectionPool:
    global pool
    if pool is None:
        await init_pool()
    return pool # type: ignore

async def embed_query_async(query: str) -> list[float]:
    """Obtiene el embedding de la query usando el factory de forma asíncrona."""
    embed_model = EmbeddingsFactory.get_eval_embed_model()
    return await embed_model.aget_text_embedding(query)

async def search_vectors_sql_async(query_embedding: list[float], limit: int = 3) -> list[Dict]:
    """Ejecuta pura consulta SQL (Operador Inner Product <#>) para latencia < 5ms."""
    p = await get_db_pool()
    async with p.connection() as conn:  # type: ignore
        from pgvector.psycopg import register_vector_async # type: ignore
        await register_vector_async(conn)
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT 
                    id, 
                    content, 
                    json_build_object('product_name', product_name, 'category', category) AS metadata_, 
                    (embedding <#> %s::vector) * -1 AS similarity
                FROM knowledge_base
                ORDER BY embedding <#> %s::vector
                LIMIT %s;
            """, (query_embedding, query_embedding, limit))
            res = await cur.fetchall()
            return res

async def rag_search(query: str, current_product: Optional[str] = None) -> dict:
    try:
        search_term = query
        if re.search(r"\b(precio|cu[aá]nto cuesta|valor|costo)\b", query.lower()) and current_product:
            search_term = current_product

        # Generación de embedding asíncrono
        query_embedding = await embed_query_async(search_term)
        
        limit = 5 if search_term == current_product else 3
        
        # Búsqueda SQL directa asíncrona
        results = await search_vectors_sql_async(query_embedding, limit=limit)
        
        # Intentar extraer precio rápido si era la intención
        if search_term == current_product and current_product and results:
            for row in results:
                text = row['content']
                if current_product.lower() in text.lower():
                    price_match = re.search(r"(?:PRECIO|VALOR|COSTO):\s*([^\n,]+)", text, re.IGNORECASE)
                    if price_match:
                        return {
                            "answer": f"El precio de {current_product} es {price_match.group(1).strip()}.",
                            "context": {"product_name": current_product, "price": price_match.group(1).strip()}
                        }

        if not results:
            return {
                "answer": "No encontré información exacta en el catálogo de Civetta. Por favor avísale al usuario que consulte con un agente.",
                "context": {}
            }

        textos_catalogo = "\n\n".join([row['content'] for row in results])
        
        # Eliminamos la generacion de LLM local. OpenAI Realtime hablará la respuesta basada en el string
        # de forma que este backend responde en < 100ms.
        final_answer = ("Información del catálogo de Civetta encontrada. "
                        "DEBES usar esta información exacta para responderle al usuario de forma elegante:\n" 
                        + textos_catalogo)

        context = {}
        best_metadata = results[0]['metadata_'] if results else {}
        
        # psycopg puede devolver el JSON como string o dict dependiendo del tipeo, aseguramos dict.
        import json
        if isinstance(best_metadata, str):
            best_metadata = json.loads(best_metadata)
            
        context["product_name"] = best_metadata.get("product_name", "")
        context["category"] = best_metadata.get("category", "")

        best_text = results[0]['content'] if results else ""
        price_match = re.search(r"(?:PRECIO|VALOR|COSTO):\s*([^\n,]+)", best_text, re.IGNORECASE)
        if price_match:
            context["price"] = price_match.group(1).strip()

        return {"answer": final_answer, "context": context}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "answer": "Hubo un problema técnico interno verificando la disponibilidad.",
            "context": {}
        }