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

// Real messages from the bank for the spot the attack game.
export const getGame = () => call('/api/game')

export const harden = (prompt, broken_categories) =>
  call('/api/harden', { method: 'POST', headers: headers(true), body: JSON.stringify({ prompt, broken_categories }) })

// Runs one scan and streams it back over a single request: onStart once, then
// onResult for every attack as it lands, then onDone with the finished result and
// its report. Nothing waits on the server between requests, which is what lets the
// API run on serverless hosting. Returns a function that stops the scan's request.
export function runScan(body, { onStart, onResult, onDone, onError }) {
  const ctrl = new AbortController()
  let finished = false
  const fail = (message) => { if (!finished && !ctrl.signal.aborted) { finished = true; onError(new Error(message)) } }

  const read = async () => {
    let res
    try {
      res = await fetch(BASE + '/api/scan', {
        method: 'POST', headers: headers(true), body: JSON.stringify(body), signal: ctrl.signal,
      })
    } catch {
      fail("Can't reach the PolyGuard server. Is it running?")
      return
    }
    if (!res.ok) {
      let detail = ''
      try {
        const j = await res.json()
        detail = typeof j.detail === 'string' ? j.detail : ''
      } catch { /* not JSON */ }
      fail(detail || `The server answered ${res.status}.`)
      return
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    try {
      for (;;) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        let cut
        while ((cut = buffer.indexOf('\n\n')) >= 0) {
          const block = buffer.slice(0, cut)
          buffer = buffer.slice(cut + 2)
          let event = 'message'
          let data = ''
          for (const line of block.split('\n')) {
            if (line.startsWith('event: ')) event = line.slice(7)
            else if (line.startsWith('data: ')) data += line.slice(6)
          }
          if (!data) continue // a keepalive comment while a live attack is in flight
          const payload = JSON.parse(data)
          if (event === 'start') onStart?.(payload)
          else if (event === 'result') onResult(payload)
          else if (event === 'done') {
            if (payload.error) fail(payload.error)
            else { finished = true; onDone(payload) }
          }
        }
      }
    } catch {
      fail('Lost the connection to the scan. Try again.')
      return
    }
    fail('The scan ended before it finished. Try again.')
  }
  read()
  return () => { finished = true; ctrl.abort() }
}

// The opening sentence of an attack, cut before its payload.
export function firstSentence(text = '') {
  const m = text.trim().match(/^.+?[.!?。।؟]/)
  return (m ? m[0] : text.split(':')[0]).trim()
}

export const pct = (v) => (v === null || v === undefined ? 'n/a' : `${Math.round(v * 100)}%`)
export const label = (category) => category.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase())
