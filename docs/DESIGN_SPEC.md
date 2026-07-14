# Prospectus — Design Spec

## Aesthetic target
**Premium research instrument.** References: **Perplexity, Hebbia, Linear.**
Clean, text-forward, citation-heavy, fast. Feels like a serious research tool — not a chatbot.

## Anti-slop rules (never)
- ❌ Violet/purple gradient hero
- ❌ Untouched shadcn defaults (ALWAYS override radius, palette, font)
- ❌ Emoji icons, glassmorphism, gradient borders, glow effects
- ❌ Placeholder content — real filings, real citations, real numbers only
- ❌ Generic chat-bubble UI — this is a research tool, not a messenger

## Palette
--background:      #FBFBF9   /* warm paper-white — this is a READING tool */
--surface:         #FFFFFF
--surface-subtle:  #F5F5F2
--border:          #E5E5E0
--ink:             #16161A
--ink-muted:       #6B6B72
--ink-subtle:      #9A9AA0

--accent:          #1F4B99   /* deep blue — research/trust */
--accent-hover:    #163A79
--accent-subtle:   #EEF2FA

--citation:        #0B6E4F   /* green — grounded/verified */
--citation-bg:     #E7F1EC
--warning:         #B54708   /* insufficient evidence */
--warning-bg:      #FFF6ED

## Typography (this is a reading tool — type quality is everything)
- Primary: **Geist** (or Inter, tightened)
- Body: 15px / 1.6 line-height — generous, readable, longer measure than a dashboard
- Citations/metadata: 12px, --ink-subtle; mono for filing IDs
- Eval report numerics: tabular figures, always
- Scale: Display 30/600 · Section 20/600 · Body 15/400 · Meta 12/500

## Radius / spacing / shadows
- Radius: 6px cards, 4px citation chips
- Generous vertical rhythm — a reading experience, don't cram
- Shadows: near-zero. Hairline borders only.

## Key components
1. **Query input** — prominent, clean, expanding. Perplexity-grade.
2. **Answer view** — answer text with **inline citation chips** (small pills in --citation),
   hoverable and clickable.
3. **Citation drawer** — clicking a citation opens a right-side drawer with the exact source
   chunk from the filing, relevant passage highlighted, showing filing name + section + date.
   **THIS IS THE PRODUCT.** Make it feel authoritative.
4. **Insufficient-evidence state** — designed deliberately, in --warning:
   "I don't have enough evidence in these filings to answer that confidently."
   Most RAG demos hallucinate. Yours abstains. That's a feature and an interview talking point.
5. **Retrieval-config toggle** (THE DEMO MOMENT) — a subtle control to switch live between
   dense-only / hybrid / hybrid+rerank, showing how the retrieved chunks change in real time.
   This makes the eval report *interactive*. Nobody else has this.
6. **Eval report page** — clean, well-typeset, the three-config comparison table with real
   numbers and Tremor bar charts. A portfolio artifact in itself.

## Component stack
shadcn/ui (customized) + Tailwind · Tremor (eval charts) · Motion (micro-interactions only:
citation drawer slide-in, chunk highlight) · curated lucide icons

## The test before shipping any screen
"Would this look at home inside Perplexity or Hebbia's actual product?"
