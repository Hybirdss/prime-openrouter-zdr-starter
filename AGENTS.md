# Set up this repository for the user

This is a generic public installer profile for official Prime Agent, OpenRouter ZDR and DeepSeek V4.1 Flash 1017. Work inside this clone. Read README.md before running commands.

1. Check Linux/macOS x64/arm64 and Python >=3.10. On Windows use WSL2. Never replace an existing Prime installation or copy existing user settings, work, sessions, prompts or credentials.
2. Run `./setup.sh`. It installs only into ignored `.runtime/`. It may download official Prime Agent, uv, Python and runtime dependencies. Do not run the upstream global installer or `prime-agent update`.
3. Run `python3 -I scripts/manage.py doctor --online` and `python3 -I -m unittest discover -s tests -v`.
4. Run `python3 -I tests/verify_wire.py`. This verifies the real agent's OpenRouter model and ZDR request payload using a local server and dummy key. It must not call paid inference.
5. Tell the user to run `./prime` in their own terminal to enter their API key with hidden input. Alternatively they can set `OPENROUTER_API_KEY` locally. Never ask for a key in chat, read existing credential stores, print a key, or commit `.runtime/`.
6. Only run `python3 -I scripts/manage.py smoke` when the user requests a paid connectivity check. The user needs their own OpenRouter account, key and credits.
7. Report the checks actually performed and any limitation. Explain `./prime --cwd /path/to/project` for their own project.

## Preserve the profile

- Model: `deepseek/deepseek-v4.1-flash-1017`.
- Provider: `openrouter-zdr`, base URL `https://openrouter.ai/api/v1`.
- Required compatibility option: `openRouterRouting.zdr: true`.
- ZDR endpoint availability may change. Never disable ZDR or switch to another model to hide a failure.
- Changes to `models.json` must use fields supported by the pinned release and pass the real wire check. Generic `requestBody` is not a supported custom-model option.
- Keep config, Python environment, caches, daemon sockets and sessions under `.runtime/`.
- Do not add site integrations, personal automation, extra skills, prompts or user projects to this public template.
- Before publishing, inspect the complete staged diff and tracked file list for keys, local paths and user content.

## Repository development

Use Python standard library tools for bootstrap and tests. Keep the official release version and all platform SHA-256 values together in `scripts/manage.py`. After changing bootstrap or routing, run unit tests and the installed binary's local wire check. No API secrets belong in CI.
