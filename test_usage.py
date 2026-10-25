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


# --- why each reply stopped, and a cost split that must add up (2026-10-25) ------
log2 = providers.USAGE.start(tmp / "stops.usage.jsonl")


class StopMessages(FakeMessages):
    """Replies that end for different reasons: normal, cut at the cap, the provider's
    own refusal stop with no text."""

    def __init__(self, stops):
        super().__init__()
        self.stops = list(stops)

    def create(self, **kw):
        stop, text = self.stops.pop(0)
        return SimpleNamespace(stop_reason=stop,
                               usage=SimpleNamespace(input_tokens=1000, output_tokens=100,
                                                     cache_creation_input_tokens=None,
                                                     cache_read_input_tokens=None),
                               content=[SimpleNamespace(type="text", text=text)] if text else [])


v2 = providers.MeteredAnthropic(SimpleNamespace(messages=StopMessages(
    [("end_turn", "Sure."), ("max_tokens", "A long answer that was cut"), ("refusal", "")])), "victim")
for _ in range(3):
    v2.messages.create(model="claude-sonnet-5", max_tokens=300, messages=[])
j2 = providers.MeteredAnthropic(SimpleNamespace(messages=StopMessages([("max_tokens", "")])), "judge")
j2.messages.create(model="claude-haiku-4-5", max_tokens=50, messages=[])
recs = [json.loads(x) for x in log2.read_text(encoding="utf-8").splitlines()]
check("each call records why it stopped and whether its text was empty",
      [r.get("stop_reason") for r in recs] == ["end_turn", "max_tokens", "refusal", "max_tokens"]
      and [r["empty"] for r in recs] == [False, False, True, True])
tv = {t["role"]: t for t in providers.USAGE.totals()}
check("truncations, refusals and empty replies are counted per role, separately",
      (tv["victim"]["truncated"], tv["victim"]["refused"], tv["victim"]["empty"]) == (1, 1, 1)
      and (tv["judge"]["truncated"], tv["judge"]["refused"], tv["judge"]["empty"]) == (1, 0, 1))

real_request2 = providers._local_request
providers._local_request = lambda url, path, body=None, **k: {
    "choices": [{"message": {"content": "cut"}, "finish_reason": "length"}],
    "usage": {"prompt_tokens": 9, "completion_tokens": 300}}
try:
    providers.local_chat("http://127.0.0.1:8080", "qwen3.5-4b", "sys", "hi", 300)
finally:
    providers._local_request = real_request2
check("a local reply cut at its cap is a truncation too",
      json.loads(log2.read_text(encoding="utf-8").splitlines()[-1])["stop_reason"] == "length"
      and {t["provider"]: t for t in providers.USAGE.totals()}["local"]["truncated"] == 1)

summ = providers.usage_summary(list(providers.USAGE.records))
expect_sonnet = 3 * (1000 * 2.00 + 100 * 10.00) / 1_000_000
expect_haiku = (1000 * 1.00 + 100 * 5.00) / 1_000_000
check("cost per role comes from the tokens at the rate card, and a local model costs nothing",
      abs(summ["roles"]["victim"]["cost_usd"] - expect_sonnet) < 1e-12
      and abs(summ["roles"]["judge"]["cost_usd"] - expect_haiku) < 1e-12)
check("the role split adds up to the total, which is summed separately from every call",
      abs(summ["split_sum_usd"] - summ["total_cost_usd"]) < 1e-12
      and abs(summ["total_cost_usd"] - (expect_sonnet + expect_haiku)) < 1e-12 and summ["calls"] == 5)

ext = [{"role": "victim", "cost_usd": 0.5, "stop_reason": "end_turn"},
       {"role": "judge", "cost_usd": 0.25, "stop_reason": "max_tokens"},
       {"role": "?", "cost_usd": 0.125, "stop_reason": "end_turn"},
       {"cost_usd": 0.0625, "stop_reason": "refusal", "empty": True},
       {"role": "victim", "model": "some-unpriced-model", "provider": "anthropic",
        "input_tokens": 5, "output_tokens": 5}]
se = providers.usage_summary(ext)
check("a log's own billed cost is used as recorded, and its total matches the split",
      abs(se["total_cost_usd"] - 0.9375) < 1e-12 and abs(se["split_sum_usd"] - 0.9375) < 1e-12)
check("calls with no role, or the placeholder '?', are reported as unlabelled, never guessed into a role",
      se["roles"]["unlabelled"]["calls"] == 2 and abs(se["roles"]["unlabelled"]["cost_usd"] - 0.1875) < 1e-12
      and se["roles"]["unlabelled"]["original_roles"] == ["?", None])
check("an unpriced call is counted as a call with unknown cost, not as zero",
      se["roles"]["victim"]["calls"] == 2 and se["roles"]["victim"]["calls_without_cost"] == 1)
check("the unlabelled truncation and refusal counts stay apart from the labelled ones",
      se["roles"]["unlabelled"]["refused"] == 1 and se["roles"]["unlabelled"]["empty"] == 1
      and se["roles"]["judge"]["truncated"] == 1)


class Drifting(dict):
    """A record whose cost reads differently each time it is asked: the split and the
    separately summed total then disagree, which must fail loudly."""

    def __init__(self):
        super().__init__(role="victim")
        self.reads = 0

    def get(self, key, default=None):
        if key == "cost_usd":
            self.reads += 1
            return 0.1 * self.reads
        return super().get(key, default)


try:
    providers.usage_summary([Drifting()])
    check("a split that does not add up to the total fails instead of printing", False)
except providers.CostSplitError:
    check("a split that does not add up to the total fails instead of printing", True)

import contextlib  # noqa: E402
import io  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()) as buf:
    cli.print_usage()
check("the usage printout gives the stop counts and the cost split that adds up to its total",
      "(1 truncated, 1 refused, 1 empty)" in buf.getvalue() and "cost at the rate card: $" in buf.getvalue())
providers.USAGE.path = None

print(f"\n{passed}/{passed + failures} usage logging checks passed")
sys.exit(1 if failures else 0)
