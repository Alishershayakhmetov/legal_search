"""Language-model backends for the cited answer (src of A1). Standard library only.

    LLM_BACKEND=ollama      (default) a local Ollama server, model LLM_MODEL (default gemma3:4b), OLLAMA_URL (default http://localhost:11434)
    LLM_BACKEND=anthropic   the Anthropic Messages API; needs ANTHROPIC_API_KEY; model LLM_MODEL (default claude-haiku-5-5)

The caller passes a system prompt and a user prompt and gets text back; nothing else in the app depends on which backend runs.
The anthropic backend is written from the public API description and has NOT been run in this project (no key yet).
"""
import json
import os
import urllib.error
import urllib.request


class LLMError(RuntimeError):
    pass


def _post(url, body, headers, timeout):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json", **headers})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        raise LLMError(f"{type(e).__name__}: {e}") from e


class Ollama:
    name = "ollama"

    def __init__(self, model=None, url=None):
        self.model = model or os.environ.get("LLM_MODEL", "gemma3:4b")
        self.url = (url or os.environ.get("OLLAMA_URL", "http://localhost:11434")).rstrip("/")

    def complete(self, system, user, max_tokens=320, temperature=0.1, timeout=300):
        r = _post(f"{self.url}/api/chat", {"model": self.model, "stream": False, "keep_alive": "10m",
                                           "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                                           "options": {"temperature": temperature, "num_ctx": 4096, "num_predict": max_tokens}}, {}, timeout)
        return r["message"]["content"].strip()


class Anthropic:
    name = "anthropic"

    def __init__(self, model=None, key=None):
        self.model = model or os.environ.get("LLM_MODEL", "claude-haiku-5-5")
        self.key = key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not self.key:
            raise LLMError("ANTHROPIC_API_KEY is not set")

    def complete(self, system, user, max_tokens=320, temperature=0.1, timeout=120):
        r = _post("https://api.anthropic.com/v1/messages", {"model": self.model, "max_tokens": max_tokens, "temperature": temperature, "system": system,
                                                            "messages": [{"role": "user", "content": user}]},
                  {"x-api-key": self.key, "anthropic-version": "2023-06-01"}, timeout)
        return "".join(b.get("text", "") for b in r.get("content", [])).strip()


def get_backend():
    kind = os.environ.get("LLM_BACKEND", "ollama").lower()
    if kind == "anthropic":
        return Anthropic()
    if kind == "ollama":
        return Ollama()
    raise LLMError(f"unknown LLM_BACKEND {kind!r}")
