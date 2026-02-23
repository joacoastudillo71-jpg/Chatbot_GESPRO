import os
import re
from supabase import create_client
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


client = OpenAI(api_key=OPENAI_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def parse_producto(bloque_texto):
    """Extrae campos específicos del bloque de texto del catálogo"""
    nombre = re.search(r"PRODUCTO: (.*)", bloque_texto)
    categoria = re.search(r"CATEGORÍA: (.*)", bloque_texto)
    
    return {
        "product_name": nombre.group(1).strip() if nombre else "Sin nombre",
        "category": categoria.group(1).strip() if categoria else "General",
        "content": bloque_texto.strip()
    }

def ejecutar_ingesta():
    if not os.path.exists("data/catalogo.txt"):
        print("❌ No se encontró data/catalogo.txt")
        return

    with open("data/catalogo.txt", "r", encoding="utf-8") as f:
        raw_text = f.read()

    # Separamos por los guiones
    bloques = raw_text.split("---")

    for bloque in bloques:
        if not bloque.strip():
            continue

        datos = parse_producto(bloque)
        print(f"📦 Procesando: {datos['product_name']}...")

        # Generar embedding del contenido completo
        embedding = client.embeddings.create(
            model="text-embedding-3-small",
            input=datos['content']
        ).data[0].embedding

        # Insertar con todas las columnas de tu imagen
        supabase.table("knowledge_base").insert({
            "product_name": datos['product_name'],
            "category": datos['category'],
            "content": datos['content'],
            "embedding": embedding
        }).execute()

    print("✅ ¡Todo el catálogo se ha cargado correctamente en las columnas id, product_name, category, content y embedding!")

if __name__ == "__main__":
    ejecutar_ingesta()