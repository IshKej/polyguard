import { useSyncExternalStore } from 'react'

// PolyGuard follows the system's reduced motion setting by default: a visitor
// who asked their computer for less motion gets a still page. The Motion switch
// overrides that either way and is remembered on this device, so turning motion
// on is an explicit choice (Windows "Animation effects" off also reports reduced
// motion, and the switch is how a visitor who wants the motion gets it back).
// The switch is also the pause control for what moves on its own: the hero
// cycle, the marquee, the bubble.
const KEY = 'polyguard.motion'
const listeners = new Set()
const query = typeof window !== 'undefined' && window.matchMedia
  ? window.matchMedia('(prefers-reduced-motion: reduce)')
  : null

// 'on' or 'off' once the visitor has used the switch; null means "follow the system".
let choice = (() => {
  try {
    const v = localStorage.getItem(KEY)
    return v === 'on' || v === 'off' ? v : null
  } catch { return null }
})()
let systemReduce = Boolean(query?.matches)
const compute = () => (choice ? choice === 'off' : systemReduce)
let off = compute()

// The page's CSS reads this attribute, so stylesheet animations stop with the rest.
const mark = () => { document.documentElement.dataset.motion = off ? 'off' : 'on' }
mark()

const notify = () => listeners.forEach((cb) => cb())

// A visitor who changes the system setting mid visit is followed, unless they
// have already made their own choice with the switch.
query?.addEventListener?.('change', (e) => {
  systemReduce = e.matches
  if (!choice) {
    off = compute()
    mark()
    notify()
  }
})

export const isMotionOff = () => off

export function setMotionOff(next) {
  choice = next ? 'off' : 'on'
  off = next
  try { localStorage.setItem(KEY, choice) } catch { /* private mode */ }
  mark()
  notify()
}

const subscribe = (cb) => {
  listeners.add(cb)
  return () => listeners.delete(cb)
}

// True when motion is off, by the system setting or by the visitor's own choice.
export const useMotionOff = () => useSyncExternalStore(subscribe, isMotionOff, () => false)
