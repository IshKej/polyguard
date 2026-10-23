import DATA from '../review-data.json'
import { PEOPLE_DETAIL, PEOPLE_LINE, REVIEWERS } from '../lib/people'

// Native review, language by language. Generated from native_review.json (the
// public status file) and the bank by review_scores.py. A reviewer's name appears
// only where they accepted credit; everyone else is "Native speaker (name
// withheld)" (verify_all 2h). Integrated feedback is not a validation.
const REPO = 'https://github.com/IshKej/polyguard'
const TIERS = [['high', 'High resource'], ['mid', 'Mid resource'], ['low', 'Low resource']]
// Order and look of each status. Shape and text carry it, not colour alone, and
// lime and red stay reserved for held and got through elsewhere on the site.
const LOOK = {
  integrated: { short: 'integrated', cls: 'bg-ink text-paper' },
  integrated_in_part: { short: 'in part', cls: 'border-2 border-ink bg-[repeating-linear-gradient(135deg,var(--color-paper-2)_0_5px,transparent_5px_9px)]' },
  feedback_no_corrections: { short: 'feedback, no edits', cls: 'border-2 border-dashed border-ink' },
  under_way: { short: 'under way', cls: 'border-[1.5px] border-dotted border-ink' },
  requested: { short: 'requested', cls: 'border-[1.5px] border-dotted border-(--mute) text-(--mute)' },
  source: { short: 'source', cls: 'border-[1.5px] border-ink font-semibold' },
  none: { short: '', cls: 'bg-(--card) text-(--mute)' },
}
const ORDER = ['integrated', 'integrated_in_part', 'feedback_no_corrections', 'under_way', 'requested', 'none']
const LABEL = { ...DATA.statuses, none: 'No native review yet', source: 'English, the source language' }

export default function ReviewCoverage({ onBack, onWhy }) {
  const langs = DATA.languages
  const count = (s) => langs.filter((l) => l.status === s).length
  const reviewed = langs.filter((l) => ['integrated', 'integrated_in_part', 'feedback_no_corrections'].includes(l.status))
    .sort((a, b) => ORDER.indexOf(a.status) - ORDER.indexOf(b.status) || a.name.localeCompare(b.name))
  const pending = langs.filter((l) => ['under_way', 'requested'].includes(l.status))
  return (
    <main>
      <section data-surface="ink" className="ink">
        <div className="mx-auto max-w-7xl px-5 pb-16 pt-28 sm:pb-20">
          <button type="button" onClick={onBack} className="caption mb-6 text-[.8rem] underline underline-offset-4">Back</button>
          <h1 className="display max-w-4xl text-[clamp(2.1rem,4.4vw,3.6rem)]">Native review, language by language.</h1>
          <p className="mt-7 max-w-2xl text-lg text-(--mute)">
            Every language PolyGuard tests, and where a native speaker has read its lines. Feedback received and
            integrated is not a validation: no language is marked as reviewed in the bank, and the automated
            translation score sits beside every result either way.
          </p>
          <p className="mt-4 max-w-2xl text-(--mute)" data-reviewers={REVIEWERS}>
            {PEOPLE_LINE} {PEOPLE_DETAIL}
          </p>
          <ul className="mt-8 flex flex-wrap gap-x-8 gap-y-3" aria-label="Totals">
            {ORDER.map((s) => (
              <li key={s}>
                <div className="display text-[2rem] tabular-nums">{count(s)}</div>
                <div className="max-w-[11rem] text-[.8rem] text-(--mute)">{LABEL[s]}</div>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section data-surface="paper" className="paper">
        <div className="mx-auto max-w-7xl px-5 py-14">
          <figure className="rounded-[10px] border-2 border-ink p-4 sm:p-5" aria-label="Review status of every language">
            <ul className="flex flex-wrap gap-x-5 gap-y-2 text-[.8rem]" aria-label="Key">
              {[...ORDER, 'source'].map((s) => (
                <li key={s} className="flex items-center gap-1.5">
                  <i className={`inline-block h-3.5 w-5 rounded-[3px] ${LOOK[s].cls}`} />
                  <span className="text-(--mute)">{LABEL[s]}</span>
                </li>
              ))}
            </ul>
            {TIERS.map(([tier, label]) => {
              const row = langs.filter((l) => l.tier === tier).sort((a, b) => a.name.localeCompare(b.name))
              return (
                <div key={tier} className="mt-3 grid gap-2 border-t border-(--line) pt-3 md:grid-cols-[8.5rem_minmax(0,1fr)]">
                  <h2 className="text-[.85rem] font-semibold md:pt-1">{label} ({row.length})</h2>
                  <ul className="flex flex-wrap gap-1.5">
                    {row.map((l) => (
                      <li key={l.code} data-status={l.status} aria-label={`${l.name}: ${LABEL[l.status]}`}
                        className={`rounded-[5px] px-2 py-1 text-[.8rem] leading-tight ${LOOK[l.status].cls}`}>
                        <span lang={l.code} title={l.native}>{l.name}</span>
                        {LOOK[l.status].short && <span className="block text-[.68rem]">{LOOK[l.status].short}</span>}
                      </li>
                    ))}
                  </ul>
                </div>
              )
            })}
          </figure>

          <h2 className="display mt-14 text-[clamp(1.5rem,2.6vw,2rem)]">Who reviewed what</h2>
          {/* On a phone, one card per language instead of a table that scrolls sideways. */}
          <ul className="mt-4 space-y-3 sm:hidden" aria-label="Languages with native speaker feedback">
            {reviewed.map((l) => (
              <li key={l.code} data-code={l.code} className="rounded-md border border-(--line) p-3 text-[.875rem]">
                <div className="flex items-baseline justify-between gap-3">
                  <span className="font-semibold">{l.name}</span>
                  <span className="whitespace-nowrap tabular-nums text-(--mute)">{l.returned}</span>
                </div>
                <div className="mt-1">{LABEL[l.status]}{l.rows_changed ? `: ${l.rows_changed} lines changed${l.rows_held ? `, ${l.rows_held} held` : ''}` : ''}</div>
                <div className="mt-1 text-(--mute)">{l.provenance === 'machine' ? 'Machine translation' : 'Written by the author'}. Credit: <span data-credit className="text-(--fg)">{l.credit}</span></div>
                {l.note && <div className="mt-1 text-[.8rem] text-(--mute)">{l.note}</div>}
              </li>
            ))}
          </ul>
          <div className="mt-4 hidden overflow-x-auto sm:block">
            <table className="w-full min-w-[40rem] text-left text-[.875rem]">
              <caption className="sr-only">Languages with native speaker feedback</caption>
              <thead>
                <tr className="border-b border-ink">
                  <th className="py-2 pr-3">Language</th><th className="pr-3">Written by</th><th className="pr-3">Status</th>
                  <th className="pr-3">Credit</th><th className="pr-3">Returned</th><th>Lines changed</th>
                </tr>
              </thead>
              <tbody>
                {reviewed.map((l) => (
                  <tr key={l.code} data-code={l.code} className="border-b border-(--line) align-top">
                    <td className="py-2 pr-3 font-semibold">{l.name}</td>
                    <td className="pr-3 text-(--mute)">{l.provenance === 'machine' ? 'machine translation' : 'the author'}</td>
                    <td className="pr-3">{LABEL[l.status]}</td>
                    <td className="pr-3" data-credit>{l.credit}</td>
                    <td className="whitespace-nowrap pr-3 tabular-nums">{l.returned}</td>
                    <td className="tabular-nums">{l.rows_changed}{l.rows_held ? `, ${l.rows_held} held` : ''}
                      {l.note && <span className="mt-1 block text-[.75rem] text-(--mute)">{l.note}</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-4 max-w-3xl text-[.85rem] text-(--mute)">
            A reviewer is named only where they accepted credit; everyone else is “{DATA.withheld}”. Waiting:{' '}
            {pending.map((l) => `${l.name} (${LABEL[l.status].toLowerCase()})`).join(', ')}.
          </p>
          <div className="mt-10 flex flex-wrap gap-3">
            <button type="button" onClick={onWhy} className="btn btn-solid">Why native review matters</button>
            <a href={`${REPO}/blob/main/docs/NATIVE_REVIEW.md`} target="_blank" rel="noopener" className="btn btn-line">The review log, row by row</a>
          </div>
        </div>
      </section>
    </main>
  )
}
