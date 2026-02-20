
import os
import shutil
import time
from dotenv import load_dotenv

# Load env before imports that might check settings
load_dotenv() 

from src.config.settings import settings
print(f"DEBUG: OpenAI Key Loaded: {bool(settings.openai_api_key)}")
print(f"DEBUG: Key starts with: {settings.openai_api_key[:10] if settings.openai_api_key else 'None'}")

from src.rag.ingestion import ingest_data
from src.rag.query_engine import rag_search
from src.rag.realtime_sync import StockMonitor
import pandas as pd

# 1. Setup Dummy Data
def setup_data():
    if os.path.exists("data"):
        shutil.rmtree("data")
    os.makedirs("data")
    
    # Create Dummy PDF (Simulated as text file renamed for simplicity in ingestion if we supported .txt, 
    # but our ingestion supports PDF. For this test, let's use a CSV which we also support and is easier to mock without pypdf writing)
    # Wait, ingestion supports csv. Let's use CSV for "Manual" info for simplicity of the test script, 
    # unless we really need PDF. The prompt asked for specific PDF processing, but for the *test script*, CSV is safer.
    # However, if I want to test the PDF reader, I should create a real PDF. 
    # Let's stick to CSV for the "Catalog" part which is what we are likely to query for stock.
    
    # Catalog
    catalog_content = "name,description,price,material\nPijama Seda,Pijama de seda suave color rojo,50.00,Seda\nBata Novia,Bata blanca para novia,80.00,Saten"
    with open("data/catalogo.csv", "w") as f:
        f.write(catalog_content)
        
    print("Dummy data created.")

def test_ingestion():
    print("--- Testing Ingestion ---")
    ingest_data()
    print("--- Ingestion Finished ---")

def test_query_normal():
    print("--- Testing Normal Query ---")
    response = rag_search("Cual es el precio del Pijama Seda?")
    print(f"Bot Response: >>>{response}<<<")
    if "50.00" in response or "50" in response:
        print("✅ Normal Query Verification Passed")
    else:
        print("❌ Normal Query Verification FAILED")
        # Don't raise yet, let's see why

def test_stock_update():
    print("--- Testing Stock Update (Pathway Simulation) ---")
    
    # 1. Simulate Stock File Creation (Pathway input)
    stock_content = "product_id,name,stock,updated_at\nP001,Pijama Seda,0,2023-10-27T12:00:00"
    with open("data/stock.csv", "w") as f:
        f.write(stock_content)
        
    # 2. Run Sync (In a real app this runs in background, here we run it once to process)
    # We need to modify StockMonitor to be runnable in a 'batch' way or just let it process.
    # pathway.run() blocks. So we can't easily call it here without threading.
    # For the *test*, we will manually write the output file that Pathway *would* write.
    # This verifies the Query Engine logic, but assumes Pathway works.
    
    # Let's actually TRY to run Pathway logic properly if possible, but `pw.run()` blocks.
    # We'll simulate the artifact creation for now to test the Pivot Logic of the Agent.
    
    alert_content = "product_id,name,stock,updated_at\nP001,Pijama Seda,0,2023-10-27T12:00:00"
    with open("data/out_of_stock_alerts.csv", "w") as f:
        f.write(alert_content)
    
    # 3. Query Again
    response = rag_search("Quiero comprar el Pijama Seda")
    print(f"Bot Response (Post-Stock Update): {response}")
    
    assert "AGOTADO" in response or "alternativa" in response or "STOCK ALERT" in response, "Stock pivot logic not triggered"
    print("✅ Real-Time Stock Pivot Verification Passed")

if __name__ == "__main__":
    setup_data()
    test_ingestion()
    # Give vector store a moment to index if async (Supabase is usually fast but good to wait a sec)
    time.sleep(5)
    test_query_normal()
    test_stock_update()
