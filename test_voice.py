import asyncio
import websockets
import json
import time
import uuid

SERVER_URL = "ws://localhost:8000/llm-websocket/test-call-123"

async def test_call_simulation():
    async with websockets.connect(SERVER_URL) as websocket:
        print(f"Connected to {SERVER_URL}")
        
        # 1. Simulate User Saying "Hola"
        # Measure TTFT (Time To First Token/Message)
        
        interaction_id = str(uuid.uuid4())
        print("User: Hola")
        start_time = time.time()
        
        simulated_event = {
            "interaction_type": "response_required",
            "transcript": "Hola, me interesa un vestido.",
            "response_id": interaction_id
        }
        
        await websocket.send(json.dumps(simulated_event))
        
        # Wait for response
        response = await websocket.recv()
        end_time = time.time()
        
        response_data = json.loads(response)
        content = response_data.get("content")
        
        ttft = (end_time - start_time) * 1000
        print(f"AI: {content}")
        print(f"TTFT / Latency: {ttft:.2f} ms")
        
        if ttft < 800:
             print("STATUS: PASS (Latency < 800ms)")
        else:
             print("STATUS: WARNING (Latency > 800ms)")

        # 2. Simulate Barge-in / Semantic Interruption
        # Scenario: User says "Aha" (Backchannel) -> Should NOT trigger full stop logic if we were streaming (hard to test without streaming setup)
        # Scenario: User interrupts with "Espera, tengo una duda"
        
        print("\n--- Testing Barge-in Logic ---")
        print("User: (Interruption) 'Espera, tengo una duda sobre el precio'")
        
        start_time_barge = time.time()
        
        barge_event = {
            "interaction_type": "response_required",
            "transcript": "Espera, tengo una duda sobre el precio",
            "response_id": str(uuid.uuid4())
        }
        await websocket.send(json.dumps(barge_event))
        
        response_barge = await websocket.recv()
        end_time_barge = time.time()
        
        # In a real Retell flow, the 'interrupt' event comes first, then 'response_required'.
        # Since we just implemented response_required logic, we measure the turnaround time.
        
        barge_latency = (end_time_barge - start_time_barge) * 1000
        print(f"Barge-in Response Latency: {barge_latency:.2f} ms")
        if barge_latency < 200: # Tight constraint!
            print("STATUS: PASS (Barge-in < 200ms)")
        else:
            print("STATUS: NOTE (Barge-in typically requires <200ms processing. LangGraph might be slower.)")

asyncio.run(test_call_simulation())
