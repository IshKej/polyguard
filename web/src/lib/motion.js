import { useSyncExternalStore } from 'react'

// PolyGuard plays its motion for everyone by default. It does not follow the
// system's reduced motion setting: that setting is often switched off for speed
// (Windows "Animation effects" sends it), and a page that freezes for those
// visitors looks broken rather than calm. Anyone can still turn motion off with
// the Motion switch, which is remembered on this device. The switch is also the
// pause control for what moves on its own: the hero cycle, the marquee, the bubble.
const KEY = 'polyguard.motion'
const listeners = new Set()
let off = (() => {
  try { return localStorage.getItem(KEY) === 'off' } catch { return false }
})()

// The page's CSS reads this attribute, so stylesheet animations stop with the rest.
const mark = () => { document.documentElement.dataset.motion = off ? 'off' : 'on' }
mark()

export const isMotionOff = () => off

export function setMotionOff(next) {
  off = next
  try { localStorage.setItem(KEY, next ? 'off' : 'on') } catch { /* private mode */ }
  mark()
  listeners.forEach((cb) => cb())
}

const subscribe = (cb) => {
  listeners.add(cb)
  return () => listeners.delete(cb)
}

// True when the visitor has switched motion off.
export const useMotionOff = () => useSyncExternalStore(subscribe, isMotionOff, () => false)
