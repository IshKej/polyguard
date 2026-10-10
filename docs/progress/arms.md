# Arms sprint, running log

Branch `sprint/arms`. Updated after every step. Implements the three answers to the open questions at the end of `docs/progress/defences.md`.

## Step 0, 2026-10-07: read and plan
- Read `defenses.py` (arms, placebo, lint), `engine.py` (`arm_table`, `sign_test`, `defense_evaluation`, `scan`), `cli.py` (`defend`), `PREREGISTRATION.md`, `docs/progress/defences.md`.
- Today one placebo is matched to the LONGER defence block, so `current` against placebo also carries a length gap (202 against 257 words with every category).
- Plan:
  1. `defenses.py`: arms become baseline, baseline_repeat, placebo_current, current, placebo_data_boundary, data_boundary. Each placebo is matched to its own defence. `REFERENCE_OF` names what each arm is compared with.
  2. `engine.arm_table`: compare each arm with its own reference, and attach the repeat against baseline difference (the noise) to every compared row.
  3. `cli.py defend`: run the repeat, pull in each defence's own placebo, `--rules all` by default, `scan` labelled exploratory in the output and the file.
  4. PREREGISTRATION deviation row, tests, mutants, all suites.

## Step 1, 2026-10-07: one placebo per defence, and a repeated baseline (`defenses.py`)
- `ARMS` is now baseline, baseline_repeat, placebo_current, current, placebo_data_boundary, data_boundary. `PLACEBO_OF` maps each defence to its placebo, `REFERENCE_OF` says what each arm is compared with (each defence with its own placebo, the repeat with the baseline), `NOISE_PAIR` is (baseline_repeat, baseline).
- `arm_blocks` matches each placebo to its own defence. Over all 31 category sets the worst length gap is 0.97% for current and 0.75% for data_boundary, limit 5%. With every category: placebo_current 202 words against current 202, placebo_data_boundary 257 against 257.
- baseline_repeat appends nothing; it is the unhardened prompt again.

## Step 2, 2026-10-07: `engine.arm_table`
- Signature is now `arm_table(arms, references=None, noise=None, exclude_langs=())`, defaults from `defenses.REFERENCE_OF` and `defenses.NOISE_PAIR` (local import, `defenses` is a leaf module).
- Each row has `vs_reference` (reference name, held-out diff, benign diff, languages paired, paired sign test) in place of `vs_placebo`, and `noise`: the repeat against baseline comparison, attached to every other compared row so it sits next to every difference. The repeat's own row carries no copy of itself.
- Same statistics as before (point differences, exact sign test paired by language); only which arm is the reference changed.

## Step 3, 2026-10-07: `cli.py defend`
- `--rules all` is the default and printed as the pre-registered headline. `--rules scan` prints an EXPLORATORY line saying the rules were selected from this bot's own scan; the file carries `analysis`.
- The baseline and its repeat always run; asking for a defence brings in its own placebo (`_parse_arms`).
- The table has a "compared with" column naming the reference, and under each defence a line with the noise beside it. A note after the table says what the noise means: simulated or temperature 0 deterministic victim, the repeat should match the baseline exactly (and says whether it did); a victim that cannot be pinned, the gap is the noise floor.
- File schema `polyguard.defence-arms/2`, with `references`, `noise_pair`, `victim_deterministic`.
- Simulated run on en,es,hi: every arm identical, the repeat matches the baseline exactly, as it must.

## Step 4, 2026-10-07: tests and mutants
- `test_engine.py`: arm registry and references, each placebo within 5% of its OWN defence over all 31 category sets, the two placebos differ like their defences, the repeat appends nothing; `arm_table` with a fixture where the repeat differs from the baseline and the two placebos break at different rates (so a wrong reference flips the sign); noise beside every defence row, absent without a repeat, never on the repeat itself; explicit references; exclusion applies to the noise too; `_parse_arms` pulls in the repeat and each defence's placebo and refuses the old single `placebo`; `--rules` defaults to `all`; simulated `defend` file and output say "pre-registered headline", `--rules scan` says EXPLORATORY; `noise_note` wording for simulated, temperature 0 and unpinnable victims. 254/254.
- `mutation_check.py`: three new mutants, all killed: placebos matched to the longer defence (the old behaviour), every defence compared with one placebo, noise measured against itself. 20/20.
- `verify_all.py` 119b: each defence against its own placebo, noise beside it, exactly zero in simulation.

## Step 5, 2026-10-07: PREREGISTRATION.md and README
- Appended one dated row (2026-10-07) after the last row of the deviation log, nothing else touched (diff is 1 insertion). It records the three changes and why: one placebo per defence, the repeated baseline as the noise shown beside every difference (expected zero on a temperature 0 victim, the noise floor otherwise), and `--rules all` as the pre-registered headline with `--rules scan` exploratory. Checked first that no live arm run exists in `results/` (no `defence-arms` file anywhere), so the row is recorded before any paid live data.
- README: the `defend` paragraph and the command comment describe the per defence placebos, the repeat and the headline default.
- No web file changed, so no web lint or build was needed.

## Step 6, 2026-10-09: all suites green, committed
- test_engine.py 254/254, test_stats_properties.py 32/32, api/test_api.py 92/92, verify_all.py 233/233, consistency.py clean, mutation_check.py 20/20 killed, rehearsal.py all planted conclusions recovered.
- Committed on `sprint/arms`. Not pushed, not merged. `docs/worklog.md` is left for the merge entry.
- Still open from the defences sprint: whether `docs/research/` should be committed so the section 3.2 citations resolve.
