"""Model providers: what is configured, how to set up the rest, and which models each offers.

The Models settings page shows one card per provider (logo, status, key field or CLI setup
instructions); role dropdowns only list models from configured providers.
"""

from __future__ import annotations

from typing import Any

import httpx

from . import config, gateway

PROVIDERS: list[dict[str, Any]] = [
    {"id": "meta", "name": "Meta Model API", "kind": "api", "logo": "meta",
     "models": ["meta/muse-spark-1.3", "meta/muse-wonder-1.0", "meta/muse-spark-1.3-contributor", "meta/muse-spark-1.2",
                "meta/muse-spark-1.1"],
     "keys_url": "https://dev.meta.ai/api-keys/",
     "note": "Muse Spark and Muse Wonder (api.meta.ai). Contributor models are cheaper; Meta may train on that content."},
    {"id": "claude-code", "name": "Claude Code", "kind": "subscription", "logo": "claude",
     "models": ["claude-code:sonnet", "claude-code:opus", "claude-code:haiku"],
     "setup": ["npm install -g @anthropic-ai/claude-code", "claude   # sign in once"],
     "note": "Uses your Claude subscription. No API key."},
    {"id": "codex", "name": "Codex", "kind": "subscription", "logo": "openai",
     "models": ["codex:gpt-5", "codex:gpt-5-codex"],
     "setup": ["npm install -g @openai/codex", "codex login"],
     "note": "Uses your ChatGPT subscription. No API key."},
    {"id": "anthropic", "name": "Anthropic API", "kind": "api", "logo": "anthropic",
     "models": ["anthropic/claude-sonnet-5-5", "anthropic/claude-opus-5-5", "anthropic/claude-haiku-5-5"],
     "keys_url": "https://console.anthropic.com/settings/keys"},
    {"id": "openai", "name": "OpenAI API", "kind": "api", "logo": "openai",
     "models": ["openai/gpt-5", "openai/gpt-5-mini"], "keys_url": "https://platform.openai.com/api-keys"},
    {"id": "gemini", "name": "Google Gemini", "kind": "api", "logo": "gemini",
     "models": ["gemini/gemini-2.5-pro", "gemini/gemini-2.5-flash"], "keys_url": "https://aistudio.google.com/apikey"},
    {"id": "openrouter", "name": "OpenRouter", "kind": "api", "logo": "openrouter",
     "models": ["openrouter/anthropic/claude-sonnet-5-5", "openrouter/meta-llama/llama-4-maverick"],
     "keys_url": "https://openrouter.ai/keys"},
    {"id": "mistral", "name": "Mistral", "kind": "api", "logo": "mistral",
     "models": ["mistral/mistral-large-latest"], "keys_url": "https://console.mistral.ai/api-keys"},
    {"id": "deepseek", "name": "DeepSeek", "kind": "api", "logo": "deepseek",
     "models": ["deepseek/deepseek-chat", "deepseek/deepseek-reasoner"], "keys_url": "https://platform.deepseek.com/api_keys"},
    {"id": "ollama", "name": "Ollama", "kind": "local", "logo": "ollama", "models": [],
     "setup": ["Install from ollama.com", "ollama pull llama3.3"], "note": "Runs models on this machine."},
    {"id": "lm_studio", "name": "LM Studio", "kind": "local", "logo": "lmstudio", "models": [],
     "setup": ["Install from lmstudio.ai", "Start the local server (port 1234)"], "note": "Runs models on this machine."},
    {"id": "mock", "name": "Offline demo", "kind": "offline", "logo": "florist", "models": ["mock"],
     "note": "Deterministic fake model for trying the app."},
]


FULL = ["minimal", "low", "medium", "high", "xhigh", "max"]
EFFORTS: dict[str, list[str]] = {
    "meta/muse-spark-1.3": FULL, "meta/muse-wonder-1.0": FULL, "meta/muse-spark-1.3-contributor": FULL[:-1],
    "claude-code:sonnet": ["low", "medium", "high", "xhigh", "max"], "claude-code:opus": ["low", "medium", "high", "xhigh", "max"],
    "claude-code:haiku": ["low", "medium", "high"],
    "codex:gpt-5": ["minimal", "low", "medium", "high"], "codex:gpt-5-codex": ["low", "medium", "high"],
    "openai/gpt-5": ["minimal", "low", "medium", "high"], "openai/gpt-5-mini": ["minimal", "low", "medium", "high"],
    "anthropic/claude-sonnet-5-5": ["low", "medium", "high"], "anthropic/claude-opus-5-5": ["low", "medium", "high"],
    "gemini/gemini-2.5-pro": ["low", "medium", "high"], "gemini/gemini-2.5-flash": ["low", "medium", "high"],
    "deepseek/deepseek-reasoner": ["low", "medium", "high"],
}
MODEL_NOTES = {
    "meta/muse-spark-1.3": "Latest Muse Spark · agentic, 1M context", "meta/muse-wonder-1.0": "Most capable · preview",
    "meta/muse-spark-1.3-contributor": "Cheaper · Meta may train on content", "meta/muse-spark-1.2": "Previous Muse Spark",
    "meta/muse-spark-1.1": "Original Muse Spark", "mock": "Offline, deterministic",
}


def _local_models(url: str, prefix: str, key: str) -> list[str]:
    try:
        r = httpx.get(url, timeout=0.4)
        data = r.json()
    except Exception:
        return []
    items = data.get(key) or []
    return [f"{prefix}/{(m.get('name') or m.get('id') or '').removesuffix(':latest')}" for m in items if isinstance(m, dict)]


def status() -> list[dict[str, Any]]:
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(2) as ex:  # probe local servers in parallel so the page never stalls
        f_ollama = ex.submit(_local_models, "http://127.0.0.1:11434/api/tags", "ollama", "models")
        f_lms = ex.submit(_local_models, "http://127.0.0.1:1234/v1/models", "lm_studio", "data")
        local = {"ollama": f_ollama.result(), "lm_studio": f_lms.result()}
    out = []
    for p in PROVIDERS:
        p = dict(p)
        models = list(p["models"])
        if p["kind"] == "subscription":
            exe = gateway.find_binary("claude" if p["id"] == "claude-code" else "codex")
            p["configured"], p["detail"] = bool(exe), (f"CLI found: {exe}" if exe else "CLI not installed")
        elif p["kind"] == "api":
            env = config.KEY_ENV.get(p["id"], p["id"].upper() + "_API_KEY")
            has = bool(config.key_for(p["id"]))
            p["configured"], p["key_env"] = has, env
            p["detail"] = "Key set" if has else f"Needs {env}"
        elif p["id"] == "ollama":
            models = local["ollama"]
            p["configured"] = bool(models)
            p["detail"] = f"{len(models)} local models" if models else "Not running"
        elif p["id"] == "lm_studio":
            models = local["lm_studio"]
            p["configured"] = bool(models)
            p["detail"] = f"{len(models)} local models" if models else "Not running"
        else:
            p["configured"], p["detail"] = True, "Always available"
        p["models"] = models
        out.append(p)
    return out


def configured_models() -> list[str]:
    s = config.get().models
    models = [m for p in status() if p["configured"] for m in p["models"]]
    for current in (s.ideate, s.fast, s.strong, s.default):  # never hide what is selected
        if current and current not in models:
            models.append(current)
    return models


def catalog() -> list[dict[str, Any]]:
    """Configured models grouped by provider, with the effort levels each supports (for the chat model picker)."""
    s = config.get().models
    selected = {s.ideate or s.strong, s.fast, s.strong, s.default}
    out = []
    for p in status():
        if not p["configured"]:
            continue
        out.append({"id": p["id"], "name": p["name"], "logo": p["logo"], "kind": p["kind"],
                    "models": [{"id": m, "efforts": EFFORTS.get(m, []), "note": MODEL_NOTES.get(m, "")} for m in p["models"]]})
    known = {m["id"] for g in out for m in g["models"]}
    extra = [m for m in selected if m and m not in known]
    if extra:
        out.append({"id": "other", "name": "Other", "logo": "", "kind": "other",
                    "models": [{"id": m, "efforts": EFFORTS.get(m, []), "note": ""} for m in extra]})
    return out
