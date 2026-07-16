"""
relay.py - AI-Agent relay for the CLI-Agent Bridge (Option A).

Runs on the Termux device, launched by Kai over the SSH tunnel.
Connects to the broker as the AGENT role.

- The USER types plain chat on the Termux CLI -> sent as CHAT to Kai.
- Kai (the agent brain) sends lines on this relay's stdin:
    * prefixed with "!" or "run:" -> executed as a shell COMMAND on the CLI
    * anything else                -> shown on Termux as a CHAT reply (agent>)
- All CLI output streams back and is printed prefixed with "agent> ".

So: user chats in Termux; Kai reads it, decides, and either runs a command
(!prefix) or replies with chat. The Termux CLI is the chat window.
"""

import asyncio
import json
import ssl
import sys
import websockets
import config


async def main():
    ssl_ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    ssl_ctx.load_verify_locations(cafile=config.CERT_PATH)

    async with websockets.connect(config.SERVER_URI, ssl=ssl_ctx) as ws:
        await ws.send(json.dumps({
            "type": "auth",
            "token": config.TOKEN,
            "role": config.ROLE_AGENT,
        }))
        auth = json.loads(await ws.recv())
        if auth.get("type") != "auth_ok":
            print("[relay] auth failed:", auth, flush=True)
            return

        print("agent> Successfully connected. What's up?", flush=True)

        async def reader():
            while True:
                try:
                    raw = await ws.recv()
                except websockets.exceptions.ConnectionClosed:
                    break
                msg = json.loads(raw)
                t = msg.get("type")
                if t == "output":
                    sys.stdout.write(msg.get("data", ""))
                    sys.stdout.flush()
                elif t == "done":
                    print("", flush=True)
                elif t == "chat":
                    print("agent> " + msg.get("data", ""), flush=True)

        async def writer():
            loop = asyncio.get_event_loop()
            while True:
                try:
                    line = await loop.run_in_executor(None, sys.stdin.readline)
                except EOFError:
                    break
                if line == "":
                    break
                line = line.rstrip("\n")
                if not line:
                    continue
                if line.startswith("!") or line.startswith("run:"):
                    cmd = line[1:].strip() if line.startswith("!") else line[4:].strip()
                    cid = "cmd-" + str(abs(hash(cmd)) % 100000)
                    await ws.send(json.dumps({"type": "command", "id": cid, "cmd": cmd}))
                else:
                    await ws.send(json.dumps({"type": "chat", "id": "chat-1", "data": line}))

        await asyncio.gather(reader(), writer())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
