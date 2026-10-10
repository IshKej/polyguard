"""
Capability rule check: how often each rule flags a language, by simulation.

    python capability_check.py          # about 15 seconds, standard library only

The capability controls decide which languages leave the primary test, so the
rule that flags them needs two numbers stated before any live data: how often it
wrongly flags a language that is as capable as English (false flags), and how
often it catches one that is not (detection). This simulates both, for the rule
in force since 2026-10-07 (`engine.capability_flag`) and the rule as first
pre-registered on 2026-09-17 (`engine.capability_flag_prereg`), using the engine's
own functions, so the table describes the code that runs.

World: English and the language each get the same number of benign controls;
English follows each with true probability e, the language with ratio x e. Each
cell is 20,000 seeded draws (seed 20261007 plus the cell index). An exact column
(full binomial enumeration, no randomness) checks the simulation for the current
rule. Nothing here is evidence about any real model; it describes the rule.
"""
from __future__ import annotations

import math
import random

import engine

DRAWS = 20_000
SEED = 20261007
ENGLISH = (1.0, 0.95, 0.9, 0.8)
RATIOS = (1.0, 0.75, 0.5, 0.3, 0.0)
OTHER_LANGUAGES = 86          # 87 catalog languages minus English


def _binom(n: int, p: float) -> list[float]:
    return [math.comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(n + 1)]


def exact_rate(flag, n: int, e: float, v: float) -> float:
    pe, pv = _binom(n, e), _binom(n, v)
    return sum(pe[kr] * pv[k] for kr in range(n + 1) for k in range(n + 1)
               if flag(k, n, kr, n))


def simulate(n: int) -> list[dict]:
    rows, cell = [], 0
    for e in ENGLISH:
        for x in RATIOS:
            rng = random.Random(SEED + cell + (1000 if n != 6 else 0))
            cell += 1
            v = x * e
            cur = old = 0
            for _ in range(DRAWS):
                kr = sum(rng.random() < e for _ in range(n))
                k = sum(rng.random() < v for _ in range(n))
                cur += engine.capability_flag(k, n, kr, n)
                old += engine.capability_flag_prereg(k, n, kr, n)
            rows.append({"n": n, "e": e, "ratio": x, "current": cur / DRAWS,
                         "prereg": old / DRAWS,
                         "current_exact": exact_rate(engine.capability_flag, n, e, v)})
    return rows


def main() -> int:
    worst_gap = 0.0
    for n in (6, 12):
        rows = simulate(n)
        print(f"\n{n} controls per language (rate a language is flagged; "
              f"'exact' is the enumeration check)")
        print("| English true rate | language / English | current rule | exact | "
              "2026-09-17 rule |")
        print("|---|---|---|---|---|")
        for r in rows:
            worst_gap = max(worst_gap, abs(r["current"] - r["current_exact"]))
            print(f"| {r['e']:.2f} | {r['ratio']:.0%} | {r['current']:.4f} | "
                  f"{r['current_exact']:.4f} | {r['prereg']:.4f} |")
        capable = [r for r in rows if r["ratio"] == 1.0]
        print(f"expected false flags across {OTHER_LANGUAGES} fully capable languages, "
              f"current rule: " + ", ".join(
                  f"{OTHER_LANGUAGES * r['current_exact']:.3f} at e={r['e']:.2f}"
                  for r in capable))
    print(f"\nlargest simulation minus exact difference: {worst_gap:.4f}")
    # 20,000 draws: standard error at most 0.0036, so 0.015 is over 4 standard errors.
    return 0 if worst_gap < 0.015 else 1


if __name__ == "__main__":
    raise SystemExit(main())
