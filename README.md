# CLI-Agent Bridge

A secure WebSocket-based bridge between a local CLI and a remote agent for
real-time command execution and output streaming.

## Topology

    CLI (local)  <--wss-->  Broker (server.py)  <--wss-->  Agent (remote)

- `server.py`  - TLS WebSocket broker. Authenticates both ends, relays messages.
- `cli.py`     - Connects as role "cli". Receives commands, executes them, streams
                 stdout/stderr back in real time.
- `agent.py`   - Connects as role "agent". Interactive prompt to send commands and
                 watch streamed output + exit codes.

## Security

- TLS: wss:// with a self-signed cert in `certs/` (CN=localhost). For production
  swap in a CA-signed cert (Let us Encrypt) and verify the chain on clients.
- Auth: v1 uses a shared bearer token in `config.py` (TOKEN). The token is
  symmetric, so protect it. The handshake is designed so an ed25519 signature
  scheme can replace it later without changing the message protocol.

## Setup

    pip install -r requirements.txt
    # certs/ already contains a self-signed cert (generated once)

## Run (all on one machine for the prototype)

Terminal 1 (broker):
    python server.py

Terminal 2 (cli):
    python cli.py

Terminal 3 (agent):
    python agent.py

Then in the agent terminal, type a shell command, e.g. `uname -a`. Output streams
back from the CLI. Type `exit` to quit the agent.

## Protocol (JSON, one object per text frame)

    auth:    {"type":"auth","token":"...","role":"agent"|"cli"}
    command: {"type":"command","id":"uuid","cmd":"ls -la"}
    output:  {"type":"output","id":"uuid","stream":"stdout"|"stderr","data":"..."}
    done:    {"type":"done","id":"uuid","code":0}
    error:   {"type":"error","message":"..."}

## TODO / hardening

- Restrict CLI command execution (allowlist / sandbox / non-priv user).
- Replace shared token with per-role ed25519 signatures.
- Support multiple CLI/Agent pairs via a session registry.
# cli-agent
