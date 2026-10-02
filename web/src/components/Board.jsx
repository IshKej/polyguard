import { pct } from '../api'

// The scan board, read like a timing screen. Every row is a language; every
// small cell is one attack. A cell is dark until its attack comes back, then
// turns highlighter if the bot held and red if the attack got through. When a
// language finishes, its status flips over.
//
// `outcomes` maps a language code to the results seen so far, in arrival order:
// 'held' | 'broke' | 'error'.

const LAMP = {
  held: 'bg-hi',
  broke: 'bg-red',
  error: 'bg-transparent shadow-[inset_0_0_0_1.5px_var(--color-amber)]',
}

function rowStatus(seen, expected) {
  const broke = seen.filter((s) => s === 'broke').length
  const scored = seen.filter((s) => s !== 'error').length
  if (!seen.length) return { text: 'Waiting', tone: 'text-mute-ink' }
  if (seen.length < expected) return { text: 'Scanning', tone: 'text-amber' }
  if (!scored) return { text: 'No answer', tone: 'text-amber' }
  if (broke) return { text: `${broke} got through`, tone: 'text-red', rate: pct(broke / scored) }
  return { text: 'Held', tone: 'text-hi', rate: '0%' }
}

// A red pen loop drawn by hand around one row. With `progress` (0 to 1) it is
// drawn as far as that; without it, it draws itself once.
function RedPen({ progress }) {
  const scrubbed = progress !== undefined
  return (
    <svg aria-hidden="true" viewBox="0 0 400 60" preserveAspectRatio="none" className="pointer-events-none absolute -left-3 -top-1 z-10 h-[calc(100%+.5rem)] w-[calc(100%+1.25rem)] overflow-visible">
      <path
        d="M40 10 C 124 2, 316 3, 380 16 C 406 26, 372 52, 214 54 C 78 56, 4 49, 10 30 C 17 15, 66 8, 136 7"
        pathLength="1" fill="none" stroke="var(--color-red)" strokeWidth="2.4" strokeLinecap="round"
        className={scrubbed ? '' : 'animate-[pen_.9s_.4s_cubic-bezier(.6,0,.3,1)_both]'}
        style={{ strokeDasharray: 1, strokeDashoffset: scrubbed ? 1 - Math.min(1, Math.max(0, progress)) : undefined }}
      />
    </svg>
  )
}

function Row({ lang, seen, expected, onOpen, compact, marked, markProgress }) {
  const st = rowStatus(seen, expected)
  const Tag = onOpen ? 'button' : 'div'
  const sameName = !lang.native || lang.native === lang.name
  return (
    <Tag
      type={onOpen ? 'button' : undefined}
      onClick={onOpen ? () => onOpen(lang.code) : undefined}
      aria-label={onOpen ? `${lang.name}: ${st.text}. Open details.` : undefined}
      className={`group relative grid w-full items-center gap-x-4 gap-y-1.5 border-t border-ink-3 text-left transition-colors duration-150 hover:bg-ink-3/45 focus-visible:bg-ink-3/45 ${
        compact ? 'grid-cols-[minmax(0,1fr)_auto] py-2 pl-3' : 'grid-cols-[minmax(0,1fr)_auto] py-2.5 pl-3 sm:grid-cols-[minmax(0,1fr)_auto_11.5rem]'
      } ${onOpen ? 'cursor-pointer' : ''}`}
    >
      {marked && <RedPen progress={markProgress} />}
      {/* The row under the cursor gets a highlighter edge, the way a finger runs down a list. */}
      <span aria-hidden="true" className="absolute inset-y-1 left-0 w-1 origin-top scale-y-0 rounded-full bg-hi transition-transform duration-150 group-hover:scale-y-100 group-focus-visible:scale-y-100" />
      <div className={`min-w-0 ${compact ? 'flex items-baseline gap-2.5' : ''}`}>
        <div dir="auto" lang={lang.code} className={`font-semibold leading-tight text-paper ${compact ? 'text-lg' : 'text-[1.3rem]'}`}>
          {lang.native || lang.name}
        </div>
        {!sameName && <div className={`caption text-mute-ink ${compact ? 'text-[.68rem]' : ''}`}>{lang.name}</div>}
      </div>

      <div className={`flex gap-[3px] ${compact ? '' : 'order-3 col-span-2 sm:order-none sm:col-span-1'}`} aria-hidden="true">
        {Array.from({ length: expected }, (_, i) => {
          const state = seen[i]
          return (
            <span
              key={state ? `${i}-${state}` : i}
              className={`rounded-[2px] ${compact ? 'h-3.5 w-2' : 'h-5 w-2'} ${state ? `${LAMP[state]} origin-top animate-flap` : 'bg-ink-3'}`}
            />
          )
        })}
      </div>

      <div className={`display flex items-baseline justify-end gap-2 whitespace-nowrap pr-3 ${compact ? 'hidden' : 'text-[.82rem]'}`}>
        <span key={st.text} className={`origin-top animate-flap ${st.tone}`}>{st.text}</span>
        {st.rate && <span className="w-11 text-right tabular-nums text-paper">{st.rate}</span>}
      </div>
    </Tag>
  )
}

export default function Board({ languages, outcomes, expected, onOpen, compact = false, columns = 1, caption, mark, markProgress }) {
  const split = columns === 2 && languages.length > 8
  const half = Math.ceil(languages.length / 2)
  const groups = split ? [languages.slice(0, half), languages.slice(half)] : [languages]
  const head = (
    <div className="caption hidden grid-cols-[minmax(0,1fr)_auto_11.5rem] gap-x-4 pb-2.5 pl-3 pr-3 text-mute-ink sm:grid">
      <span>Language</span>
      <span>Attacks</span>
      <span className="text-right">Status</span>
    </div>
  )
  return (
    <div className={`rounded-[14px] bg-ink-2 text-paper ring-1 ring-ink-3 ${compact ? 'p-3 sm:p-4' : 'p-4 sm:p-6'}`}>
      <div className={split ? 'grid gap-x-10 lg:grid-cols-2' : ''}>
        {groups.map((group, gi) => (
          <div key={gi}>
            {!compact && head}
            {group.map((lang) => (
              <Row
                key={lang.code} lang={lang} seen={outcomes[lang.code] || []} expected={expected} onOpen={onOpen} compact={compact}
                marked={mark === lang.code} markProgress={markProgress}
              />
            ))}
          </div>
        ))}
      </div>
      {caption && <p className="caption mt-3 border-t border-ink-3 pl-3 pt-3 text-mute-ink">{caption}</p>}
    </div>
  )
}
