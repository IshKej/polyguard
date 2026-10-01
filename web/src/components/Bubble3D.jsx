import { useEffect, useRef, useState } from 'react'
import gsap from 'gsap'
import * as THREE from 'three'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'
import { useReducedMotion } from '../lib/motion'

const HI = '#e6ff2e'
const RED = '#ff4a2b'
const INK = '#1a1c15'

// The speech bubble's outline: a rounded body with a tail at the lower left.
function bubbleShape() {
  const W = 1.7
  const H = 1.12
  const R = 0.72
  const s = new THREE.Shape()
  s.moveTo(-W + R, -H)
  s.lineTo(-0.62, -H)
  s.lineTo(-1.08, -H - 0.72)
  s.lineTo(-0.02, -H)
  s.lineTo(W - R, -H)
  s.quadraticCurveTo(W, -H, W, -H + R)
  s.lineTo(W, H - R)
  s.quadraticCurveTo(W, H, W - R, H)
  s.lineTo(-W + R, H)
  s.quadraticCurveTo(-W, H, -W, H - R)
  s.lineTo(-W, -H + R)
  s.quadraticCurveTo(-W, -H, -W + R, -H)
  return { shape: s, W, H }
}

// Draws the bubble's word onto a canvas, as large as fits.
function paintWord(canvas, word) {
  const g = canvas.getContext('2d')
  g.clearRect(0, 0, canvas.width, canvas.height)
  g.fillStyle = INK
  g.textAlign = 'center'
  g.textBaseline = 'middle'
  let size = 300
  const fit = () => { g.font = `800 ${size}px "Mona Sans", "Nirmala UI", "Microsoft YaHei", "Malgun Gothic", "Segoe UI", system-ui, sans-serif` }
  fit()
  while (g.measureText(word).width > canvas.width * 0.8 && size > 60) { size -= 10; fit() }
  g.fillText(word, canvas.width / 2, canvas.height / 2 + size * 0.04)
}

// The hero object: a glossy highlighter bubble that says "no" in whatever
// language the page is on, turns to face the cursor, and spins over to the next
// language. When an attack gets through it turns red pen red.
export default function Bubble3D({ word, broke, className = '' }) {
  const wrap = useRef(null)
  const canvasRef = useRef(null)
  const api = useRef(null)
  const reduce = useReducedMotion()
  const [failed] = useState(() => {
    try { return !document.createElement('canvas').getContext('webgl2') } catch { return true }
  })

  useEffect(() => {
    const box = wrap.current
    const canvas = canvasRef.current
    if (failed || !canvas) return undefined
    let renderer
    try {
      renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true })
    } catch {
      return undefined
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
    renderer.toneMapping = THREE.NeutralToneMapping
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(28, 1, 0.1, 100)
    camera.position.set(0, 0, 10.5)
    const pmrem = new THREE.PMREMGenerator(renderer)
    const env = pmrem.fromScene(new RoomEnvironment(), 0.04).texture
    scene.environment = env
    const key = new THREE.DirectionalLight(0xffffff, 1.4)
    key.position.set(3, 5, 6)
    scene.add(key)

    const { shape, W } = bubbleShape()
    const depth = 0.5
    const bevel = 0.22
    const geo = new THREE.ExtrudeGeometry(shape, {
      depth, bevelEnabled: true, bevelThickness: bevel, bevelSize: 0.2, bevelSegments: 12, curveSegments: 40,
    })
    geo.computeBoundingBox()
    const bb = geo.boundingBox
    const cx = (bb.min.x + bb.max.x) / 2
    const cy = (bb.min.y + bb.max.y) / 2
    geo.translate(-cx, -cy, -(bb.min.z + bb.max.z) / 2)
    const body = new THREE.MeshPhysicalMaterial({
      color: HI, roughness: 0.3, clearcoat: 1, clearcoatRoughness: 0.12, emissive: HI, emissiveIntensity: 0.14,
    })
    const bubble = new THREE.Mesh(geo, body)

    const text = document.createElement('canvas')
    text.width = 1024
    text.height = 640
    const map = new THREE.CanvasTexture(text)
    map.colorSpace = THREE.SRGBColorSpace
    map.anisotropy = renderer.capabilities.getMaxAnisotropy()
    const face = new THREE.Mesh(
      new THREE.PlaneGeometry(W * 1.8, W * 1.8 * (640 / 1024)),
      new THREE.MeshBasicMaterial({ map, transparent: true, toneMapped: false }),
    )
    face.position.set(-cx, -cy, depth / 2 + bevel + 0.012)

    const obj = new THREE.Group()
    obj.add(bubble, face)
    obj.scale.setScalar(0.92)
    scene.add(obj)

    const state = { spin: 0, tx: 0, ty: 0, t: 0 }
    const size = () => {
      const w = box.clientWidth
      const h = box.clientHeight
      renderer.setSize(w, h, false)
      camera.aspect = w / h
      camera.position.z = w / h < 1 ? 13.5 : 10.5
      camera.updateProjectionMatrix()
    }
    size()
    const ro = new ResizeObserver(size)
    ro.observe(box)

    const onMove = (e) => {
      state.ty = (e.clientX / window.innerWidth - 0.5) * 0.9
      state.tx = (e.clientY / window.innerHeight - 0.5) * 0.55
    }
    window.addEventListener('pointermove', onMove, { passive: true })

    let visible = true
    const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting })
    io.observe(box)
    let raf = 0
    const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const loop = () => {
      raf = requestAnimationFrame(loop)
      if (!visible) return
      state.t += 0.016
      const float = still ? 0 : Math.sin(state.t * 1.1) * 0.08
      obj.rotation.x += (state.tx - 0.08 - obj.rotation.x) * 0.06
      obj.rotation.y += (state.ty - 0.22 + state.spin - obj.rotation.y) * 0.08
      obj.position.y = float
      renderer.render(scene, camera)
    }
    loop()

    let first = true
    api.current = {
      show(nextWord, isBroke) {
        const apply = () => {
          paintWord(text, nextWord)
          map.needsUpdate = true
          body.color.set(isBroke ? RED : HI)
          body.emissive.set(isBroke ? RED : HI)
        }
        if (first || still) { first = false; document.fonts.ready.then(apply); return }
        gsap.timeline()
          .to(state, { spin: state.spin + Math.PI, duration: 0.42, ease: 'power2.in' })
          .call(apply)
          .to(state, { spin: state.spin + Math.PI * 2, duration: 0.6, ease: 'back.out(1.6)' })
      },
    }

    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
      io.disconnect()
      window.removeEventListener('pointermove', onMove)
      gsap.killTweensOf(state)
      geo.dispose(); body.dispose(); map.dispose(); face.geometry.dispose(); face.material.dispose()
      env.dispose(); pmrem.dispose(); renderer.dispose()
      api.current = null
    }
  }, [reduce, failed])

  useEffect(() => { api.current?.show(word, broke) }, [word, broke, reduce, failed])

  return (
    <div ref={wrap} className={`relative ${className}`} aria-hidden="true">
      {failed ? (
        <div className="grid h-full place-items-center">
          <span className="display rounded-[28px] px-10 py-6 text-6xl text-ink" style={{ background: broke ? RED : HI }}>{word}</span>
        </div>
      ) : (
        <canvas ref={canvasRef} className="block h-full w-full" />
      )}
    </div>
  )
}
