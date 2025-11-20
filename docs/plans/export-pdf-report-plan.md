# Phase Report PDF Export Plan

## Goal & Context
- Deliver a one-click PDF export that mirrors the Phase workflow UI (Phase 2 goal → Phase 3 execution → Phase 4 final article).
- Reuse confirmed UI styling for typography, color, chips, and cards so the document feels like an offline snapshot of the app.
- Include the small product logo in the top-right corner of each page to reinforce branding.

## Source Material Inventory
- `workflowStore` selectors expose the active session’s Phase 2 research goal, Phase 3 step content (ordered steps, summaries, artifacts), and Phase 4 final article.
- Session history JSON files backfill past runs; ensure the export can work from either in-memory state or a persisted session ID.
- Confirm the localization strategy (we expect Chinese labels in current Phase 3 design) so the PDF strings match the UI language.

## Visual Language Alignment
- **Typography**: carry over the UI pairing (`Inter` or current sans-serif) for headings and body; enforce h1/h2/h3 scales identical to the live Step cards.
- **Color Palette**: reuse the primary accent (#3B82F6) for section headers and the muted neutral background (#F7F9FC) for cards.
- **UI Elements Reused**:
  - Pill badges for step phases (e.g., `Phase2Synthesize`, `Phase3Execute`) with the same chip styling.
  - Card containers with 12px radius, subtle shadow, and vertical rhythm identical to `Phase3StepCard`.
  - Subtle timeline dots/connector borrowed from the Phase 3 left column to visually link steps.
  - Status micro-icons (checkmarks, info) from the component library for callouts.
- **Branding**: mini logo (36px width) anchored in the top-right margin with low opacity watermark variation available for later iterations.

## Layout Blueprint (ASCII Draft)
```
┌────────────────────────────────────────────── PDF Page ──────────────────────────────────────────────┐
│ Research Tool                                                                                 ⬤Logo │
│ ─────────────────────────────────────────────────────────────────────────────────────────────────── │
│ Research Objective                                                                              │Pill│
│ ┌──────────────────────────────────────────────────────────────────────────────────────────────┐    │
│ │ Goal Statement (bold h2)                                                                     │    │
│ │ Supporting bullets, key metrics, links (body text)                                           │    │
│ └──────────────────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                                      │
│ Research Execution Summary                                                                         │
│ ┌ Insight Card ─────────────────────────────┐   ┌ Insight Card ──────────────────────────────┐       │
│ │ Chip: StepLabel              Timestamp     │   │ Chip: StepLabel              Timestamp      │       │
│ │ - Key Insight bullet                                                            │ CTA tag   │       │
│ │ - Evidence snippet                                                             │           │       │
│ │ Callout box for artifacts (icon + link)                                        │           │       │
│ └─────────────────────────────────────────────┘   └────────────────────────────────────────────┘     │
│ ... (additional insight cards stacked with timeline connector)                                      │
│                                                                                                      │
│ Final Report Article                                                                                │
│ ┌──────────────────────────────────────────────────────────────────────────────────────────────┐    │
│ │ Headline (h1)                                                                                 │    │
│ │ Subheading (italic)                                                                           │    │
│ │ Body paragraphs with preserved emphasis, quotes styled using speech-bubble callouts           │    │
│ │ Key Recommendations grid (two-column pill list)                                               │    │
│ └──────────────────────────────────────────────────────────────────────────────────────────────┘    │
│ Footer: session name • researcher • exported timestamp • page X of Y                               │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Service Architecture Plan
- **Data Layer**: build `selectReportSnapshot(sessionId?)` utility returning normalized sections with fallbacks (e.g., “尚未生成结果” badges).
- **Template Renderer**:
  - Option A (preferred): HTML/CSS template rendered via headless Chromium in backend service to ensure fidelity with existing stylesheets.
  - Option B: Client-side `react-pdf` for lighter footprint if backend deployment is constrained; verify support for Chinese fonts and badges.
- **Asset Pipeline**: store the logo SVG and font files in a shared assets bundle; embed or subset fonts for PDF to avoid missing glyphs.
- **API Surface**:
  - `POST /exports/phase-report` accepting `sessionId` or `payload`.
  - Streams PDF binary; includes caching headers for repeated downloads.
  - Frontend hook `useExportPhaseReport(sessionId)` to trigger request, handle progress toast, download blob.

## Implementation Phases
1. **Design Handoff**: collect UI tokens (spacing, colors, badge styles), confirm logo treatment, and finalize copywriting tone.
2. **Data Normalization**: implement selectors and unit tests with mock sessions (complete, partial, missing sections).
3. **Template Development**: reproduce layout in HTML/CSS (or `react-pdf`) with responsive behavior for optional long content.
4. **PDF Generation Service**: integrate chosen renderer, embed fonts, add watermark toggle.
5. **Frontend Integration**: add export entry point in Phase workflow UI, confirm consistent loading/error states.
6. **QA & Localization**: verify multi-page flows, non-Latin characters, right-to-left fallback, and long artifact lists.

## Asset & Content Checklist
- Logo SVG + optional watermark PNG.
- Font licensing confirmation (Inter or replacement) for embedded usage.
- Icon set for tips, warnings, artifacts.
- Copy deck for section titles in both CN and EN variants.

## Testing Strategy
- Golden-master snapshot tests comparing generated PDF against fixture using PDF diff tooling.
- Manual review in Acrobat, macOS Preview, Chrome PDF viewer.
- Performance benchmarks on large sessions (≥10 Phase 3 steps).
- Accessibility audit: tagged headings, alt text for logo, selectable text verification.

## Open Questions
- Should we allow partial exports during Phase 3 or restrict to completed sessions?
- Do we need customization (e.g., hide Phase 2 goal) per client?
- Any compliance requirements for embedding researcher signatures or legal footers?

## Next Actions
- Align with design team on final color tokens and confirm logo placement.
- Prototype HTML template with one sample session to validate layout proportions.
- Decide between backend vs client rendering based on infrastructure constraints.


