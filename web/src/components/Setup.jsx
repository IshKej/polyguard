import { useMemo, useState } from 'react'
import { getPasscode, label, setPasscode } from '../api'
import { TIERS, representative } from '../lib/languages'

function Step({ n, title, hint, children }) {
  return (
    <section className="card p-6 sm:p-8">
      <div className="mb-7 flex items-start gap-4">
        <span className="display grid size-12 shrink-0 place-items-center rounded-md bg-ink text-2xl text-hi" aria-hidden="true">{n}</span>
        <div>
          <h2 className="display text-[2rem]">{title}</h2>
          {hint && <p className="mt-1 text-(--mute)">{hint}</p>}
        </div>
      </div>
      {children}
    </section>
  )
}

// A toggle that reads like a marked word: ink when on, outlined when off, and
// the highlighter passes under it while the cursor is there.
function Chip({ on, onClick, children }) {
  return (
    <button
      type="button" aria-pressed={on} onClick={onClick}
      className={`hl-hover rounded-md border-2 px-4 py-2 text-base font-semibold transition-colors ${
        on ? 'border-ink bg-ink text-paper' : 'border-(--line) text-(--mute) hover:border-ink hover:text-ink'
      }`}
    >
      {on ? children : <span className="hl">{children}</span>}
    </button>
  )
}

export default function Setup({ meta, initial, onLaunch, onBack, onUnlock }) {
  const examples = meta.examples
  const [exampleName, setExampleName] = useState(initial?.exampleName ?? examples[0]?.name ?? '')
  const [prompt, setPrompt] = useState(initial?.prompt ?? examples[0]?.prompt ?? '')
  const all = useMemo(() => meta.languages.map((l) => l.code), [meta])
  const quick = useMemo(() => representative(meta.languages), [meta])
  const [langs, setLangs] = useState(initial?.langs ?? all)
  const [cats, setCats] = useState(initial?.categories ?? meta.categories)
  const [phrasings, setPhrasings] = useState(initial?.phrasings ?? 3)
  const [model, setModel] = useState(initial?.model ?? meta.default_model)
  const [pass, setPass] = useState(getPasscode())
  const [passError, setPassError] = useState('')

  const attacks = langs.length * cats.length * phrasings
  const ready = prompt.trim() && langs.length && cats.length
  const same = (a, b) => a.length === b.length && a.every((x) => b.includes(x))
  const preset = same(langs, all) ? 'all' : same(langs, quick) ? 'quick' : 'custom'
  const tiersPresent = TIERS.filter((t) => meta.languages.some((l) => l.tier === t))
  const hasLow = tiersPresent.includes('low')
  const locked = meta.live_configured && meta.needs_passcode && !meta.live

  const pickExample = (ex) => { setExampleName(ex.name); setPrompt(ex.prompt) }
  const toggle = (list, set, v) => set(list.includes(v) ? list.filter((x) => x !== v) : [...list, v])

  const unlock = async (e) => {
    e.preventDefault()
    setPasscode(pass)
    const ok = await onUnlock()
    setPassError(ok ? '' : 'That passcode did not unlock live scans.')
    if (!ok) setPasscode('')
  }

  return (
    <main data-surface="paper" className="paper min-h-screen">
      <div className="ruler" />
      <div className="mx-auto max-w-5xl px-5 pb-48 pt-28">
        <button type="button" onClick={onBack} className="hl-hover caption mb-6 text-[.8rem]"><span className="hl">Back</span></button>
        <h1 className="display text-[clamp(2.8rem,7vw,5.6rem)]">
          Set up <span className="serif">the scan.</span>
        </h1>

        <div className="mt-10 space-y-4">
          <Step n="1" title="Pick a chatbot" hint="Start from an example, or paste the system prompt your own bot runs on.">
            <div className="grid gap-3 sm:grid-cols-2">
              {examples.map((ex) => {
                const on = exampleName === ex.name
                return (
                  <button
                    key={ex.name} type="button" aria-pressed={on} onClick={() => pickExample(ex)}
                    className={`hl-hover rounded-md border-2 p-4 text-left transition-[transform,background-color,border-color] duration-150 hover:-translate-y-0.5 ${
                      on ? 'border-ink bg-ink text-paper' : 'border-(--line) bg-paper hover:border-ink'
                    }`}
                  >
                    <div className="display text-[1.35rem]">{on ? ex.name : <span className="hl">{ex.name}</span>}</div>
                    <div className={`mt-1 ${on ? 'text-mute-ink' : 'text-(--mute)'}`}>{ex.description}</div>
                  </button>
                )
              })}
            </div>
            <label htmlFor="prompt" className="caption mb-2 mt-7 block">System prompt</label>
            <textarea
              data-lenis-prevent
              id="prompt" value={prompt} maxLength={8000} rows={6}
              onChange={(e) => { setPrompt(e.target.value); setExampleName('') }}
              placeholder="You are a helpful assistant for ..."
              className="w-full resize-y rounded-md border-2 border-ink bg-paper p-4 text-base leading-relaxed text-ink placeholder:text-(--mute)"
            />
            <p className="mt-2 text-sm text-(--mute)">Edit it freely. This is exactly what the bot will run on.</p>
          </Step>

          <Step n="2" title="Pick the languages" hint="Every attack is written in each language you choose.">
            <div className="mb-5 flex flex-wrap gap-2">
              <Chip on={preset === 'all'} onClick={() => setLangs(all)}>All {all.length}</Chip>
              <Chip on={preset === 'quick'} onClick={() => setLangs(quick)}>Quick {quick.length}</Chip>
              {preset === 'custom' && <Chip on onClick={() => {}}>Custom, {langs.length} chosen</Chip>}
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-5">
              {meta.languages.map((l) => {
                const on = langs.includes(l.code)
                return (
                  <button
                    key={l.code} type="button" aria-pressed={on} onClick={() => toggle(langs, setLangs, l.code)}
                    className={`hl-hover relative rounded-md border-2 px-3 py-2.5 text-left transition-colors ${
                      on ? 'border-ink bg-ink text-paper' : 'border-(--line) text-(--mute) hover:border-ink hover:text-ink'
                    }`}
                  >
                    {on && <span aria-hidden="true" className="absolute right-2.5 top-2.5 size-2 rounded-full bg-hi" />}
                    <div dir="auto" lang={l.code} className="truncate pr-4 font-semibold">{on ? l.native : <span className="hl">{l.native}</span>}</div>
                    {l.native !== l.name && <div className={`caption mt-0.5 ${on ? 'text-mute-ink' : ''}`}>{l.name}</div>}
                  </button>
                )
              })}
            </div>
            {!hasLow && (
              <p className="mt-6 border-l-4 border-ink pl-4 text-base">
                <span className="font-semibold">No low resource languages yet.</span>{' '}
                The bank holds {tiersPresent.join(' and ')} resource languages so far, so the low versus high
                comparison can’t be made until the others are generated. Results per language still work.
              </p>
            )}
          </Step>

          <Step n="3" title="Pick the attacks" hint="Five ways of trying to make a bot break its own rules.">
            <div className="flex flex-wrap gap-2">
              {meta.categories.map((c) => (
                <Chip key={c} on={cats.includes(c)} onClick={() => toggle(cats, setCats, c)}>{label(c)}</Chip>
              ))}
            </div>
            <div className="mt-7 flex flex-wrap items-center gap-3">
              <span className="caption">Phrasings of each attack</span>
              <div className="flex gap-1" role="group" aria-label="Phrasings of each attack">
                {[1, 2, 3].map((n) => (
                  <button
                    key={n} type="button" aria-pressed={phrasings === n} onClick={() => setPhrasings(n)}
                    className={`display size-11 rounded-md border-2 text-xl transition-colors ${
                      phrasings === n ? 'border-ink bg-ink text-hi' : 'border-(--line) text-(--mute) hover:border-ink hover:text-ink'
                    }`}
                  >
                    {n}
                  </button>
                ))}
              </div>
              <span className="text-(--mute)">{phrasings === 3 ? 'Three is the most reliable.' : 'Fewer is faster, but noisier.'}</span>
            </div>
            {meta.live && meta.models.length > 1 && (
              <div className="mt-7">
                <label htmlFor="model" className="caption mr-3">Model under test</label>
                <select
                  id="model" value={model} onChange={(e) => setModel(e.target.value)}
                  className="rounded-md border-2 border-ink bg-paper px-4 py-2 text-ink"
                >
                  {meta.models.map((m) => <option key={m.key} value={m.key}>{m.label} ({m.vendor})</option>)}
                </select>
              </div>
            )}
          </Step>

          {locked && (
            <form onSubmit={unlock} className="card flex flex-wrap items-end gap-3 p-6">
              <div>
                <label htmlFor="pass" className="caption block">Passcode for live scans</label>
                <p className="mb-2 mt-1 text-sm text-(--mute)">Live scans on this site spend the owner’s credits, so they are locked.</p>
                <input
                  id="pass" type="password" value={pass} onChange={(e) => setPass(e.target.value)} autoComplete="off"
                  className="rounded-md border-2 border-ink bg-paper px-4 py-2 text-ink"
                />
              </div>
              <button type="submit" className="btn btn-line btn-sm">Unlock</button>
              {passError && <span role="alert" className="font-semibold text-red-text">{passError}</span>}
            </form>
          )}
        </div>
      </div>

      <div data-surface="ink" className="ink fixed inset-x-0 bottom-0 z-20">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-5 py-4">
          <div>
            <div className="display text-[1.7rem]">
              <span className="tabular-nums">{attacks}</span> attacks, <span className="serif">
                <span className="tabular-nums">{langs.length}</span> language{langs.length === 1 ? '' : 's'}
              </span>
            </div>
            <div className="text-sm text-(--mute)">
              {meta.live ? 'Live: real attacks on a real model.' : 'Simulated: no model is attacked, so the outcomes are made up.'}
            </div>
          </div>
          <button
            type="button" disabled={!ready}
            onClick={() => onLaunch({ prompt, exampleName, langs, categories: cats, phrasings, model })}
            className="btn btn-solid"
          >
            Launch scan
          </button>
        </div>
      </div>
    </main>
  )
}
