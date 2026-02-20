# GESPRO AI - Public Testing Framework

This guide explains how to deploy the local agent to a public URL and connect it to Retell AI for stress testing.

## 1. Start the Environment
Run the deployment script. This script starts the FastAPI server and opens an Ngrok tunnel automatically.

```powershell
python deploy_test.py
```

You should see output like:
```
🌍 PUBLIC URL: https://<random-id>.ngrok-free.app
🏥 Health Check: https://<random-id>.ngrok-free.app/health
🔗 Retell Webhook: https://<random-id>.ngrok-free.app/llm-websocket/{call_id}
```

## 2. Verify Health
Open the **Health Check** URL in your browser. You should see:
```json
{"status": "ok", "database": "connected", "version": "0.0.1"}
```

## 3. Configure Retell AI
1. Go to the **Retell AI Dashboard** -> **Agents**.
2. Select your testing Agent.
3. In the **LLM Configuration** section (or "Custom LLM"), find the **Webhook URL** field.
4. Paste the **Retell Webhook** URL from step 1.
   - **Important:** Ensure `{call_id}` is at the end if Retell expects a templated URL, or just the base path if Retell appends the ID.
   - *Correction:* For Retell "Custom LLM" over WebSocket, you usually provide the base URL `wss://<your-url>/llm-websocket`. Retell appends the call_id.
   - **Update your dashboard URL to:** `wss://<random-id>.ngrok-free.app/llm-websocket` (replace `https://` with `wss://`).

## 4. Run a Test Call
1. In the Retell Dashboard, click "Test Call".
2. Allow microphone access.
3. Speak to the agent.
4. **Monitor the Console:** Look at the `deploy_test.py` terminal window to see real-time logs of transcripts and "Barge-in" events.

## 5. Troubleshooting
- **Ngrok Error (ERR_NGROK_4018):** You MUST sign up for a free Ngrok account and install your authtoken.
  1. Go to [dashboard.ngrok.com](https://dashboard.ngrok.com)
  2. Copy your Authtoken.
  3. Run in terminal: `ngrok config add-authtoken <YOUR_TOKEN>`
  4. Run `python deploy_test.py` again.
