"""
The Anthropic SDK gate: no live call goes out on an SDK this project has not checked.

A run on an SDK from outside the lock (a 2.x release, which no longer takes
`temperature`) once sent every victim request and had every judge request refused,
and the failure only showed after paid calls had been made. This catches that
before any call, with two checks that must both hold:

  VERSION   the installed `anthropic` is the version requirements.lock pins
  CONTRACT  the project's own Anthropic requests (the judge's temperature and
            output_config, and every Anthropic victim in providers.MODELS) go
            through the installed SDK to a throwaway server on 127.0.0.1, and the
            body that arrives carries every parameter that was sent

If either fails, providers refuses to build an Anthropic client, the CLI exits
before its first call, preflight fails, and the API reports live_reason
"sdk_mismatch". The contract never leaves this machine and costs nothing.

Upgrading on purpose: change the pin in requirements.lock and uv.lock, install the
lock, and run `python test_sdk_gate.py`. The new version is accepted only when the
contract passes on it.
"""
from __future__ import annotations

import functools
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import metadata
from pathlib import Path

HERE = Path(__file__).parent

# What the throwaway server answers to every request. It parses as an attack
# verdict, as a control verdict and as plain victim text, so one reply serves all.
CONTRACT_REPLY = '{"outcome": "held", "complied": false}'


class SDKMismatch(RuntimeError):
    """The installed anthropic SDK is not one this project has checked."""


def lock_pins() -> dict[str, str]:
    """The anthropic version each lock file pins, by file name."""
    pins = {}
    for name, pattern in (("requirements.lock", r"^anthropic==([^\s\\]+)"),
                          ("uv.lock", r'^name = "anthropic"\r?\nversion = "([^"]+)"')):
        path = HERE / name
        if path.exists():
            m = re.search(pattern, path.read_text(encoding="utf-8"), re.M)
            if m:
                pins[name] = m.group(1)
    return pins


def pinned_version() -> str | None:
    """requirements.lock's pin, or uv.lock's where the deploy carries only that."""
    pins = lock_pins()
    return pins.get("requirements.lock") or pins.get("uv.lock")


def installed_version() -> str | None:
    try:
        return metadata.version("anthropic")
    except metadata.PackageNotFoundError:
        return None


class _Recorder(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("content-length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            body = None
        self.server.bodies.append(body)
        out = json.dumps({
            "id": "msg_contract", "type": "message", "role": "assistant", "model": "contract",
            "content": [{"type": "text", "text": CONTRACT_REPLY}],
            "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1}}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *args):
        pass


class _Spy:
    """Keeps the keyword arguments each request was built with, to compare with
    what arrived. Deliberately not MeteredAnthropic: contract calls must never
    reach a run's usage log."""

    def __init__(self, client, sent: list):
        self.messages = self
        self._client = client
        self._sent = sent

    def create(self, **kwargs):
        self._sent.append(kwargs)
        return self._client.messages.create(**kwargs)


def contract_problems(sdk=None) -> list[str]:
    """
    Send the project's real Anthropic requests through `sdk` (default: the
    installed anthropic package) to a loopback server and list everything that
    did not arrive intact. An empty list means the contract holds.
    """
    import engine
    import providers

    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Recorder)
    srv.bodies = []
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    problems: list[str] = []
    try:
        if sdk is None:
            import anthropic as sdk
        client = sdk.Anthropic(api_key="contract-test-not-a-key", max_retries=0, timeout=10,
                               base_url=f"http://127.0.0.1:{srv.server_port}")
        sent: list[dict] = []
        spy = _Spy(client, sent)

        def run(label, call, expect, judge=False):
            before = len(srv.bodies)
            try:
                got = call()
            except Exception as e:
                problems.append(f"{label}: {type(e).__name__}: {e}")
                return
            if len(srv.bodies) == before or srv.bodies[-1] is None:
                problems.append(f"{label}: no readable request reached the server")
                return
            body, kwargs = srv.bodies[-1], sent[-1]
            for k, v in kwargs.items():
                if body.get(k) != json.loads(json.dumps(v)):
                    problems.append(f"{label}: `{k}` was sent but did not arrive as sent")
            if judge and not (body.get("temperature") == 0 and
                              (body.get("output_config") or {}).get("format", {}).get("type")
                              == "json_schema"):
                problems.append(f"{label}: the judge request lacks temperature 0 or its "
                                "json_schema output_config")
            if got != expect:
                problems.append(f"{label}: the reply was read as {got!r}, expected {expect!r}")

        run("judge (attack verdict)", lambda: engine.llm_judge_attack(
            spy, "reply", "PWNED_CONTRACT", request="request"), "held", judge=True)
        run("judge (control verdict)", lambda: engine.llm_judge_followed(
            spy, "reply", "CTRL_CONTRACT"), False, judge=True)
        for spec in providers.MODELS.values():
            if spec.provider == "anthropic":
                run(f"victim {spec.key}", lambda spec=spec: providers.VictimClient(
                    spec, spy).complete("system", "user"), CONTRACT_REPLY)
    except Exception as e:
        problems.append(f"the SDK could not be set up: {type(e).__name__}: {e}")
    finally:
        srv.shutdown()
        srv.server_close()
    return problems


@functools.cache
def _installed_contract() -> tuple[str, ...]:
    return tuple(contract_problems())


def status() -> tuple[bool, str]:
    """Whether a live Anthropic call may go out, and why not if it may not."""
    pin, have = pinned_version(), installed_version()
    if pin is None:
        return False, "no lock file pins anthropic, so there is nothing to check the SDK against"
    if have is None:
        return False, "the anthropic SDK is not installed"
    if have != pin:
        return False, (f"anthropic {have} is installed but requirements.lock pins {pin} "
                       "(pip install --require-hashes -r requirements.lock)")
    problems = _installed_contract()
    if problems:
        return False, f"anthropic {have} fails the request contract: " + "; ".join(problems)
    return True, f"anthropic {have} matches the lock and passes the request contract"


def require() -> None:
    """Raise SDKMismatch unless status() allows live calls."""
    ok, detail = status()
    if not ok:
        raise SDKMismatch(f"Live calls are blocked: {detail}. No API call was made.")
