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
    "claude-opus-5", "claude-opus-4-8", "claude-opus-4-7",
    "claude-sonnet-5", "claude-fable-5", "claude-fable-5-1",
    "claude-mythos-5", "claude-mythos-5-1",
}

# Anthropic models where thinking runs unless explicitly disabled. A victim
# standing in for a shipped chatbot should not be reasoning at length before it
# answers, so these get thinking switched off for both fairness and cost.
_ANTHROPIC_THINKING_ON_BY_DEFAULT = {
    "claude-opus-5", "claude-sonnet-5", "claude-fable-5", "claude-fable-5-1",
    "claude-mythos-5", "claude-mythos-5-1",
}

# OpenAI reasoning models reject temperature the same way the newer Claudes do.
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
# Key resolution
# --------------------------------------------------------------------------- #
def resolve_key(env_name: str) -> str | None:
    """Environment first, then Streamlit secrets. Never a literal in source."""
    key = os.environ.get(env_name)
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
        kwargs = {
            "model": self.spec.model_id,
            "max_tokens": self.max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_text}],
        }
        if self.spec.supports_temperature:
            kwargs["temperature"] = 0            # reproducible where the API allows it
        if self.spec.model_id in _ANTHROPIC_THINKING_ON_BY_DEFAULT:
            # A shipped chatbot does not reason at length before replying, so the
            # victim should not either. Leaving thinking on would test a system
            # the user is not actually deploying.
            kwargs["thinking"] = {"type": "disabled"}
        resp = self._client.messages.create(**kwargs)
        if getattr(resp, "stop_reason", None) == "refusal":
            return BLOCKED_SENTINEL
        return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")

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
        client = anthropic.Anthropic(api_key=key, max_retries=5)
    elif spec.provider == "openai":
        import openai
        client = openai.OpenAI(api_key=key, max_retries=5)
    elif spec.provider == "openai_compat":
        import openai
        client = openai.OpenAI(api_key=key, base_url=spec.base_url, max_retries=5)
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
    return anthropic.Anthropic(api_key=key, max_retries=5)


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
