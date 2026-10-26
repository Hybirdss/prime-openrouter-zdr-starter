#!/usr/bin/env python3
"""Verify real routing, reasoning and billing against a local SSE server. No paid API."""
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
REPORTED_COST = 0.00123456


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
            if finish:
                event["usage"] = {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110, "prompt_tokens_details": {"cached_tokens": 50}, "cost": REPORTED_COST}
            self.wfile.write(("data: " + json.dumps(event) + "\n\n").encode())
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


def assistant_messages(value):
    if isinstance(value, dict):
        if value.get("role") == "assistant" and "usage" in value:
            yield value
        for nested in value.values():
            yield from assistant_messages(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from assistant_messages(nested)


def verify_run(server, profile, thinking=None):
    requests.clear()
    with tempfile.TemporaryDirectory(dir=manage.STATE / "tmp") as directory:
        work = Path(directory)
        config = work / "config"
        config.mkdir()
        models = manage.models_config(profile)
        # The upstream adapter recognizes OpenRouter by this URL substring.
        models["providers"][manage.PROVIDER]["baseUrl"] = f"http://127.0.0.1:{server.server_port}/openrouter.ai/api/v1"
        (config / "models.json").write_text(json.dumps(models))
        (config / "settings.json").write_text(json.dumps(manage.settings_config()))
        env = manage.environment(profile)
        env.update({"PRIME_AGENT_CODING_AGENT_DIR": str(config), "PRIME_AGENT_DAEMON_SOCKET": str(manage.STATE / "tmp/wire.sock"), "OPENROUTER_API_KEY": "dummy-local-test-key"})
        args = [str(manage.BINARY), "--provider", manage.PROVIDER, "--model", manage.MODEL, "--offline", "--no-session", "--no-context-files", "--no-skills", "--no-prompt-templates", "--no-themes", "--mode", "json", "-p", "Reply OK without calling tools."]
        if thinking:
            args += ["--thinking", thinking]
        try:
            result = subprocess.run(args, cwd=work, env=env, capture_output=True, text=True, timeout=90)
            if result.returncode:
                raise RuntimeError(f"Agent exited {result.returncode}: {result.stderr[-3000:]}")
            assert requests, "No HTTP inference request captured"
            for path, auth, payload in requests:
                assert path.endswith("/chat/completions"), path
                assert auth == "Bearer dummy-local-test-key"
                assert payload["model"] == manage.MODEL, payload.get("model")
                # Assert the literal wire contract, independently of config generation.
                expected_route = {"zdr": True}
                if profile == "economy":
                    expected_route["sort"] = "price"
                elif profile == "fast":
                    expected_route["sort"] = "throughput"
                assert payload["provider"] == expected_route, payload.get("provider")
                expected_reasoning = {"effort": "none" if thinking == "off" else thinking or "low"}
                assert payload["reasoning"] == expected_reasoning, payload.get("reasoning")
                assert payload.get("tools"), "No real agent tools in request"
            events = [json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]
            messages = list(assistant_messages(events))
            assert any(any(block.get("type") == "text" and block.get("text") == "OK" for block in message.get("content", [])) for message in messages), "No assistant OK response"
            usages = [message["usage"] for message in messages]
            assert any(abs(usage["cost"]["total"] - REPORTED_COST) < 1e-12 for usage in usages), "OpenRouter reported billing cost was not preserved"
            assert any(usage["cacheRead"] == 50 for usage in usages), "Cached prompt tokens were not preserved"
            print(f"PASS: {profile}, thinking={thinking or 'default low'}: literal ZDR/routing/reasoning payload, tools, cached tokens and reported billing cost.")
        finally:
            subprocess.run([str(manage.BINARY), "shutdown"], env=env, cwd=work, capture_output=True, timeout=30)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), MockOpenRouter)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        for profile in ("balanced", "economy", "fast"):
            verify_run(server, profile)
        for thinking in ("high", "max", "off"):
            verify_run(server, "balanced", thinking)
    finally:
        server.shutdown()
    print("PASS: all checks used the official agent and a local server. No external inference.")


if __name__ == "__main__":
    main()
