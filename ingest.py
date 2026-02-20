import os
from dotenv import load_dotenv
from llama_index.core import Document, VectorStoreIndex, Settings
from llama_index.vector_stores.supabase import SupabaseVectorStore
from src.config.llm_factory import LLMFactory
from src.config.embeddings_factory import EmbeddingsFactory

# Cargar variables de entorno locales (.env)
load_dotenv()

def subir_datos_a_supabase():
    print("🚀 Iniciando lectura del catálogo...")
    
    # 1. Validar claves críticas
    db_string = os.getenv("DB_CONNECTION_STRING")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not db_string:
        print("❌ ERROR: No encontré DB_CONNECTION_STRING en tu .env")
        return
    if not openai_key:
        print("❌ ERROR: No encontré OPENAI_API_KEY en tu .env. ¡Sin esto no puedo generar vectores!")
        return

    # 2. Leer el archivo txt
    ruta_txt = "data/catalogo.txt"
    if not os.path.exists(ruta_txt):
        print(f"❌ ERROR: No se encuentra el archivo en {ruta_txt}")
        return

    with open(ruta_txt, "r", encoding="utf-8") as f:
        contenido = f.read()
        
    # 3. Separar los productos usando el separador '---'
    productos_crudos = contenido.split('---')
    
    documentos = []
    for prod in productos_crudos:
        texto_limpio = prod.strip()
        if texto_limpio:
            doc = Document(text=texto_limpio)
            documentos.append(doc)
            
    print(f"📦 Se encontraron {len(documentos)} productos listos para procesar.")
    
    # 4. Conectar a Supabase
    print("🔌 Conectando a Supabase (esquema vecs)...")
    try:
        vector_store = SupabaseVectorStore(
            postgres_connection_string=db_string,
            collection_name="knowledge_base",
            schema_name="public" 
        )
    except Exception as e:
        print(f"❌ ERROR CONECTANDO A SUPABASE: {e}")
        return
    
    # 5. Configurar Modelos (LLM y Embeddings)
    Settings.llm = LLMFactory.get_llm()
    Settings.embed_model = EmbeddingsFactory.get_eval_embed_model()
    
    # 6. Generar vectores y subir
    print("🧠 Generando vectores con OpenAI y subiendo a Supabase (esto puede tomar unos 10-20 segundos)...")
    try:
        VectorStoreIndex.from_documents(
            documentos,
            vector_store=vector_store,
            show_progress=True
        )
        print("✅ ¡ÉXITO TOTAL! Todos los datos fueron subidos correctamente a la tabla 'knowledge_base'.")
    except Exception as e:
        print(f"❌ ERROR CRÍTICO AL SUBIR DATOS: {e}")

if __name__ == "__main__":
    subir_datos_a_supabase()