# Prime Agent + OpenRouter ZDR + DeepSeek Flash 1017

A public starter repository that an AI coding agent can clone, install, and configure for you. It uses official Prime Agent **0.10.1** with **`deepseek/deepseek-v4.1-flash-1017`** and sends **`provider.zdr: true`** on OpenRouter requests.

The repository contains no personal projects, conversations, prompts, or account credentials. Installation files, API keys, sessions, and caches stay in `.runtime/`, which Git ignores.

## Ask an AI agent to install it

Give this prompt to an AI coding agent that can run commands on your computer:

```text
Clone https://github.com/Hybirdss/prime-openrouter-zdr-starter into a new folder.
Read AGENTS.md, then run ./setup.sh. Run doctor --online and the local wire
verification. Do not copy my existing Prime settings or personal work.
Do not ask for my API key in chat. Tell me how to enter it in my local terminal.
Run the paid smoke check only if I request it.
```

After setup and verification, run `./prime` from the cloned folder. On first launch, enter your API key at the hidden terminal prompt. The key is saved to `.runtime/openrouter.key` with `0600` permissions.

Create your own OpenRouter account, generate an API key, and add credits. [Manage OpenRouter API keys](https://openrouter.ai/settings/keys).

## Install manually

Requirements: Linux or macOS on x64/arm64, Python 3.10 or newer, Git, and an internet connection. Linux requires glibc. On Windows, use Ubuntu in WSL2. Python's `venv` module is also required; install `python3-venv` on Ubuntu if it is missing.

```sh
git clone https://github.com/Hybirdss/prime-openrouter-zdr-starter.git
cd prime-openrouter-zdr-starter
./setup.sh
python3 -I scripts/manage.py doctor --online
./prime
```

The setup script:

- Verifies the pinned official release's SHA-256 and installs it into `.runtime/bin/`.
- Prepares separate model settings, session paths, daemon sockets, and a Python environment.
- Installs `uv 0.9.5` into `.runtime/tools/` if `uv` is unavailable.
- Prepares Prime Agent's Python 3.11 kernel and runtime dependencies.

Setup leaves other Prime Agent installations and services in place. It requires no administrator privileges or global npm installation. You can rerun `./setup.sh`; it regenerates this repository's `models.json` and `settings.json` with their defaults. Python dependencies follow the upstream bootstrap process, so this is not a fully locked offline distribution.

## Work on your project

Prime Agent works in the current directory by default. To use another project, pass its absolute or relative path:

```sh
./prime --cwd /path/to/your/project
```

To avoid saving your key to a file, set `OPENROUTER_API_KEY` in your terminal before launching. The environment variable takes precedence over the saved key. Keep keys out of command arguments, GitHub issues, and AI chats.

## Choose a cost and speed profile

The default profile is `balanced`. It uses the model's supported `low` reasoning effort and OpenRouter's default routing based on price and availability. It leaves provider ordering unset so automatic cache reuse can work across a conversation. All three profiles use the same Flash 1017 model with ZDR.

| Profile | Command | Routing | When to use it |
| --- | --- | --- | --- |
| `balanced` | `./prime` | OpenRouter default | Balance price, availability, and automatic caching |
| `economy` | `./prime --profile economy` | `sort: price` | Prioritize the lowest price; responses may be slower |
| `fast` | `./prime --profile fast` | `sort: throughput` | Prioritize generated tokens per second; requests may cost more |

Place `--profile` immediately after `./prime`. Each profile has separate settings, sessions, and a daemon. Profiles share the installed binary, Python environment, download cache, and API key. Switching profiles does not overwrite another profile's settings.

```sh
./prime --profile economy --cwd /path/to/your/project
./prime --profile fast --cwd /path/to/your/project

# Increase reasoning effort for complex tasks.
./prime --thinking high
./prime --thinking max

# Explicitly disable reasoning for short, simple tasks.
./prime --profile fast --thinking off
```

The model advertises `none`, `low`, `high`, and `max` reasoning efforts. This starter replaces the unsupported `medium` default with `low` and maps Prime's `off` to `none` and `max` to `max`. Lower effort can affect results on difficult tasks; use `high` when needed.

The output limit remains 65,536 tokens. Lowering a limit does not save the cost of tokens that were never generated, and it can truncate reasoning or code. Context compaction and subagent limits also remain unchanged without evidence from a representative workload.

The native `openrouter` provider ID lets Prime use the response's `usage.cost` and cached token counts. The previous `openrouter-zdr` alias bypassed this reported-cost handling. Catalog estimates apply when reported cost is unavailable. Reference rates checked on 2026-10-26 were $0.30/M input tokens, $1.20/M output tokens, and $0.006/M cached input tokens. Actual charges depend on the endpoint, time discounts, and BYOK terms. Use your OpenRouter usage records to confirm spending.

Check current ZDR endpoint base prices without an API key:

```sh
python3 -I scripts/manage.py doctor --online --profile economy
```

The table printed by this command excludes time-based price overrides. No fixed setting guarantees both the lowest price and the highest speed. Setting `sort` replaces default price-weighted load balancing with the selected ordering. At the time of research, this model's public latency and throughput metrics were empty, so this repository makes no measured speed-ranking or savings claims. See the [cost and speed research notes, in Korean](docs/research.md) for the repositories compared and the reasons behind these choices.

## Verify the setup

```sh
# Check local settings and installation without a key.
python3 -I scripts/manage.py doctor

# Check public ZDR endpoint availability. No paid inference.
python3 -I scripts/manage.py doctor --online

# Inspect real agent requests through a local server. No key required.
python3 -I tests/verify_wire.py

# Check setup, secret storage, configuration guards, and corrupt downloads.
python3 -I -m unittest discover -s tests -v

# Optional: send one small paid inference request using your key.
python3 -I scripts/manage.py smoke
```

`verify_wire.py` runs the official binary and checks the actual ZDR, sorting, reasoning, and tool payloads for all three profiles. It also checks reported cost and cached token accounting using mock responses. Unit tests verify that attempts to select another model are rejected before credentials are accessed. These tests make no external inference requests.

`smoke` checks OpenRouter connectivity; it does not validate a complete agent task. To check another profile, use `smoke --profile economy`.

GitHub Actions runs tests, installation, public ZDR availability checks, and local wire verification on Linux and macOS. CI requires no API secrets.

## Understand the ZDR scope

Each profile sets `compat.openRouterRouting.zdr: true`. Prime sends it as `provider.zdr` in the API request, restricting OpenRouter routing to eligible ZDR endpoints. Requests fail if no endpoint meets the conditions. This repository does not retry with weaker privacy settings.

ZDR concerns request retention by OpenRouter and model providers. Local sessions remain in `.runtime/`. Prime Agent can execute commands and edit files with your user permissions; this installation is not a security sandbox. Additional MCP servers, search services, and other integrations have their own data policies.

Before launch, `./prime` checks the model configuration and allowed-model policy. It rejects CLI attempts to select another provider or model. Daemon sessions also enforce `allowedModels`. This does not prevent someone from running the binary directly. To restore the defaults for all three profiles:

```sh
./setup.sh --configure-only
```

## Troubleshoot

- For `401`, check your OpenRouter key. To replace a saved key, delete `.runtime/openrouter.key` and run `./prime` again.
- For `402`, check your OpenRouter credits.
- For `404` or a provider availability error, run `doctor --online` and check the model's endpoint status. Keep ZDR enabled.
- If the daemon socket path is too long, move the repository to a shorter path.
- A SHA-256 mismatch stops installation. Retry setup; if it still fails, check the official release.
- If Python kernel setup fails, check your network and `uv` installation, then rerun `./setup.sh`.

Use `./prime shutdown` to stop the default profile's daemon. For another profile, use a command such as `./prime --profile fast shutdown`. Each command connects only to that profile's daemon socket. To uninstall, stop the daemons you used and delete the cloned folder. Preserve any project files you want to keep.

To upgrade from the earlier version, finish active sessions and run `./prime shutdown` using that version before updating. Then refresh the configuration:

```sh
git pull --ff-only
./setup.sh --configure-only
./prime
```

Keys and existing session files are preserved. Start a new session instead of resuming a session that used the old `openrouter-zdr` alias.

Review the release version and platform checksums together, then rerun wire verification when updating the pinned release. To preserve this isolated installation, follow this repository's setup procedure instead of the upstream global `update` command.

## Official references

- [Prime Agent v0.10.1 release and SHA256SUMS](https://github.com/PrimeIntellect-ai/prime-agent/releases/tag/v0.10.1)
- [Prime Agent custom model implementation](https://github.com/PrimeIntellect-ai/prime-agent/blob/v0.10.1/crates/pa-core/src/models/custom.rs)
- [OpenRouter ZDR policy](https://openrouter.ai/docs/guides/features/zdr)
- [OpenRouter provider routing](https://openrouter.ai/docs/guides/routing/provider-selection)
- [Model details and providers](https://openrouter.ai/deepseek/deepseek-v4.1-flash-1017)
- [Current ZDR endpoint API](https://openrouter.ai/api/v1/endpoints/zdr)
- [Current model pricing and reasoning API](https://openrouter.ai/api/v1/models)
- [OpenRouter automatic prompt caching](https://openrouter.ai/docs/guides/best-practices/prompt-caching)

This is an independent starter repository, not an official distribution from Prime Intellect, OpenRouter, or DeepSeek. This repository uses the MIT license. Downloaded Prime Agent releases and dependencies retain their respective licenses.
