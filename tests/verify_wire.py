#!/usr/bin/env python3
"""Verify the pinned agent's real HTTP payload against a local SSE server. No paid API."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("manage", ROOT / "scripts/manage.py")
manage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manage)
requests = []


class MockOpenRouter(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        requests.append((self.path, self.headers.get("Authorization"), body))
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for delta, finish in (({"role": "assistant", "content": "OK"}, None), ({}, "stop")):
            event = {"id": "test", "object": "chat.completion.chunk", "created": 1, "model": manage.MODEL, "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}
            self.wfile.write(("data: " + json.dumps(event) + "\n\n").encode())
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), MockOpenRouter)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with tempfile.TemporaryDirectory(dir=manage.STATE / "tmp") as directory:
        work = Path(directory)
        config = work / "config"
        config.mkdir()
        models = manage.models_config()
        # The actual upstream adapter recognizes OpenRouter by this URL substring.
        models["providers"][manage.PROVIDER]["baseUrl"] = f"http://127.0.0.1:{server.server_port}/openrouter.ai/api/v1"
        (config / "models.json").write_text(json.dumps(models))
        (config / "settings.json").write_text(json.dumps(manage.settings_config()))
        env = manage.environment()
        env.update({"PRIME_AGENT_CODING_AGENT_DIR": str(config), "PRIME_AGENT_DAEMON_SOCKET": str(manage.STATE / "tmp/wire.sock"), "OPENROUTER_API_KEY": "dummy-local-test-key"})
        args = [str(manage.BINARY), "--provider", manage.PROVIDER, "--model", manage.MODEL, "--offline", "--no-session", "--no-context-files", "--no-skills", "--no-prompt-templates", "--no-themes", "-p", "Reply OK without calling tools."]
        try:
            result = subprocess.run(args, cwd=work, env=env, capture_output=True, text=True, timeout=90)
            if result.returncode:
                raise RuntimeError(f"Agent exited {result.returncode}: {result.stderr[-3000:]}")
            assert requests, "No HTTP inference request captured"
            for path, auth, payload in requests:
                assert path.endswith("/chat/completions"), path
                assert auth == "Bearer dummy-local-test-key"
                assert payload["model"] == manage.MODEL, payload.get("model")
                assert payload["provider"]["zdr"] is True, payload.get("provider")
                assert payload.get("tools"), "No real agent tools in request"
            assert "OK" in result.stdout, result.stdout[-1000:]
            print("PASS: official Prime Agent sent the pinned model, ZDR=true and real tool definitions; consumed local SSE response. No external inference.")
        finally:
            subprocess.run([str(manage.BINARY), "shutdown"], env=env, cwd=work, capture_output=True, timeout=30)
            server.shutdown()


if __name__ == "__main__":
    main()
