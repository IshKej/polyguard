"""
Is engine.power_simulation optimistic? A seeded check, standard library only.

    python power_check.py            # about two minutes, prints a table

engine.power_simulation gives every language in a tier exactly the same true
break rate, so the only noise it models is which of the 15 attacks happened to
land. Real languages differ from each other even inside a tier (translation
quality, script, how much safety training covered them), and every language
gets the same 15 attacks, so a hard attack is hard everywhere at once. Both of
those add spread that more attacks cannot remove.

This script measures the minimum detectable gap (the smallest low minus high
gap that the pre-registered Mann-Whitney test detects in 80% of scans) twice:
once with engine.power_simulation as it is, and once with a model that adds
the extra spread on the logit scale. Since the fix, power_simulation carries
that spread itself (lang_sd, default engine.LANG_SD), so the old model is run
here with lang_sd=0 and the new default is shown last. Same test, same rejection rule, same
designs, fixed seeds. The sizes of the extra spread are assumptions, not
measurements; the first live scan is what can estimate them. The result is
recorded in docs/progress/stats.md.
"""
from __future__ import annotations

import math
import random
import sys
from statistics import NormalDist

import engine
from languages_catalog import CATALOG

ATTACKS = 15
GAPS = [0.04, 0.06, 0.08, 0.10, 0.12, 0.14, 0.16, 0.18, 0.20]
N_SIMS = 1000
_Q = [NormalDist().inv_cdf((i + 0.5) / 400) for i in range(400)]


def _expit(v: float) -> float:
    return 1 / (1 + math.exp(-v))


def mean_rate(loc: float, sd: float) -> float:
    """Expected rate when the logit is Normal(loc, sd), by 400 equal probability nodes."""
    return sum(_expit(loc + sd * q) for q in _Q) / len(_Q)


def logit_for(rate: float, sd: float) -> float:
    """The logit location whose expected rate under spread `sd` is `rate` (bisection)."""
    lo, hi = -12.0, 12.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if mean_rate(mid, sd) < rate:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def spread_power(n_low: int, n_high: int, p_low: float, p_high: float,
                 lang_sd: float, attack_sd: float, noise_sd: float,
                 n_sims: int, seed: int) -> float:
    """Power of engine.mann_whitney_u when languages and attacks vary on the logit scale.

    Tier means are calibrated so the EXPECTED per language rate is exactly p_low
    and p_high, the same targets engine.power_simulation uses, so the two are
    compared at the same gap."""
    s_tot = math.sqrt(lang_sd ** 2 + attack_sd ** 2 + noise_sd ** 2)
    loc_lo, loc_hi = logit_for(p_low, s_tot), logit_for(p_high, s_tot)
    rng = random.Random(seed)
    hits = 0
    for _ in range(n_sims):
        att = [attack_sd * rng.gauss(0, 1) for _ in range(ATTACKS)]   # shared by every language

        def lang_rate(loc):
            eta = loc + lang_sd * rng.gauss(0, 1)
            return sum(rng.random() < _expit(eta + a + noise_sd * rng.gauss(0, 1))
                       for a in att) / ATTACKS

        lo = [lang_rate(loc_lo) for _ in range(n_low)]
        hi = [lang_rate(loc_hi) for _ in range(n_high)]
        if (engine.mann_whitney_u(lo, hi)["p"] or 1.0) < 0.05:   # the engine's own rule
            hits += 1
    return hits / n_sims


def mde(curve: list[tuple[float, float]], target: float = 0.80) -> float | None:
    """Smallest gap reaching `target` power, linear interpolation between grid points."""
    prev = None
    for gap, pw in curve:
        if pw >= target:
            if prev is None:
                return gap
            g0, p0 = prev
            return g0 + (gap - g0) * (target - p0) / (pw - p0)
        prev = (gap, pw)
    return None


SCENARIOS = {  # name: (language sd, attack sd, translation noise sd), logit scale
    "engine, old model (lang_sd=0)": "engine0",
    "spread check (0, 0, 0)": (0.0, 0.0, 0.0),
    "language spread only (0.5, 0, 0)": (0.5, 0.0, 0.0),
    "realistic, as in the note (0.5, 1.0, 0.5)": (0.5, 1.0, 0.5),
    "engine, new default (lang_sd=LANG_SD)": "engine",
}
OLD = "engine, old model (lang_sd=0)"
NEW = "engine, new default (lang_sd=LANG_SD)"
REAL = "realistic, as in the note (0.5, 1.0, 0.5)"


def main() -> int:
    tiers = [m["tier"] for m in CATALOG.values()]
    designs = {"catalog now": (tiers.count("low"), tiers.count("high")),
               "note's design": (35, 28)}
    print(f"Minimum detectable gap at 80% power, Mann-Whitney, {ATTACKS} attacks per "
          f"language, {N_SIMS} scans per point, gaps {GAPS[0]} to {GAPS[-1]}")
    rows = []
    for d_i, (dname, (n_low, n_high)) in enumerate(designs.items()):
        for p_i, p_high in enumerate((0.15, 0.30)):
            out = {}
            for s_i, (sname, sd) in enumerate(SCENARIOS.items()):
                curve = []
                for g_i, gap in enumerate(GAPS):
                    # One fixed seed per point, from its position in the grid.
                    seed = 20261007 + ((d_i * 2 + p_i) * 4 + s_i) * len(GAPS) + g_i
                    if s_i >= 4:
                        seed += 1000
                    if isinstance(sd, str):
                        kw = {"lang_sd": 0.0} if sd == "engine0" else {}
                        pw = engine.power_simulation(n_low, n_high, ATTACKS, p_high + gap, p_high,
                                                     n_sims=N_SIMS, seed=seed, **kw)["power"]
                    else:
                        pw = spread_power(n_low, n_high, p_high + gap, p_high, *sd,
                                          n_sims=N_SIMS, seed=seed)
                    curve.append((gap, pw))
                out[sname] = mde(curve)
                print(f"  {dname} ({n_low} low / {n_high} high), high rate {p_high:.2f}, "
                      f"{sname}: MDE {out[sname] if out[sname] is None else round(out[sname], 4)}  "
                      f"curve {[round(p, 3) for _, p in curve]}", flush=True)
            rows.append((dname, p_high, out))
    print("\nOld engine model against the realistic one, and the new default:")
    for dname, p_high, out in rows:
        e, r, d = out[OLD], out[REAL], out[NEW]
        if e and r and d:
            print(f"  {dname}, high rate {p_high:.2f}: old {e:.4f}, realistic {r:.4f} "
                  f"(realistic {r / e - 1:+.1%} larger, old {1 - e / r:.1%} smaller); "
                  f"new default {d:.4f} ({d / r - 1:+.1%} against realistic)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
