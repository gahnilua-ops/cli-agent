"""
WebSocket broker for the CLI-Agent Bridge.

Responsibilities:
- Accept TLS-encrypted WebSocket connections (wss://).
- Authenticate each client via a bearer token in the first message.
- Assign a role (cli / agent) from the auth message.
- Relay: commands from Agent are forwarded to the registered CLI; output from
  the CLI is forwarded back to the Agent. Only one CLI and one Agent per session
  (extendable to a registry of pairs later).

Message protocol (JSON, one object per text frame):
  auth:     {"type":"auth","token":"...","role":"agent"|"cli"}
  command:  {"type":"command","id":"uuid","cmd":"ls -la"}
  output:   {"type":"output","id":"uuid","stream":"stdout"|"stderr","data":"..."}
  done:     {"type":"done","id":"uuid","code":0}
  error:    {"type":"error","message":"..."}
"""

import asyncio
import json
import ssl
import websockets
import config

# Active session: we support one CLI and one Agent for v1.
_cli = None      # websockets connection
_agent = None    # websockets connection


async def _send(ws, obj):
    try:
        await ws.send(json.dumps(obj))
    except Exception as e:
        print(f"[broker] send error: {e}")


async def handler(ws):
    global _cli, _agent
    peer = ws.remote_address
    print(f"[broker] connection from {peer}")
    # 1) Authenticate
    try:
        raw = await asyncio.wait_for(ws.recv(), timeout=10)
    except asyncio.TimeoutError:
        await _send(ws, {"type": "error", "message": "auth timeout"})
        return
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        await _send(ws, {"type": "error", "message": "bad json"})
        return
    if msg.get("type") != "auth" or msg.get("token") != config.TOKEN:
        await _send(ws, {"type": "error", "message": "unauthorized"})
        return
    role = msg.get("role")
    if role not in (config.ROLE_CLI, config.ROLE_AGENT):
        await _send(ws, {"type": "error", "message": "bad role"})
        return
    # 2) Register by role (single slot per role for v1)
    if role == config.ROLE_CLI:
        if _cli is not None:
            await _send(ws, {"type": "error", "message": "cli slot taken"})
            return
        _cli = ws
    else:
        if _agent is not None:
            await _send(ws, {"type": "error", "message": "agent slot taken"})
            return
        _agent = ws
    await _send(ws, {"type": "auth_ok", "role": role})
    print(f"[broker] {role} authenticated ({peer})")

    # 3) Relay loop
    try:
        while True:
            try:
                raw = await ws.recv()
            except websockets.exceptions.ConnectionClosed:
                break
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if role == config.ROLE_AGENT:
                # Agent -> CLI
                if msg.get("type") in ("command", "chat"):
                    if _cli is not None:
                        await _send(_cli, msg)
                    else:
                        await _send(ws, {"type": "error", "message": "no cli connected"})
            elif role == config.ROLE_CLI:
                # CLI -> Agent
                if msg.get("type") in ("output", "done", "error", "chat"):
                    if _agent is not None:
                        await _send(_agent, msg)
    finally:
        if role == config.ROLE_CLI and _cli is ws:
            _cli = None
            print("[broker] cli disconnected")
        elif role == config.ROLE_AGENT and _agent is ws:
            _agent = None
            print("[broker] agent disconnected")


async def main():
    ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_ctx.load_cert_chain(certfile=config.CERT_PATH, keyfile=config.KEY_PATH)
    async with websockets.serve(handler, config.HOST, config.PORT, ssl=ssl_ctx):
        print(f"[broker] listening on wss://{config.HOST}:{config.PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
