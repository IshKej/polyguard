"""
The Anthropic SDK gate fails closed: a live call never goes out on an SDK that is
not the locked one, or that alters the judge's or a victim's request. No network
call is made and no key is used. Run: python test_sdk_gate.py
"""
from __future__ import annotations

import contextlib
import io
import os
import socket
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import providers
import sdk_gate

failures = 0
passed = 0


def check(name: str, ok: bool) -> None:
    global failures, passed
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if ok:
        passed += 1
    else:
        failures += 1


def raises(fn, kind=Exception) -> bool:
    try:
        fn()
    except kind:
        return True
    except Exception:
        return False
    return False


# --- the pin ------------------------------------------------------------------
pins = sdk_gate.lock_pins()
check("requirements.lock and uv.lock both pin anthropic, to the same version",
      set(pins) == {"requirements.lock", "uv.lock"} and len(set(pins.values())) == 1)
check("the pin is a 0.x release, inside requirements.txt's anthropic>=0.40,<1",
      sdk_gate.pinned_version().split(".")[0] == "0")

# --- the SDK this checkout installs passes, through the real SDK, on loopback only
real_connect = socket.socket.connect
outside: list = []


def loopback_only(self, address):
    host = address[0] if isinstance(address, tuple) else address
    if host not in ("127.0.0.1", "::1", "localhost"):
        outside.append(address)
        raise OSError("test: a connection off this machine was attempted")
    return real_connect(self, address)


socket.socket.connect = loopback_only
try:
    real = sdk_gate.contract_problems()
finally:
    socket.socket.connect = real_connect
check(f"the installed anthropic {sdk_gate.installed_version()} passes the request contract",
      real == [])
check("the contract connects only to 127.0.0.1", outside == [])
ok, detail = sdk_gate.status()
check("the installed SDK is the locked one, so the gate opens", ok)

log = providers.USAGE.start(Path(tempfile.mkdtemp()) / "run.usage.jsonl")
sdk_gate.contract_problems()
check("contract calls never reach a run's usage log", not log.exists() and providers.USAGE.records == [])
providers.USAGE.path = None


# --- an SDK that refuses temperature, as 2.x does, is caught before any paid call
class _FakeSDK:
    """Wraps the real SDK and changes one thing about messages.create."""

    def __init__(self, change):
        import anthropic
        self._real, self._change = anthropic, change

    def Anthropic(self, **kw):
        client = self._real.Anthropic(**kw)
        inner, change = client.messages.create, self._change
        return SimpleNamespace(messages=SimpleNamespace(create=lambda **k: change(inner, k)))


def no_temperature(inner, kw):
    if "temperature" in kw:
        raise TypeError("Messages.create() got an unexpected keyword argument 'temperature'")
    return inner(**kw)


p = sdk_gate.contract_problems(_FakeSDK(no_temperature))
check("an SDK that refuses temperature fails both judge requests",
      any(x.startswith("judge (attack verdict)") and "temperature" in x for x in p)
      and any(x.startswith("judge (control verdict)") for x in p))
check("...while a victim sent without temperature still passes, which is why the "
      "victim calls alone never showed it",
      not any("claude-sonnet-5" in x for x in p))


def drop_output_config(inner, kw):
    return inner(**{k: v for k, v in kw.items() if k != "output_config"})


p = sdk_gate.contract_problems(_FakeSDK(drop_output_config))
check("an SDK that silently drops output_config is caught from the body that arrives",
      any("`output_config` was sent but did not arrive" in x for x in p))


def misread_reply(inner, kw):
    inner(**kw)
    return SimpleNamespace(content=[SimpleNamespace(type="text", text='{"outcome": "complied"}')],
                           stop_reason="end_turn")


p = sdk_gate.contract_problems(_FakeSDK(misread_reply))
check("an SDK that hands back a different reply than the server sent is caught",
      any("judge (attack verdict): the reply was read as 'complied'" in x for x in p))


def never_sends(inner, kw):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=sdk_gate.CONTRACT_REPLY)],
                           stop_reason="end_turn")


p = sdk_gate.contract_problems(_FakeSDK(never_sends))
check("an SDK that answers without sending anything is caught",
      any("no readable request reached the server" in x for x in p))


# --- fail closed: every way the gate can be shut ------------------------------
saved = {"installed": sdk_gate.installed_version, "pinned": sdk_gate.pinned_version,
         "contract": sdk_gate._installed_contract, "dotenv": providers._DOTENV,
         "env": {k: os.environ.get(k) for k in ("ANTHROPIC_API_KEY", "POLYGUARD_JUDGE_BACKEND",
                                                "POLYGUARD_LOCAL_URL", "POLYGUARD_JUDGE_URL")}}
providers._DOTENV = {}                       # a developer's .env must not leak in
for k in saved["env"]:
    os.environ.pop(k, None)
os.environ["ANTHROPIC_API_KEY"] = "not-a-real-key"
try:
    sdk_gate.installed_version = lambda: "2.3.0"
    ok, detail = sdk_gate.status()
    check("a different installed version shuts the gate and names both versions",
          not ok and "2.3.0" in detail and sdk_gate.pinned_version() in detail)
    check("the judge client is refused with SDKMismatch, not built",
          raises(providers.judge_client, sdk_gate.SDKMismatch))
    check("an Anthropic victim is refused with SDKMismatch, not built",
          raises(lambda: providers.build_victim("claude-sonnet-5"), sdk_gate.SDKMismatch))

    import cli
    tmp = Path(tempfile.mkdtemp())
    (tmp / "p.txt").write_text("You are a support bot.", encoding="utf-8")
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        code = cli.main(["scan", "--prompt", str(tmp / "p.txt"), "--model", "claude-sonnet-5",
                         "--langs", "en", "--out", str(tmp / "s.json"), "--quiet"])
    check("cli scan exits 2 before any call and says why",
          code == 2 and "No API call was made" in err.getvalue() and not (tmp / "s.json").exists())
    providers.USAGE.path = None

    try:
        from api import server
        check("the API reports live_reason sdk_mismatch instead of no_key",
              server._live_state(None) == (False, "sdk_mismatch"))
    except ImportError:
        print("  [SKIP] API check: fastapi is not installed here")

    os.environ["POLYGUARD_JUDGE_BACKEND"] = "local"
    check("a local judge does not use the Anthropic SDK, so the gate does not apply to it",
          not raises(providers.judge_client, sdk_gate.SDKMismatch))
    os.environ.pop("POLYGUARD_JUDGE_BACKEND")

    sdk_gate.installed_version = saved["installed"]
    sdk_gate._installed_contract = lambda: ("judge (attack verdict): example",)
    check("the locked version with a failing contract still shuts the gate",
          not sdk_gate.status()[0] and raises(sdk_gate.require, sdk_gate.SDKMismatch))

    sdk_gate._installed_contract = saved["contract"]
    sdk_gate.pinned_version = lambda: None
    check("with no pin to check against, the gate stays shut", not sdk_gate.status()[0])

    sdk_gate.pinned_version = saved["pinned"]
    sdk_gate.installed_version = lambda: None
    check("with no SDK installed, the gate stays shut", not sdk_gate.status()[0])
finally:
    sdk_gate.installed_version = saved["installed"]
    sdk_gate.pinned_version = saved["pinned"]
    sdk_gate._installed_contract = saved["contract"]
    providers._DOTENV = saved["dotenv"]
    for k, v in saved["env"].items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

print(f"\n{passed}/{passed + failures} SDK gate checks passed")
sys.exit(1 if failures else 0)
