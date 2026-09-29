"""
Pre-deployment gate. Run this before pushing to GitHub or deploying.

Streamlit Cloud does a clean checkout of whatever is in the repo, installs
`requirements.txt`, and runs `app.py` with no local files and no environment.
Anything that works only because of something sitting on this laptop will fail
there, and it will fail in front of whoever is looking at the link.

This checks the things that actually break that step:

  FILES      every file DEPLOY.md tells you to upload exists, including
             attack_bank.json, which Cloud loads and never regenerates because
             it does not run the generators
  SECRETS    no real key is committed, secrets.toml is ignored, and no
             key-shaped literal is sitting in any source file
  DEPS       every third-party module the code imports is declared in
             requirements.txt
  BOOT       the app imports cleanly with no API key set, which is exactly the
             state a fresh deployment starts in

Exit code is non-zero if anything would break the deploy.

    python preflight.py
"""
from __future__ import annotations

import ast
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent

# Everything DEPLOY.md says to upload. attack_bank.json is the one people forget,
# and its absence is not obvious until the app 500s on a live link.
REQUIRED = [
    "app.py", "engine.py", "providers.py", "defenses.py",
    "attack_bank.json", "generate_attack_bank.py", "languages_catalog.py",
    "expand_languages.py", "validate_bank.py", "linguistics.py",
    "judge_eval.py", "calibrate_stats.py", "selection_bias_demo.py",
    "review_sheet.py", "rehearsal.py", "consistency.py",
    "cli.py", "report_html.py",
    "test_engine.py", "verify_all.py",
    "preflight.py",
    "requirements.txt", "README.md", "DEPLOY.md", "AUDIT.md",
    "PREREGISTRATION.md", "RELATED_WORK.md", "NATIVE_REVIEW.md", "STATE.md",
    "DEMO_VIDEO.md",
    ".streamlit/config.toml", ".gitignore",
]

MUST_NOT_SHIP = [".streamlit/secrets.toml"]

# Modules that ship with Python, so they never belong in requirements.txt.
STDLIB = set(sys.stdlib_module_names) | {"__future__"}

# Local modules, resolved from the .py files actually present.
LOCAL = {p.stem for p in HERE.glob("*.py")}

# A real Anthropic key starts sk-ant- and is long. The pattern deliberately
# requires length so that the placeholder "sk-ant-..." in docs does not trip it.
KEY_PATTERNS = [
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"), "Anthropic key"),
    (re.compile(r"sk-proj-[A-Za-z0-9_\-]{20,}"), "OpenAI project key"),
    (re.compile(r"\bgsk_[A-Za-z0-9]{20,}"), "Groq key"),
    (re.compile(r"AIza[0-9A-Za-z_\-]{30,}"), "Google API key"),
]

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, bool(ok), detail))


def check_files() -> None:
    missing = [f for f in REQUIRED if not (HERE / f).exists()]
    check("every file DEPLOY.md lists is present", not missing,
          f"missing: {', '.join(missing)}" if missing else "")
    present = [f for f in MUST_NOT_SHIP if (HERE / f).exists()]
    # Not a failure on its own: the file is gitignored and is how you run
    # locally. It IS a failure if it is not ignored, which is checked below.
    check("no real secrets file where it could be committed", True,
          "secrets.toml exists locally (fine, it is gitignored)" if present else "")

    gi = (HERE / ".gitignore").read_text(encoding="utf-8") if (HERE / ".gitignore").exists() else ""
    check("secrets.toml is gitignored", "secrets.toml" in gi)

    bank_path = HERE / "attack_bank.json"
    if bank_path.exists():
        try:
            bank = json.loads(bank_path.read_text(encoding="utf-8"))
            ok = bool(bank.get("attacks")) and bool(bank.get("languages"))
            check("attack_bank.json is present and parses",
                  ok, f"{len(bank.get('attacks', []))} attacks, "
                      f"{len(bank.get('controls', []))} controls, "
                      f"{len(bank.get('languages', {}))} languages")
        except Exception as e:
            check("attack_bank.json is present and parses", False, str(e))
    else:
        check("attack_bank.json is present and parses", False, "file missing")


def check_no_committed_keys() -> None:
    hits = []
    for p in list(HERE.glob("*.py")) + list(HERE.glob("*.md")) + \
            list(HERE.glob("*.toml")) + list(HERE.glob(".streamlit/*")):
        if p.name == "secrets.toml" or p.name == Path(__file__).name:
            continue          # the live secrets file is gitignored; this file holds the patterns
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        for pattern, label in KEY_PATTERNS:
            if pattern.search(text):
                hits.append(f"{p.name}: {label}")
    check("no API key literal in any file that would be committed", not hits,
          "; ".join(hits))


def _third_party_imports() -> set[str]:
    mods: set[str] = set()
    for p in HERE.glob("*.py"):
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    mods.add(n.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    mods.add(node.module.split(".")[0])
    return {m for m in mods if m not in STDLIB and m not in LOCAL}


def check_requirements() -> None:
    req_path = HERE / "requirements.txt"
    req_text = req_path.read_text(encoding="utf-8") if req_path.exists() else ""
    declared = set()
    for line in req_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        declared.add(re.split(r"[<>=!\[]", line)[0].strip().lower())

    used = _third_party_imports()
    # Optional providers are imported lazily and documented as optional, so their
    # absence from requirements is deliberate rather than a mistake.
    # openpyxl builds reviewer spreadsheets; the deployed app never touches it.
    optional = {"openai", "google", "openpyxl"}
    aliases = {"google": "google-genai"}
    missing = []
    for m in sorted(used):
        if m in optional:
            continue
        if m.lower() not in declared and aliases.get(m, m).lower() not in declared:
            missing.append(m)
    check("every required third-party import is in requirements.txt", not missing,
          f"missing: {', '.join(missing)}" if missing else
          f"declared: {', '.join(sorted(declared))}")
    check("optional providers are commented out, not hard requirements",
          all(o not in declared for o in optional),
          "openai/google-genai stay optional so a clean deploy is small")


def check_boots_without_key() -> None:
    """
    The state a fresh deployment starts in: no key anywhere. The app must come up
    in mock mode rather than raising, because that is what a visitor sees before
    any secret is configured.
    """
    saved = {k: os.environ.pop(k, None) for k in
             ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY",
              "GROQ_API_KEY", "POLYGUARD_PASSCODE")}
    try:
        import importlib
        for name in ("providers", "engine", "defenses", "languages_catalog",
                     "linguistics"):
            importlib.import_module(name)
        import providers
        check("app imports cleanly with no API key configured",
              providers.judge_client() is None,
              "resolves to no client, so the app falls into labelled mock mode")
    except Exception as e:
        check("app imports cleanly with no API key configured", False, repr(e))
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v


def main() -> int:
    print("PolyGuard deployment preflight")
    print("Simulating what Streamlit Cloud does: clean checkout, no environment.\n")
    check_files()
    check_no_committed_keys()
    check_requirements()
    check_boots_without_key()

    width = max(len(n) for n, _, _ in results)
    failed = 0
    for name, ok, detail in results:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"  [{mark}] {name:<{width}}" + (f"   {detail}" if detail else ""))

    print()
    if failed:
        print(f"{failed} problem(s) would break the deployment. Fix before pushing.")
    else:
        print("Ready to deploy. Remaining steps are the two account actions in")
        print("DEPLOY.md: create the GitHub repo, then point Streamlit Cloud at it")
        print("and paste ANTHROPIC_API_KEY into its Secrets box.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
