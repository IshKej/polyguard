import LOCAL from '../local-example.json'
import { bubbleWords } from '../lib/outcomes'

// The hero's object: two speech bubbles, cut like stickers from the test sheet.
// English says no. The other language answers with its REAL result from the
// 2026-10-11 local scan (web/src/local-example.json): held, or got through and
// torn open in red pen. Nothing here is an illustration.
// A speech bubble drawn by hand: a slightly uneven body, the tail at the lower left.
const BODY = 'M28 14C120 6 270 11 372 16C392 18 395 34 393 60C391 110 396 150 390 176C388 194 376 199 350 199L152 201L92 236L106 200L34 198C14 197 8 186 9 160C11 110 6 70 10 36C12 20 18 15 28 14Z'
// The tear across a bubble that gave way: where the pen went through.
const TEAR = 'M300 14L318 46L298 70L326 98L304 124L330 150'

function Bubble({ broke, label, labelLang, children, className = '', flip }) {
  return (
    <div className={`relative [container-type:inline-size] ${className}`}>
      <svg viewBox="-6 -6 420 256" className="block w-full overflow-visible" aria-hidden="true">
        <path d={BODY} transform="translate(9 10)" className="fill-ink" />
        <path
          d={BODY}
          className={broke ? 'fill-red' : 'fill-hi'}
          stroke="#1a1c15" strokeWidth="5" strokeLinejoin="round"
        />
        {broke && <path d={TEAR} fill="none" stroke="#eeede5" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" />}
      </svg>
      <div
        className={`absolute inset-x-[7%] top-[14%] bottom-[22%] grid place-items-center text-center text-ink ${flip ? 'animate-flap' : ''}`}
      >
        {children}
      </div>
      <div dir="auto" lang={labelLang} className="caption absolute left-[8%] top-[10%] whitespace-nowrap text-ink/70">
        {label}
      </div>
    </div>
  )
}

// The size the word is set at: short words fill the bubble, the code word fits.
// Wide characters (Chinese, Japanese, Korean) count twice.
const units = (w) => [...w].reduce((s, c) => s + (/[ᄀ-ᇿ⺀-鿿가-힯＀-￯]/.test(c) ? 2 : 1), 0)
const fit = (w) => {
  const u = units(w)
  return u <= 4 ? 'text-[26cqw]' : u <= 7 ? 'text-[17cqw]' : u <= 9 ? 'text-[12cqw]' : 'text-[9.6cqw]'
}

export default function HeroBubbles({ code, name, native, animate }) {
  const { word, lead, broke, plain } = bubbleWords(code)
  const l = LOCAL.languages[code]
  return (
    <figure className="relative mx-auto w-full max-w-[34rem] select-none" aria-labelledby="bubbles-caption">
      <Bubble label="English" labelLang="en" className="w-[62%]">
        <span lang="en" className={`font-display font-extrabold leading-none tracking-tight ${fit('No.')}`}>No.</span>
      </Bubble>
      <Bubble
        key={animate ? code : 'still'} flip={animate}
        broke={broke} label={native} labelLang={code}
        className="-mt-[6%] ml-auto w-[78%] rotate-[-3deg]"
      >
        <span className="block">
          {lead && <span lang={code} className="mb-[2cqw] block text-[6.4cqw] font-semibold leading-tight">{lead}</span>}
          <span
            lang={broke ? undefined : code} dir="auto"
            className={`block whitespace-nowrap font-display leading-none tracking-tight ${broke ? 'font-bold' : 'font-extrabold'} ${plain ? 'text-[15cqw]' : fit(word)}`}
          >
            {word}
          </span>
        </span>
      </Bubble>
      <figcaption id="bubbles-caption" className="mt-5 flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span dir="auto" lang={code} className="text-2xl font-bold leading-tight">{native}</span>
        <span className="caption text-(--mute)">{name}</span>
        <span className={`tag ${broke ? 'bg-red text-ink' : 'bg-hi text-ink'}`}>
          {broke ? `Got through ${l.kept} of ${LOCAL.per_language}` : `Held all ${LOCAL.per_language}`}
        </span>
        <span className="caption basis-full text-(--mute)">
          Real result: local scan of {LOCAL.scanned}, a small open model on a laptop. English held all{' '}
          {LOCAL.per_language}.
        </span>
      </figcaption>
    </figure>
  )
}
