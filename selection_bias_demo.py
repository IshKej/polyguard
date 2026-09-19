"""
Why PolyGuard does not report "worst language vs English" as a finding.

This script reproduces the numbers quoted in AUDIT.md finding 19. Run it and you
get the table yourself; nothing here depends on the rest of the project.

The setup is a victim with NO language gap whatsoever: every language shares one
identical true break rate. Any gap that appears is therefore noise, by
construction. We then compute the statistic the app used to headline, namely

    worst observed language rate  -  English observed rate

and ask how big it gets anyway, purely because "worst of N" is a maximum and a
maximum runs high the more places you look.

The answer at PolyGuard's own target scale (87 languages, 5 categories x 3
phrasings = 15 attacks each) is that a perfectly even model still shows a
worst-minus-English gap averaging about +30 points, and a naive "more than 5
points means an equity gap" rule fires in roughly 98 runs out of 100.

That is the whole argument for `engine.max_gap_permutation_test`, which scores
the observed maximum against the distribution of the maximum under the null
instead of against a fixed threshold.

    python selection_bias_demo.py
"""
from __future__ import annotations

import random

TRUE_RATE = 0.29        # identical for every language: the null we are testing under
N_TRIALS = 4000         # simulated scans per configuration
THRESHOLD = 0.05        # the old app rule: gap > 5 points => "equity gap found"


def one_scan(n_langs: int, n_per_lang: int, p: float, rng: random.Random) -> float:
    """Simulate one whole scan and return worst-minus-English, in rate points."""
    rates = [sum(rng.random() < p for _ in range(n_per_lang)) / n_per_lang
             for _ in range(n_langs)]
    english = rates[0]                       # language 0 stands in for English
    return max(rates[1:]) - english


def main() -> None:
    rng = random.Random(7)                   # fixed seed: the table is reproducible
    print(__doc__.strip().split("\n\n")[0])
    print(f"\nEvery language has the SAME true break rate ({TRUE_RATE:.0%}).")
    print(f"Any gap below is pure noise. {N_TRIALS:,} simulated scans per row.\n")
    print(f"{'languages':>10}  {'attacks/lang':<18} {'mean gap':>9} {'median':>9} "
          f"{'fires >+5pt':>12}")
    print("-" * 62)
    for n_langs in (12, 20, 42, 87):
        for n_per_lang in (15, 5):
            gaps = sorted(one_scan(n_langs, n_per_lang, TRUE_RATE, rng)
                          for _ in range(N_TRIALS))
            mean = sum(gaps) / len(gaps)
            median = gaps[len(gaps) // 2]
            fires = sum(g > THRESHOLD for g in gaps) / len(gaps)
            label = "15 (3 phrasings)" if n_per_lang == 15 else "5 (1 phrasing)"
            print(f"{n_langs:>10}  {label:<18} {mean:>+9.1%} {median:>+9.1%} "
                  f"{fires:>11.0%}")

    print("\nRead the last column as: how often a model with no language gap at all")
    print("would still have been announced as having one. At 87 languages that is")
    print("98% of runs, which is why the uncorrected statistic was removed from the")
    print("app and replaced with engine.max_gap_permutation_test (AUDIT.md, 19).")


if __name__ == "__main__":
    main()
