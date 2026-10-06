"""
Mutation check: plant a small bug in the statistics, one at a time, and confirm
the tests notice.

    python mutation_check.py

A green test suite proves less than it looks: tests that would also pass on
broken code are decoration. Each mutant below is a mistake that has really been
made in statistics code (dropping the add-one from a permutation p, a one-sided
test where a two-sided one was meant, the wrong z, a broken false discovery
correction) or one this project specifically fixed (the order-dependent p of
AUDIT.md finding 63, the held-out rule of finding 65). The code is copied to a
temporary folder, one mutant is applied, and the unit tests and the property
tests run against the copy. A mutant is KILLED when they fail. Every mutant must
be killed; a survivor is a hole in the tests, reported by name.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

# (file, original text, mutated text, what the bug is)
MUTANTS = [
    ("engine.py", "p = (ge + 1) / (n_iter + 1)", "p = ge / n_iter",
     "permutation p without the add-one, so it can be exactly zero"),
    ("engine.py", "        if g >= observed - 1e-9:", "        if g > observed + 1e-9:",
     "permutation test counting only strictly larger gaps"),
    ("engine.py", "        if g >= observed - 1e-9:", "        if g >= observed:",
     "permutation test dropping ties that differ only in floating point"),
    ("engine.py", '"n_langs": len(by), "n_iter": n_iter, "significant": p < 0.05,',
     '"n_langs": len(by), "n_iter": n_iter, "significant": p < 0.5,',
     "worst-language test at the wrong alpha"),
    ("engine.py", 'key=lambda r: (r["lang"], r.get("category", ""), r.get("variant", 0), r.get("id", "")))',
     "key=lambda r: 0)", "rows left in arrival order (AUDIT.md 63)"),
    ("engine.py", "def wilson_ci_cc(successes: int, n: int, z: float = 1.96)",
     "def wilson_ci_cc(successes: int, n: int, z: float = 1.64)", "a 90% interval passed off as 95%"),
    ("engine.py", "        val = min(prev, pvals[i] * m / rank)", "        val = pvals[i] * m / rank",
     "Benjamini-Hochberg without the step-down minimum"),
    ("engine.py", "        val = min(prev, pvals[i] * m / rank)", "        val = min(prev, pvals[i] * m / (rank + 1))",
     "Benjamini-Hochberg with an off-by-one rank"),
    ("engine.py", "    p = min(1.0, 2 * tail)", "    p = min(1.0, tail)", "a one-sided sign test"),
    ("engine.py", "        avg_rank = (i + 1 + j + 1) / 2", "        avg_rank = (i + j + 1) / 2",
     "Mann-Whitney ranks off by half"),
    ("engine.py", 'd["capability_limited"] = bool(ref and d["ci_hi"] < threshold)',
     'd["capability_limited"] = bool(ref and d["ci_lo"] < threshold)',
     "capability limit read from the wrong end of the interval"),
    ("engine.py", "            if x > y:", "            if x >= y:",
     "Cliff's delta counting ties as wins"),
    ("defenses.py", 'if r.get("broke") and r.get("variant", 0) != HELDOUT_VARIANT}',
     'if r.get("broke")}', "defences chosen using the held-out phrasing (AUDIT.md 65)"),
]

SUITES = ["test_engine.py", "test_stats_properties.py"]


def run_mutant(src: Path, file: str, old: str, new: str) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for p in src.iterdir():
            if p.suffix in (".py", ".json") and p.is_file():
                shutil.copy2(p, tmp / p.name)
        target = tmp / file
        text = target.read_text(encoding="utf-8")
        if text.count(old) != 1:
            return False, f"mutation site not found exactly once in {file}"
        target.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
        for suite in SUITES:
            r = subprocess.run([sys.executable, suite], cwd=tmp, capture_output=True, text=True,
                               timeout=600, env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
            if r.returncode != 0:
                failed = [ln.strip() for ln in r.stdout.splitlines() if "[FAIL]" in ln]
                return True, f"{suite}: {failed[0] if failed else 'crashed'}"
        return False, "every test still passed"


def main() -> int:
    killed = 0
    for file, old, new, what in MUTANTS:
        dead, why = run_mutant(HERE, file, old, new)
        killed += dead
        print(f"  [{'KILLED' if dead else 'SURVIVED'}] {what}\n             {why[:150]}", flush=True)
    print(f"\n{killed}/{len(MUTANTS)} mutants killed")
    return 0 if killed == len(MUTANTS) else 1


if __name__ == "__main__":
    sys.exit(main())
