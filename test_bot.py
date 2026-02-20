import asyncio
import sys
import uuid

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from langchain_core.messages import HumanMessage
from src.database.client import get_checkpointer
from src.agent.graph import builder

async def run_test():
    print("🚀 Iniciando Test de Fase 1 - GESPRO AI")
    
    # 1. Simular identificadores
    thread_id = str(uuid.uuid4())
    print(f"🆔 Thread ID Generado: {thread_id}")
    
    config = {"configurable": {"thread_id": thread_id}}
    
    # 2. Inicializar Checkpointer y Grafo
    print("🔌 Conectando a Base de Datos (Supabase)...")
    try:
        async with get_checkpointer() as checkpointer:
            print("✅ Conexión establecida o simulada (dependiendo de configuración).")
            app = builder.compile(checkpointer=checkpointer)
            
            # 3. Interacción 1: Usuario saluda (Sin consentimiento previo)
            print("\n--- Intento 1: Saludo inicial ---")
            input_1 = {"messages": [HumanMessage(content="Hola, quiero información.")]}
            
            # Stream the response
            async for event in app.astream(input_1, config=config):
                for k, v in event.items():
                   if "messages" in v:
                       print(f"🤖 Bot ({k}): {v['messages'][-1].content}")
            
            # Verificar estado (debería pedir consentimiento)
            state_1 = await app.aget_state(config)
            if not state_1.values.get("lopdp_consent"):
                print("📝 Validado: El bot solicitó consentimiento (LOPDP).")
            else:
                print("⚠️ Error: El bot no debería tener consentimiento aún.")

            # 4. Interacción 2: Usuario da consentimiento
            print("\n--- Intento 2: Usuario dice 'Acepto' ---")
            input_2 = {"messages": [HumanMessage(content="Acepto los términos.")]}
            
            async for event in app.astream(input_2, config=config):
                for k, v in event.items():
                    if "messages" in v:
                        print(f"🤖 Bot ({k}): {v['messages'][-1].content}")
            
            # Verificar estado (debería tener consentimiento)
            state_2 = await app.aget_state(config)
            if state_2.values.get("lopdp_consent"):
                 print("✅ Validado: Consentimiento guardado en estado.")
            else:
                 print("❌ Error: El consentimiento no se guardó.")
                 
            # 5. Prueba de Persistencia (Simular nueva sesión / reinicio)
            print("\n--- Prueba de Persistencia (Nueva Instancia) ---")
            
            # Re-compilar grafo (simulando reinicio del proceso)
            app_new = builder.compile(checkpointer=checkpointer)
            
            # Obtener estado con el MISMO thread_id
            state_restored = await app_new.aget_state(config)
            
            if state_restored.values.get("lopdp_consent"):
                print("💾 ÉXITO: El bot recordó el consentimiento de la sesión anterior.")
                print("🚀 FASE 1 COMPLETADA CON ÉXITO")
            else:
                print("❌ FALLO: Amnesia conversacional detectada.")

    except Exception as e:
        print(f"❌ Error durante el test: {e}")
        print("Asegúrate de configurar las credenciales en .env")

if __name__ == "__main__":
    asyncio.run(run_test())
