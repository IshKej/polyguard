export const TIERS = ['high', 'mid', 'low']

// A set that spans whatever resource tiers the bank really has, filled round
// robin so it is as balanced as the bank allows and always the size it claims.
export function representative(languages, target = 12) {
  const buckets = Object.fromEntries(
    TIERS.map((t) => [t, languages.filter((l) => l.tier === t).map((l) => l.code)]),
  )
  const order = TIERS.filter((t) => buckets[t].length)
  const pick = []
  let i = 0
  while (pick.length < target && order.some((t) => buckets[t].length)) {
    const t = order[i % order.length]
    if (buckets[t].length) pick.push(buckets[t].shift())
    i += 1
  }
  return pick
}
