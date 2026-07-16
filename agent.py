"""
Agent side of the bridge.

Type "exit" or Ctrl-C to quit cleanly.
"""

import asyncio
import json
import uuid
import signal
import ssl
import websockets
import config


async def main():
    ssl_ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    ssl_ctx.load_verify_locations(cafile=config.CERT_PATH)

    stop = asyncio.Event()

    async with websockets.connect(config.SERVER_URI, ssl=ssl_ctx) as ws:
        await ws.send(json.dumps({"type": "auth", "token": config.TOKEN, "role": config.ROLE_AGENT}))
        auth = json.loads(await ws.recv())
        if auth.get("type") != "auth_ok":
            print("[agent] auth failed:", auth)
            return
        print("[agent] authenticated. Type a command, or exit to quit.")

        async def reader():
            while True:
                try:
                    raw = await ws.recv()
                except websockets.exceptions.ConnectionClosed:
                    break
                msg = json.loads(raw)
                t = msg.get("type")
                if t == "output":
                    tag = "ERR" if msg.get("stream") == "stderr" else "OUT"
                    print("[" + tag + "] " + msg["data"], end="", flush=True)
                elif t == "done":
                    print("\n[done] exit code " + str(msg["code"]))
                elif t == "error":
                    print("[error] " + msg["message"])

        async def writer():
            loop = asyncio.get_event_loop()
            while True:
                try:
                    line = await loop.run_in_executor(None, input, "agent> ")
                except EOFError:
                    break
                line = line.strip()
                if line in ("exit", "quit"):
                    break
                if not line:
                    continue
                cid = str(uuid.uuid4())
                await ws.send(json.dumps({"type": "command", "id": cid, "cmd": line}))

        loop = asyncio.get_event_loop()
        try:
            loop.add_signal_handler(signal.SIGINT, stop.set)
        except (NotImplementedError, RuntimeError):
            pass

        reader_task = asyncio.create_task(reader())
        try:
            await writer()
        finally:
            stop.set()
            try:
                await ws.close()
            except Exception:
                pass
            await reader_task


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    print("\n[agent] bye")
