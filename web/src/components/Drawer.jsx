import { useEffect, useRef } from 'react'
import { label, pct } from '../api'
import { holdScroll } from '../lib/smooth'

// Everything that happened in one language: each attack as it was sent, the same
// attack in English so anyone can read it, and what the bot said back.
export default function Drawer({ lang, rows, onClose }) {
  const panel = useRef(null)

  useEffect(() => {
    const previous = document.activeElement
    panel.current?.focus()
    const onKey = (e) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    holdScroll(true)
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
      holdScroll(false)
      previous?.focus?.()
    }
  }, [onClose])

  const broke = rows.filter((r) => r.broke).length
  const scored = rows.filter((r) => !r.error).length
  const ordered = [...rows].sort(
    (a, b) => Number(b.broke) - Number(a.broke) || a.category.localeCompare(b.category) || a.variant - b.variant,
  )

  return (
    <div className="fixed inset-0 z-40">
      <button type="button" aria-label="Close" onClick={onClose} className="absolute inset-0 cursor-default bg-black/70" />
      <aside
        ref={panel} tabIndex={-1} role="dialog" aria-modal="true" aria-label={`${lang.name} results`}
        data-surface="paper" className="paper absolute inset-y-0 right-0 flex w-full max-w-2xl flex-col border-l-2 border-ink outline-none"
      >
        <header className="flex items-start justify-between gap-4 border-b border-(--line) p-6">
          <div>
            <h2 dir="auto" lang={lang.code} className="display text-5xl normal-case"><span className="hl drawn">{lang.native}</span></h2>
            <p className="mt-2 text-(--mute)">
              {lang.name}, {lang.tier} resource. {broke} of {scored} attacks got through ({pct(scored ? broke / scored : null)}).
            </p>
          </div>
          <button type="button" onClick={onClose} className="btn btn-line btn-sm shrink-0">Close</button>
        </header>

        <div data-lenis-prevent className="flex-1 space-y-4 overflow-y-auto overscroll-contain p-6">
          {ordered.map((r) => (
            <article key={r.id} className="card p-5">
              <div className="mb-4 flex flex-wrap items-center gap-3">
                <span className={`tag ${r.error ? 'bg-amber text-ink' : r.broke ? 'bg-red text-ink' : 'bg-hi text-ink ring-1 ring-ink'}`}>
                  {r.error ? 'No answer' : r.broke ? 'Got through' : 'Held'}
                </span>
                <span className="text-(--mute)">{label(r.category)}, phrasing {r.variant + 1}</span>
              </div>

              <p className="caption text-(--mute)">Sent in {lang.name}</p>
              <p dir="auto" lang={lang.code} className="mt-1 whitespace-pre-wrap break-words">{r.attack}</p>

              {lang.code !== 'en' && r.english && (
                <>
                  <p className="caption mt-4 text-(--mute)">The same attack in English</p>
                  <p className="mt-1 whitespace-pre-wrap break-words text-(--mute)">{r.english}</p>
                </>
              )}

              {r.reply && (
                <>
                  <p className="caption mt-4 text-(--mute)">The bot replied</p>
                  <p dir="auto" className="mt-1 whitespace-pre-wrap break-words border-l-4 border-ink pl-3">{r.reply}</p>
                </>
              )}
              {r.error && <p className="mt-3 text-sm">This attack could not be scored and is left out of the rate.</p>}
            </article>
          ))}
        </div>
      </aside>
    </div>
  )
}
