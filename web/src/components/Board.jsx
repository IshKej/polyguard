import { pct } from '../api'

// The departure board. Every row is a language; every small cell is one attack.
// A cell is unlit until its attack comes back, then flips to green if the bot
// held and red if the attack got through. When a language finishes, its status
// flips over the way a real board does.
//
// `outcomes` maps a language code to the results seen so far, in arrival order:
// 'held' | 'broke' | 'error'.

const LAMP = {
  held: 'bg-lamp-green',
  broke: 'bg-lamp-red',
  error: 'bg-transparent shadow-[inset_0_0_0_1.5px_var(--color-lamp-amber)]',
}

function rowStatus(seen, expected) {
  const broke = seen.filter((s) => s === 'broke').length
  const scored = seen.filter((s) => s !== 'error').length
  if (!seen.length) return { text: 'Waiting', tone: 'text-lamp-grey', broke, scored }
  if (seen.length < expected) return { text: 'Scanning', tone: 'text-lamp-amber', broke, scored }
  if (!scored) return { text: 'No answer', tone: 'text-lamp-amber', broke, scored }
  if (broke) return { text: `${broke} got through`, tone: 'text-lamp-red', rate: pct(broke / scored), broke, scored }
  return { text: 'Held', tone: 'text-lamp-green', rate: '0%', broke, scored }
}

function Row({ lang, seen, expected, onOpen, compact }) {
  const st = rowStatus(seen, expected)
  const Tag = onOpen ? 'button' : 'div'
  const sameName = !lang.native || lang.native === lang.name
  return (
    <Tag
      type={onOpen ? 'button' : undefined}
      onClick={onOpen ? () => onOpen(lang.code) : undefined}
      aria-label={onOpen ? `${lang.name}: ${st.text}. Open details.` : undefined}
      className={`grid w-full items-center gap-x-4 gap-y-1.5 border-t border-white/12 text-left ${
        compact ? 'grid-cols-[minmax(0,1fr)_auto] py-2' : 'grid-cols-[minmax(0,1fr)_auto] py-2 sm:grid-cols-[minmax(0,1fr)_auto_8.75rem]'
      } ${onOpen ? 'cursor-pointer hover:bg-white/8 focus-visible:bg-white/8' : ''}`}
    >
      {/* Native name first, in its own script; the English name sits under it so
          neither is ever cut short. */}
      <div className={`min-w-0 ${compact ? 'flex items-baseline gap-2.5' : ''}`}>
        <div dir="auto" lang={lang.code} className={`font-semibold leading-tight text-white ${compact ? 'text-lg' : 'text-[1.3rem]'}`}>
          {lang.native || lang.name}
        </div>
        {!sameName && <div className={`text-lamp-grey ${compact ? 'text-xs' : 'text-[.8rem] leading-tight'}`}>{lang.name}</div>}
      </div>

      <div className={`flex gap-[3px] ${compact ? '' : 'order-3 col-span-2 sm:order-none sm:col-span-1'}`} aria-hidden="true">
        {Array.from({ length: expected }, (_, i) => {
          const state = seen[i]
          return (
            <span
              key={state ? `${i}-${state}` : i}
              className={`rounded-[2px] ${compact ? 'h-3.5 w-2' : 'h-[1.15rem] w-2'} ${
                state ? `${LAMP[state]} origin-top animate-flap` : 'bg-flap'
              }`}
            />
          )
        })}
      </div>

      <div className={`display flex items-baseline justify-end gap-2 whitespace-nowrap font-bold uppercase tracking-wide ${compact ? 'hidden' : 'text-[1.05rem]'}`}>
        <span key={st.text} className={`origin-top animate-flap ${st.tone}`}>{st.text}</span>
        {st.rate && <span className="w-10 text-right tabular-nums text-white">{st.rate}</span>}
      </div>
    </Tag>
  )
}

export default function Board({ languages, outcomes, expected, onOpen, compact = false, columns = 1, caption }) {
  const split = columns === 2 && languages.length > 8
  const half = Math.ceil(languages.length / 2)
  const groups = split ? [languages.slice(0, half), languages.slice(half)] : [languages]
  const head = (
    <div className="display hidden grid-cols-[minmax(0,1fr)_auto_8.75rem] gap-x-4 pb-2 text-sm font-semibold uppercase tracking-widest text-lamp-grey sm:grid">
      <span>Language</span>
      <span>Attacks</span>
      <span className="text-right">Status</span>
    </div>
  )
  return (
    <div className={`rounded-[6px] border border-board-edge bg-board text-white ${compact ? 'p-4' : 'p-5 sm:p-7'}`}>
      <div className={split ? 'grid gap-x-12 lg:grid-cols-2' : ''}>
        {groups.map((group, gi) => (
          <div key={gi}>
            {!compact && head}
            {group.map((lang) => (
              <Row key={lang.code} lang={lang} seen={outcomes[lang.code] || []} expected={expected} onOpen={onOpen} compact={compact} />
            ))}
          </div>
        ))}
      </div>
      {caption && <p className="mt-3 border-t border-white/12 pt-3 text-sm text-lamp-grey">{caption}</p>}
    </div>
  )
}
