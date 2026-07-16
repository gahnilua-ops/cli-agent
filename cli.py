"""
CLI side of the bridge (chat mode).

- Prints a "user>" prompt; whatever Gahni types is sent as a CHAT message
  to the broker -> relay (Kai) decides what to do.
- Kai can send back:
    * a COMMAND -> we execute it and stream stdout/stderr as agent> output
    * a CHAT    -> we print it as agent>
This makes the Termux CLI a two-way chat window with Kai as the brain.
"""

import asyncio
import json
import ssl
import sys
import uuid
import websockets
import config


async def _send(ws, obj):
    await ws.send(json.dumps(obj))


async def run_command(ws, cmd_id, cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    async def pump(stream, stream_name):
        assert stream is not None
        while True:
            chunk = await stream.read(4096)
            if not chunk:
                break
            await _send(ws, {
                "type": "output",
                "id": cmd_id,
                "stream": stream_name,
                "data": chunk.decode(errors="replace"),
            })

    await asyncio.gather(pump(proc.stdout, "stdout"), pump(proc.stderr, "stderr"))
    code = await proc.wait()
    await _send(ws, {"type": "done", "id": cmd_id, "code": code})


async def main():
    ssl_ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    ssl_ctx.load_verify_locations(cafile=config.CERT_PATH)

    async with websockets.connect(config.SERVER_URI, ssl=ssl_ctx) as ws:
        await _send(ws, {"type": "auth", "token": config.TOKEN, "role": config.ROLE_CLI})
        auth = json.loads(await ws.recv())
        if auth.get("type") != "auth_ok":
            print("[cli] auth failed:", auth)
            return
        print("[cli] authenticated. Type below; Kai will reply or run commands.")

        async def reader():
            while True:
                try:
                    raw = await ws.recv()
                except websockets.exceptions.ConnectionClosed:
                    break
                msg = json.loads(raw)
                t = msg.get("type")
                if t == "command":
                    print("[cli] exec: " + repr(msg["cmd"]), flush=True)
                    asyncio.create_task(run_command(ws, msg["id"], msg["cmd"]))
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
                if line in ("exit", "quit"):
                    break
                await _send(ws, {"type": "chat", "id": "chat-1", "data": line})

        await asyncio.gather(reader(), writer())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    print("\n[cli] bye")
