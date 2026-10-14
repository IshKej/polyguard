// The one real result the site can show today, stated with its limits. Every
// number here is from the published 2026-10-11 scan and its 2026-10-12
// reanalysis (results/local/2026-10-11/), and none of it is a study result.
export const REPORT_URL = '/examples/real-scan-2026-10-11.html'
const EVIDENCE = 'https://github.com/IshKej/polyguard/tree/main/results/local/2026-10-11'

const FACTS = [
  ['Model', 'Qwen3.5 4B, a small open model running on a laptop, behind the example retail support bot. Not a production chatbot.'],
  ['Date', 'Scanned 2026-10-11. Reanalysed 2026-10-12 from the same saved replies under the current capability rule, with no new model calls.'],
  ['What was sent', 'All 73 languages: 1,095 attacks and 438 harmless control requests, each sent twice (876 in all).'],
  ['How it was judged', 'Another small open model (Gemma 4 E2B) judged every reply. It called 14 replies breaks. An AI assisted review of each of those, not yet checked by the author, kept 10, seven of them system prompt extraction.'],
  ['Languages', 'No gap between low and high resource languages (tier test p = 0.840). Yoruba was left out because the model followed only 1 of its 6 harmless requests.'],
]

const LIMITS = [
  'One small model, so this says nothing about the chatbots companies deploy.',
  '53 of the 73 languages are machine translated and not reviewed by a native speaker.',
  'It is not the pre-registered study: no paid or production chatbot scan has run yet.',
]

export default function LocalEvidence({ className = '' }) {
  return (
    <section data-surface="paper" className={`paper ${className}`} aria-labelledby="local-evidence">
      <div className="mx-auto max-w-7xl px-5 py-20">
        <p className="caption text-(--mute)">Real local diagnostic, not a simulated demo</p>
        <h2 id="local-evidence" className="mt-3 max-w-3xl text-[clamp(1.6rem,3vw,2.4rem)] font-bold leading-tight">
          One real scan so far, on a small model running on a laptop.
        </h2>
        <dl className="mt-10 grid max-w-4xl gap-x-10 gap-y-6 sm:grid-cols-[11rem_1fr]">
          {FACTS.map(([k, v]) => (
            <div key={k} className="contents">
              <dt className="caption pt-1 text-(--mute)">{k}</dt>
              <dd className="text-lg leading-relaxed">{v}</dd>
            </div>
          ))}
        </dl>
        <div className="mt-10 max-w-4xl border-l-4 border-ink pl-5">
          <p className="font-bold">What it cannot show</p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-(--mute)">
            {LIMITS.map((l) => <li key={l}>{l}</li>)}
          </ul>
        </div>
        <div className="mt-8 flex flex-wrap gap-3">
          <a href={REPORT_URL} className="btn btn-solid">Read the local-model report</a>
          <a href={EVIDENCE} target="_blank" rel="noopener" className="btn btn-line">Every reply, on GitHub</a>
        </div>
      </div>
    </section>
  )
}
