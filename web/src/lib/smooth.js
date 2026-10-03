import Lenis from 'lenis'
import 'lenis/dist/lenis.css'
import { isMotionOff } from './motion'

let lenis = null

// Weighted scrolling, the way the award sites feel. Off when the visitor turns
// motion off, and touch screens keep their own scrolling, which is already right.
export function startSmoothScroll() {
  if (lenis) return lenis
  if (isMotionOff()) return null
  lenis = new Lenis({ autoRaf: true, lerp: 0.11, anchors: { offset: -12 }, allowNestedScroll: true })
  return lenis
}

export function stopSmoothScroll() {
  lenis?.destroy()
  lenis = null
}

// A new screen starts at the top, at once, with no glide.
export function jumpToTop() {
  if (lenis) lenis.scrollTo(0, { immediate: true, force: true })
  else window.scrollTo({ top: 0 })
}

// Glides to a point on the page, used when a step of the scroll story is clicked.
export function glideTo(y) {
  if (lenis) lenis.scrollTo(y, { duration: 1.2 })
  else window.scrollTo({ top: y, behavior: 'smooth' })
}

// Holds the page still while something sits over it, like the drawer.
export function holdScroll(held) {
  if (!lenis) return
  if (held) lenis.stop()
  else lenis.start()
}
