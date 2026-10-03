"""
Plug in the Anthropic API key, once, everywhere it is needed.

    python setup_key.py               # local .env, the Vercel project, and a redeploy
    python setup_key.py --local-only  # just the local .env

What it does, in order, and what it never does:

  1. Asks for the key without echoing it, and checks its shape.
  2. Verifies the key against Anthropic's model list, which costs nothing: no
     tokens are generated. It does NOT make a paid call. The first paid call is
     stage 0 of docs/pilot-plan.md, and that needs Ishaan's written approval.
  3. Generates the site passcode (or keeps the one already in .env). Live scans on
     the website fail closed without one.
  4. Writes both to .env, which git and Vercel both ignore.
  5. Checks the Vercel CLI is logged in as the right account, asks before touching
     anything, stores both as Sensitive production variables (values go over
     stdin, never on a command line), and redeploys production so they take effect.
  6. Prints the passcode and the exact next commands from the pilot plan.

The key is never printed, logged, or written anywhere but .env and Vercel.
"""
from __future__ import annotations

import argparse
import getpass
import json
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENV_FILE = HERE / ".env"
VERCEL_ACCOUNT = "ishkej"           # Ishaan's own Vercel account, never anyone else's
VICTIM_AND_JUDGE = "claude-haiku-4-5"


def read_env() -> dict[str, str]:
    out = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def write_env(updates: dict[str, str]) -> None:
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else [
        "# Local secrets for PolyGuard. Ignored by git and by Vercel. Never commit this file."]
    seen = set()
    for i, line in enumerate(lines):
        k = line.split("=", 1)[0].strip()
        if k in updates:
            lines[i] = f"{k}={updates[k]}"
            seen.add(k)
    lines += [f"{k}={v}" for k, v in updates.items() if k not in seen]
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def verify_key(key: str) -> str | None:
    """None when the key works; otherwise what went wrong. Costs nothing."""
    try:
        import anthropic
    except ImportError:
        return "the anthropic package is not installed (pip install -r requirements.txt)"
    try:
        client = anthropic.Anthropic(api_key=key, max_retries=2, timeout=20)
        client.models.retrieve(VICTIM_AND_JUDGE)       # a model lookup, not a generation
        return None
    except Exception as e:
        name = type(e).__name__
        if name in ("AuthenticationError", "PermissionDeniedError"):
            return "Anthropic rejected the key. Check it was copied whole."
        if name == "NotFoundError":
            return f"the key works but cannot see {VICTIM_AND_JUDGE}."
        return f"could not reach Anthropic ({name}). Check the connection and try again."


def npx() -> str:
    exe = shutil.which("npx") or shutil.which("npx.cmd")
    if not exe:
        raise SystemExit("npx was not found. Install Node.js, or run with --local-only.")
    return exe


def vercel(*args, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([npx(), "--yes", "vercel@latest", *args], cwd=HERE, input=stdin,
                          capture_output=True, text=True, timeout=300)


def push_to_vercel(values: dict[str, str]) -> bool:
    who = vercel("whoami").stdout.strip().splitlines()
    who = who[-1].strip() if who else ""
    if who != VERCEL_ACCOUNT:
        print(f"  The Vercel CLI is logged in as {who or 'nobody'!r}, not {VERCEL_ACCOUNT!r}. "
              f"Nothing was sent. Run `npx vercel login` as {VERCEL_ACCOUNT} and try again.")
        return False
    if input(f"  Store the key and passcode in Vercel project 'polyguard' ({who}) and redeploy? [y/N] "
             ).strip().lower() != "y":
        print("  Skipped Vercel. The site stays simulated until these are set there.")
        return False
    for name, value in values.items():
        r = vercel("env", "add", name, "production", "--sensitive", "--force", stdin=value + "\n")
        if r.returncode != 0:
            print(f"  Could not set {name} on Vercel:\n{(r.stderr or r.stdout)[-400:]}")
            return False
        print(f"  set {name} (Sensitive, production)")
    ls = vercel("ls", "--environment", "production", "-F", "json")
    try:
        latest = json.loads(ls.stdout)["deployments"][0]["url"]
    except Exception:
        print("  Variables are set. Redeploy production from the Vercel dashboard so they take effect.")
        return True
    print(f"  redeploying {latest} so the site picks them up (about a minute)...")
    r = vercel("redeploy", latest, "--target", "production")
    print("  redeployed" if r.returncode == 0 else f"  redeploy failed; redeploy from the dashboard:\n{r.stderr[-300:]}")
    return r.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--local-only", action="store_true", help="only write .env, leave Vercel alone")
    args = ap.parse_args()

    print("PolyGuard key setup. The key is not shown as you type.\n")
    key = getpass.getpass("  Anthropic API key: ").strip()
    if not key.startswith("sk-ant-") or len(key) < 40:
        print("  That does not look like an Anthropic API key (they start with sk-ant-).")
        return 2
    problem = verify_key(key)
    if problem:
        print(f"  Not saved: {problem}")
        return 2
    print(f"  key verified (it can see {VICTIM_AND_JUDGE}); no tokens were spent")

    env = read_env()
    passcode = env.get("POLYGUARD_PASSCODE") or secrets.token_urlsafe(12)
    write_env({"ANTHROPIC_API_KEY": key, "POLYGUARD_PASSCODE": passcode})
    print(f"  wrote {ENV_FILE.name} (ignored by git and Vercel)")

    if not args.local_only:
        push_to_vercel({"ANTHROPIC_API_KEY": key, "POLYGUARD_PASSCODE": passcode})

    print(f"""
Done. The site passcode is:  {passcode}
Type it on the scan screen to unlock live scans. Share it only with people you trust
to spend from your key.

Before any paid call:
  1. In the Anthropic Console, set a spend limit of $10 on this key's workspace.
  2. Approve docs/pilot-plan.md in writing (stages 0 and 1).

Then, and only then:
  python providers.py --smoke claude-haiku-4-5                    # stage 0, one call
  python cli.py scan --prompt pilot_prompt.txt --model claude-haiku-4-5 --langs en,es,vi \\
      --bundle pilot/pilot_a                                       # stage 1, 63 + up to 63 calls
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
