import os
from typing import List
from llama_index.core import VectorStoreIndex, StorageContext, Document
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.vector_stores.supabase import SupabaseVectorStore
from dotenv import load_dotenv
load_dotenv()
from src.config.settings import settings
from src.config.embeddings_factory import EmbeddingsFactory

# Inicializamos el modelo de embeddings
embed_model = EmbeddingsFactory.get_eval_embed_model()


def load_catalog_txt(file_path: str = "data/catalogo.txt") -> List[Document]:
    """
    Carga el archivo catalogo.txt y separa productos usando '---'
    """
    if not os.path.exists(file_path):
        print("❌ No se encontró catalogo.txt")
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    productos = raw_text.split("---")

    documents = []
    for producto in productos:
        producto = producto.strip()
        if producto:
            doc = Document(
                text=producto,
                metadata={"source": "catalogo.txt", "type": "product"}
            )
            documents.append(doc)

    print(f"✅ Se cargaron {len(documents)} productos desde catalogo.txt")
    return documents


def setup_vector_store():
    """
    Conecta con Supabase usando pgvector
    """
    vector_store = SupabaseVectorStore(
        postgres_connection_string=settings.db_connection_string,
        collection_name="knowledge_base",  # 🔥 UNIFICADO
        dimension=1536  # text-embedding-3-small
    )
    return vector_store


def ingest_data():
    documents = load_catalog_txt()
    if not documents:
        print("❌ No hay documentos para ingerir")
        return

    print("✂️ Dividiendo documentos en chunks semánticos...")
    splitter = SemanticSplitterNodeParser(
        buffer_size=1,
        breakpoint_percentile_threshold=95,
        embed_model=embed_model
    )

    nodes = splitter.get_nodes_from_documents(documents)
    print(f"✅ Se generaron {len(nodes)} chunks")

    print("📦 Conectando a Supabase Vector Store...")
    vector_store = setup_vector_store()
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    print("🧠 Generando embeddings y guardando en Supabase...")
    VectorStoreIndex(
        nodes,
        storage_context=storage_context,
        embed_model=embed_model
    )

    print("🎉 Ingesta completada correctamente en knowledge_base")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    ingest_data()