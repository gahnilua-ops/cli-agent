"""
CLI-Agent Bridge - shared configuration.

SECURITY NOTE:
- TOKEN is a shared bearer secret. For a prototype this is fine, but it is
  symmetric: anyone with the token can impersonate either the CLI or the Agent.
  The handshake is structured so an ed25519 signature scheme can replace this
  later without touching the message protocol (see AUTH section in README).
- The self-signed cert in certs/ is for local or prototype use only. For a real
  deployment use a CA-signed cert (e.g. Let us Encrypt) and verify the chain.
"""

import os

# Network
HOST = "0.0.0.0"
PORT = 8765
SERVER_URI = "wss://localhost:8765"

# TLS
CERT_PATH = os.path.join(os.path.dirname(__file__), "certs", "cert.pem")
KEY_PATH = os.path.join(os.path.dirname(__file__), "certs", "key.pem")

# Authentication (shared bearer token, v1)
TOKEN = "change-me-super-secret-token"

# Roles
ROLE_CLI = "cli"
ROLE_AGENT = "agent"
