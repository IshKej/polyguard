import LOCAL from '../local-example.json'
import { NO } from './languages'

// What each language did in the 2026-10-11 local scan, for the hero.
export const CODE = 'PWNED_7F3A'

// Every language in the scan, with what it did. `kept` is how many attacks got
// through after review; English is the baseline.
export function outcomes() {
  return Object.entries(LOCAL.languages).map(([code, l]) => ({
    code, name: l.name, native: l.native, kept: l.kept, excluded: l.excluded,
  }))
}

// What the bubble says for one language. A break shows the code word the attack
// asked for; for Welsh, the reply itself. A hold shows "no" in that language
// where the bank has the word, and plain "Held." where it does not.
export function bubbleWords(code) {
  const l = LOCAL.languages[code]
  if (!l) return { word: 'No.', lead: null, broke: false }
  if (l.kept > 0) {
    const real = LOCAL.hero[code]
    const lead = real ? real.reply.split(CODE)[0].trim() || null : null
    return { word: CODE, lead, broke: true }
  }
  return { word: NO[code] || 'Held.', lead: null, broke: false, plain: !NO[code] }
}
