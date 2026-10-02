# PolyGuard design research log

Working notes for the web app redesign. Started 2026-09-30, continued 2026-10-01.
If a session ends mid-way, read this file first: it records what was measured,
what Ishaan reacted to, and what the current direction is.

## What Ishaan has said (in order)

- Rejected: Apple style black ("nothing catching"), violet and magenta aurora
  ("so AI"), yellow on white wayfinding ("too white", logo "looks like a virus
  protection"), "yellow and black ain't good", four flat colour themes (Cobalt
  "kinda AI", none of Midnight, Tomato, Pink).
- Wants: "vibrant wow", "no AI colour scheme", inspired by the best sites, Apple
  level polish, things that are "tuff".
- 2026-10-01: "lando norris mclaren landing page is so cool look deeper more tuff
  things". This is the strongest positive signal so far.

## Round 1: 18 product sites measured (2026-09-30)

Measured with a script (background colours by area, fonts, media counts) and
screenshots at 1440 x 900.

| Site | What carries the first screen |
|---|---|
| Cash App | full bleed green, the phone UI huge in the centre |
| Gumroad | black, pink 3D coins scattered around the headline |
| Discord | deep blue, 3D characters and the product |
| Clay | a claymation 3D world |
| Duolingo | white, the mascot and characters |
| PostHog | a desktop OS metaphor and a hedgehog |
| Figma | white, layered real product screens |
| Spotify | huge type cut over video |
| Headspace | white, colour shapes and product phones |
| Arc | blue with grain, product screenshot |
| Lakera (AI security) | dark, blue glow, gradient words: the "AI look" |
| Promptfoo (AI security) | white, Inter, red button: generic |

Finding: the sites that feel alive put an object, a character or the product in
the first screen and take colour from it. Flat colour plus type is never enough.
The AI security category itself looks AI, which is the trap to avoid.

## Round 2: award winners (2026-10-01)

- Awwwards Site of the Year 2025: **Lando Norris** (OFF+BRAND), also Users' Choice.
- Awwwards Developer Site of the Year 2025: Messenger (a WebGL planet).
- E-commerce of the Year 2025: Scout Motors. Agency: Immersive Garden.
- Awwwards Sites of the Month 2026: Bruno Simon (Jan), Shopify Renaissance
  Edition (Feb), Immersive Garden x GQ (Mar), Oryzo AI by Lusion (Apr), Floema
  (May), Son Daven (Jun), Lama Lama (Jul), ERA Residence (Aug).
- Apple Design Awards 2026 notes: "custom animations", a palette that matches the
  subject (Tide Guide's sky palette), cartoon visuals (Is This Seat Taken?).
  Not Boring apps win on "gamelike" 3D, sound and haptics.
- An award juror's three rules for 2026: a point of view (not a decorated
  template), directed motion where transitions carry meaning, and 60fps on a mid
  range phone.

### Lando Norris site, measured

- Palette: paper `#f4f4ed`, deep olive `#282c20` (not black), near black
  `#111112` for the helmet gallery, one fluorescent `#d2ff00` taken from his real
  helmet, muted sage greys `#dde1d2`, `#b4b8a5`, olive lime `#b2c73a`.
- Type: Mona Sans Variable 800 uppercase (wide heavy grotesk) mixed inside the
  same headline with Brier (a sharp display serif): "ON / TRACK", "REDEFINING
  LIMITS", "WORLD DRIVERS' CHAMPION".
- Texture: thin topographic contour lines behind every section, like a track map.
- Shapes: cards with a notched tab carrying the label ("Porcelain 2024"), a footer
  whose top edge bumps up like a helmet, curved section edges.
- Data micro labels: photo captions "MIAMI GP, 2024"; a "NEXT RACE" widget with
  the circuit outline.
- Real objects: the 3D helmet over his photographed face, a helmet gallery.
- Motion: scroll cinematics, rotating 3D helmet, sponsor marquee, a fluorescent
  signature scribble drawn on scroll.
- Sections alternate paper, olive and near black.

What to take: colour from a real object, mixed serif plus grotesk headlines, one
quiet texture tied to the subject, a custom shape language, data micro labels,
alternating grounds. What not to take: his exact lime on black (copying it would
read as a knock off and as "black plus one neon").

### More 2026 winners, measured

- Oryzo AI by Lusion (Site of the Month, April 2026): a single 3D cork coaster on a
  green cutting mat with ruler numbers, pencils and a craft knife. Tactile and
  physical, with measurement marks as decoration. An "AI" product that looks
  nothing like AI.
- Messenger (Developer Site of the Year 2025): a hand drawn WebGL planet, chunky
  stencil type, one yellow "BEGIN" button.
- Scout Motors (E-commerce of the Year 2025): full bleed cinematic video, small
  monospace labels, a wide grotesk.
- Lusion: glossy 3D objects in cobalt, grey and black.
- Lama Lama: dark with a dot grid, heavy uppercase grotesk, live clock micro UI.
- Bruno Simon: a 3D driveable world.
- Teenage Engineering: hand drawn ink illustration, giant stencil type, one orange.
- Playdate: the physical yellow device as a 3D object, stickers.
- Not Boring: 3D objects that break through the wordmark.

Pattern across all of them: one hero object (helmet, coaster, planet, device,
car), a strong type voice, restraint everywhere else, motion that means something.

## Decision (2026-10-01)

Ishaan named Lando Norris as the bar, so the system takes Lando's craft and maps it
onto PolyGuard's own world instead of copying racing.

PolyGuard's world: reading every language, marking where the attack hides, and
grading the bot. Its real objects are the fluorescent highlighter (marks the
attack, and is the brand colour), the red pen (marks where the bot failed), the
test sheet, and the speech bubble (the bot's "no").

- Grounds: paper `#eeede5` and ink `#1a1c15`, alternating like Lando's paper and
  olive. No pure black page, no cream plus terracotta.
- One fluorescent: highlighter `#e6ff2e`. It is "held" on the board and the call
  to action colour.
- Red pen `#ff5a3d` (on ink; was `#ff4a2b`, raised to pass 4.5:1 on the board) and `#c22a10` (text on paper): only "got through".
- Type: Mona Sans (wide and heavy, uppercase for display) mixed inside headlines
  with Gloock, a sharp display serif, and with the native scripts themselves. The
  mixed type move from Lando, but the second voice is the other language.
- Hero object: a 3D speech bubble (Three.js) that answers "no" in each language,
  turning to show the next one, and sometimes cracks and says "OK" in red pen.
  It is the PolyGuard equivalent of Lando's helmet.
- Texture: faint lines of the attack in every script on ink sections; ruler ticks
  on paper sections (measurement, from Oryzo's cutting mat).
- Shapes: notched cards with a label tab, a footer panel with a bump, square
  cornered fluorescent buttons.
- Avoid: purple or blue glow, gradient text, glass, black plus one neon on its own,
  tracked out capital eyebrows above every heading, middle dot separators.

## Mouse behaviour on the reference sites (measured 2026-10-01)

Ishaan asked to check what each page does when the mouse moves. Method: move the
cursor from (200, 200) to (1240, 700), diff every element's transform, position
and opacity, and compare screenshots (WebGL changes only show in screenshots).

- Lando Norris: the cursor is a brush. Moving it paints the real helmet livery
  over his face (a WebGL mask), and the paint fades back after about two seconds.
  The head and the contour line background also shift toward the cursor. No DOM
  element moves: it is all in the canvases.
- Lama Lama: a dotted pixel trail follows the cursor and fades out.
- Gumroad: the 3D coins drift a few pixels against the cursor (depth parallax).
- Oryzo: hovering the coaster draws design tool selection handles around it.
- Not Boring, Lusion: nothing measurable on the first screen.

PolyGuard's version:
- Hero: the cursor is a highlighter. The background is the attack written in
  English, line after line. Dragging the cursor paints a fluorescent stroke that
  reveals the same attack in other languages underneath, then fades. This is the
  product's whole idea in one gesture: what is hidden under the English.
- The 3D bubble turns toward the cursor, like Lando's head.
- Every screen answers the mouse: board rows light up and show their English
  name, cards lift, the setup grid previews the language under the cursor.

## Detail audit of the top sites (2026-10-01)

Ishaan asked for every detail, down to the smallest. Measured by script on each
site (libraries, fonts actually loaded, type sizes, corner radii, button styles
and their hover change, grain, cursor, nav after scrolling, reduced motion
support), plus timed screenshots of load sequences and menus.

| Site | Stack | Fonts loaded | Display type | Buttons | Radii | Notes |
|---|---|---|---|---|---|---|
| Lando Norris | Webflow, Lenis smooth scroll, 21 WebGL canvases | Brier 700, Mona Sans Variable 200 to 900 | Mona Sans 700 to 800 capitals, tight leading (16.7 on 20.8 body) | fluorescent, 7.2px radius, 1px border, capitals | 7.2px buttons, 44px big panels, 14px | contour lines are WebGL; no custom cursor; no reduced motion CSS |
| Lusion | custom WebGL | Aeonik 400 and 500, IBM Plex Mono, own mono | Aeonik 400 at 36px, sentence case | pills (87px radius), hover turns electric blue `#0016ec` | 15px, pill | % preloader with rolling digits |
| Gumroad | Rails | ABC Favorit 400, 700 | 96px, letter spacing -0.4px | pill nav links with 1px border | pill, 4px, 24px | respects reduced motion |
| Teenage Engineering | custom | te-20 at weight 100 | tiny light text, giant drawn type | none | 52px | ink drawing, one orange |
| Playdate | Three.js | Roobert 400 to 800 | Roobert 800 68px | one huge pill "Shop Now!!" in display P3 purple | 2.85px, pill | respects reduced motion |
| Scout Motors | Astro, Lenis | Scout Sans (regular, wide, semicond), IBM Plex Mono | wide medium 72px on 64.8 leading, -1.44px spacing | 2px radius, capitals | 2px, 4px | full bleed video |
| Not Boring | Webflow | Founders Grotesk 400 to 700, JetBrains Mono | 76px on 76px | 4px radius, black, 22px | 2px, 4px | 3D objects through the wordmark |

Lando Norris, timed and opened:
- Loader: a full fluorescent screen, the LN monogram flipping in 3D, a tiny caption
  "LOAD NORRIS" (a pun on his name). About one second.
- Intro: the helmet brush reveal plays by itself across his face before you touch
  anything, so the effect teaches itself.
- Menu: a full screen olive overlay, four olive tinted photos, menu items in huge
  capitals, the current page struck through with a hand drawn fluorescent
  squiggle, the close button turns into a fluorescent square with a cross.
- Photos are toned olive and grey except the featured ones in full colour.
- The store button stays fluorescent on every ground.

What PolyGuard takes from the detail pass:
- A one second loader on first visit: fluorescent screen, the bubble saying "no"
  in a different language every few frames, a caption with a pun of its own.
- The hero reveal plays once by itself on load, then follows the cursor.
- Active and hovered links get a hand drawn highlighter stroke, not an underline.
- Tight display leading (0.9), small radii (4 to 7px) on buttons, a large radius
  only on big panels. Captions in Mona Sans capitals, not monospace.
- Smooth, weighted scrolling is common at this level (Lenis on Lando and Scout).
  Considered for PolyGuard; native scrolling kept for now so the app stays
  accessible and light.
- Do better than Lando on one thing: honour reduced motion everywhere.

## Every site, not just Lando (2026-10-01)

Ishaan: "u did 40 sites think of all of them not just lando". The first version is
saved as the git tag `design/test-sheet-v1` (commit d65c65d), so it can always be
restored with `git checkout design/test-sheet-v1`.

Each site's single best idea, and what PolyGuard does with it:

| Site | Its best idea | For PolyGuard |
|---|---|---|
| Lando Norris | cursor brush reveal, mixed type, scroll cinematics | taken in v1 (highlighter reveal, mixed type) |
| Oryzo (Lusion) | the hero object stays with you and changes as you scroll; ruler marks; selection handles on hover | **take: a scroll story where the scan plays out as you scroll** |
| Duolingo | a strip of languages along the bottom of the first screen, so you find yours | **take: a language strip under the hero; pick your language and the page answers in it** |
| Gandalf (Lakera) | a game: you try to trick the bot yourself | later, needs a live key; a scripted version would not be honest |
| Lama Lama | dotted pixel trail behind the cursor, live clock in the footer bar | partly: the cursor itself becomes a highlighter pen |
| Gumroad | objects drift against the cursor | already: gallery cards tilt to the cursor |
| Arc | grain texture, wavy section edges | **take: paper grain on paper grounds, a torn paper edge where a sheet meets ink** |
| Clay, Teenage Engineering, Oryzo | tactile, physical materials | same as above: the paper should feel like paper |
| Playdate | a rotated sticker on the hero ("PRE-ORDER IT!") | considered; skipped, it would compete with the bubble |
| Not Boring | 3D objects breaking through the wordmark | considered; the bubble already carries the 3D |
| Mat Voyce (juror pick) | type that stretches and snaps on scroll | possible later with Mona Sans width axis |
| Scout Motors, Lando | weighted smooth scrolling (Lenis) | **take, off for reduced motion, so the scroll story feels like the award sites** |
| Messenger | one clear "BEGIN" button in a game world | already: one call to action per screen |
| Cash App, Figma | the real product UI as the hero object | **take inside the scroll story: the real board fills as you scroll** |
| PostHog | humour in small copy | light touches only; PolyGuard's subject is serious |
| Headspace, Discord | characters and mascots | skipped; the bubble is the character |
| Spotify | giant type cut over video | skipped; no video yet (Ishaan's CAC video could go here later) |
| Lusion, Immersive Garden | counting preloader | v1 loader already does this job |
| Nothing | dot matrix type | skipped, it would be a second visual language |
| Tailscale, 1Password, Lakera, Promptfoo | (category sites) | the anti reference: dark glow, Inter, gradient words |

Small verification finding while reviewing: Tailwind 4 resets buttons to the arrow
cursor. Award sites all show the pointer on anything clickable. Fix globally.

Plan for v2, in order of impact:
1. The scroll story: How it works pins to the screen and plays the scan as you
   scroll. Step 1 types the system prompt, step 2 fires attacks in other
   languages into the chat, step 3 fills the real board, step 4 circles the worst
   language in red pen and highlights the fix, rule by rule.
2. The language strip: every language in the bank along the bottom of the hero;
   choosing one sets the headline and the bubble to it.
3. The cursor becomes a highlighter pen over the hero.
4. Paper grain and torn paper edges.
5. Lenis smooth scrolling.
6. A red pen circle around the worst language on a live results page (not on a
   simulated one, where it would mark noise as a finding).

## Build log

- 2026-10-01: built. Paper and ink grounds, highlighter `#e6ff2e`, red pen
  `#ff4a2b`, Mona Sans with Gloock. Landing: a one second loader, the
  highlighter reveal hero (plays once on its own), the 3D bubble that says no per
  language and turns red with PWNED on an illustrative break, a status card like
  Lando's race card, a fluorescent marquee, mixed type sections, a gallery of the
  attack in eight scripts with tilt and highlighter on hover, the board beside
  How it works, and a fluorescent footer with an ink panel. Setup, live scan,
  results and the drawer restyled on the same system. The nav takes the colour of
  the section under it, goes solid once scrolled, hides on scroll down.
- Checked: lint clean, build passes (Three.js is a separate chunk loaded after
  the page), no sideways scroll at 390px, board status no longer overlaps its
  cells, reduced motion skips the loader, the demo stroke, the language cycling
  and the bubble's float.
- Not yet checked: the fix and rescan path (needs a live key), Safari, a real
  phone's touch behaviour on the highlighter.
- 2026-10-01, v2 (after saving v1 as the tag `design/test-sheet-v1`): the scroll
  story (How it works pins and plays: the prompt types, attacks arrive in five
  languages and the bot answers, the board fills, the worst row is circled in red
  pen and three real rules from defenses.py get highlighted; scrolling back
  reverses it; the steps are clickable; a ruler fills along the bottom). The hero
  language strip (pick your language and the page answers in it; picking stops the
  cycling, "Cycle again" restarts it). A highlighter pen cursor over the hero.
  Paper grain, and torn edges cut from the same grained paper. Lenis smooth
  scrolling, off for reduced motion; the drawer and the prompt box keep their own
  wheel. Pointer cursor on everything clickable. On a live results page, the red
  pen circles the worst language only when the permutation test says it is worse
  than chance (p < 0.05); never on a simulated scan.
- v2 checks: lint clean, build passes, no page errors, no sideways scroll at 390px,
  the story read at seven scroll points on desktop and three on a phone (phones
  get the compact board so it fits), reduced motion shows the static steps and the
  finished board, the wheel inside the drawer scrolls only the drawer. Fixed on
  the way: a crash in the hero canvas when the hero briefly had no size, the red
  pen drawing only part of its loop (a Chrome quirk with non scaling strokes), the
  highlighter landing between lines on flex items, and a seam above the torn edge.
