"""Local credential-injecting proxy (ADR-009).

Agents (the Claude Code CLI started by the Agent SDK) get
ANTHROPIC_BASE_URL=http://127.0.0.1:<port> and a random *dummy* key. The proxy checks the
dummy, swaps in the real credential and streams the upstream response back. The real key
therefore never exists in an agent process, in the Bash tool, or in code an agent writes.
"""
from __future__ import annotations

import http.client
import secrets
import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOP_BY_HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te",
              "trailers", "transfer-encoding", "upgrade", "host", "content-length",
              "accept-encoding"}


class KeyProxy:
    def __init__(self, api_key: str | None = None, oauth_token: str | None = None,
                 upstream_host: str = "api.anthropic.com", upstream_port: int = 443,
                 upstream_tls: bool = True):
        if not (api_key or oauth_token):
            raise ValueError("KeyProxy needs a credential")
        self.api_key, self.oauth_token = api_key, oauth_token
        self.dummy = "sk-ant-autose-dummy-" + secrets.token_hex(16)
        self.upstream = (upstream_host, upstream_port, upstream_tls)
        self.requests = 0
        proxy = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):  # keep CI logs quiet
                pass

            def _handle(self):
                if not self.path.startswith("/v1/") or self._presented() != proxy.dummy:
                    self.send_response(403)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else None
                headers = {k.lower(): v for k, v in self.headers.items()
                           if k.lower() not in HOP_BY_HOP | {"x-api-key", "authorization"}}
                if proxy.api_key:
                    headers["x-api-key"] = proxy.api_key
                else:
                    headers["authorization"] = f"Bearer {proxy.oauth_token}"
                    beta = [b for b in (headers.pop("anthropic-beta", "") or "").split(",") if b]
                    headers["anthropic-beta"] = ",".join(beta + ["oauth-2025-04-20"])
                host, port, tls = proxy.upstream
                conn = (http.client.HTTPSConnection(host, port, timeout=600,
                                                    context=ssl.create_default_context())
                        if tls else http.client.HTTPConnection(host, port, timeout=600))
                try:
                    conn.request(self.command, self.path, body=body, headers=headers)
                    resp = conn.getresponse()
                    proxy.requests += 1
                    self.send_response(resp.status, resp.reason)
                    for k, v in resp.getheaders():
                        if k.lower() not in HOP_BY_HOP:
                            self.send_header(k, v)
                    self.send_header("Transfer-Encoding", "chunked")
                    self.end_headers()
                    while True:
                        chunk = resp.read1(65536)
                        if not chunk:
                            break
                        self.wfile.write(b"%x\r\n%s\r\n" % (len(chunk), chunk))
                        self.wfile.flush()
                    self.wfile.write(b"0\r\n\r\n")
                    self.wfile.flush()
                finally:
                    conn.close()

            def _presented(self) -> str:
                key = self.headers.get("x-api-key")
                if key:
                    return key
                auth = self.headers.get("authorization") or ""
                return auth[7:] if auth.lower().startswith("bearer ") else ""

            do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = _handle

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self) -> "KeyProxy":
        self._thread.start()
        return self

    def stop(self) -> None:
        self.server.shutdown()

    def agent_env(self) -> dict[str, str]:
        """Environment for the agent CLI. Only the dummy credential is ever exposed."""
        return {"ANTHROPIC_BASE_URL": self.url, "ANTHROPIC_API_KEY": self.dummy}
