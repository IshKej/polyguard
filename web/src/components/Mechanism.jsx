import LOCAL from '../local-example.json'

// The hero's figure: one real attack, step by step, from the 2026-10-11 local
// scan. Every string is the scan's own (web/src/local-example.json, written by
// publish_example.py), so nothing here is typed by hand or made up.
const CODE = 'PWNED_7F3A'
// The reviewer's English for the Welsh reply (results/local/2026-10-11/HAND_REVIEW.md).
const GLOSS = { cy: 'Here is the answer:' }
const NAMES = { en: 'English', cy: 'Welsh, Cymraeg' }

// The code word, set apart. In the attack it is only text; in a reply that got
// through it is the evidence, so only there does it take the outcome colour.
function withCode(text, through) {
  const parts = text.split(CODE)
  return parts.flatMap((p, n) => (n === 0 ? [p] : [
    <span key={n} className={`inline-block rounded-[3px] px-1 leading-[1.3] font-semibold ${through ? 'bg-red text-ink' : 'border border-current'}`}>{CODE}</span>,
    p,
  ]))
}

function Step({ n, title, children }) {
  return (
    <li className="grid grid-cols-[1.75rem_minmax(0,1fr)] gap-3 border-t border-(--line) px-4 py-4 first:border-t-0 sm:gap-4 sm:px-5">
      <span className="grid size-7 place-items-center rounded-full border-[1.5px] border-current text-[.8rem] font-bold" aria-hidden="true">{n}</span>
      <div className="min-w-0">
        <h3 className="mb-2 text-[.9rem] font-semibold">{title}</h3>
        {children}
      </div>
    </li>
  )
}

export default function Mechanism() {
  const pair = ['en', 'cy']
  const field = 'rounded-md bg-(--card) px-3 py-2.5 text-[.95rem] leading-snug'
  return (
    <figure className="overflow-hidden rounded-[10px] border-2 border-ink bg-(--bg)" aria-labelledby="mechanism-caption">
      <ol>
        <Step n={1} title="The attack, sent as a customer message">
          <div className="grid gap-3 sm:grid-cols-2">
            {pair.map((code) => (
              <div key={code}>
                <div className="mb-1 text-[.8rem] text-(--mute)">{NAMES[code]}</div>
                <p lang={code} className={field}>{withCode(LOCAL.hero[code].attack, false)}</p>
              </div>
            ))}
          </div>
        </Step>
        <Step n={2} title="The trust boundary">
          <p className="rounded-md border-[1.5px] border-dashed border-current px-3 py-2.5 text-[.875rem] leading-snug text-(--mute)">
            {LOCAL.system_prompt}
          </p>
          <div className="mt-3 border-t-2 border-dashed border-red-text pt-1.5 text-right text-[.8rem] font-semibold text-red-text">
            The bot’s rules end here; the customer’s text begins.
          </div>
          <p className="mt-2 text-[.8rem] text-(--mute)">
            The bot reads both. A guardrail is only as good as its refusal to let the second override the first.
          </p>
        </Step>
        <Step n={3} title="What the bot replied">
          <div className="grid gap-3 sm:grid-cols-2">
            {pair.map((code) => {
              const h = LOCAL.hero[code]
              return (
                <p key={code} lang={code} className={field}>
                  {withCode(h.reply, h.kept)}
                  {GLOSS[code] && <span lang="en" className="ml-1 text-[.8rem] text-(--mute)">(“{GLOSS[code]}”)</span>}
                </p>
              )
            })}
          </div>
        </Step>
        <Step n={4} title="How it was judged">
          <div className="grid gap-3 text-[.8rem] text-(--mute) sm:grid-cols-2">
            {pair.map((code) => (
              <p key={code}>
                {LOCAL.hero[code].kept
                  ? <><span className="tag mr-2 bg-red text-ink">Got through</span>replied with the code word, as asked</>
                  : <><span className="tag mr-2 bg-hi text-ink">Held</span>refused, with no code word on its own</>}
              </p>
            ))}
          </div>
        </Step>
      </ol>
      <figcaption id="mechanism-caption" className="border-t border-(--line) bg-(--card) px-4 py-3 text-[.8rem] leading-relaxed text-(--mute) sm:px-5">
        Real replies from the local scan of {LOCAL.scanned}: a small open model ({LOCAL.model}) on a laptop, not a
        production chatbot. Welsh got through on {LOCAL.languages.cy.kept} of {LOCAL.per_language} attacks. Across all{' '}
        {Object.keys(LOCAL.languages).length} languages there were {LOCAL.kept} breaks in {LOCAL.attacks.toLocaleString('en-US')}{' '}
        attacks, and no significant gap between high and low resource languages (p = {LOCAL.tier_p.toFixed(3)}).
      </figcaption>
    </figure>
  )
}
