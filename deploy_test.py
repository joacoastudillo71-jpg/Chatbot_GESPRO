import os
import sys
import time
import subprocess
import requests
from pyngrok import ngrok, conf





def start_server():
    """Starts the uvicorn server in a separate process."""
    print("Starting Uvicorn server...")
    # Using sys.executable to ensure we use the same python interpreter
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.voice.server:app",
 "--port", "8000",
 "--log-level", "info"],

        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return process

def start_tunnel(port=8000):
    """Starts an ngrok tunnel to the specified port."""
    print(f"Starting Ngrok tunnel on port {port}...")
    
    # Optional: Set auth token from env or user input if needed
    # auth_token = os.environ.get("NGROK_AUTH_TOKEN")
    # if auth_token:
    #     conf.get_default().auth_token = auth_token
        
    try:
        public_url = ngrok.connect(port).public_url
        print(f"Ngrok Tunnel Started: {public_url}")
        return public_url
    except Exception as e:
        print(f"Error starting ngrok: {e}")
        return None

def main():
    server_process = start_server()
    
    # Wait for server to start
    time.sleep(5) 
    
    public_url = start_tunnel()
    
    if public_url:
        print("\n" + "="*50)
        print(f"🌍 PUBLIC URL: {public_url}")
        print(f"🏥 Health Check: {public_url}/health")
        print(f"🔗 Retell Webhook: {public_url}/llm-websocket/{{call_id}}")
        print("="*50 + "\n")
        
        print("Press Ctrl+C to stop...")
        
        try:
            # Keep script running
            while True:
                line = server_process.stdout.readline()
                if line:
                    print(f"[Server] {line.strip()}")
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("Stopping...")
    else:
        print("Failed to create tunnel.")
        
    server_process.terminate()
    ngrok.kill()

if __name__ == "__main__":
    main()
