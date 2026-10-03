"""
Property tests for the statistics: rules every result must obey, checked on
thousands of random inputs instead of a handful of hand-picked ones.

    python test_stats_properties.py      # PASS/FAIL per property, exits non-zero on failure

A unit test checks that a function gives one known answer. A property says what
must be true of EVERY answer: a confidence interval contains its estimate, a
two-sided test does not care which group is called first, a p-value from a
permutation test cannot be zero, a corrected p-value is never smaller than the raw
one. The inputs are random but seeded, so a failure always reproduces.

`mutation_check.py` then plants small bugs in the statistics and confirms these
properties and the unit tests catch them.
"""
from __future__ import annotations

import random
import sys

import engine

RNG = random.Random(20261002)
TRIALS = 300
CASES: list[tuple[str, bool]] = []


def prop(name, ok):
    CASES.append((name, bool(ok)))


def close(a, b, tol=1e-9):
    return (a is None and b is None) or (a is not None and b is not None and abs(a - b) <= tol)


# --- confidence intervals ----------------------------------------------------------
ok_contains = ok_bounds = ok_mirror = ok_width = True
for _ in range(TRIALS):
    n = RNG.randint(1, 60)
    k = RNG.randint(0, n)
    lo, hi = engine.wilson_ci_cc(k, n)
    p = k / n
    ok_contains &= lo - 1e-12 <= p <= hi + 1e-12
    ok_bounds &= 0.0 <= lo <= hi <= 1.0
    lo2, hi2 = engine.wilson_ci_cc(n - k, n)
    ok_mirror &= close(lo, 1 - hi2, 1e-9) and close(hi, 1 - lo2, 1e-9)
    if n >= 2:
        # Same proportion, more data: never a wider interval.
        lo3, hi3 = engine.wilson_ci_cc(2 * k, 2 * n)
        ok_width &= (hi3 - lo3) <= (hi - lo) + 1e-12
prop("a continuity corrected interval always contains its own estimate", ok_contains)
prop("interval bounds stay inside 0 to 1, in order", ok_bounds)
prop("successes and failures give mirror image intervals", ok_mirror)
prop("doubling the data at the same rate never widens the interval", ok_width)

# --- Mann-Whitney U ----------------------------------------------------------------
ok_range = ok_sym = ok_mono = ok_shift = True
for _ in range(TRIALS):
    xs = [RNG.random() for _ in range(RNG.randint(2, 12))]
    ys = [RNG.random() for _ in range(RNG.randint(2, 12))]
    a = engine.mann_whitney_u(xs, ys)
    ok_range &= a["p"] is None or 0.0 <= a["p"] <= 1.0
    ok_sym &= close(a["p"], engine.mann_whitney_u(ys, xs)["p"], 1e-9)
    # Ranks only: any strictly increasing transform of all the data changes nothing.
    ok_mono &= close(a["p"], engine.mann_whitney_u([v ** 3 + 5 for v in xs], [v ** 3 + 5 for v in ys])["p"], 1e-9)
    # Moving one group far above the other can only make it more significant.
    far = engine.mann_whitney_u([v + 10 for v in xs], ys)
    ok_shift &= far["p"] <= a["p"] + 1e-12
prop("Mann-Whitney p is a probability", ok_range)
prop("Mann-Whitney is two sided: which group is named first does not matter", ok_sym)
prop("Mann-Whitney depends on ranks only, not on the scale of the data", ok_mono)
prop("separating the groups completely never makes the test less significant", ok_shift)

# --- sign test, Cliff's delta, Benjamini-Hochberg, kappa, two proportions ----------
ok_sign = ok_delta = ok_anti = ok_bh = ok_bh_order = ok_kappa = ok_two = True
for _ in range(TRIALS):
    w, b = RNG.randint(0, 20), RNG.randint(0, 20)
    s1, s2 = engine.sign_test(w, b), engine.sign_test(b, w)
    ok_sign &= close(s1["p"], s2["p"], 1e-12) and 0 <= s1["p"] <= 1
    xs = [RNG.random() for _ in range(RNG.randint(1, 10))]
    ys = [RNG.random() for _ in range(RNG.randint(1, 10))]
    d = engine.cliffs_delta(xs, ys)["delta"]
    ok_delta &= -1.0 <= d <= 1.0
    ok_anti &= close(d, -engine.cliffs_delta(ys, xs)["delta"], 1e-12)
    ps = [RNG.random() for _ in range(RNG.randint(1, 8))]
    adj = engine.benjamini_hochberg(ps)
    ok_bh &= all(a + 1e-12 >= p and a <= 1.0 for a, p in zip(adj, ps))
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    ok_bh_order &= all(adj[order[i]] <= adj[order[i + 1]] + 1e-12 for i in range(len(ps) - 1))
    labels = [RNG.random() < 0.5 for _ in range(RNG.randint(2, 30))]
    if len(set(labels)) > 1:
        ok_kappa &= close(engine.cohens_kappa(labels, labels)["kappa"], 1.0, 1e-12)
    n1, n2 = RNG.randint(1, 50), RNG.randint(1, 50)
    k1, k2 = RNG.randint(0, n1), RNG.randint(0, n2)
    t1, t2 = engine.two_proportion_test(k1, n1, k2, n2), engine.two_proportion_test(k2, n2, k1, n1)
    ok_two &= close(t1["p"], t2["p"], 1e-12)
prop("the sign test is symmetric in worse and better", ok_sign)
prop("Cliff's delta lies between -1 and 1", ok_delta)
prop("Cliff's delta changes sign when the groups swap", ok_anti)
prop("a group compared with itself has a Cliff's delta of exactly 0, ties counted as ties",
     all(engine.cliffs_delta(v, v)["delta"] == 0
         for v in ([RNG.random() for _ in range(RNG.randint(1, 9))] for _ in range(50))))
prop("a Benjamini-Hochberg adjusted p is never below the raw p, nor above 1", ok_bh)
prop("Benjamini-Hochberg keeps the order of the raw p-values", ok_bh_order)
prop("two identical raters agree perfectly (kappa 1)", ok_kappa)
prop("the two proportion test does not care which proportion comes first", ok_two)

# --- the worst-language permutation test ------------------------------------------
def fake_rows(rates: dict[str, float], per_lang: int, rng: random.Random) -> list[dict]:
    rows = []
    for lang, r in rates.items():
        for i in range(per_lang):
            rows.append({"id": f"{lang}_{i}", "lang": lang, "category": "c", "variant": i % 3,
                         "broke": rng.random() < r, "error": None})
    return rows


ok_pos = ok_rename = ok_order = ok_strong = True
null_sig = 0
for t in range(40):
    rng = random.Random(t)
    langs = ["en"] + [f"l{i}" for i in range(rng.randint(3, 9))]
    rows = fake_rows({l: 0.3 for l in langs}, 9, rng)
    res = engine.max_gap_permutation_test(rows, n_iter=300)
    ok_pos &= res["p"] is not None and 0 < res["p"] <= 1
    null_sig += res["significant"]
    renamed = [{**r, "lang": ("en" if r["lang"] == "en" else "z_" + r["lang"])} for r in rows]
    ok_rename &= close(res["p"], engine.max_gap_permutation_test(renamed, n_iter=300)["p"], 1e-12)
    shuffled = rows[:]
    rng.shuffle(shuffled)
    ok_order &= close(res["p"], engine.max_gap_permutation_test(shuffled, n_iter=300)["p"], 1e-12)
for t in range(10):
    rng = random.Random(100 + t)
    rows = fake_rows({"en": 0.0, "a": 0.0, "b": 0.0, "c": 0.0, "d": 0.95}, 15, rng)
    ok_strong &= engine.max_gap_permutation_test(rows, n_iter=400)["significant"]
prop("the permutation p is never zero (add-one) and never above 1", ok_pos)
prop("renaming the languages, keeping their order, does not change the p-value", ok_rename)
prop("the order rows arrive in does not change the p-value", ok_order)
prop("with no language gap at all, the test rarely calls one (under 1 in 5 of 40 runs)", null_sig <= 8)
prop("one language broken almost every time against zero elsewhere is called significant", ok_strong)

# The extremes pin the p-value exactly, which a vaguer check would miss.
_extreme = fake_rows({"en": 0.0, "a": 0.0, "b": 0.0, "c": 1.0}, 12, random.Random(1))
_px = engine.max_gap_permutation_test(_extreme, n_iter=500)
prop("when no shuffle is as extreme as the data, p is exactly 1/(n+1), never 0",
     close(_px["p"], 1 / 501, 1e-12))
# Nothing broke anywhere: every shuffle reproduces the observed gap exactly, so
# every one is a tie, and a tie must count as at least as extreme.
_ties = [{"id": f"{l}_{i}", "lang": l, "category": "c", "variant": 0, "broke": False, "error": None}
         for l in ("en", "a", "b", "c") for i in range(3)]
prop("when nothing broke anywhere, p is 1: ties count as at least as extreme",
     close(engine.max_gap_permutation_test(_ties, n_iter=300)["p"], 1.0, 1e-12))

passed = sum(1 for _, ok in CASES if ok)
for name, ok in CASES:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
print(f"\n{passed}/{len(CASES)} statistical properties hold")
sys.exit(0 if passed == len(CASES) else 1)
