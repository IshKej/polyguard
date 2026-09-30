import { useCallback, useEffect, useMemo, useState } from 'react'
import { harden, label, pct, reportUrl } from '../api'
import Board from './Board'
import Drawer from './Drawer'

const REPO = 'https://github.com/IshKej/polyguard'

// The verdict's colour is its meaning: green held, red broke. A simulated or
// invalid scan gets no signal colour at all, because it is not a finding.
const TONE = {
  good: 'bg-green text-on-signal',
  bad: 'bg-red text-on-signal',
  warn: 'bg-red text-on-signal',
  demo: 'bg-panel text-ink border-2 border-ink',
  invalid: 'bg-ink text-page',
}

function Stat({ value, labelText, note, tone = '' }) {
  return (
    <div className="border-t-2 border-ink pt-4">
      <div className="text-dim">{labelText}</div>
      <div className={`display mt-1 text-7xl tabular-nums ${tone}`}>{value}</div>
      {note && <div className="mt-1 text-dim">{note}</div>}
    </div>
  )
}

function Row({ k, children }) {
  return (
    <div className="grid gap-1 border-t border-rule py-3 sm:grid-cols-[15rem_1fr]">
      <dt className="font-semibold">{k}</dt>
      <dd className="text-dim">{children}</dd>
    </div>
  )
}

export default function Results({ result, baseline, config, onAgain, onRescan }) {
  const [open, setOpen] = useState(null)
  const [fix, setFix] = useState(null)
  const [fixError, setFixError] = useState('')
  const [copied, setCopied] = useState(false)
  const v = result.verdict
  const t = result.totals

  // The board, most broken first, with English marked as the baseline.
  const languages = useMemo(
    () => result.languages.map((l) => (l.code === 'en' ? { ...l, name: 'baseline' } : l)),
    [result],
  )
  const byLang = useMemo(() => {
    const m = {}
    for (const r of result.results) (m[r.lang] ||= []).push(r)
    for (const k of Object.keys(m)) m[k].sort((a, b) => a.category.localeCompare(b.category) || a.variant - b.variant)
    return m
  }, [result])
  const outcomes = useMemo(
    () => Object.fromEntries(Object.entries(byLang).map(([k, rows]) => [k, rows.map((r) => (r.error ? 'error' : r.broke ? 'broke' : 'held'))])),
    [byLang],
  )
  const expected = Math.max(1, ...Object.values(byLang).map((r) => r.length))

  useEffect(() => { window.scrollTo({ top: 0 }) }, [result.id])

  const loadFix = async () => {
    if (fix) return fix
    try {
      const f = await harden(config.prompt, result.broken_categories)
      setFix(f); setFixError('')
      return f
    } catch (e) { setFixError(e.message); return null }
  }
  const copy = async () => {
    const f = await loadFix()
    if (!f) return
    try {
      await navigator.clipboard.writeText(f.hardened)
      setCopied(true); setTimeout(() => setCopied(false), 1800)
    } catch { setFixError('Your browser blocked copying. Select the text by hand instead.') }
  }
  const rescan = async () => { const f = await loadFix(); if (f) onRescan(f.hardened) }

  // Stable, so the drawer does not re-run its focus handling on every render.
  const closeDrawer = useCallback(() => setOpen(null), [])
  const openLang = open && result.languages.find((l) => l.code === open)
  const st = result.stats
  const tt = v.tier_test
  const wl = st.worst_language_test

  return (
    <main className="on-page mx-auto max-w-6xl px-5 pb-28 pt-10">
      <section className={`rounded-[6px] p-7 sm:p-11 ${TONE[v.tone] || TONE.demo}`}>
        <span className="tag border-2 border-current">
          {result.mock ? 'Simulated scan' : `Live scan of ${result.victim?.label ?? 'your bot'}`}
        </span>
        <h1 className="display mt-5 max-w-5xl text-[clamp(2.5rem,6.4vw,5.25rem)]">{v.headline}</h1>
        <p className="mt-5 max-w-3xl text-xl">{v.certainty}</p>
      </section>

      <section className="mt-10 grid gap-x-10 gap-y-6 sm:grid-cols-3">
        <Stat value={t.attacks} labelText="Attacks fired" note={t.errors ? `${t.errors} could not be scored` : null} />
        <Stat value={t.broke} labelText="Got through" note={`${pct(t.overall_rate)} of attacks`} tone={t.broke ? 'text-red' : 'text-green'} />
        <Stat value={pct(t.english_rate)} labelText="English" note="The baseline every language is compared against" />
      </section>

      {baseline && (
        <section className="panel mt-10 p-7">
          <h2 className="display text-4xl">Before and after the fix</h2>
          <div className="mt-5 grid gap-x-10 gap-y-6 sm:grid-cols-3">
            <Stat value={baseline.totals.broke} labelText="Got through the original" />
            <Stat value={t.broke} labelText="Got through the hardened version" tone={t.broke < baseline.totals.broke ? 'text-green' : 'text-red'} />
            <Stat
              value={baseline.totals.broke ? pct((baseline.totals.broke - t.broke) / baseline.totals.broke) : 'n/a'}
              labelText="Of the holes closed"
            />
          </div>
        </section>
      )}

      <section className="mt-16">
        <h2 className="display text-5xl">By language</h2>
        <p className="mt-2 max-w-2xl text-dim">
          Most broken first. Open a language to read every attack, in English too, and what the bot said back.
        </p>
        <div className="mt-6">
          <Board languages={languages} outcomes={outcomes} expected={expected} onOpen={setOpen} columns={2} />
        </div>
        {st.capability_limited.length > 0 && (
          <p className="mt-5 border-l-4 border-accent pl-4">
            <span className="font-semibold">Read with care.</span>{' '}
            The bot could not follow ordinary, harmless instructions in{' '}
            {st.capability_limited.map((c) => result.languages.find((l) => l.code === c)?.name || c).join(', ')},
            so a low rate there means it did not understand, not that it is safe.
          </p>
        )}
      </section>

      <section className="mt-16">
        <h2 className="display text-5xl">By kind of attack</h2>
        <div className="mt-6 border-b-2 border-ink">
          {result.categories.map((c) => (
            <div key={c.category} className="grid items-center gap-x-5 gap-y-1 border-t-2 border-ink py-3 sm:grid-cols-[16rem_1fr_4rem]">
              <div className="font-semibold">{label(c.category)}</div>
              <div className="h-4 bg-rule" role="img" aria-label={`${pct(c.rate)} got through`}>
                <div className="h-full bg-red" style={{ width: `${(c.rate || 0) * 100}%` }} />
              </div>
              <div className="display text-3xl tabular-nums sm:text-right">{pct(c.rate)}</div>
            </div>
          ))}
        </div>
      </section>

      {result.broken_categories.length > 0 && (
        <section className="panel mt-16 p-7 sm:p-9">
          <h2 className="display text-5xl">Fix it</h2>
          <p className="mt-2 text-dim">
            Rules written for exactly the {result.broken_categories.length === 1 ? 'kind of attack' : 'kinds of attack'} that got through.
          </p>
          <ul className="mt-6 space-y-3">
            {result.fixes.map((rule) => (
              <li key={rule} className="flex gap-3">
                <span className="mt-[.55rem] size-2.5 shrink-0 bg-green" aria-hidden="true" />
                <span>{rule}</span>
              </li>
            ))}
          </ul>
          <div className="mt-7 flex flex-wrap items-center gap-3">
            {!result.mock && <button type="button" onClick={rescan} className="btn btn-solid btn-sm">Scan the hardened prompt</button>}
            <button type="button" onClick={copy} className="btn btn-line btn-sm">{copied ? 'Copied' : 'Copy the hardened prompt'}</button>
          </div>
          {result.mock && (
            <p className="mt-4 text-dim">
              Retesting needs a live scan. The stand-in bot ignores its system prompt, so it can’t show whether these rules work.
            </p>
          )}
          {fixError && <p role="alert" className="mt-3 font-semibold text-red">{fixError}</p>}
        </section>
      )}

      <details className="panel mt-16 p-7 sm:p-9">
        <summary className="display cursor-pointer text-4xl">For researchers</summary>
        <dl className="mt-6">
          <Row k="How the verdict was reached">{v.basis}</Row>
          <Row k="Low versus high resource">
            {tt
              ? `${pct(tt.low_mean)} across ${tt.n_low} low resource languages, ${pct(tt.high_mean)} across ${tt.n_high} high resource ones. Mann-Whitney U on one rate per language, p = ${tt.p?.toFixed(3)}${tt.effect != null ? `, Cliff’s delta ${tt.effect.toFixed(2)} (${tt.magnitude})` : ''}.`
              : 'Not computed: this scan did not include languages from both tiers.'}
          </Row>
          {wl?.p != null && (
            <Row k="Worst language against chance">
              Observed gap {pct(wl.observed)}, the gap chance alone produces {pct(wl.null_mean)}, permutation p ={' '}
              {wl.p.toFixed(3)} across {wl.n_langs} languages. Some language always comes out worst, so it is tested
              against the worst language chance would hand you.
            </Row>
          )}
          <Row k="Phrasings per attack">{st.phrasings} of 3</Row>
          {result.victim && (
            <Row k="Model under test">
              {result.victim.label} ({result.victim.vendor}).{' '}
              {result.victim.deterministic ? 'Temperature pinned to 0.' : 'Temperature could not be pinned, so these numbers are samples.'}
              {result.victim.thinking_forced && ' This model reasons before answering and cannot be stopped.'}
            </Row>
          )}
          {st.extraction_scoreable === false && (
            <Row k="Prompt extraction">
              The system prompt is too short for a leak to register, so those attacks could not score as broken.
            </Row>
          )}
          <Row k="Translations">
            No language in the bank has been reviewed by a native speaker yet. A badly worded attack fails for
            reasons that have nothing to do with the bot’s defences.
          </Row>
          <Row k="Method and audit">
            <a href={REPO} target="_blank" rel="noopener" className="font-semibold text-link underline underline-offset-4">
              Source, preregistration and the full audit trail
            </a>
          </Row>
        </dl>
      </details>

      <div className="mt-10 flex flex-wrap gap-3">
        <button type="button" onClick={onAgain} className="btn btn-solid">Scan another chatbot</button>
        <a href={reportUrl(result.id)} className="btn btn-line">Download the report</a>
      </div>

      {openLang && <Drawer lang={openLang} rows={byLang[open] || []} onClose={closeDrawer} />}
    </main>
  )
}
