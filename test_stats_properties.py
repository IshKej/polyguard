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


def _exact_max_gap_p(rows, ref="en", n_iter=2000, seed=12345):
    """The same test in exact fractions: the reference the float version must match."""
    from fractions import Fraction
    rows = sorted((r for r in rows if r.get("error") is None),
                  key=lambda r: (r["lang"], r.get("category", ""), r.get("variant", 0), r.get("id", "")))
    by = {}
    for r in rows:
        by.setdefault(r["lang"], []).append(bool(r["broke"]))
    sizes = {k: len(v) for k, v in by.items()}
    order = [k for k in sizes if k != ref]
    obs = max(Fraction(sum(by[k]), sizes[k]) for k in order) - Fraction(sum(by[ref]), sizes[ref])
    pool = [o for v in by.values() for o in v]
    rng, ge = random.Random(seed), 0
    for _ in range(n_iter):
        rng.shuffle(pool)
        i, rates = 0, {}
        for k in [ref] + order:
            rates[k] = Fraction(sum(pool[i:i + sizes[k]]), sizes[k])
            i += sizes[k]
        ge += max(rates[k] for k in order) - rates[ref] >= obs
    return (ge + 1) / (n_iter + 1)


# Gaps that are equal as fractions but reached through different counts
# (3/15 - 1/15 against 4/15 - 2/15) are unequal in floating point. The float
# test once dropped those exact ties and reported p too small.
_tie_rows = fake_rows({"en": 0.1, "a": 0.25, "b": 0.3, "c": 0.15, "d": 0.2}, 15, random.Random(2))
prop("tied gaps reached through different counts are counted (p matches exact fractions)",
     close(engine.max_gap_permutation_test(_tie_rows, n_iter=2000)["p"], _exact_max_gap_p(_tie_rows), 1e-12))

# --- the EXPLORATORY resource trend test --------------------------------------------
def _trend_case(rng: random.Random, n: int) -> tuple[dict, dict]:
    """Random per-language rates (multiples of 1/15, so ties are common) and shares."""
    codes = [f"l{i:02d}" for i in range(n)]
    return ({c: rng.randint(0, 15) / 15 for c in codes},
            {c: 10 ** rng.uniform(-3, 1.6) for c in codes})


ok_t_order = ok_t_rename = ok_t_range = ok_t_mono = True
for t in range(60):
    rng = random.Random(500 + t)
    rates, share = _trend_case(rng, rng.randint(5, 30))
    base = engine.resource_trend_test(rates, share, n_iter=300)
    items = list(rates.items())
    rng.shuffle(items)
    ok_t_order &= close(base["p"], engine.resource_trend_test(dict(items), share, n_iter=300)["p"], 1e-12)
    # Arbitrary new names, so the alphabetical order of the languages changes too.
    names = {c: f"{rng.random():.12f}" for c in rates}
    ren = engine.resource_trend_test({names[c]: r for c, r in rates.items()},
                                     {names[c]: s for c, s in share.items()}, n_iter=300)
    ok_t_rename &= close(base["p"], ren["p"], 1e-12) and close(base["rho"], ren["rho"], 1e-12)
    ok_t_range &= 1 / 301 - 1e-12 <= base["p"] <= 1 and (base["rho"] is None or -1 <= base["rho"] <= 1)
    # Ranks only: any increasing transform of the measure changes nothing.
    ok_t_mono &= close(base["p"], engine.resource_trend_test(
        rates, {c: s ** 3 + 7 for c, s in share.items()}, n_iter=300)["p"], 1e-12)
prop("trend test: the order rates arrive in does not change the p-value", ok_t_order)
prop("trend test: renaming the languages, in any order, changes neither p nor rho", ok_t_rename)
prop("trend test: p is never 0 (add-one) and never above 1, rho stays in [-1, 1]", ok_t_range)
prop("trend test: depends on the ranks of the measure only, so log or cube changes nothing", ok_t_mono)

ok_t_strong = True
for t in range(10):
    rng = random.Random(700 + t)
    n = rng.randint(12, 40)
    shares = sorted(10 ** rng.uniform(-3, 1.6) for _ in range(n))
    rates = {f"l{i}": 1 - i / n for i in range(n)}            # strictly falling with share
    res = engine.resource_trend_test(rates, {f"l{i}": s for i, s in enumerate(shares)}, n_iter=400)
    ok_t_strong &= (res["significant"] and close(res["rho"], -1.0, 1e-12)
                    and close(res["p"], 1 / 401, 1e-12))
prop("trend test: a strong monotone trend is detected, rho -1 and the smallest possible p",
     ok_t_strong)

_flat_share = {f"l{i}": 10 ** (i / 7 - 3) for i in range(25)}
prop("trend test: flat break rates are never significant, every shuffle ties, p is exactly 1",
     all(engine.resource_trend_test({c: v for c in _flat_share}, _flat_share, n_iter=300)["p"] == 1.0
         for v in (0.0, 0.2, 1.0)))

_null_sig = 0
for t in range(100):
    rates, share = _trend_case(random.Random(900 + t), 30)
    _null_sig += engine.resource_trend_test(rates, share, n_iter=199, seed=t)["significant"]
prop(f"trend test: with no relationship it rarely calls one (saw {_null_sig} of 100)",
     _null_sig <= 12)


def _exact_trend_p(rates, share, n_iter, seed):
    """The same test in exact fractions with sorted average ranks, as a reference."""
    from fractions import Fraction
    rows = sorted((share[c], r, c) for c, r in rates.items())

    def ranks(vals):
        srt = sorted(vals)
        return [Fraction(sum(i + 1 for i, w in enumerate(srt) if w == v), srt.count(v)) for v in vals]

    ry, rx = ranks([r for _, r, _ in rows]), ranks([s for s, _, _ in rows])
    my, mx = sum(ry) / len(ry), sum(rx) / len(rx)
    a, b = [v - my for v in ry], [v - mx for v in rx]
    obs = abs(sum(x * y for x, y in zip(a, b)))
    rng, perm, ge = random.Random(seed), b[:], 0
    for _ in range(n_iter):
        rng.shuffle(perm)
        ge += abs(sum(x * y for x, y in zip(a, perm))) >= obs
    return (ge + 1) / (n_iter + 1)


ok_t_exact = True
for t in range(8):
    rates, share = _trend_case(random.Random(1100 + t), 12)
    ok_t_exact &= close(engine.resource_trend_test(rates, share, n_iter=300, seed=t)["p"],
                        _exact_trend_p(rates, share, 300, t), 1e-12)
prop("trend test: tied ranks are handled exactly (p matches an exact fraction computation)",
     ok_t_exact)

passed = sum(1 for _, ok in CASES if ok)
for name, ok in CASES:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
print(f"\n{passed}/{len(CASES)} statistical properties hold")
sys.exit(0 if passed == len(CASES) else 1)
