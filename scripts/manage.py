#!/usr/bin/env python3
"""Install and run the isolated Prime Agent OpenRouter ZDR profile."""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request
import venv

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / ".runtime"
BINARY = STATE / "bin" / "prime-agent"
CONFIG = STATE / "config"
MODEL = "deepseek/deepseek-v4.1-flash-1017"
PROVIDER = "openrouter"
PROFILES = {"balanced": None, "economy": "price", "fast": "throughput"}
VERSION = "0.10.1"
UV_VERSION = "0.9.5"
BASE = f"https://github.com/PrimeIntellect-ai/prime-agent/releases/download/v{VERSION}"
CHECKSUMS = {
    "darwin-arm64": "2b47bd9cefa0b531151aaeb7295073ba0a16cf694177c18b4f9f74a54b24e279",
    "darwin-x64": "9e2812084acead5a2c44209ffac350f762da67a27f4abcc5b417b7a6ef436632",
    "linux-arm64": "5af68c10a088538fd4990fd18778d8c7fe28c0491083dc069c5177f733770e91",
    "linux-x64": "21ec219183f4134dd23dce9572102e69456066fe374846525561c776d4d1945c",
}


def initialize():
    STATE.mkdir(exist_ok=True, mode=0o700)
    STATE.chmod(0o700)
    for name in ("config", "tmp", "downloads"):
        (STATE / name).mkdir(exist_ok=True, mode=0o700)


def profile_config(profile="balanced"):
    if profile not in PROFILES:
        raise RuntimeError("Choose a profile: balanced, economy, fast.")
    return CONFIG if profile == "balanced" else STATE / "profiles" / profile


def environment(profile="balanced"):
    env = os.environ.copy()
    env.update({
        "PRIME_AGENT_CODING_AGENT_DIR": str(profile_config(profile)),
        "PRIME_AGENT_KERNEL_VENV": str(STATE / "kernel-venv"),
        "PRIME_AGENT_DAEMON_SOCKET": str(STATE / "tmp" / f"{profile}.sock"),
        "UV_CACHE_DIR": str(STATE / "uv-cache"),
        "UV_PYTHON_INSTALL_DIR": str(STATE / "python"),
        "UV_PYTHON_BIN_DIR": str(STATE / "python-bin"),
        "TMPDIR": str(STATE / "tmp"),
        "DO_NOT_TRACK": "1",
    })
    env["PATH"] = str(STATE / "tools" / "bin") + os.pathsep + env.get("PATH", "")
    # Parent sessions must not steer this profile to another config/session store.
    for name in ("PRIME_AGENT_SESSION_DIR", "PRIME_AGENT_CODING_AGENT_SESSION_DIR"):
        env.pop(name, None)
    if len(os.fsencode(env["PRIME_AGENT_DAEMON_SOCKET"])) > 100:
        raise RuntimeError("Clone this repository under a shorter path (daemon socket exceeds 100 bytes).")
    return env


def routing(profile="balanced"):
    profile_config(profile)
    value = {"zdr": True}
    if PROFILES[profile]:
        value["sort"] = PROFILES[profile]
    return value


def models_config(profile="balanced"):
    return {"providers": {PROVIDER: {
        "baseUrl": "https://openrouter.ai/api/v1",
        "api": "openai-completions",
        "apiKey": "OPENROUTER_API_KEY",
        "compat": {"openRouterRouting": routing(profile)},
        "models": [{
            "id": MODEL,
            "name": "DeepSeek V4.1 Flash 1017 (OpenRouter ZDR)",
            "reasoning": True,
            "thinkingLevelMap": {"off": "none", "minimal": None, "low": "low", "medium": None, "high": "high", "xhigh": None, "max": "max"},
            "input": ["text", "image"],
            "contextWindow": 1048576,
            "maxTokens": 65536,
            # Catalog reference rates, USD/M tokens; reported usage.cost takes precedence.
            "cost": {"input": 0.30, "output": 1.20, "cacheRead": 0.006, "cacheWrite": 0.30},
        }],
    }}}


def settings_config():
    return {
        "defaultProvider": PROVIDER,
        "defaultModel": MODEL,
        "defaultThinkingLevel": "low",
        "allowedModels": [f"{PROVIDER}/{MODEL}"],
        "telemetry": {"enabled": False},
    }


def write_private(path, data):
    # os.open sets permissions before the first byte is written.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        os.chmod(path, 0o600)
        handle.write(data)


def configure():
    for profile in PROFILES:
        folder = profile_config(profile)
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        for filename, value in (("models.json", models_config(profile)), ("settings.json", settings_config())):
            write_private(folder / filename, json.dumps(value, indent=2) + "\n")
    print("Configured balanced, economy and fast ZDR profiles. Default: balanced, low reasoning.")


def verify_profile(profile="balanced"):
    expected = models_config(profile)
    path = profile_config(profile) / "models.json"
    if not path.exists() or json.loads(path.read_text()) != expected:
        raise RuntimeError("Profile differs from the verified ZDR template. Run ./setup.sh --configure-only.")
    settings = profile_config(profile) / "settings.json"
    if not settings.exists() or json.loads(settings.read_text()).get("allowedModels") != [f"{PROVIDER}/{MODEL}"]:
        raise RuntimeError("Pinned-model policy differs. Run ./setup.sh --configure-only.")


def target():
    machine = {"x86_64": "x64", "amd64": "x64", "arm64": "arm64", "aarch64": "arm64"}.get(platform.machine().lower())
    name = f"{platform.system().lower()}-{machine}"
    if name not in CHECKSUMS:
        raise RuntimeError("Supported: Linux/macOS on x64/arm64. On Windows use WSL2 with Ubuntu.")
    return name


def download(url, path):
    request = urllib.request.Request(url, headers={"User-Agent": "prime-openrouter-zdr-starter"})
    try:
        with urllib.request.urlopen(request, timeout=90) as response, path.open("wb") as output:
            shutil.copyfileobj(response, output)
    except (OSError, urllib.error.URLError):
        path.unlink(missing_ok=True)
        raise RuntimeError("Download failed. Check your network and retry setup.") from None


def unpack(archive, destination):
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle.getmembers():
            resolved = (destination / member.name).resolve()
            if not resolved.is_relative_to(destination.resolve()) or not (member.isfile() or member.isdir()):
                raise RuntimeError("Unsafe release archive entry; installation stopped.")
        bundle.extractall(destination)


def install():
    arch = target()
    marker = STATE / "installed.json"
    identity = {"version": VERSION, "target": arch, "sha256": CHECKSUMS[arch]}
    if BINARY.exists() and marker.exists() and json.loads(marker.read_text()) == identity:
        print(f"Prime Agent {VERSION} is already installed here.")
        return
    archive = STATE / "downloads" / f"prime-agent-{VERSION}-{arch}.tar.gz"
    if not archive.exists():
        print(f"Downloading official Prime Agent {VERSION} ({arch})...", flush=True)
        download(f"{BASE}/{archive.name}", archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != CHECKSUMS[arch]:
        archive.unlink()
        raise RuntimeError("Release SHA-256 mismatch. Archive removed; retry setup.")
    destination = STATE / "bin"
    destination.mkdir(exist_ok=True)
    unpack(archive, destination)
    BINARY.chmod(0o755)
    actual = subprocess.check_output([str(BINARY), "--version"], env=environment(), text=True).strip()
    if actual != VERSION:
        raise RuntimeError("Installed binary version differs from the pinned release.")
    write_private(marker, json.dumps(identity) + "\n")
    print(f"Verified SHA-256 and installed Prime Agent {VERSION}.")


def bootstrap():
    env = environment()
    if not shutil.which("uv", path=env["PATH"]):
        print(f"Installing uv {UV_VERSION} into .runtime/tools...", flush=True)
        venv.create(STATE / "tools", with_pip=True)
        subprocess.run([str(STATE / "tools" / "bin" / "python"), "-m", "pip", "install", f"uv=={UV_VERSION}"], check=True, env=env)
    subprocess.run([str(BINARY), "--prime-agent-bootstrap"], check=True, env=environment())


def api_key(interactive=False):
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    saved = STATE / "openrouter.key"
    if not key and saved.exists():
        key = saved.read_text().strip()
    if not key and interactive and sys.stdin.isatty():
        key = getpass.getpass("OpenRouter API key (hidden; stored only in ignored .runtime/openrouter.key): ").strip()
        if key:
            write_private(saved, key + "\n")
    if not key or "\n" in key or "\r" in key:
        raise RuntimeError("Set OPENROUTER_API_KEY locally, or run ./prime in a terminal to enter your key. Do not paste keys into AI chat.")
    return key


def request_json(url, payload=None, key=None):
    headers = {"User-Agent": "prime-openrouter-zdr-starter"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=None if payload is None else json.dumps(payload).encode(), headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        # Avoid echoing response bodies that can contain request details.
        raise RuntimeError(f"OpenRouter HTTP {error.code}. Check key, credits, model availability and ZDR eligibility. No privacy fallback was attempted.") from None
    except urllib.error.URLError:
        raise RuntimeError("Cannot reach OpenRouter. Check your network and retry.") from None


def doctor(online=False, profile="balanced"):
    verify_profile(profile)
    if not BINARY.exists():
        raise RuntimeError("Prime Agent is missing. Run ./setup.sh.")
    subprocess.run([str(BINARY), "--version"], check=True, env=environment(profile))
    print(f"PASS: {profile} ZDR profile, pinned model, local config and daemon paths.")
    if not (STATE / "kernel-venv" / "bin" / "python").exists():
        raise RuntimeError("Python kernel is missing. Run ./setup.sh to complete runtime bootstrap.")
    print("PASS: Python kernel installed.")
    if online:
        data = request_json("https://openrouter.ai/api/v1/endpoints/zdr")
        endpoints = [entry for entry in data["data"] if entry.get("model_id") == MODEL or entry.get("model") == MODEL]
        if not endpoints:
            raise RuntimeError("No matching ZDR endpoints were found in OpenRouter's current public list.")
        print(f"PASS: {len(endpoints)} current ZDR endpoints for {MODEL}. No paid inference requested.")
        print("Advertised base USD/M tokens (time-based overrides may differ; not a billing guarantee):")
        for endpoint in sorted(endpoints, key=lambda item: item["tag"]):
            prices = endpoint["pricing"]
            prompt = float(prices["prompt"]) * 1_000_000
            output = float(prices["completion"]) * 1_000_000
            cached = prices.get("input_cache_read")
            cache_label = "unknown" if cached is None else f"{float(cached) * 1_000_000:.4g}"
            print(f"  {endpoint['tag']}: input={prompt:.4g} output={output:.4g} cached-input={cache_label}")


def smoke(profile="balanced"):
    verify_profile(profile)
    result = request_json("https://openrouter.ai/api/v1/chat/completions", {
        "model": MODEL, "provider": routing(profile),
        "messages": [{"role": "user", "content": "Reply with OK."}],
        "reasoning": {"enabled": False}, "max_tokens": 16,
    }, api_key())
    if not result.get("choices"):
        raise RuntimeError("OpenRouter returned no choices.")
    print("PASS: paid ZDR inference returned a completion. No prompt or API key logged.")


def validate_selection(arguments):
    pinned = {"--provider": PROVIDER, "--model": MODEL}
    for index, argument in enumerate(arguments):
        if argument == "--":
            break
        for flag, expected in pinned.items():
            value = None
            if argument == flag:
                value = arguments[index + 1] if index + 1 < len(arguments) else ""
            elif argument.startswith(flag + "="):
                value = argument.split("=", 1)[1]
            if value is not None and value != expected:
                raise RuntimeError(f"This profile pins {flag} to {expected}; use --profile to change routing.")


def run(arguments):
    profile = "balanced"
    if arguments[:1] == ["--profile"]:
        if len(arguments) < 2:
            raise RuntimeError("--profile requires balanced, economy or fast.")
        profile, arguments = arguments[1], arguments[2:]
    verify_profile(profile)
    validate_selection(arguments)
    if not BINARY.exists():
        raise RuntimeError("Run ./setup.sh first.")
    env = environment(profile)
    if arguments and arguments[0] in ("help", "status", "doctor", "shutdown", "model"):
        os.execve(str(BINARY), [str(BINARY), *arguments], env)
    if not arguments or arguments[0] not in ("--help", "-h", "--version", "-v"):
        env["OPENROUTER_API_KEY"] = api_key(interactive=True)
    os.execve(str(BINARY), [str(BINARY), "--provider", PROVIDER, "--model", MODEL, *arguments], env)


def main():
    os.umask(0o077)
    if sys.version_info < (3, 10):
        raise RuntimeError("Python 3.10 or newer is required.")
    initialize()
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        run(sys.argv[2:])
        return
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("setup")
    setup.add_argument("--configure-only", action="store_true")
    setup.add_argument("--skip-bootstrap", action="store_true")
    check = commands.add_parser("doctor")
    check.add_argument("--online", action="store_true")
    check.add_argument("--profile", choices=PROFILES, default="balanced")
    probe = commands.add_parser("smoke", help="Send one small paid ZDR request using your local key")
    probe.add_argument("--profile", choices=PROFILES, default="balanced")
    args = parser.parse_args()
    if args.command == "setup":
        configure()
        if not args.configure_only:
            install()
            if not args.skip_bootstrap:
                bootstrap()
        print("Ready. Run ./prime, or python3 -I scripts/manage.py doctor --online.")
    elif args.command == "doctor":
        doctor(args.online, args.profile)
    elif args.command == "smoke":
        smoke(args.profile)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
