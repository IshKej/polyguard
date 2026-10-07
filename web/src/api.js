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

// A fresh key for each press of Launch. The server remembers it for an hour, so a
// request sent twice (a retry, a resubmit) is recognised as the same scan and is
// never started, or paid for, twice.
const newKey = () => (globalThis.crypto?.randomUUID
  ? crypto.randomUUID()
  : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`)

// Runs one scan and streams it back over a single request: onStart once, then
// onResult for every attack as it lands, then onDone with the finished result and
// its report. Nothing waits on the server between requests, which is what lets the
// API run on serverless hosting. Returns a function that stops the scan's request.
export function runScan(body, { onStart, onResult, onDone, onError }, key = newKey()) {
  const ctrl = new AbortController()
  let finished = false
  const fail = (message) => { if (!finished && !ctrl.signal.aborted) { finished = true; onError(new Error(message)) } }

  const read = async () => {
    let res
    try {
      res = await fetch(BASE + '/api/scan', {
        method: 'POST', headers: { ...headers(true), 'Idempotency-Key': key }, body: JSON.stringify(body), signal: ctrl.signal,
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

// --- Share links ---------------------------------------------------------------------
// A saved scan lives behind an unguessable link for 30 days. Whoever saved it gets a
// delete token, kept in this browser so the link can be removed from here later.
export const saveScan = (result, keepReplies = false) =>
  call('/api/scans', { method: 'POST', headers: headers(true), body: JSON.stringify({ result, keep_replies: keepReplies }) })

export const getSavedScan = (id) => call(`/api/scans/${encodeURIComponent(id)}`)

export async function deleteSavedScan(id, token) {
  let res
  try {
    res = await fetch(`${BASE}/api/scans/${encodeURIComponent(id)}`, { method: 'DELETE', headers: { 'X-Delete-Token': token } })
  } catch {
    throw new Error("Can't reach the PolyGuard server.")
  }
  if (res.status !== 204) throw new Error('That link could not be deleted. It may already be gone.')
}

const LINKS = 'polyguard.links'
const readLinks = () => { try { return JSON.parse(localStorage.getItem(LINKS) || '{}') } catch { return {} } }
const writeLinks = (v) => { try { localStorage.setItem(LINKS, JSON.stringify(v)) } catch { /* private mode */ } }
export const rememberLink = (id, token, expires) => writeLinks({ ...readLinks(), [id]: { token, expires } })
export const linkToken = (id) => readLinks()[id]?.token || null
export const forgetLink = (id) => { const l = readLinks(); delete l[id]; writeLinks(l) }

// --- The game's crowd numbers --------------------------------------------------------
// Fire and forget: a lost answer is a lost data point, never an error for a player.
export const postGameAnswer = (item_id, answered_attack) =>
  fetch(`${BASE}/api/game/answer`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ item_id, answered_attack }), keepalive: true,
  }).catch(() => {})

export const getGameStats = () => call('/api/game/stats')

// --- Evidence ------------------------------------------------------------------------
// The whole result as JSON, every attack with its verdict, for anyone checking the
// work without an account or a key. The bot's replies can be left out, because a
// reply to an extraction attack can contain the bot's own system prompt.
export function evidenceOf(result, leaveOutReplies) {
  const { report: _report, ...rest } = result
  if (!leaveOutReplies) return rest
  return { ...rest, results: rest.results.map((r) => ({ ...r, reply: '', reply_redacted: true })) }
}

export function downloadFile(text, filename, type) {
  const url = URL.createObjectURL(new Blob([text], { type }))
  const a = Object.assign(document.createElement('a'), { href: url, download: filename })
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}

// A result saved earlier with downloadFile, opened again with no server involved.
export function readResultFile(text) {
  let r
  try { r = JSON.parse(text) } catch { throw new Error('That file is not JSON.') }
  if (r?.schema === 'polyguard.scan-file/1') {
    throw new Error('That file is from the command line. Open it with: python cli.py report <file> --html report.html')
  }
  if (r?.schema !== 'polyguard.scan/1' || !Array.isArray(r.results) || !Array.isArray(r.languages) || !r.verdict) {
    throw new Error('That is not a PolyGuard scan saved from this site.')
  }
  return r
}

// The opening sentence of an attack, cut before its payload.
export function firstSentence(text = '') {
  const m = text.trim().match(/^.+?[.!?。।؟]/)
  return (m ? m[0] : text.split(':')[0]).trim()
}

export const pct = (v) => (v === null || v === undefined ? 'n/a' : `${Math.round(v * 100)}%`)
export const label = (category) => category.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase())
