from supabase import create_client
from openai import OpenAI

SUPABASE_URL="https://tgpihxyzapnvhcqlaekj.supabase.co"
SUPABASE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRncGloeHl6YXBudmhjcWxhZWtqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTM0OTkwMSwiZXhwIjoyMDg2OTI1OTAxfQ.qXdya4bikrZjuQEkkt6m8guBhYIpKkl86Dk3-eZILQA"

OPENAI_API_KEY = "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"

client = OpenAI(api_key=OPENAI_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

with open("catalogo.txt", "r", encoding="utf-8") as f:
    raw_text = f.read()

productos = raw_text.split("---")

for producto in productos:
    producto = producto.strip()
    if not producto:
        continue

    embedding = client.embeddings.create(
        model="text-embedding-3-small",
        input=producto
    ).data[0].embedding

    supabase.table("knowledge_base").insert({
        "content": producto,
        "embedding": embedding
    }).execute()

    print("✅ Producto cargado")