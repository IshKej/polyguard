import { useEffect, useRef } from 'react'
import gsap from 'gsap'
import { useReducedMotion } from '../lib/motion'

const ROW = 40        // px between lines of text
const SIZE = 20       // px text size
const PEN = 70        // px width of the highlighter
const FADE = 0.032    // how much of the highlight fades each frame

// The hero's paper: the attack, printed in English, line after line. The cursor
// is a highlighter. Wherever it passes, the same attack shows through in the
// other languages, and then the ink settles back. On load it highlights one
// stroke by itself, so the effect explains itself before anyone moves the mouse.
export default function HighlighterField({ english, lines }) {
  const host = useRef(null)
  const canvas = useRef(null)
  const reduce = useReducedMotion()

  useEffect(() => {
    const box = host.current
    const cv = canvas.current
    if (!box || !cv || !lines.length) return undefined
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    const ctx = cv.getContext('2d')
    const printed = document.createElement('canvas')   // the English
    const under = document.createElement('canvas')     // every other language, on highlighter
    const mask = document.createElement('canvas')      // where the highlighter has been
    const comp = document.createElement('canvas')
    const m = mask.getContext('2d')
    const root = getComputedStyle(document.documentElement)
    const HI = root.getPropertyValue('--color-hi').trim() || '#e6ff2e'
    let w = 0
    let h = 0
    let last = null
    let energy = 0
    let raf = 0
    let alive = true

    const rows = (c, background, colour, textFor) => {
      const g = c.getContext('2d')
      g.setTransform(dpr, 0, 0, dpr, 0, 0)
      g.clearRect(0, 0, w, h)
      if (background) { g.fillStyle = background; g.fillRect(0, 0, w, h) }
      g.fillStyle = colour
      g.font = `600 ${SIZE}px "Mona Sans", system-ui, sans-serif`
      g.textBaseline = 'middle'
      const count = Math.ceil(h / ROW) + 1
      for (let r = 0; r < count; r++) {
        const text = textFor(r)
        const step = g.measureText(`${text}    `).width || 200
        let x = -((r * 173) % step)
        while (x < w) { g.fillText(text, x, r * ROW + ROW / 2); x += step }
      }
    }

    const draw = () => {
      ctx.setTransform(1, 0, 0, 1, 0, 0)
      ctx.clearRect(0, 0, cv.width, cv.height)
      ctx.drawImage(printed, 0, 0)
      const k = comp.getContext('2d')
      k.globalCompositeOperation = 'source-over'
      k.clearRect(0, 0, comp.width, comp.height)
      k.drawImage(mask, 0, 0)
      k.globalCompositeOperation = 'source-in'
      k.drawImage(under, 0, 0)
      ctx.drawImage(comp, 0, 0)
    }

    const tick = () => {
      raf = 0
      m.setTransform(1, 0, 0, 1, 0, 0)
      m.globalCompositeOperation = 'destination-out'
      m.fillStyle = `rgba(0,0,0,${FADE})`
      m.fillRect(0, 0, mask.width, mask.height)
      energy *= 1 - FADE
      if (energy < 0.03) m.clearRect(0, 0, mask.width, mask.height)
      draw()
      if (alive && energy >= 0.03) raf = requestAnimationFrame(tick)
    }

    const mark = (x, y) => {
      m.setTransform(dpr, 0, 0, dpr, 0, 0)
      m.globalCompositeOperation = 'source-over'
      m.strokeStyle = '#000'
      m.lineCap = 'round'
      m.lineJoin = 'round'
      m.lineWidth = PEN
      m.beginPath()
      m.moveTo(last ? last.x : x, last ? last.y : y)
      m.lineTo(x, y)
      m.stroke()
      last = { x, y }
      energy = 1
      if (!raf) raf = requestAnimationFrame(tick)
    }

    const layout = () => {
      w = box.clientWidth
      h = box.clientHeight
      for (const c of [cv, printed, under, mask, comp]) { c.width = Math.round(w * dpr); c.height = Math.round(h * dpr) }
      cv.style.width = `${w}px`
      cv.style.height = `${h}px`
      rows(printed, null, 'rgba(26, 28, 21, 0.05)', () => english)
      rows(under, HI, 'rgba(26, 28, 21, 0.34)', (r) => lines[r % lines.length].text)
      draw()
    }

    const onMove = (e) => {
      const r = box.getBoundingClientRect()
      const x = e.clientX - r.left
      const y = e.clientY - r.top
      if (x < 0 || y < 0 || x > r.width || y > r.height) { last = null; return }
      mark(x, y)
    }
    const onLeave = () => { last = null }

    const ro = new ResizeObserver(() => layout())
    let demo
    document.fonts.ready.then(() => {
      if (!alive) return
      layout()
      ro.observe(box)
      if (reduce) return
      // One stroke on its own, across the lower middle, to show what the cursor does.
      const p = { t: 0 }
      demo = gsap.to(p, {
        t: 1, duration: 1.7, delay: 0.5, ease: 'power1.inOut',
        onUpdate: () => mark(w * (0.04 + 0.92 * p.t), h * (0.66 + 0.07 * Math.sin(p.t * Math.PI * 3))),
        onComplete: () => { last = null },
      })
    })
    window.addEventListener('pointermove', onMove, { passive: true })
    document.addEventListener('pointerleave', onLeave)

    return () => {
      alive = false
      demo?.kill()
      ro.disconnect()
      cancelAnimationFrame(raf)
      window.removeEventListener('pointermove', onMove)
      document.removeEventListener('pointerleave', onLeave)
    }
  }, [english, lines, reduce])

  return (
    <div ref={host} className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
      <canvas ref={canvas} className="block" />
    </div>
  )
}
