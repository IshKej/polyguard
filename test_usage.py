"""
Token usage logging: every API response's token counts reach a durable log, for the
victim and the judge, on every provider, with no network call. Run: python test_usage.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import providers

failures = 0
passed = 0


def check(name: str, ok: bool) -> None:
    global failures, passed
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if ok:
        passed += 1
    else:
        failures += 1


tmp = Path(tempfile.mkdtemp())
log = providers.USAGE.start(tmp / "nested" / "run.usage.jsonl")
check("starting the log creates its folder", log.parent.is_dir())


# --- Anthropic: the wrapped client records what each response reports ---------
class FakeMessages:
    def __init__(self):
        self.calls = 0

    def create(self, **kw):
        self.calls += 1
        return SimpleNamespace(usage=SimpleNamespace(input_tokens=120, output_tokens=30,
                                                     cache_creation_input_tokens=None,
                                                     cache_read_input_tokens=None),
                               content=[SimpleNamespace(type="text", text="No.")])


class FakeAnthropic:
    def __init__(self):
        self.messages = FakeMessages()
        self.api_key = "not-a-key"


inner = FakeAnthropic()
victim = providers.MeteredAnthropic(inner, "victim")
judge = providers.MeteredAnthropic(FakeAnthropic(), "judge")
r = victim.messages.create(model="claude-sonnet-5", max_tokens=10, messages=[])
check("the wrapped client returns the response unchanged", r.content[0].text == "No.")
check("everything else on the client passes through", victim.api_key == "not-a-key")
judge.messages.create(model="claude-haiku-4-5", max_tokens=10, messages=[])
judge.messages.create(model="claude-haiku-4-5", max_tokens=10, messages=[])

lines = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
check("one line per call is written to disk as it happens", len(lines) == 3)
check("each line names role, provider, model and both token counts",
      lines[0]["role"] == "victim" and lines[0]["provider"] == "anthropic"
      and lines[0]["model"] == "claude-sonnet-5"
      and lines[0]["input_tokens"] == 120 and lines[0]["output_tokens"] == 30)
check("fields a response did not carry are left out, not written as null",
      "cache_read_input_tokens" not in lines[0])

tot = {(t["role"], t["model"]): t for t in providers.USAGE.totals()}
check("totals add up per role and model",
      tot[("judge", "claude-haiku-4-5")]["calls"] == 2
      and tot[("judge", "claude-haiku-4-5")]["input_tokens"] == 240
      and tot[("victim", "claude-sonnet-5")]["output_tokens"] == 30)


# --- a response with no usage counts as a call with unknown tokens -------------
class NoUsage(FakeMessages):
    def create(self, **kw):
        return SimpleNamespace(content=[])


bare = providers.MeteredAnthropic(SimpleNamespace(messages=NoUsage()), "judge")
bare.messages.create(model="claude-haiku-4-5", max_tokens=10, messages=[])
t2 = {(t["role"], t["model"]): t for t in providers.USAGE.totals()}
check("a response without usage is counted as a call, never as zero tokens",
      t2[("judge", "claude-haiku-4-5")]["calls"] == 3
      and t2[("judge", "claude-haiku-4-5")]["calls_without_usage"] == 1
      and t2[("judge", "claude-haiku-4-5")]["input_tokens"] == 240)


# --- local llama-server: usage comes from the OpenAI-shaped reply --------------
real_request = providers._local_request
providers._local_request = lambda url, path, body=None, **k: {
    "choices": [{"message": {"content": "Held."}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 50, "completion_tokens": 4}}
try:
    providers.local_chat("http://127.0.0.1:8080", "qwen3.5-4b", "sys", "hi", 20)
    providers._LocalMessages("http://127.0.0.1:8081", "gemma").create(
        max_tokens=20, system="judge", messages=[{"role": "user", "content": "reply"}])
finally:
    providers._local_request = real_request
roles = {(t["role"], t["provider"]): t for t in providers.USAGE.totals()}
check("local victim calls are recorded as victim", roles[("victim", "local")]["input_tokens"] == 50)
check("local judge calls are recorded as judge", roles[("judge", "local")]["output_tokens"] == 4)


# --- the CLI puts the log beside the results, never in a temporary folder ------
import cli  # noqa: E402

args = SimpleNamespace(bundle=str(tmp / "bundle"), out=None)
check("with --bundle the log is usage.jsonl inside the bundle",
      cli.start_usage_log(args, "scan") == tmp / "bundle" / "usage.jsonl")
args = SimpleNamespace(bundle=None, out=str(tmp / "scan.json"))
check("with --out the log sits beside it", cli.start_usage_log(args, "scan") == tmp / "scan.usage.jsonl")
args = SimpleNamespace(bundle=None, out=None)
p = cli.start_usage_log(args, "scan")
check("with neither, it goes under results/usage/", p.parts[:2] == ("results", "usage"))
try:
    p.parent.rmdir() if not any(p.parent.iterdir()) else None
except OSError:
    pass

print(f"\n{passed}/{passed + failures} usage logging checks passed")
sys.exit(1 if failures else 0)
