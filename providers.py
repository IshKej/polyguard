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

STATUS: the Anthropic adapter is exercised by the test suite. The OpenAI,
Google and OpenAI-compatible adapters are written against each vendor's
documented request shape but have NOT been run against a live key yet. Run
`python providers.py --smoke` once keys exist, before trusting any number that
comes out of them.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

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
    provider: str                # anthropic | openai | google | openai_compat
    model_id: str                # the vendor's own model string
    label: str                   # human name for charts
    vendor: str                  # who makes it
    api_key_env: str             # env var / secret name holding the key
    base_url: str | None = None  # openai_compat only
    notes: str = ""

    @property
    def supports_temperature(self) -> bool:
        if self.provider == "anthropic":
            return self.model_id not in _ANTHROPIC_NO_SAMPLING
        if self.provider in ("openai", "openai_compat"):
            return not self.model_id.startswith(_OPENAI_NO_SAMPLING_PREFIXES)
        return True

    @property
    def deterministic(self) -> bool:
        """True when the victim can be pinned to temperature 0.

        Models without sampling controls cannot be made bit-reproducible, so any
        result from them is a sample, not a fixed value. The report says so
        rather than implying a precision the API cannot give.
        """
        return self.supports_temperature

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


def _sdk_present(provider: str) -> bool:
    mod = {"anthropic": "anthropic", "openai": "openai",
           "openai_compat": "openai", "google": "google.genai"}[provider]
    try:
        __import__(mod)
        return True
    except Exception:
        return False


def model_status(spec: ModelSpec) -> dict:
    """Everything the UI needs to say why a model is or is not usable."""
    has_key = resolve_key(spec.api_key_env) is not None
    has_sdk = _sdk_present(spec.provider)
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


def available_models() -> list[dict]:
    return [model_status(s) for s in MODELS.values()]


def ready_model_keys() -> list[str]:
    return [s.key for s in MODELS.values() if model_status(s)["ready"]]


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

    def __init__(self, spec: ModelSpec, client, max_tokens: int = 300):
        self.spec = spec
        self._client = client
        self.max_tokens = max_tokens

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
    spec = MODELS[model_key]
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
    """
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
        status = model_status(MODELS[k])
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
