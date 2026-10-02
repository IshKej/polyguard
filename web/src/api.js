// The only place the app talks to the server. Every function either returns data
// or throws an Error whose message is safe to show a person.

const BASE = import.meta.env.VITE_API_URL ?? ''
const PASS_KEY = 'polyguard.passcode'

export const getPasscode = () => sessionStorage.getItem(PASS_KEY) || ''
export const setPasscode = (v) => (v ? sessionStorage.setItem(PASS_KEY, v) : sessionStorage.removeItem(PASS_KEY))

function headers(json) {
  const h = {}
  if (json) h['Content-Type'] = 'application/json'
  const p = getPasscode()
  if (p) h['X-PolyGuard-Passcode'] = p
  return h
}

async function call(path, options = {}) {
  let res
  try {
    res = await fetch(BASE + path, options)
  } catch {
    throw new Error("Can't reach the PolyGuard server. Is it running?")
  }
  if (!res.ok) {
    let detail = ''
    try {
      const body = await res.json()
      detail = typeof body.detail === 'string' ? body.detail : ''
    } catch { /* not JSON */ }
    throw new Error(detail || `The server answered ${res.status}.`)
  }
  return res.json()
}

export const getMeta = () => call('/api/meta', { headers: headers(false) })

export const startScan = (body) =>
  call('/api/scans', { method: 'POST', headers: headers(true), body: JSON.stringify(body) })

export const getResult = (id) => call(`/api/scans/${id}`)

// Real messages from the bank for the spot the attack game.
export const getGame = () => call('/api/game')

export const harden = (prompt, broken_categories) =>
  call('/api/harden', { method: 'POST', headers: headers(true), body: JSON.stringify({ prompt, broken_categories }) })

export const reportUrl = (id) => `${BASE}/api/scans/${id}/report`

// Streams one scan. Calls onResult for every attack as it lands and resolves
// when the server says the scan is done. Returns a function that stops listening.
export function streamScan(id, { onResult, onDone, onError }) {
  const es = new EventSource(`${BASE}/api/scans/${id}/stream`)
  let finished = false
  es.addEventListener('result', (e) => onResult(JSON.parse(e.data)))
  es.addEventListener('done', (e) => {
    finished = true
    es.close()
    const { error } = JSON.parse(e.data)
    if (error) onError(new Error(error))
    else onDone()
  })
  es.onerror = () => {
    if (finished) return
    es.close()
    onError(new Error('Lost the connection to the scan. Try again.'))
  }
  return () => { finished = true; es.close() }
}

// The opening sentence of an attack, cut before its payload.
export function firstSentence(text = '') {
  const m = text.trim().match(/^.+?[.!?。।؟]/)
  return (m ? m[0] : text.split(':')[0]).trim()
}

export const pct = (v) => (v === null || v === undefined ? 'n/a' : `${Math.round(v * 100)}%`)
export const label = (category) => category.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase())
