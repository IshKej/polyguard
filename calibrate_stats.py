"""
Calibration suite for PolyGuard's statistics.

Unit tests prove a function runs and returns the number you expected on one
hand-checked example. They do not prove a statistical test is *correct*, because
correctness for a test means something else entirely: when there is genuinely no
effect, it must falsely claim one no more than alpha of the time, and when there
is a real effect it must actually find it.

That property cannot be asserted, only measured. So this file measures it, by
simulating thousands of complete scans against ground truth that it controls.

Two directions matter, and they are not symmetric:

  ANTI-CONSERVATIVE  the test rejects more often than alpha under the null. This
                     manufactures findings. For a project whose entire credibility
                     rests on not manufacturing findings, this is a failure.
  CONSERVATIVE       the test rejects less often than alpha. This costs power and
                     makes null results harder to interpret, but it never invents
                     an effect. Reported, not failed.

Exit code is non-zero only for the anti-conservative direction.

    python calibrate_stats.py            # full run
    python calibrate_stats.py --quick    # fewer simulations, for CI
"""
from __future__ import annotations

import random
import sys

import engine

ALPHA = 0.05
# Monte Carlo slack. With N simulations the observed rejection rate has standard
# error sqrt(a(1-a)/N); this is roughly a 3-sigma band at N=2000 plus headroom,
# so ordinary sampling noise never trips the failure condition.
TOLERANCE = 0.03

results = []


def record(name: str, observed: float, expected: float, n_sims: int,
           kind: str = "type1", note: str = "") -> None:
    """kind: 'type1' (must not exceed expected+TOLERANCE) or 'power'/'info'."""
    if kind == "type1":
        anti = observed > expected + TOLERANCE
        verdict = "ANTI-CONSERVATIVE" if anti else (
            "conservative" if observed < expected - TOLERANCE else "calibrated")
        ok = not anti
    elif kind == "power":
        ok = observed >= expected
        verdict = "adequate" if ok else "UNDERPOWERED"
    else:
        ok, verdict = True, "info"
    results.append({"name": name, "observed": observed, "expected": expected,
                    "n_sims": n_sims, "kind": kind, "verdict": verdict,
                    "ok": ok, "note": note})


# --------------------------------------------------------------------------- #
# 1. Wilson interval coverage
# --------------------------------------------------------------------------- #
def calibrate_wilson(n_sims: int) -> None:
    """A 95% interval should contain the true proportion about 95% of the time.

    Checked at small n and at extreme p, which is exactly where the normal
    approximation PolyGuard deliberately avoided would fall apart.
    """
    rng = random.Random(11)
    for n, p_true in ((15, 0.30), (15, 0.15), (15, 0.05), (75, 0.30), (300, 0.10)):
        cov_plain = cov_cc = 0
        for _ in range(n_sims):
            k = sum(rng.random() < p_true for _ in range(n))
            lo, hi = engine.wilson_ci(k, n)
            if lo <= p_true <= hi:
                cov_plain += 1
            lo2, hi2 = engine.wilson_ci_cc(k, n)
            if lo2 <= p_true <= hi2:
                cov_cc += 1
        a, b = cov_plain / n_sims, cov_cc / n_sims
        # Plain Wilson is the validated reference implementation, but its coverage
        # is known to OSCILLATE on discrete data and it dips below nominal at some
        # (n, p). Recorded as information, not as a failure of the code.
        record(f"Wilson plain coverage (n={n}, p={p_true})", 1 - a, 0.05, n_sims,
               "info", note=f"coverage {a:.1%}"
                            + ("  DIPS BELOW NOMINAL" if a < 0.95 else ""))
        # The continuity-corrected interval is what the app displays, so it is the
        # one held to the standard: it must never be narrower than nominal.
        record(f"Wilson continuity-corrected coverage (n={n}, p={p_true})",
               1 - b, 0.05, n_sims, "type1", note=f"coverage {b:.1%}")


def calibrate_wilson_sweep(n_sims: int, n: int = 15) -> None:
    """
    Sweep p across the range to expose the Wilson interval's coverage OSCILLATION.

    A single (n, p) spot check can land on a lucky point and miss the problem
    entirely, which is exactly what happened before this sweep existed. Coverage
    for a discrete binomial does not converge smoothly to nominal; it bounces, and
    the useful summary is the WORST point across the range, not the average.

    The worst-case figures this prints are the ones quoted in AUDIT.md finding 23,
    so they are reproducible from a committed artefact rather than from a number
    someone typed once.
    """
    rng = random.Random(97)
    ps = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40,
          0.45, 0.50, 0.60, 0.70, 0.80, 0.90]
    worst_plain, worst_cc = 1.0, 1.0
    worst_p_plain = worst_p_cc = None
    dips = 0
    for p_true in ps:
        cp = cc = 0
        for _ in range(n_sims):
            k = sum(rng.random() < p_true for _ in range(n))
            lo, hi = engine.wilson_ci(k, n)
            if lo <= p_true <= hi:
                cp += 1
            lo2, hi2 = engine.wilson_ci_cc(k, n)
            if lo2 <= p_true <= hi2:
                cc += 1
        a, b = cp / n_sims, cc / n_sims
        if a < worst_plain:
            worst_plain, worst_p_plain = a, p_true
        if b < worst_cc:
            worst_cc, worst_p_cc = b, p_true
        if a < 0.95:
            dips += 1
    record(f"Wilson sweep WORST plain coverage (n={n}, {len(ps)} values of p)",
           1 - worst_plain, 0.05, n_sims, "info",
           note=f"worst {worst_plain:.1%} at p={worst_p_plain}; "
                f"below nominal at {dips}/{len(ps)} points")
    record(f"Wilson sweep WORST continuity-corrected coverage (n={n})",
           1 - worst_cc, 0.05, n_sims, "type1",
           note=f"worst {worst_cc:.1%} at p={worst_p_cc}")


# --------------------------------------------------------------------------- #
# 2. Mann-Whitney on per-language rates: the headline test
# --------------------------------------------------------------------------- #
def _scan_rates(n_langs: int, attacks: int, p: float, rng: random.Random):
    return [sum(rng.random() < p for _ in range(attacks)) / attacks
            for _ in range(n_langs)]


def calibrate_mann_whitney(n_sims: int) -> None:
    """
    Type I error under a true null: both tiers drawn from the SAME rate.

    The per-language rates are discrete (k/15), so ties are everywhere. The tie
    correction and continuity correction in `mann_whitney_u` are what keep this
    honest, and this is the check that proves they work rather than assuming so.
    """
    rng = random.Random(23)
    for n_langs, attacks, p in ((6, 15, 0.30), (14, 15, 0.30), (14, 15, 0.05),
                                (42, 15, 0.30), (14, 5, 0.30)):
        rejects = 0
        for _ in range(n_sims):
            a = _scan_rates(n_langs, attacks, p, rng)
            b = _scan_rates(n_langs, attacks, p, rng)
            if (engine.mann_whitney_u(a, b)["p"] or 1.0) < ALPHA:
                rejects += 1
        record(f"Mann-Whitney type I ({n_langs} langs/tier, {attacks} attacks, p={p})",
               rejects / n_sims, ALPHA, n_sims, "type1")


def calibrate_mann_whitney_power(n_sims: int) -> None:
    """Power at effect sizes PolyGuard might plausibly meet."""
    rng = random.Random(29)
    cases = [
        (28, 15, 0.45, 0.30, 0.50, "15-point gap, 28 langs/tier"),
        (35, 15, 0.45, 0.30, 0.80, "15-point gap, 35 low vs 28 high"),
        (28, 15, 0.60, 0.20, 0.80, "40-point gap, 28 langs/tier"),
    ]
    for n_langs, attacks, p_lo, p_hi, want, label in cases:
        hits = 0
        for _ in range(n_sims):
            lo = _scan_rates(n_langs, attacks, p_lo, rng)
            hi = _scan_rates(28, attacks, p_hi, rng)
            if (engine.mann_whitney_u(lo, hi)["p"] or 1.0) < ALPHA:
                hits += 1
        record(f"Mann-Whitney power: {label}", hits / n_sims, want, n_sims, "power")


# --------------------------------------------------------------------------- #
# 3. The permutation test on the maximum
# --------------------------------------------------------------------------- #
def _fake_results(n_langs: int, attacks: int, p: float, rng: random.Random,
                  ref="en"):
    codes = [ref] + [f"l{i}" for i in range(n_langs - 1)]
    out = []
    for c in codes:
        for _ in range(attacks):
            out.append({"lang": c, "category": "c", "goal": "canary",
                        "broke": rng.random() < p, "error": None})
    return out


def calibrate_permutation(n_sims: int, n_iter: int) -> None:
    """
    The test that replaced the worst-language headline must itself be calibrated.

    Under the null every language shares one true rate, so a correct test rejects
    about alpha of the time no matter how many languages are scanned. The whole
    point of this test was that the naive rule fired 98% of the time here.
    """
    rng = random.Random(31)
    for n_langs in (20, 42):
        rejects = 0
        for i in range(n_sims):
            res = _fake_results(n_langs, 15, 0.30, rng)
            mg = engine.max_gap_permutation_test(res, n_iter=n_iter, seed=1000 + i)
            if mg["significant"]:
                rejects += 1
        record(f"Max-gap permutation type I ({n_langs} languages)",
               rejects / n_sims, ALPHA, n_sims, "type1")


def calibrate_permutation_power(n_sims: int, n_iter: int) -> None:
    """One language genuinely far worse than the rest must still be detected."""
    rng = random.Random(37)
    hits = 0
    for i in range(n_sims):
        res = _fake_results(20, 15, 0.25, rng)
        for r in res:                      # plant one badly broken language
            if r["lang"] == "l0":
                r["broke"] = rng.random() < 0.90
        mg = engine.max_gap_permutation_test(res, n_iter=n_iter, seed=2000 + i)
        if mg["significant"]:
            hits += 1
    record("Max-gap permutation power: one language at 90% vs 25%",
           hits / n_sims, 0.80, n_sims, "power")


# --------------------------------------------------------------------------- #
# 4. Benjamini-Hochberg false discovery rate control
# --------------------------------------------------------------------------- #
def calibrate_bh(n_sims: int) -> None:
    """
    Across a family of 5 category tests, BH should hold the false discovery
    proportion at or under alpha on average. Simulated with all 5 nulls true,
    where FDR reduces to the familywise error rate and is the strictest case.
    """
    rng = random.Random(41)
    any_reject = 0
    for _ in range(n_sims):
        pvals = [rng.random() for _ in range(5)]        # uniform under the null
        if any(a < ALPHA for a in engine.benjamini_hochberg(pvals)):
            any_reject += 1
    record("BH-FDR type I across 5 all-null category tests",
           any_reject / n_sims, ALPHA, n_sims, "type1")

    # and the uncorrected comparison, to show what the correction is buying
    rng2 = random.Random(41)
    naive = 0
    for _ in range(n_sims):
        pvals = [rng2.random() for _ in range(5)]
        if any(p < ALPHA for p in pvals):
            naive += 1
    record("(reference) UNCORRECTED 5 category tests", naive / n_sims,
           ALPHA, n_sims, "info",
           note="this is what BH is protecting against")


# --------------------------------------------------------------------------- #
# 5. Two-proportion z-test, the attack-level number shown for reference
# --------------------------------------------------------------------------- #
def calibrate_two_proportion(n_sims: int) -> None:
    """
    This one is EXPECTED to look fine here and still be wrong in practice.

    Under independent Bernoulli draws it is properly calibrated, and this run
    confirms that. But real attacks are clustered within a language, and the
    clustered check below shows what that does to it. That gap is the entire
    reason the app labels this number optimistic and does not headline it.
    """
    rng = random.Random(43)
    rejects = 0
    n = 300
    for _ in range(n_sims):
        s1 = sum(rng.random() < 0.3 for _ in range(n))
        s2 = sum(rng.random() < 0.3 for _ in range(n))
        if engine.two_proportion_test(s1, n, s2, n)["significant"]:
            rejects += 1
    record("Two-proportion z-test type I (independent draws)",
           rejects / n_sims, ALPHA, n_sims, "type1")


def demonstrate_clustering(n_sims: int) -> None:
    """
    The clustering problem, measured rather than argued.

    Both tiers share one true rate, so there is NO effect. But each language gets
    its own random per-language rate drawn around that shared mean, which is what
    correlated attacks within a language actually look like. The attack-level
    z-test treats all 630 attacks as independent and rejects far too often; the
    clustered test stays near alpha. This is AUDIT.md finding 16 as a number.
    """
    rng = random.Random(47)
    pooled_rejects = clustered_rejects = 0
    for _ in range(n_sims):
        lo_rates, hi_rates = [], []
        s_lo = s_hi = 0
        n_per = 15
        for _ in range(21):
            # per-language rate varies around the SAME tier mean: no real effect
            p_l = min(1, max(0, rng.gauss(0.30, 0.12)))
            p_h = min(1, max(0, rng.gauss(0.30, 0.12)))
            k_l = sum(rng.random() < p_l for _ in range(n_per))
            k_h = sum(rng.random() < p_h for _ in range(n_per))
            lo_rates.append(k_l / n_per)
            hi_rates.append(k_h / n_per)
            s_lo += k_l
            s_hi += k_h
        n_tot = 21 * n_per
        if engine.two_proportion_test(s_lo, n_tot, s_hi, n_tot)["significant"]:
            pooled_rejects += 1
        if (engine.mann_whitney_u(lo_rates, hi_rates)["p"] or 1.0) < ALPHA:
            clustered_rejects += 1
    record("Pooled attack-level z-test under CLUSTERED null",
           pooled_rejects / n_sims, ALPHA, n_sims, "info",
           note="inflated by clustering; this is why it is not the headline")
    record("Clustered Mann-Whitney under CLUSTERED null",
           clustered_rejects / n_sims, ALPHA, n_sims, "type1",
           note="the headline test, under the realistic null")


# --------------------------------------------------------------------------- #
# 6. Cliff's delta bootstrap interval coverage
# --------------------------------------------------------------------------- #
def calibrate_cliffs(n_sims: int) -> None:
    """Under the null the true delta is 0, so a 95% interval should contain 0."""
    rng = random.Random(53)
    covered = 0
    for _ in range(n_sims):
        a = _scan_rates(14, 15, 0.30, rng)
        b = _scan_rates(14, 15, 0.30, rng)
        ci = engine.cliffs_delta_ci(a, b, n_boot=300, seed=rng.randrange(10 ** 6))
        if ci["lo"] is not None and ci["lo"] <= 0 <= ci["hi"]:
            covered += 1
    cov = covered / n_sims
    record("Cliff's delta bootstrap CI covers 0 under the null",
           1 - cov, 0.05, n_sims, "type1", note=f"actual coverage {cov:.1%}")


# --------------------------------------------------------------------------- #
def main() -> int:
    quick = "--quick" in sys.argv
    n = 400 if quick else 2000
    n_perm, perm_iter = (60, 150) if quick else (300, 300)

    print("PolyGuard statistical calibration")
    print("Simulating complete scans against known ground truth.")
    print(f"{'quick mode, ' if quick else ''}{n} simulations per cell\n")

    calibrate_wilson(n)
    calibrate_wilson_sweep(n)
    calibrate_mann_whitney(n)
    calibrate_mann_whitney_power(max(200, n // 4))
    calibrate_permutation(n_perm, perm_iter)
    calibrate_permutation_power(max(40, n_perm // 3), perm_iter)
    calibrate_bh(n)
    calibrate_two_proportion(n)
    demonstrate_clustering(max(300, n // 2))
    calibrate_cliffs(max(200, n // 4))

    print(f"{'check':<58} {'obs':>7} {'target':>7}  verdict")
    print("-" * 92)
    bad = []
    for r in results:
        tgt = f"<={r['expected']:.0%}" if r["kind"] == "type1" else (
            f">={r['expected']:.0%}" if r["kind"] == "power" else "-")
        print(f"{r['name']:<58} {r['observed']:>6.1%} {tgt:>7}  {r['verdict']}"
              + (f"   [{r['note']}]" if r["note"] else ""))
        if not r["ok"]:
            bad.append(r)

    print()
    anti = [r for r in bad if r["kind"] == "type1"]
    weak = [r for r in bad if r["kind"] == "power"]
    if anti:
        print(f"FAIL: {len(anti)} test(s) reject more often than alpha under a true "
              f"null. That direction manufactures findings.")
        for r in anti:
            print(f"  - {r['name']}: {r['observed']:.1%} vs {r['expected']:.0%}")
    if weak:
        print(f"NOTE: {len(weak)} power target(s) not met. Not a correctness "
              f"failure, but it limits what a null result can be said to rule out:")
        for r in weak:
            print(f"  - {r['name']}: {r['observed']:.0%} power, wanted "
                  f">={r['expected']:.0%}")
    if not anti and not weak:
        print("All tests calibrated. None reject more often than alpha under a true "
              "null, and every power target was met.")
    elif not anti:
        print("No test is anti-conservative. Nothing here manufactures a finding.")
    return 1 if anti else 0


if __name__ == "__main__":
    raise SystemExit(main())
