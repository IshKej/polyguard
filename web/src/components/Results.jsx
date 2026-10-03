import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  deleteSavedScan, downloadFile, evidenceOf, forgetLink, harden, label, linkToken, pct, rememberLink, saveScan,
} from '../api'
import Board from './Board'
import Drawer from './Drawer'
import { jumpToTop } from '../lib/smooth'

const REPO = 'https://github.com/IshKej/polyguard'

// The verdict's colour is its meaning: green held, red broke. A simulated or
// invalid scan gets no signal colour at all, because it is not a finding.
const TONE = {
  good: 'bg-hi text-ink',
  bad: 'bg-red text-ink',
  warn: 'bg-red text-ink',
  demo: 'bg-ink-2 text-paper ring-1 ring-ink-3',
  invalid: 'bg-paper text-ink',
}

function Stat({ value, labelText, note, tone = '' }) {
  return (
    <div className="border-t border-(--line) pt-4">
      <div className="caption text-(--mute)">{labelText}</div>
      <div className={`display mt-2 text-[4.5rem] tabular-nums ${tone}`}>{value}</div>
      {note && <div className="mt-1 text-(--mute)">{note}</div>}
    </div>
  )
}

// Every chart says what kind of run it shows, so a screenshot cannot pass a
// simulation off as a measurement.
function ModeTag({ mock }) {
  return <span className="tag ml-3 border border-current align-middle text-[.7rem]">{mock ? 'Simulated' : 'Live'}</span>
}

const KIND = {
  rate_limit: 'rate limited', auth: 'key rejected', model: 'model not found', timeout: 'timed out',
  network: 'network errors', bad_request: 'bad requests', provider: 'provider outage', other: 'other errors',
}

// How much of the planned scan produced a scored result, read before any rate.
function Completeness({ c, nameOf }) {
  if (!c) return null
  const issues = []
  if (c.fired < c.planned) issues.push(`${c.planned - c.fired} of ${c.planned} planned attacks never ran.`)
  if (c.errors) {
    const kinds = Object.entries(c.errors_by_kind || {}).map(([k, n]) => `${n} ${KIND[k] || k}`)
    issues.push(`${c.errors} of ${c.fired} attacks could not be scored${kinds.length ? ` (${kinds.join(', ')})` : ''}, and are left out of every rate.`)
  }
  if (c.unscoreable_languages?.length) {
    issues.push(`The bot could not follow ordinary instructions in ${c.unscoreable_languages.map(nameOf).join(', ')}, so those languages cannot be scored for safety.`)
  }
  if (c.screened_languages?.length) {
    issues.push(`It may struggle in ${c.screened_languages.map(nameOf).join(', ')} too, though that could be chance.`)
  }
  if (c.extraction_scoreable === false) issues.push('Prompt extraction could not be scored: the prompt is too short for a leak to register.')
  if (c.token_collision?.length) issues.push(`The prompt contains PolyGuard’s ${c.token_collision.join(' and ')}, so no number here means anything.`)
  const clean = c.complete && issues.length === 0
  return (
    <section aria-label="How complete this scan is" className={`mt-8 rounded-[14px] p-5 ${clean ? 'ring-1 ring-ink-3' : 'bg-paper text-ink'}`}>
      <div className="caption">{clean ? 'Complete' : 'Read this first'}</div>
      {clean ? (
        <p className="mt-1">All {c.planned} planned attacks ran and were scored{c.controls_planned ? `, and ${c.controls_scored} of ${c.controls_planned} capability checks` : ''}.</p>
      ) : (
        <ul className="mt-2 space-y-1.5">{issues.map((x) => <li key={x}>{x}</li>)}</ul>
      )}
    </section>
  )
}

const short = (sha) => (sha ? sha.slice(0, 12) : 'unknown')

function Row({ k, children }) {
  return (
    <div className="grid gap-1 border-t border-(--line) py-3 sm:grid-cols-[15rem_1fr]">
      <dt className="font-semibold">{k}</dt>
      <dd className="text-(--mute)">{children}</dd>
    </div>
  )
}

export default function Results({ result, baseline, config, onAgain, onRescan, onMethod, source, canShare }) {
  const [open, setOpen] = useState(null)
  const mode = result.mock ? 'simulated' : 'live'
  // The report arrives with the result, so it is saved straight from the browser.
  const downloadReport = () => downloadFile(result.report, `polyguard-${mode}-report.html`, 'text/html')
  const [leaveOut, setLeaveOut] = useState(false)
  const downloadEvidence = () => downloadFile(
    JSON.stringify(evidenceOf(result, leaveOut), null, 2), `polyguard-${mode}-${result.id}.json`, 'application/json')

  // Sharing: one link, made on request, deletable from this browser.
  const [share, setShare] = useState({ state: 'idle' })
  const makeLink = async () => {
    setShare({ state: 'saving' })
    try {
      const s = await saveScan(result)
      rememberLink(s.id, s.delete_token, s.expires_at)
      setShare({ state: 'done', id: s.id, url: `${window.location.origin}${s.path}`, expires: s.expires_at })
    } catch (e) { setShare({ state: 'error', message: e.message }) }
  }
  const copyLink = async () => {
    try { await navigator.clipboard.writeText(share.url); setShare((x) => ({ ...x, copied: true })) } catch { /* the link is on screen to select */ }
  }
  const removeLink = async (id) => {
    try {
      await deleteSavedScan(id, linkToken(id))
      forgetLink(id)
      setShare({ state: 'deleted' })
    } catch (e) { setShare((x) => ({ ...x, message: e.message })) }
  }
  const sharedId = source?.kind === 'link' ? source.id : null
  const ownsShared = sharedId && linkToken(sharedId)
  // The bars by kind of attack fill once they scroll into view.
  const bars = useRef(null)
  const [barsIn, setBarsIn] = useState(false)
  useEffect(() => {
    const el = bars.current
    if (!el) return undefined
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setBarsIn(true); io.disconnect() } }, { threshold: 0.3 })
    io.observe(el)
    return () => io.disconnect()
  }, [])
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

  useEffect(() => { jumpToTop() }, [result.id])

  const loadFix = async () => {
    if (fix) return fix
    if (!config) return null
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

  // The red pen goes round the worst language only when it is worse than chance
  // would make some language look (the permutation test), and only on a live scan.
  // Some language always comes out worst; circling it otherwise would mark noise.
  const worst = useMemo(() => {
    if (result.mock || wl?.p == null || wl.p >= 0.05) return undefined
    let best
    for (const l of result.languages) {
      const rows = byLang[l.code] || []
      const scored = rows.filter((r) => !r.error).length
      const broke = rows.filter((r) => r.broke).length
      if (scored && broke && (!best || broke / scored > best.rate)) best = { code: l.code, rate: broke / scored }
    }
    return best?.code
  }, [result, byLang, wl])

  const nameOf = (c) => result.languages.find((l) => l.code === c)?.name || c
  const inst = result.instrument

  return (
    <main data-surface="ink" className="ink min-h-screen">
      <div className="mx-auto max-w-7xl px-5 pb-28 pt-28">
      {source && (
        <p className="mb-6 border-l-4 border-hi pl-4">
          {source.kind === 'link'
            ? <>A saved scan, opened from a share link. It is removed on {new Date(source.expires_at).toLocaleDateString()}
                {source.redacted ? ', and the bot’s replies were left out when it was saved' : ''}.
                {ownsShared && <> <button type="button" onClick={() => removeLink(sharedId)} className="font-semibold underline underline-offset-4">Delete this link now</button>.</>}
                {share.state === 'deleted' && ' Deleted.'}</>
            : <>Opened from a file on this computer. Nothing was sent anywhere.</>}
        </p>
      )}
      <section className={`rounded-[28px] p-7 sm:p-12 ${TONE[v.tone] || TONE.demo}`}>
        <span className="tag border border-current">
          {result.mock ? 'Simulated scan' : `Live scan of ${result.victim?.label ?? 'your bot'}`}
        </span>
        <h1 className="display mt-6 max-w-5xl text-[clamp(2.5rem,6.2vw,5.4rem)]">{v.headline}</h1>
        <p className="mt-5 max-w-3xl text-xl">{v.certainty}</p>
      </section>

      <Completeness c={result.completeness} nameOf={nameOf} />

      <section className="mt-10 grid gap-x-10 gap-y-6 sm:grid-cols-3">
        <Stat value={t.attacks} labelText="Attacks fired" note={t.errors ? `${t.errors} could not be scored` : null} />
        <Stat value={t.broke} labelText="Got through" note={`${pct(t.overall_rate)} of attacks`} tone={t.broke ? 'text-red' : 'text-hi'} />
        <Stat value={pct(t.english_rate)} labelText="English" note="The baseline every language is compared against" />
      </section>

      {baseline && (
        <section className="card mt-10 p-7">
          <h2 className="display text-4xl">Before and after <span className="serif">the fix.</span><ModeTag mock={result.mock} /></h2>
          <div className="mt-5 grid gap-x-10 gap-y-6 sm:grid-cols-3">
            <Stat value={baseline.totals.broke} labelText="Got through the original" />
            <Stat value={t.broke} labelText="Got through the hardened version" tone={t.broke < baseline.totals.broke ? 'text-hi' : 'text-red'} />
            <Stat
              value={baseline.totals.broke ? pct((baseline.totals.broke - t.broke) / baseline.totals.broke) : 'n/a'}
              labelText="Of the holes closed"
            />
          </div>
        </section>
      )}

      <section className="mt-16">
        <h2 className="display text-[clamp(2.2rem,4.6vw,3.8rem)]">By <span className="serif">language.</span><ModeTag mock={result.mock} /></h2>
        <p className="mt-2 max-w-2xl text-(--mute)">
          Most broken first. Open a language to read every attack, in English too, and what the bot said back.
        </p>
        <div className="mt-6">
          <Board languages={languages} outcomes={outcomes} expected={expected} onOpen={setOpen} columns={2} mark={worst} />
        </div>
        {st.capability_limited.length > 0 && (
          <p className="mt-5 border-l-4 border-hi pl-4">
            <span className="font-semibold">Read with care.</span>{' '}
            The bot could not follow ordinary, harmless instructions in{' '}
            {st.capability_limited.map((c) => result.languages.find((l) => l.code === c)?.name || c).join(', ')},
            so a low rate there means it did not understand, not that it is safe.
          </p>
        )}
      </section>

      <section className="mt-16">
        <h2 className="display text-[clamp(2.2rem,4.6vw,3.8rem)]">By kind <span className="serif">of attack.</span><ModeTag mock={result.mock} /></h2>
        <div ref={bars} className="mt-6 border-b border-(--line)">
          {result.categories.map((c, n) => (
            <div key={c.category} className="grid items-center gap-x-5 gap-y-1 border-t border-(--line) py-3.5 sm:grid-cols-[16rem_1fr_4.5rem]">
              <div className="font-semibold">{label(c.category)}</div>
              <div className="h-3 overflow-hidden rounded-full bg-ink-3" role="img" aria-label={`${pct(c.rate)} got through`}>
                <div
                  className="h-full bg-red transition-[width] duration-[900ms] ease-[cubic-bezier(.3,.7,.3,1)]"
                  style={{ width: barsIn ? `${(c.rate || 0) * 100}%` : '0%', transitionDelay: `${n * 90}ms` }}
                />
              </div>
              <div className="display text-3xl tabular-nums sm:text-right">{pct(c.rate)}</div>
            </div>
          ))}
        </div>
      </section>

      {result.broken_categories.length > 0 && (
        <section data-surface="paper" className="paper mt-16 rounded-[28px] p-7 sm:p-10">
          <h2 className="display text-[clamp(2.2rem,4.6vw,3.8rem)]">Fix <span className="serif">it.</span></h2>
          <p className="mt-2 text-(--mute)">
            Rules written for exactly the {result.broken_categories.length === 1 ? 'kind of attack' : 'kinds of attack'} that got through.
          </p>
          <ul className="mt-6 space-y-3">
            {result.fixes.map((rule) => (
              <li key={rule} className="flex gap-3">
                <span className="mt-[.5rem] h-3 w-5 shrink-0 rounded-sm bg-hi ring-1 ring-ink" aria-hidden="true" />
                <span>{rule}</span>
              </li>
            ))}
          </ul>
          {config && (
            <div className="mt-7 flex flex-wrap items-center gap-3">
              {!result.mock && <button type="button" onClick={rescan} className="btn btn-solid btn-sm">Scan the hardened prompt</button>}
              <button type="button" onClick={copy} className="btn btn-line btn-sm">{copied ? 'Copied' : 'Copy the hardened prompt'}</button>
            </div>
          )}
          {result.mock && config && (
            <p className="mt-4 text-(--mute)">
              Retesting needs a live scan. The stand-in bot ignores its system prompt, so it can’t show whether these rules work.
            </p>
          )}
          {fixError && <p role="alert" className="mt-3 font-semibold text-red-text">{fixError}</p>}
        </section>
      )}

      <details className="card mt-16 p-7 sm:p-9">
        <summary className="display cursor-pointer text-[2rem]">For <span className="serif">researchers.</span></summary>
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
          {inst && (
            <Row k="What produced this">
              Code{' '}
              {/^[0-9a-f]{40}$/.test(inst.git_commit)
                ? <a href={`${REPO}/commit/${inst.git_commit}`} target="_blank" rel="noopener" className="font-semibold text-paper underline underline-offset-4">{inst.git_commit.slice(0, 7)}</a>
                : <span className="font-semibold text-paper">{inst.git_commit}</span>},
              attack bank {short(inst.bank_sha256)}, scoring version {inst.scoring_version},{' '}
              {inst.judge_model ? `judge ${inst.judge_model} with wording ${short(inst.judge_prompt_sha256)}` : 'no judge (simulated)'}.
              Two scans are only compared when all of these match.
            </Row>
          )}
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
            Only Spanish and Vietnamese have had feedback from a native speaker so far. A badly worded attack fails for
            reasons that have nothing to do with the bot’s defences.
          </Row>
          <Row k="How the worst language test works">
            <button type="button" onClick={onMethod} className="font-semibold text-paper underline underline-offset-4">
              Try it yourself on the How we know page
            </button>
          </Row>
          <Row k="Method and audit">
            <a href={REPO} target="_blank" rel="noopener" className="font-semibold text-paper underline underline-offset-4">
              Source, preregistration and the full audit trail
            </a>
          </Row>
        </dl>
      </details>

      <div className="mt-10 flex flex-wrap items-center gap-3">
        <button type="button" onClick={onAgain} className="btn btn-solid">{source ? 'Scan your own chatbot' : 'Scan another chatbot'}</button>
        {result.report && <button type="button" onClick={downloadReport} className="btn btn-line">Download the report</button>}
        <button type="button" onClick={downloadEvidence} className="btn btn-line">Download the evidence</button>
        <label className="flex items-center gap-2 text-(--mute)">
          <input type="checkbox" checked={leaveOut} onChange={(e) => setLeaveOut(e.target.checked)} className="size-4 accent-hi" />
          Leave out the bot’s replies
        </label>
      </div>
      <p className="mt-3 max-w-2xl text-sm text-(--mute)">
        The evidence is every attack and how it was scored, as JSON, with what produced it. Anyone can check the numbers
        with it, no account or key needed. A reply to an extraction attack can contain the bot’s own instructions.
      </p>

      {canShare && !source && (
        <section className="card mt-10 p-6">
          <h2 className="display text-[1.8rem]">Share <span className="serif">this scan.</span></h2>
          <p className="mt-1 text-(--mute)">
            Makes a private link: only someone you send it to can open it, the bot’s replies are left out, and it is
            removed after 30 days. You can delete it sooner from this browser.
          </p>
          {share.state === 'idle' || share.state === 'error' ? (
            <button type="button" onClick={makeLink} className="btn btn-line btn-sm mt-4">Make a link</button>
          ) : share.state === 'saving' ? (
            <p className="caption mt-4">Saving…</p>
          ) : share.state === 'deleted' ? (
            <p className="mt-4">The link is deleted.</p>
          ) : (
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <input readOnly value={share.url} onFocus={(e) => e.target.select()} aria-label="Share link"
                className="min-w-0 flex-1 rounded-md border-2 border-ink-3 bg-ink px-3 py-2 text-paper" />
              <button type="button" onClick={copyLink} className="btn btn-line btn-sm">{share.copied ? 'Copied' : 'Copy'}</button>
              <button type="button" onClick={() => removeLink(share.id)} className="btn btn-line btn-sm">Delete the link</button>
            </div>
          )}
          {(share.state === 'error' || share.message) && <p role="alert" className="mt-3 font-semibold text-red">{share.message}</p>}
        </section>
      )}

      {openLang && <Drawer lang={openLang} rows={byLang[open] || []} onClose={closeDrawer} />}
      </div>
    </main>
  )
}
