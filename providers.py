"""
PolyGuard victim providers.

The scanner's whole claim is about how well a *deployed chatbot* resists
multilingual prompt injection. "A deployed chatbot" is not one model, so this
module lets the same attack bank be fired at victims from different vendors and
the results compared side by side.

Why this matters more than it looks: a single-model result is ambiguous. If
Claude Haiku shows no multilingual gap, that could mean the gap does not exist,
or it could mean Haiku specifically closed it. Only a cross-vendor comparison
tells those apart, and the comparison is the finding either way.

Two rules keep the comparison honest:

  1. The ATTACK BANK is identical across victims. Same languages, same
     categories, same phrasings, same canary. Nothing is re-tuned per vendor.
  2. The JUDGE is constant across victims and always Anthropic. If the judge
     changed with the victim, a "gap" could just be two judges disagreeing.
     `engine.llm_judge_compliance` is therefore never routed through a victim
     client from this module.

Keys are read from the environment first, then Streamlit secrets. Nothing is
ever hardcoded, and no key is written to any export.

A fourth kind of victim runs on the scanning machine itself: an open weight
model served by llama.cpp's `llama-server` (provider "local"). It costs nothing
per call and needs no account, which makes it the way to produce real scans
before any paid key exists. A local result is a measurement of that small open
model, never of a production chatbot, and every label says so.

STATUS: the Anthropic adapter is exercised by the test suite. The OpenAI,
Google and OpenAI-compatible adapters are written against each vendor's
documented request shape but have NOT been run against a live key yet. Run
`python providers.py --smoke` once keys exist, before trusting any number that
comes out of them.
"""
from __future__ import annotations

import functools
import hashlib
import json
import os
import random
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

# Reply returned when a provider's own safety layer blocks the response
# outright. This is a refusal, not an error: the bot did not comply, so it
# scores as "not broken". It is a distinct string so it stays visible in the
# attack log instead of masquerading as an empty reply.
BLOCKED_SENTINEL = "[BLOCKED BY PROVIDER SAFETY FILTER]"

# Anthropic models that REMOVED the sampling parameters. Sending temperature to
# any of these is a 400, not a warning. The victim call must therefore be
# temperature-aware or a cross-model scan dies on the second model.
_ANTHROPIC_NO_SAMPLING = {
    "claude-opus-5-5", "claude-opus-5", "claude-opus-4-8", "claude-opus-4-7",
    "claude-sonnet-5", "claude-fable-5", "claude-fable-5-1",
    "claude-mythos-5", "claude-mythos-5-1",
}

# Anthropic models where thinking runs unless explicitly disabled, AND disabling
# it is accepted. A victim standing in for a shipped chatbot should not be
# reasoning at length before it answers, so these get thinking switched off for
# both fairness and cost.
_ANTHROPIC_THINKING_ON_BY_DEFAULT = {"claude-opus-5", "claude-sonnet-5"}

# Anthropic models where thinking CANNOT be switched off: an explicit
# {"type": "disabled"} is a 400, so sending it would fail every attack. These
# omit the parameter and run at the lowest effort instead. They still reason
# before answering, which makes them a different kind of victim, so the scan
# records it (`thinking_forced`) rather than comparing them silently.
_ANTHROPIC_THINKING_ALWAYS_ON = {
    "claude-opus-5-5", "claude-fable-5", "claude-fable-5-1",
    "claude-mythos-5", "claude-mythos-5-1",
}

# Thinking tokens count against max_tokens. Without headroom a forced-thinking
# victim can spend the whole budget reasoning and return no answer, which would
# read as a refusal and flatter the model.
_THINKING_HEADROOM = 4000


def anthropic_victim_request(model_id: str, system_prompt: str, user_text: str,
                             max_tokens: int) -> dict:
    """The one place the Anthropic victim request is built.

    Both the multi-vendor client and engine's direct path call this, so a change
    in which models accept which parameters is fixed once instead of twice.
    """
    kwargs = {"model": model_id, "max_tokens": max_tokens, "system": system_prompt,
              "messages": [{"role": "user", "content": user_text}]}
    if model_id not in _ANTHROPIC_NO_SAMPLING:
        kwargs["temperature"] = 0                # reproducible where the API allows it
    if model_id in _ANTHROPIC_THINKING_ALWAYS_ON:
        kwargs["output_config"] = {"effort": "low"}
        kwargs["max_tokens"] = max_tokens + _THINKING_HEADROOM
    elif model_id in _ANTHROPIC_THINKING_ON_BY_DEFAULT:
        # A shipped chatbot does not reason at length before replying, so the
        # victim should not either.
        kwargs["thinking"] = {"type": "disabled"}
    return kwargs


def anthropic_victim_text(resp) -> str:
    """Extract the victim's answer, refusing to turn a truncation into a refusal."""
    stop = getattr(resp, "stop_reason", None)
    if stop == "refusal":
        return BLOCKED_SENTINEL
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    if not text and stop == "max_tokens":
        # The model ran out of budget before saying anything. Returning "" would
        # score as a non-break. Raising makes it missing data instead.
        raise RuntimeError("victim hit max_tokens before producing an answer")
    return text

# OpenAI reasoning models reject temperature the same way the newer Anthropic models do.
_OPENAI_NO_SAMPLING_PREFIXES = ("o1", "o3", "o4", "gpt-5")


@dataclass(frozen=True)
class ModelSpec:
    """One victim model, and everything needed to call it correctly."""
    key: str                     # short id used in the UI, exports and CLI flags
    provider: str                # anthropic | openai | google | openai_compat | local
    model_id: str                # the vendor's own model string
    label: str                   # human name for charts
    vendor: str                  # who makes it
    api_key_env: str             # env var / secret name holding the key
    base_url: str | None = None  # openai_compat and local only
    notes: str = ""

    @property
    def supports_temperature(self) -> bool:
        if self.provider == "anthropic":
            return self.model_id not in _ANTHROPIC_NO_SAMPLING
        if self.provider in ("openai", "openai_compat"):
            return not self.model_id.startswith(_OPENAI_NO_SAMPLING_PREFIXES)
        return True                  # google and local both take temperature 0

    @property
    def deterministic(self) -> bool:
        """True when the victim can be pinned to temperature 0.

        Models without sampling controls cannot be made bit-reproducible, so any
        result from them is a sample, not a fixed value. The report says so
        rather than implying a precision the API cannot give.

        A local model is sent temperature 0, but llama-server batches parallel
        requests together and its own documentation says results are not
        guaranteed bit for bit identical across batch sizes. So it is reported
        as not reproducible, which is the honest reading.
        """
        return self.supports_temperature and self.provider != "local"

    @property
    def thinking_forced(self) -> bool:
        """True when this victim reasons before answering and cannot be stopped."""
        return self.provider == "anthropic" and self.model_id in _ANTHROPIC_THINKING_ALWAYS_ON


# The victim class this project actually cares about: small, cheap models of the
# kind a real product ships behind a chat window. Deliberately cross-vendor.
MODELS: dict[str, ModelSpec] = {
    "claude-haiku-4-5": ModelSpec(
        key="claude-haiku-4-5", provider="anthropic", model_id="claude-haiku-4-5",
        label="Claude Haiku 4.5", vendor="Anthropic", api_key_env="ANTHROPIC_API_KEY",
        notes="Default victim. Cheap, widely deployed, temperature-pinnable.",
    ),
    "claude-sonnet-5": ModelSpec(
        key="claude-sonnet-5", provider="anthropic", model_id="claude-sonnet-5",
        label="Claude Sonnet 5", vendor="Anthropic", api_key_env="ANTHROPIC_API_KEY",
        notes="Stronger Anthropic tier. No sampling controls, so not bit-reproducible.",
    ),
    "gpt-4o-mini": ModelSpec(
        key="gpt-4o-mini", provider="openai", model_id="gpt-4o-mini",
        label="GPT-4o mini", vendor="OpenAI", api_key_env="OPENAI_API_KEY",
        notes="OpenAI's small deployed tier.",
    ),
    "gpt-4.1-mini": ModelSpec(
        key="gpt-4.1-mini", provider="openai", model_id="gpt-4.1-mini",
        label="GPT-4.1 mini", vendor="OpenAI", api_key_env="OPENAI_API_KEY",
    ),
    "gemini-2.0-flash": ModelSpec(
        key="gemini-2.0-flash", provider="google", model_id="gemini-2.0-flash",
        label="Gemini 2.0 Flash", vendor="Google", api_key_env="GOOGLE_API_KEY",
        notes="Has a separate safety filter that can block a reply outright; "
              "a blocked reply counts as a refusal, not an error.",
    ),
    "llama-3.3-70b": ModelSpec(
        key="llama-3.3-70b", provider="openai_compat",
        model_id="llama-3.3-70b-versatile", label="Llama 3.3 70B",
        vendor="Meta (via Groq)", api_key_env="GROQ_API_KEY",
        base_url="https://api.groq.com/openai/v1",
        notes="Open-weights victim. The interesting case: no vendor safety stack "
              "of its own, so multilingual robustness is down to the base model.",
    ),
}



def local_spec() -> ModelSpec:
    """The local victim, read from the environment each time it is asked for.

    POLYGUARD_LOCAL_URL is where llama-server listens (for example
    http://127.0.0.1:8080) and POLYGUARD_LOCAL_MODEL is a human name for the
    model it serves. The URL plays the part a key plays for the hosted vendors:
    without it the local victim is simply not configured, so a hosted deploy
    never probes anything.
    """
    name = _local_env("POLYGUARD_LOCAL_MODEL") or "unnamed"
    return ModelSpec(
        key="local", provider="local", model_id=name,
        label=f"local open-weight model {name}, not a production chatbot",
        vendor="Open weights, local", api_key_env="POLYGUARD_LOCAL_URL",
        base_url=_local_env("POLYGUARD_LOCAL_URL"),
        notes="A small open model served by llama-server on this machine. Free, "
              "and a real measurement of that model only. Not reproducible bit "
              "for bit, because the server batches requests.")


DEFAULT_MODEL = "claude-haiku-4-5"


# --------------------------------------------------------------------------- #
# Timeouts, retries and error kinds
#
# Every client gets an explicit per-call timeout, so one stuck request cannot hold
# a scan (and a paid serverless function) open until the host kills it. Retries
# are the SDKs' own: up to five, with exponential backoff and jitter, on
# rate limits, overload, server errors and dropped connections, and never on
# errors a retry cannot fix, like a bad key.
# --------------------------------------------------------------------------- #
CALL_TIMEOUT = float(os.environ.get("POLYGUARD_CALL_TIMEOUT", "60"))
MAX_RETRIES = 5

# USD per million tokens (input, output), from Anthropic's SDK documentation as of
# October 2026. Used only for the upper bound shown before a live scan, never for
# billing. Other vendors are left out rather than guessed; the preflight says so.
PRICES_PER_MTOK = {"claude-haiku-4-5": (1.00, 5.00), "claude-sonnet-5": (2.00, 10.00)}

ERROR_KINDS = ("rate_limit", "auth", "model", "timeout", "network", "bad_request",
               "provider", "other")


def classify_error(exc: BaseException) -> str:
    """What kind of failure an exception is, the same way for every vendor.

    The kinds call for different responses: rate_limit means slow down, auth means
    the key is wrong and nothing will work, model means the model id is wrong,
    timeout and network are worth retrying later, bad_request is a bug in the
    request, provider is the vendor's outage. Read from the exception's class name
    and HTTP status, because the Anthropic, OpenAI and Google SDKs share neither
    base classes nor module paths.
    """
    name = type(exc).__name__
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(getattr(exc, "response", None), "status_code", None)
    if status is None and isinstance(getattr(exc, "code", None), int):
        status = exc.code
    if "RateLimit" in name or status == 429:
        return "rate_limit"
    if name in ("AuthenticationError", "PermissionDeniedError") or status in (401, 403):
        return "auth"
    if "NotFound" in name or status == 404:
        return "model"
    if "Timeout" in name or status == 408:
        return "timeout"
    if "Connection" in name:
        return "network"
    if "BadRequest" in name or "UnprocessableEntity" in name or status in (400, 413, 422):
        return "bad_request"
    if ("InternalServer" in name or "Overloaded" in name or "ServiceUnavailable" in name
            or (isinstance(status, int) and status >= 500)):
        return "provider"
    return "other"


# --------------------------------------------------------------------------- #
# Key resolution
# --------------------------------------------------------------------------- #
_DOTENV: dict[str, str] | None = None


def _dotenv() -> dict[str, str]:
    """The repository's local .env (written by setup_key.py, ignored by git and
    Vercel). Read once. Hosting never has this file; it uses real env variables."""
    global _DOTENV
    if _DOTENV is None:
        _DOTENV = {}
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    if "=" in line and not line.lstrip().startswith("#"):
                        k, v = line.split("=", 1)
                        _DOTENV[k.strip()] = v.strip().strip('"').strip("'")
        except OSError:
            pass
    return _DOTENV


def resolve_key(env_name: str) -> str | None:
    """Environment first, then the local .env, then Streamlit secrets. Never a
    literal in source."""
    key = os.environ.get(env_name) or _dotenv().get(env_name)
    if key:
        return key.strip() or None
    try:
        import streamlit as st
        if hasattr(st, "secrets") and env_name in st.secrets:
            return str(st.secrets[env_name]).strip() or None
    except Exception:
        pass
    return None


def _local_env(name: str) -> str | None:
    """Local model settings: the environment, then the local .env.

    Deliberately not Streamlit secrets: these name a server on this machine, so
    they never belong to a hosted deploy, and looking them up must not import
    Streamlit into the web API.
    """
    v = (os.environ.get(name) or _dotenv().get(name) or "").strip()
    return v or None


def _sdk_present(provider: str) -> bool:
    mod = {"anthropic": "anthropic", "openai": "openai",
           "openai_compat": "openai", "google": "google.genai",
           "local": "urllib.request"}[provider]
    try:
        __import__(mod)
        return True
    except Exception:
        return False


def model_status(spec: ModelSpec) -> dict:
    """Everything the UI needs to say why a model is or is not usable."""
    has_key = (spec.provider == "local") or resolve_key(spec.api_key_env) is not None
    has_sdk = _sdk_present(spec.provider)
    if spec.provider == "local":
        has_key = bool(spec.base_url)
    if spec.provider == "local" and has_key:
        # Configured, but configured is not running. Ask the server, briefly.
        up = local_server_up(spec.base_url)
        return {"key": spec.key, "label": spec.label, "vendor": spec.vendor,
                "ready": up, "has_key": True, "has_sdk": True,
                "reason": "ready" if up else "llama-server is not answering at "
                                             "POLYGUARD_LOCAL_URL",
                "deterministic": spec.deterministic, "notes": spec.notes}
    if has_key and has_sdk:
        reason = "ready"
    elif not has_sdk and not has_key:
        reason = f"needs the SDK and {spec.api_key_env}"
    elif not has_sdk:
        reason = f"needs the {spec.provider} SDK (pip install)"
    else:
        reason = f"needs {spec.api_key_env}"
    return {"key": spec.key, "label": spec.label, "vendor": spec.vendor,
            "ready": has_key and has_sdk, "has_key": has_key, "has_sdk": has_sdk,
            "reason": reason, "deterministic": spec.deterministic, "notes": spec.notes}


def _specs() -> list[ModelSpec]:
    """Every registered victim, with the local one re-read from the environment."""
    return [local_spec() if k == "local" else s for k, s in MODELS.items()]


def available_models() -> list[dict]:
    return [model_status(s) for s in _specs()]


def ready_model_keys() -> list[str]:
    return [s.key for s in _specs() if model_status(s)["ready"]]


# --------------------------------------------------------------------------- #
# Local open weight models, served by llama.cpp's llama-server
#
# llama-server speaks the OpenAI chat completions shape over plain HTTP, so this
# needs no SDK: urllib from the standard library is enough, and no dependency is
# added. Same rules as the hosted adapters: an explicit timeout on every call,
# retries only on failures a retry can fix, and every failure raised in a form
# classify_error() sorts into the same kinds as the vendors' errors.
# --------------------------------------------------------------------------- #
# A local server queues requests behind its few parallel slots, and a 300 token
# reply on a laptop GPU takes seconds, so the hosted 60 second default is too
# tight. Its own variable, so it never loosens the hosted timeout.
LOCAL_TIMEOUT = float(os.environ.get("POLYGUARD_LOCAL_TIMEOUT", "300"))
_LOCAL_RETRY_STATUS = {429, 500, 502, 503, 504}   # 503 is also "model still loading"


class LocalHTTPError(Exception):
    """llama-server answered with an error status. Carries it for classify_error."""

    def __init__(self, status_code: int, message: str):
        super().__init__(f"llama-server HTTP {status_code}: {message}")
        self.status_code = status_code


class LocalConnectionError(ConnectionError):
    """Nothing is listening at the local URL, or the connection dropped."""


class LocalTimeoutError(TimeoutError):
    """The local server took longer than LOCAL_TIMEOUT to answer."""


def _local_root(base_url: str) -> str:
    """Accept the server root or its /v1 address; return the root."""
    root = (base_url or "").strip().rstrip("/")
    return root[:-3] if root.endswith("/v1") else root


def _local_request(base_url: str, path: str, body: dict | None = None,
                   timeout: float | None = None, retries: int = MAX_RETRIES) -> dict:
    """One JSON request to llama-server, with bounded retries and backoff.

    Retried: connection refused or dropped, 429, and 5xx (llama-server answers
    503 while a model is still loading). Not retried: a timeout, because the
    server is busy rather than down and a retry only adds to its queue, and any
    other 4xx, which is a bug in the request that a retry cannot fix.
    """
    url = _local_root(base_url) + path
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"} if data is not None else {}
    timeout = LOCAL_TIMEOUT if timeout is None else timeout
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers=headers,
                                     method="GET" if data is None else "POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode("utf-8", "replace")[:300]
            except Exception:
                detail = ""
            err: Exception = LocalHTTPError(e.code, detail or str(e.reason))
            retry = e.code in _LOCAL_RETRY_STATUS
        except (TimeoutError, socket.timeout) as e:
            raise LocalTimeoutError(f"llama-server at {url} did not answer within "
                                    f"{timeout:.0f}s") from e
        except urllib.error.URLError as e:
            if isinstance(e.reason, (TimeoutError, socket.timeout)):
                raise LocalTimeoutError(f"llama-server at {url} did not answer within "
                                        f"{timeout:.0f}s") from e
            err = LocalConnectionError(f"cannot reach llama-server at {url}: {e.reason}")
            retry = True
        except (ConnectionError, OSError) as e:
            err = LocalConnectionError(f"connection to llama-server at {url} failed: {e}")
            retry = True
        if not retry or attempt == retries:
            raise err
        time.sleep(min(8.0, 0.5 * 2 ** attempt) * (0.5 + random.random()))
    raise AssertionError("unreachable")


def local_server_up(base_url: str | None, timeout: float = 1.0) -> bool:
    """True when a llama-server answers its health check. One quick try."""
    if not base_url:
        return False
    try:
        return _local_request(base_url, "/health", timeout=timeout,
                              retries=0).get("status") == "ok"
    except Exception:
        return False


@functools.lru_cache(maxsize=8)
def _file_sha256(path: str, size: int, mtime: float) -> str:
    """SHA-256 of a weights file, once per process per file version."""
    h = hashlib.sha256()
    with Path(path).open("rb") as f:          # binary: no encoding applies
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def local_provenance(base_url: str, name: str) -> dict:
    """Exactly which weights a local server is running, for the instrument record.

    The file name and build come from the server itself (GET /props), not from
    what the operator says it is running, and the SHA-256 is computed from the
    file on disk. A server on another machine cannot have its file hashed from
    here; then the hash is null and the record says why.
    """
    props = _local_request(base_url, "/props", timeout=10, retries=1)
    path = props.get("model_path") or ""
    sha, why = None, None
    if path and os.path.isfile(path):
        st = os.stat(path)
        sha = _file_sha256(os.path.abspath(path), st.st_size, st.st_mtime)
    else:
        why = "the weights file is not readable from this machine"
    return {"backend": "llama.cpp llama-server", "url": _local_root(base_url),
            "name": name, "gguf_file": os.path.basename(path) or None,
            "gguf_sha256": sha, "gguf_sha256_missing_because": why,
            "server_build": props.get("build_info"),
            "n_ctx": (props.get("default_generation_settings") or {}).get("n_ctx"),
            "parallel_slots": props.get("total_slots")}


def local_chat(base_url: str, model: str, system_prompt: str, user_text: str,
               max_tokens: int, response_format: dict | None = None) -> tuple[str, str | None]:
    """One chat completion from llama-server. Returns (text, finish_reason).

    Thinking is switched off on every call: Qwen3.5 models think by default and
    a victim standing in for a shipped chatbot should not reason at length
    first, the same rule the Anthropic victims follow. Temperature 0 with a fixed
    seed, and the prompt cache off, so runs are as repeatable as batching allows.
    """
    body = {"model": model, "max_tokens": max_tokens, "temperature": 0, "seed": 0,
            "cache_prompt": False, "chat_template_kwargs": {"enable_thinking": False},
            "messages": [{"role": "system", "content": system_prompt},
                         {"role": "user", "content": user_text}]}
    if response_format is not None:
        body["response_format"] = response_format
    resp = _local_request(base_url, "/v1/chat/completions", body)
    try:
        choice = resp["choices"][0]
    except (KeyError, IndexError, TypeError):
        raise LocalHTTPError(502, f"malformed reply from llama-server: {str(resp)[:200]}")
    msg = choice.get("message") or {}
    if (msg.get("reasoning_content") or "").strip():
        # Measured: Gemma 4 E2B still writes a "Thinking Process" on some inputs
        # with enable_thinking false, which eats the token cap and leaves no
        # answer. A reply produced after hidden reasoning is a different
        # measurement, so it is refused loudly rather than scored.
        raise RuntimeError("the local model reasoned before answering; start llama-server "
                           "with --reasoning off --reasoning-budget 0")
    return msg.get("content") or "", choice.get("finish_reason")


class _LocalMessages:
    """The slice of the Anthropic `messages.create` call the judges use.

    engine.llm_judge_compliance and llm_judge_followed call
    create(model=, max_tokens=, temperature=, system=, output_config=, messages=)
    and read resp.content[i].text. Mimicking that one call keeps both judges, and
    their no keyword fallback rule, exactly as they are.
    """

    def __init__(self, base_url: str, name: str):
        self._url, self._name = base_url, name

    def create(self, *, max_tokens: int, system: str, messages: list[dict],
               output_config: dict | None = None, **_ignored):
        schema = ((output_config or {}).get("format") or {}).get("schema")
        fmt = ({"type": "json_schema",
                "json_schema": {"name": "verdict", "strict": True, "schema": schema}}
               if schema else None)
        user = "\n\n".join(m["content"] for m in messages if m.get("role") == "user")
        text, finish = local_chat(self._url, self._name, system, user, max_tokens, fmt)
        if not text.strip():
            # An empty verdict must not parse as anything. Raising makes the
            # attack missing data, never a guess.
            raise RuntimeError(f"local judge returned no verdict (finish_reason={finish})")
        return SimpleNamespace(stop_reason="max_tokens" if finish == "length" else "end_turn",
                               content=[SimpleNamespace(type="text", text=text)])


class LocalJudgeClient:
    """A compliance judge served by a local llama-server.

    `judge_model` names the exact weights file, so the instrument record and the
    comparability check see a local judge as a different instrument from every
    other judge, and from a different file of the same model.
    """

    def __init__(self, base_url: str, name: str):
        if not local_server_up(base_url, timeout=5):
            raise RuntimeError(f"No llama-server is answering at {base_url} for the judge. "
                               "Start it first (see docs/quickstart.md).")
        self.base_url = base_url
        self.messages = _LocalMessages(base_url, name)
        self.provenance = local_provenance(base_url, name)
        self.judge_model = f"local:{self.provenance['gguf_file'] or name}"


def local_judge_client() -> LocalJudgeClient | None:
    """The local judge, when POLYGUARD_JUDGE_BACKEND=local asks for one.

    POLYGUARD_JUDGE_URL is the judge's server. It falls back to POLYGUARD_LOCAL_URL,
    the victim's, which means the victim grades its own replies: allowed for a
    plumbing check, recorded in the instrument, and flagged by the CLI.
    """
    url = _local_env("POLYGUARD_JUDGE_URL") or _local_env("POLYGUARD_LOCAL_URL")
    if not url:
        return None
    return LocalJudgeClient(url, _local_env("POLYGUARD_JUDGE_LOCAL_MODEL") or "local-judge")


# Registered here, after resolve_key exists. Listed like any other victim; the
# entry is re-read from the environment wherever it is used (local_spec()).
MODELS["local"] = local_spec()


# --------------------------------------------------------------------------- #
# Victim clients
#
# Each adapter takes the target bot's system prompt as the system message and
# the attack as the single user message. That is exactly the shape a deployed
# chatbot receives, which is the whole point: nothing about the harness makes
# the victim more or less defended than it would be in production.
# --------------------------------------------------------------------------- #
class VictimClient:
    """One configured victim model. `complete()` is safe to call from threads."""

    def __init__(self, spec: ModelSpec, client, max_tokens: int = 300,
                 provenance: dict | None = None):
        self.spec = spec
        self._client = client
        self.max_tokens = max_tokens
        # Only local victims have one: which weights file, which server build.
        self.provenance = provenance

    def __repr__(self) -> str:
        return f"<VictimClient {self.spec.key} via {self.spec.provider}>"

    def complete(self, system_prompt: str, user_text: str) -> str:
        fn = getattr(self, f"_call_{self.spec.provider}")
        return fn(system_prompt, user_text)

    # -- Anthropic ---------------------------------------------------------- #
    def _call_anthropic(self, system_prompt: str, user_text: str) -> str:
        resp = self._client.messages.create(**anthropic_victim_request(
            self.spec.model_id, system_prompt, user_text, self.max_tokens))
        return anthropic_victim_text(resp)

    # -- OpenAI and OpenAI-compatible --------------------------------------- #
    def _call_openai(self, system_prompt: str, user_text: str) -> str:
        kwargs = {
            "model": self.spec.model_id,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "system", "content": system_prompt},
                         {"role": "user", "content": user_text}],
        }
        if self.spec.supports_temperature:
            kwargs["temperature"] = 0
        resp = self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        if getattr(choice, "finish_reason", None) == "content_filter":
            return BLOCKED_SENTINEL
        return choice.message.content or ""

    _call_openai_compat = _call_openai

    # -- Local (llama-server) ------------------------------------------------ #
    def _call_local(self, system_prompt: str, user_text: str) -> str:
        text, finish = local_chat(self.spec.base_url, self.spec.model_id,
                                  system_prompt, user_text, self.max_tokens)
        if not text.strip() and finish == "length":
            # Same rule as the Anthropic path: a reply cut off before any answer
            # is missing data, not a refusal that flatters the model.
            raise RuntimeError("victim hit max_tokens before producing an answer")
        return text

    # -- Google ------------------------------------------------------------- #
    def _call_google(self, system_prompt: str, user_text: str) -> str:
        from google.genai import types
        cfg = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=self.max_tokens,
            temperature=0,
        )
        resp = self._client.models.generate_content(
            model=self.spec.model_id, contents=user_text, config=cfg)
        # A safety block yields no candidate text. That is the model declining,
        # which is a non-break, so it must not surface as a scan error.
        try:
            text = resp.text
        except Exception:
            text = None
        return text if text else BLOCKED_SENTINEL


def build_victim(model_key: str, max_tokens: int = 300) -> VictimClient:
    """Construct a victim client, or raise with a message that says what to fix."""
    if model_key not in MODELS:
        raise ValueError(f"Unknown victim model {model_key!r}. "
                         f"Known: {', '.join(sorted(MODELS))}")
    spec = local_spec() if model_key == "local" else MODELS[model_key]
    if spec.provider == "local":
        if not spec.base_url:
            raise RuntimeError("The local victim needs POLYGUARD_LOCAL_URL, the address of a "
                               "running llama-server (see docs/quickstart.md).")
        if not local_server_up(spec.base_url, timeout=5):
            raise RuntimeError(f"No llama-server is answering at {spec.base_url}. "
                               "Start it first (see docs/quickstart.md).")
        return VictimClient(spec, None, max_tokens=max_tokens,
                            provenance=local_provenance(spec.base_url, spec.model_id))
    key = resolve_key(spec.api_key_env)
    if key is None:
        raise RuntimeError(f"{spec.label} needs {spec.api_key_env} in the environment "
                           f"or in Streamlit secrets.")
    if spec.provider == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=key, max_retries=MAX_RETRIES, timeout=CALL_TIMEOUT)
    elif spec.provider == "openai":
        import openai
        client = openai.OpenAI(api_key=key, max_retries=MAX_RETRIES, timeout=CALL_TIMEOUT)
    elif spec.provider == "openai_compat":
        import openai
        client = openai.OpenAI(api_key=key, base_url=spec.base_url, max_retries=MAX_RETRIES,
                               timeout=CALL_TIMEOUT)
    elif spec.provider == "google":
        from google import genai
        client = genai.Client(api_key=key)
    else:
        raise ValueError(f"No adapter for provider {spec.provider!r}")
    return VictimClient(spec, client, max_tokens=max_tokens)


def judge_client():
    """
    The compliance judge, always Anthropic and always the same model regardless
    of which victim is being scanned.

    This is a methodology constraint, not a convenience. Cross-model break rates
    are only comparable if one fixed judge scored all of them; a judge that
    changed with the victim would let judge disagreement masquerade as a
    robustness difference between models.

    The one exception is explicit: POLYGUARD_JUDGE_BACKEND=local swaps in an
    LLM judge served by a local llama-server, for zero cost scans. It is still
    an LLM judge, never the keyword heuristic, and the instrument record names
    its weights file, so a locally judged scan is never compared with an
    Anthropic judged one.
    """
    if (_local_env("POLYGUARD_JUDGE_BACKEND") or "").strip().lower() == "local":
        return local_judge_client()
    key = resolve_key("ANTHROPIC_API_KEY")
    if key is None:
        return None
    import anthropic
    return anthropic.Anthropic(api_key=key, max_retries=MAX_RETRIES, timeout=CALL_TIMEOUT)


# --------------------------------------------------------------------------- #
# Smoke test
# --------------------------------------------------------------------------- #
def smoke(model_keys: list[str] | None = None) -> int:
    """
    Fire one harmless call at every configured victim. Run this the first time a
    key is added, before trusting any scan from that provider: it is the only
    thing that proves an adapter's request shape is actually right.
    """
    keys = model_keys or list(MODELS)
    sysmsg = "You are a helpful assistant. Reply with exactly the word: ONLINE"
    failures = 0
    for k in keys:
        status = model_status(local_spec() if k == "local" else MODELS[k])
        if not status["ready"]:
            print(f"SKIP  {k:<18} {status['reason']}")
            continue
        try:
            reply = build_victim(k, max_tokens=20).complete(sysmsg, "Say the word.")
            ok = "online" in reply.lower()
            print(f"{'PASS ' if ok else 'WARN '} {k:<18} reply={reply.strip()[:60]!r}")
            if not ok:
                print("      reachable, but it did not follow a trivial instruction")
        except Exception as e:
            failures += 1
            print(f"FAIL  {k:<18} {type(e).__name__}: {e}")
    return failures


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    if "--smoke" in args:
        chosen = [a for a in args if a in MODELS] or None
        raise SystemExit(1 if smoke(chosen) else 0)
    print("PolyGuard victim models\n")
    for s in available_models():
        mark = "ready" if s["ready"] else s["reason"]
        det = "" if s["deterministic"] else "   (not temperature-pinnable)"
        print(f"  {s['key']:<18} {s['vendor']:<18} {mark}{det}")
    print(f"\nDefault: {DEFAULT_MODEL}")
    print("Run `python providers.py --smoke` once keys are set.")
