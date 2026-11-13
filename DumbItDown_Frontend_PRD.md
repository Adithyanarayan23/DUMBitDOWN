# DumbItDown — Frontend PRD
**Version 1.0 | Product Requirements Document**

---

## 1. Overview

DumbItDown is a RAG-powered research simplification tool. This PRD defines the complete frontend redesign — visual direction, component specs, animation system, and implementation stack. The backend is production-ready; this document covers everything from the browser inward.

---

## 2. Design Direction: *The Grand Archive*

The concept is a **living library** — cinematic, immersive, and impossibly beautiful. Think: the forbidden section of a centuries-old research library at midnight, lit by amber lanterns, bookshelves receding infinitely into the dark, with modern glass interfaces floating over the scene like digital ghosts.

**The one thing a visitor will remember:** Scrolling into the hero feels like stepping through the doors of an ancient library that somehow has an AI inside it.

### Core Aesthetic Pillars

**1. Cinematic Immersion** — The hero section is a full-viewport 3D-illustrated or CSS-layered library scene (infinite bookshelves, floating dust motes, warm amber god-rays) that parallaxes as you scroll. Headlines float over it like titles carved into the air.

**2. Glass-on-Warmth** — All interactive UI (navbar, input cards, result panels) are pure frosted glass — `backdrop-filter: blur(20px)` over the warm maroon/amber scene beneath. The contrast of cold glass against warm parchment is the visual signature.

**3. Typography as Architecture** — Headlines mix serif weight and italic style exactly like the reference image (Cormorant Garamond or Playfair Display). "Dumb" is set italic, "ItDown" is set bold roman. Words feel like they were typeset by hand.

**4. Book-Stitched Containers** — The main tool card and key UI panels have SVG stitched/ruled border insets — think the ruled lines inside a moleskine, or the stitching on a leather cover. Subtle, but unmistakable.

**5. Amber-Maroon Palette** — Deep library darkness with warm maroon accent light, parchment-toned text, and gold leaf highlights.

---

## 3. Tech Stack Recommendation

**Use React + Vite.** The animation complexity (GSAP ScrollTrigger, layered parallax, component-level motion) would become unmaintainable in vanilla JS. React enables clean separation of the landing page from the app interface, smooth state handling for the conversation thread, and access to Framer Motion.

| Layer | Choice | Reason |
|---|---|---|
| Framework | React 18 + Vite | Fast HMR, component reuse, ecosystem |
| Animations | GSAP + ScrollTrigger | Industry standard for scroll-driven cinematic animation |
| UI Motion | Framer Motion | Component enter/exit transitions, layout animations |
| Styling | CSS Modules + CSS Variables | Scoped styles, no Tailwind bloat for this level of custom CSS |
| Icons | Lucide React | Clean, consistent |
| Fonts | Google Fonts (Cormorant Garamond + DM Serif Display) | Serif authority, zero licensing |
| PDF Upload | React Dropzone | Drag-and-drop, file type validation |
| Routing | React Router v6 | `/` landing, `/app` tool interface |
| Build | Vite | Replaces Python HTTP server in dev, Nginx-compatible in prod |

---

## 4. Design System

### 4.1 Color Palette

```css
:root {
  /* Core */
  --color-void:        #0D0806;   /* near-black background */
  --color-maroon:      #6B2232;   /* primary accent, glow source */
  --color-maroon-deep: #3D0F19;   /* deep panel fill */
  --color-amber:       #C8832A;   /* god-ray, highlight accent */
  --color-gold:        #D4A853;   /* citation wax seals, subtle borders */

  /* Parchment text scale */
  --color-parchment:   #F2E4C4;   /* primary text */
  --color-parchment-2: #C9B99A;   /* secondary/muted text */
  --color-parchment-3: #7A6A54;   /* placeholder, disabled */

  /* Glass system */
  --glass-bg:          rgba(255, 248, 235, 0.06);
  --glass-border:      rgba(255, 248, 235, 0.12);
  --glass-blur:        blur(20px);
  --glass-bg-heavy:    rgba(255, 248, 235, 0.10);
  --glass-border-heavy:rgba(210, 168, 83, 0.25);  /* gold-tinted border for key panels */
}
```

### 4.2 Typography

```css
/* Import in index.css */
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;0,700;1,400;1,600&family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500&display=swap');

:root {
  --font-display:  'DM Serif Display', serif;       /* Hero headlines */
  --font-serif:    'Cormorant Garamond', serif;     /* Section headers, labels */
  --font-body:     'DM Sans', sans-serif;           /* Body copy, UI text */
}
```

**Typographic Scale:**

| Token | Size | Font | Weight | Use |
|---|---|---|---|---|
| `--t-hero` | clamp(56px, 8vw, 96px) | DM Serif Display | 400 + italic mix | Hero headline |
| `--t-section` | clamp(36px, 4vw, 52px) | Cormorant Garamond | 600 | Section titles |
| `--t-card-title` | 22px | Cormorant Garamond | 600 | Card headers |
| `--t-body` | 16px | DM Sans | 400 | Body copy |
| `--t-caption` | 13px | DM Sans | 300 | Citations, labels |
| `--t-ui` | 14px | DM Sans | 500 | Buttons, nav items |

**Hero Headline Typesetting Rule:** Alternate italic and roman within a single headline. "Understand *Research.* Instantly." — the italic word creates tension and rhythm, like a book title typeset in the 1800s.

### 4.3 Motion System

All animations are orchestrated via GSAP timelines. Framer Motion handles component-level transitions.

**Easing Tokens:**
```js
// gsap-config.js
export const ease = {
  smooth:   "power2.out",
  snap:     "expo.out",
  drift:    "sine.inOut",   // for floating/parallax elements
  reveal:   "power3.out",   // for scroll-triggered text reveals
}
```

**Animation Vocabulary:**

| Motion | Technique | When |
|---|---|---|
| Hero parallax | GSAP ScrollTrigger — bookshelf layers move at different rates | Scroll from hero |
| Section reveal | Words/lines mask-clip from bottom, staggered 80ms | Element enters viewport |
| Glass panel entry | `opacity: 0 → 1` + `translateY(24px → 0)` over 600ms | Component mount |
| Dust motes | CSS keyframe `float` on 20–30 small `div` circles | Always on in hero |
| God-ray pulse | CSS `@keyframes` opacity pulse on gradient overlay | Always on, 8s cycle |
| Citation expand | Framer Motion `AnimatePresence` height animation | Click citation |
| Response stream | Character-by-character append via `requestAnimationFrame` | API response |

### 4.4 Book-Stitch Border System

Applied to the main tool card and key landing sections using an SVG inset border:

```css
.stitched-panel {
  position: relative;
}

.stitched-panel::before {
  content: '';
  position: absolute;
  inset: 8px;
  border: 1px dashed rgba(210, 168, 83, 0.3);
  border-radius: inherit;
  pointer-events: none;
  z-index: 1;
}

/* Alternate: use an SVG background-image of a ruled/stitched pattern */
.stitched-panel::after {
  content: '';
  position: absolute;
  inset: 0;
  background-image: url('/assets/stitch-border.svg');
  background-size: 100% 100%;
  opacity: 0.15;
  pointer-events: none;
}
```

The `stitch-border.svg` is a simple dashed rectangle with rounded corners and corner flourishes — export once from Figma or Illustrator, use everywhere.

---

## 5. Page Architecture

```
/           → LandingPage.jsx
/app        → AppPage.jsx
```

Both pages share the `<Navbar />` component. `LandingPage` is pure scroll experience; `AppPage` is the functional tool interface.

---

## 6. Landing Page — Section Specs

### 6.1 Navbar

**Behavior:** Transparent on hero, transitions to `glass-bg-heavy` with `backdrop-filter` once user scrolls past 80px. Smooth `transition: background 300ms ease`.

**Layout:** Logo left (Cormorant serif, "Dumb*It*Down"), nav links center (How It Works / Features / Launch App), CTA button right ("Open the Archive →").

**Glass style:** `background: var(--glass-bg-heavy); backdrop-filter: var(--glass-blur); border-bottom: 1px solid var(--glass-border);`

**Mobile:** Hamburger collapses to a full-screen glass drawer overlay with nav items in large serif type. The drawer slides in from the right with a Framer Motion `x` animation.

---

### 6.2 Hero Section

**The centrepiece of the entire design.**

**Layout:** Full viewport height (`100svh`). The library scene fills the entire background. The headline and CTA float in the lower-left third of the screen (like the "Venture Past Our Sky" reference).

**Background Scene Implementation:**

Build with 4–6 absolutely-positioned CSS layers that parallax at different speeds:

| Layer | Content | Parallax Speed |
|---|---|---|
| Layer 0 (back) | Near-black gradient base | 0 (static) |
| Layer 1 | Left bookshelf (dark, blurred) | 0.1x scroll speed |
| Layer 2 | Right bookshelf (dark, blurred) | 0.15x scroll speed |
| Layer 3 | Center aisle vanishing point gradient (amber glow deep in the stack) | 0.05x |
| Layer 4 | Floating dust motes (20 small divs, CSS float animation) | 0.3x |
| Layer 5 (front) | Maroon god-ray gradient overlay | 0.0x (static) |

The bookshelves can be: (a) a high-quality royalty-free library photo with `filter: brightness(0.3) sepia(0.5)`, or (b) a CSS-drawn repeating shelf pattern using `repeating-linear-gradient`. Option (b) is more controllable.

**Headline Typesetting:**
```html
<h1>
  Understand <em>Research.</em><br/>
  <strong>Instantly.</strong>
</h1>
```
`em` → italic, `strong` → bold roman. Same typographic pattern as the reference image.

**Subheadline:** "RAG-powered simplification for 1,250+ academic papers. Ask once, then keep asking." — DM Sans 300, parchment-2 color, max-width 480px.

**CTAs:** Two buttons side-by-side:
- Primary: `"Simplify a Paper →"` — glass button with gold border, filled on hover
- Secondary: `"See How It Works"` — text link with underline animation

**Scroll Indicator:** Animated chevron-down at bottom-center, pulses gently, disappears after first scroll.

**Entry Animation (GSAP timeline on mount):**
1. `t=0` — bookshelf layers fade in from black (staggered, 800ms each)
2. `t=0.6` — headline words clip in from bottom, one word at a time, 80ms stagger
3. `t=1.0` — subheadline fades in
4. `t=1.2` — CTA buttons slide up and fade in
5. `t=1.4` — scroll indicator pulses in

---

### 6.3 "How It Works" Section — Chapter I

**Visual concept:** Parchment-textured section (subtle `noise.svg` overlay at 4% opacity, warm background). Three numbered steps styled as book chapters.

**Layout:** Horizontal on desktop (3 steps), vertical stacked on mobile.

**Step card design:**
- Chapter number in Cormorant Garamond, 80px, `var(--color-parchment-3)` — large and ghosted behind the card
- Step title in Cormorant Garamond 600, 22px
- Body copy in DM Sans 300
- Connecting dotted line between cards (desktop only)

**Scroll animation:** Each card reveals from bottom with mask-clip as it enters viewport. Chapter numbers count up with a GSAP `innerText` counter animation.

---

### 6.4 Features Section — Chapter II

**Visual concept:** Glass cards on a dark maroon-gradient background. Six feature cards in a 3×2 grid (desktop) / 1-column (mobile).

**Card anatomy:**
- Glass background with stitched inner border
- Lucide icon at top, amber colored
- Feature title in Cormorant Garamond 600
- One-sentence description in DM Sans 300

**Scroll animation:** Cards stagger-reveal in a wave pattern left-to-right, top-to-bottom. Hover: card lifts `translateY(-4px)`, border brightens, amber glow appears behind.

---

### 6.5 Call-to-Action Strip

**Full-width dark panel.** Centered headline: *"The archive is open."* in DM Serif Display, 52px. Subtext below. Single "Begin Simplifying →" glass button.

Thin parchment horizontal rule above and below the section with decorative serif ornaments (`❧` or SVG flourish).

---

### 6.6 Footer

Minimal. Logo left. "Built on RAG + Gemini 2.0 Flash" center in caption type. GitHub link right. Dark background, parchment-3 text.

---

## 7. App Page (`/app`) — Section Specs

### 7.1 Layout

Three-column flex layout on desktop:

```
[ Sidebar: Session History ]  [ Main: Input + Response ]  [ Panel: Citations ]
       240px                         flex-grow                    320px
```

On tablet: citation panel collapses to a drawer. On mobile: single column, history becomes a slide-up sheet.

All three panels are glass cards with stitched borders over a persistent dark maroon gradient background (not the full library scene — that's only for the landing page).

---

### 7.2 Left Sidebar — Session History

**Purpose:** Shows the list of previous Q&A exchanges in the current session.

**Each history item:**
- Truncated version of the original query (1 line, ellipsis)
- Relative timestamp ("2 min ago")
- Clicking scrolls the main panel to that exchange

**Header:** "Session" in Cormorant Garamond 600, with a session counter badge.

**Empty state:** Italic serif placeholder — *"Your questions will appear here."*

---

### 7.3 Main Panel — Input + Conversation Thread

**Input Area (top of panel):**

- Textarea with glass styling, parchment placeholder text: *"Paste a passage, upload a PDF, or ask about the paper..."*
- Character counter (bottom-right of textarea, `var(--color-parchment-3)`)
- PDF drag-drop zone: inline below textarea, dashed gold border, icon + "Drop a PDF or click to upload" — uses React Dropzone
- Action bar: `"Simplify"` (primary, gold-bordered glass button) + `"Clear"` (text button)

**Conversation Thread (below input):**

The thread is a scrollable vertical stack of `<Exchange />` components. Each exchange contains:

**Query bubble:**
- Right-aligned
- Parchment background pill with user's question text
- DM Sans 400, dark text

**Response block:**
- Full-width glass card with stitched border
- Response text streams in character-by-character using `requestAnimationFrame` for smooth typing effect
- Technical terms are auto-highlighted with amber underline; hovering shows a tooltip definition (rendered via a `<Tooltip />` positioned with Floating UI)
- Below the response: `"Ask a follow-up..."` — a small inline input that submits the follow-up and appends a new exchange to the thread. Placeholder references the last exchange: *"Ask about this response..."*
- "Sources" button at bottom-right of response card — clicking expands the citation panel on the right

**Inline Sources Accordion** (below response, before follow-up input):
- Collapsible — collapsed by default, "3 sources used" toggle
- Expands via Framer Motion height animation
- Each source: paper title (truncated), author, year, contribution percentage bar

---

### 7.4 Right Panel — Citation Detail View

**Triggered by:** clicking "Sources" on any response, or clicking a specific source in the inline accordion.

**Panel content:**
- Heading: "Sources" in Cormorant Garamond 600
- Each citation is a glass card with:
  - Paper title (Cormorant serif, 600)
  - Authors + year (DM Sans 300, parchment-2)
  - Contribution percentage — amber horizontal bar, thin, like a reading progress bar
  - APA-formatted citation block (monospace-ish, small, parchment-3)
  - Two action links: `"PubMed ↗"` and `"arXiv ↗"` — open in new tab
  - **Wax seal accent:** A small SVG wax seal stamp (maroon circle with "✓") in the top-right corner of each citation card. Purely decorative, but unmistakable.

---

## 8. Component Library Summary

| Component | File | Key Props |
|---|---|---|
| `<Navbar />` | `components/Navbar.jsx` | `transparent` (bool) |
| `<HeroSection />` | `components/HeroSection.jsx` | — |
| `<ParallaxLayer />` | `components/ParallaxLayer.jsx` | `speed`, `children` |
| `<DustMotes />` | `components/DustMotes.jsx` | `count` (default 24) |
| `<ChapterSection />` | `components/ChapterSection.jsx` | `number`, `title`, `steps[]` |
| `<FeatureCard />` | `components/FeatureCard.jsx` | `icon`, `title`, `desc` |
| `<GlassCard />` | `components/GlassCard.jsx` | `stitched` (bool), `heavy` (bool) |
| `<Exchange />` | `components/Exchange.jsx` | `query`, `response`, `sources[]`, `streaming` |
| `<CitationCard />` | `components/CitationCard.jsx` | `citation` object |
| `<PDFDropzone />` | `components/PDFDropzone.jsx` | `onFile` callback |
| `<StreamingText />` | `components/StreamingText.jsx` | `text`, `speed` (ms/char) |
| `<TermTooltip />` | `components/TermTooltip.jsx` | `term`, `definition` |
| `<SessionHistory />` | `components/SessionHistory.jsx` | `exchanges[]`, `onSelect` |

---

## 9. Responsive Breakpoints

| Breakpoint | Layout |
|---|---|
| `>= 1280px` | Full 3-column app layout, full hero |
| `>= 1024px` | 2-column app (no citation panel — drawer instead) |
| `>= 768px` | Single column app, landing sections stack vertically |
| `< 768px` | Mobile: hamburger nav, stacked everything, session history becomes bottom sheet |

---

## 10. Performance Notes

- Bookshelf background layers: use `will-change: transform` on parallax elements. Limit to 6 layers max to avoid compositor overload.
- Dust motes: CSS-only `@keyframes`, never JS-animated. Use `transform: translate()` only (compositor-safe).
- Fonts: `font-display: swap` on all Google Fonts imports.
- GSAP ScrollTrigger: `invalidateOnRefresh: true` for resize safety.
- PDF uploads: validate file type client-side before sending to backend. Show filename confirmation before submit.
- Streaming text: batch characters (5–8 at a time per `rAF` tick) rather than one at a time to avoid layout thrash on long responses.

---

## 11. File Structure

```
frontend/
├── public/
│   ├── assets/
│   │   ├── stitch-border.svg
│   │   ├── noise.svg
│   │   ├── bookshelf-left.png       # or CSS-drawn
│   │   └── bookshelf-right.png
├── src/
│   ├── components/
│   │   ├── Navbar.jsx
│   │   ├── HeroSection.jsx
│   │   ├── ParallaxLayer.jsx
│   │   ├── DustMotes.jsx
│   │   ├── GlassCard.jsx
│   │   ├── Exchange.jsx
│   │   ├── CitationCard.jsx
│   │   ├── PDFDropzone.jsx
│   │   ├── StreamingText.jsx
│   │   ├── TermTooltip.jsx
│   │   └── SessionHistory.jsx
│   ├── pages/
│   │   ├── LandingPage.jsx
│   │   └── AppPage.jsx
│   ├── styles/
│   │   ├── globals.css              # CSS variables, reset, font imports
│   │   ├── glass.module.css         # Glass + stitch system
│   │   └── animations.css           # Dust motes, god-ray keyframes
│   ├── hooks/
│   │   ├── useScrollReveal.js       # GSAP ScrollTrigger wrapper
│   │   └── useParallax.js           # Parallax scroll hook
│   ├── App.jsx
│   └── main.jsx
├── index.html
├── vite.config.js
└── package.json
```

---

## 12. What To Build First (Suggested Order)

1. `globals.css` — Set every CSS variable. This anchors all downstream work.
2. `GlassCard` + `StitchBorder` — The design's atomic unit. Get this perfect before anything else.
3. `HeroSection` — The most important screen. Build the parallax layers, headline typesetting, and entry animation. Once this is right, everything else follows.
4. `Navbar` — Transparent → glass scroll behavior.
5. Landing sections (Chapter I, II, CTA, Footer)
6. `AppPage` layout skeleton — three-column shell with glass panels
7. `Exchange` component — conversation thread, streaming text, inline accordion
8. `PDFDropzone`
9. `CitationCard` + right panel
10. `SessionHistory` sidebar
11. Mobile responsive pass
12. Performance audit + animation polish

---

---

## Addendum — Implementation Spec (Kimi 2.5 / Coding Model Input)

*This section translates the design PRD into machine-executable constraints. Feed this alongside Sections 1–12 when prompting a coding model.*

---

### A. API Contract

**Base URL:** `http://localhost:5000/api` (dev) · proxied via `/api` in production (configure in `vite.config.js`)

| Endpoint | Method | Request Body | Response Shape |
|---|---|---|---|
| `/health` | GET | — | `{status, version}` |
| `/search` | POST | `{query, question?, k?, conversation_id?}` | `{query, context, simplified_text, citations: {sources[], total, primary_source}, technical_terms: [{term, definition}], answer?, conversation_id}` |
| `/qa` | POST | `{query, question, k?, conversation_id?}` | `{query, question, context, simplified_text, answer, technical_terms: [{term, definition}], conversation_id}` |
| `/followup` | POST | `{conversation_id, question, k?}` | `{question, answer, context, technical_terms: [{term, definition}]}` |
| `/conversations` | GET | — | `{conversations: [{id, created_at, updated_at, metadata}]}` |
| `/conversations/:id` | GET | — | `{id, created_at, updated_at, messages: [{role, content, timestamp, metadata}]}` |
| `/conversations/:id` | DELETE | — | `{status: "deleted", conversation_id}` |
| `/upload/pdf` | POST | `multipart/form-data (file)` | `{filename, metadata: {title, author, pages, chunks}, text_preview, documents[]}` |
| `/upload/pdf-simplify` | POST | `multipart/form-data (file)` | `{filename, metadata, simplified_text, context, technical_terms: [{term, definition}], conversation_id}` |

**Streaming:** Not implemented. All responses are blocking complete JSON (3–5s typical). Streaming text in the UI is **simulated** — reveal the `simplified_text` word-by-word on the frontend using `requestAnimationFrame` after the full response lands.

**`technical_terms` → tooltip matching (frontend logic):** On `Exchange` reaching `complete` state, iterate `technical_terms[]` from the response. For each `term`, find all occurrences in `simplified_text` (case-insensitive, whole-word match) and wrap in `<TermTooltip term={term} definition={definition} />`. Run as a single-pass string split — do not use `dangerouslySetInnerHTML`. If `technical_terms` is `[]` (backend fallback scenario), render `simplified_text` as plain text with no tooltip pass, no error triggered.

**Error format:**
```json
{ "detail": "Error message string" }
```
Status codes: `400` bad input · `404` conversation not found · `500` server error. All errors should render the Exchange component's `error` state with the `detail` string.

---

### B. Component State Table

| Component | States | Key Notes |
|---|---|---|
| `Exchange` | `idle → loading → streaming → complete → error` | "Streaming" is simulated word-by-word reveal. Sources button hidden until `complete`. Textarea disabled during `loading`/`streaming`. Error shows red banner with `detail` message. **Response field mapping:** use `simplified_text` for `/search` and `/upload/pdf-simplify` responses; use `answer` for `/followup` and `/qa` responses. The `Exchange` component must check for both: `const responseText = data.simplified_text ?? data.answer ?? ""`. |
| `PDFDropzone` | `idle → dragover → uploading → processing → success → error` | `.pdf` only, 50MB max. `success` shows filename + text preview + "Simplify this PDF" button. `error` shows red border + message string. `processing` shows spinner + "Extracting..." label. |
| `CitationPanel` | `collapsed → loading → expanded → detail` | `collapsed` = hidden (right panel not visible). `detail` = single citation full view with PubMed/arXiv links. Contribution % bars visible in `expanded`. Toggle between list and detail without closing panel. |
| `SessionHistory` | `empty → loading → list → active` | `empty` shows only "New Chat" button. `list` newest-first, title = first 50 chars of first message. `active` highlights selected conversation. Preserve scroll position on re-render. |
| `TextInput` | `empty → typing → valid → invalid` | Counter format: `0/10000`. Submit disabled in `empty` and `invalid`. `valid` threshold: >10 chars. `invalid` threshold: >10,000 chars (counter turns red). |

---

### C. Non-Goals — Explicitly Out of Scope for V1

**Auth & Users:** No login, no accounts, no OAuth, no JWT. Fully anonymous.

**Cross-device persistence:** No cloud sync. Conversation history lives in SQLite on the server; it does not sync across browsers or devices.

**Streaming responses:** The backend returns full blocking JSON. Do not implement SSE or WebSocket. Simulate streaming on the frontend only.

**Theme toggle:** Dark theme only. No light mode switch.

**File types beyond PDF:** No DOCX, PPT, image, or CSV upload. PDF only.

**Advanced citation UI:** No "verify citation" button, no confidence score display, no "export bibliography." CitationPanel shows title, authors, year, contribution bar, and external links only.

**Mobile optimisation:** The layout must be responsive and not broken on mobile, but no bottom sheets, no swipe gestures, no mobile-specific interaction patterns. That is V2.

**Collaborative/real-time features:** No multi-user, no shared sessions, no live updates.

---

### D. Primary Interaction Walkthrough

This is the single most important user flow. The implementation must satisfy this end-to-end before any other feature work.

**Flow 1 — Paste Text → Simplify → Follow-up**

1. **Initial state.** User arrives at `/app`. Left sidebar (`SessionHistory`) shows `empty` state — only "New Chat" button visible. Main area shows `Exchange` in `idle` state. Textarea is empty, char counter reads `0/10000`, Simplify button is disabled.

2. **User pastes text.** Char counter updates live. At >10 chars, `TextInput` transitions to `valid`. Simplify button enables.

3. **User clicks Simplify.** `Exchange` → `loading`. Button label changes to "Simplifying..." with spinner. Textarea is disabled. `POST /api/search` fires with `{query: pastedText}`.

4. **Response arrives (2–4s).** Response contains `simplified_text`, `citations`, and `conversation_id` (e.g. `"abc-123"`). Store `conversation_id` in component state — every subsequent follow-up in this session uses it.

5. **Simulated streaming begins.** `Exchange` → `streaming`. `simplified_text` is revealed word-by-word in the output area. Sources button does not appear yet.

6. **Streaming complete.** `Exchange` → `complete`. "Sources (N)" button appears bottom-right of the response card. Textarea re-enables. `SessionHistory` updates to show this conversation as the active item, titled with the first 50 chars of the original query.

7. **User opens sources.** Clicks "Sources". `CitationPanel` → `loading` briefly → `expanded`. Right panel slides in. Shows list of sources with title, authors, year, and amber contribution % bar. Each source has a chevron; clicking it transitions panel to `detail` view for that source (full APA string + PubMed/arXiv links).

8. **User asks follow-up.** Types into the inline follow-up input below the response: *"What does that mean for diabetes?"*. Clicks "Ask". `POST /api/followup` fires with `{conversation_id: "abc-123", question: "..."}`. A new `Exchange` block appends to the thread showing the Q and streaming A. Thread scrolls to bottom.

---

**Flow 2 — PDF Upload → Simplify**

1. User drags a PDF onto `PDFDropzone`. State → `dragover` (gold dashed border highlights).

2. On drop, state → `uploading`. Filename shown, progress bar animates.

3. `POST /upload/pdf-simplify` fires. State → `processing` ("Extracting text..." spinner).

4. Response arrives. State → `success`. Shows filename, page count, and text preview (first 200 chars). "Simplify this PDF" button appears.

5. User clicks "Simplify this PDF". `Exchange` populates with `simplified_text` from the upload response. `conversation_id` stored. `CitationPanel` auto-opens if `citations.sources` array is non-empty.

---

*End of PRD — DumbItDown Frontend v1.0 + Addendum*