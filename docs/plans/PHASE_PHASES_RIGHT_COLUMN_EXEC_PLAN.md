# Research Phases Right Column Alignment Plan

## 1. Context & Problem Statement
- Phase pages (`phase0` through `phase4`, including `phase0_5`) display heterogeneous layouts: only `Phase3SessionPage` consistently renders the sticky interaction column (`lg:sticky lg:top-24`).
- Phases without the right column lose parity in status/controls, leading to user confusion and requiring extra navigation to access AI actions or streaming updates.
- Upcoming UX goals call for a unified two-column research workspace so users always see investigation steps on the left and the live AI console on the right regardless of phase progression.
- The provided screenshot highlights missing right-column UI on other phases that should mirror the Phase 3 experience.
- Legacy layouts for phases 0–2 surface the `AI 响应流` card inside the main content area; this block becomes redundant once the sticky sidebar exists and must be removed/repositioned.
- Phase 3 currently delivers the desired UX (card styling, sticky behavior, interaction controls); it will serve as the canonical reference for visual design, spacing, and interactivity.
- The streamed output can grow very long, overwhelming the sidebar. We need an adaptive design (inspired by the Cursor screenshot) that offers folding, quick jump controls, and a glowing “now” summary without losing earlier context.

## 2. Objectives
1. **Uniform Layout**: Ensure every research phase view (0, 0.5, 1, 2, 3, 4) uses a two-column grid with a persistent right-side interaction panel that matches Phase 3 styling.
2. **Dedicated Main Showcase**: Guarantee the left column focuses on phase-specific primary content (e.g., goals, plan steps, evidence), with no embedded stream cards or duplicate interaction boxes for phases 0–2.
3. **Reusable Components**: Abstract shared right-column elements into composable components/hooks to avoid duplication across pages while preserving Phase 3 look-and-feel.
4. **Responsive Consistency**: Maintain current mobile behavior (stacked layout) while guaranteeing the right column stays visible/sticky on large screens, mirroring Phase 3 breakpoints.
5. **State Integration**: Wire each phase to the appropriate websocket/message handlers so the right column always reflects live status, stream logs, and manual inputs when required.
6. **Adaptive Stream UX**: Provide progressive disclosure for long streams—folding, collapsing, and quick navigation controls, plus a “current highlight” summary chip.
7. **Regression Safety**: Provide testing coverage and manual QA guidance to prevent layout regressions, scroll issues, or broken stream interactions.

## 3. Key Deliverables
- `client/src/components/phaseCommon/PhaseInteractionPanel.tsx`: evolving into a composable shell supporting stream folding and summary sections.
- `client/src/components/phaseCommon/StreamSegments.tsx` (new): renders grouped stream items with expand/collapse logic and height constraints.
- `client/src/components/phaseCommon/StreamSummaryGlance.tsx` (new): badge-style "glowing" summary highlighting the active action, modeled after the screenshot.
- Updated store selectors/utilities to derive segment metadata (current status, new tokens count, timestamps).
- Interaction affordances: fold/unfold buttons, scroll-to-top/active controls, truncated preview with "展开" button when content exceeds thresholds.
- Accessibility copy + animation tokens aligned with existing design language.
- QA checklist documenting collapse/expand behavior, summary chip updates, and responsive behavior.

## 4. Work Breakdown & Sequencing

### 4.1 Discovery & Inventory (0.5 day)
- Locate all stream rendering entry points (`PhaseInteractionPanel`, `StreamDisplay`, store buffers).
- Audit current message structure (roles, timestamps, token counts) to ensure we can compute segment lengths and grouping boundaries.
- Capture Cursor screenshot characteristics: summary glow style, tab toggles, copy/expand buttons.
- Confirm with UX how many messages to show by default (e.g., latest 3 expanded, older collapsed).

### 4.2 Stream Segmentation Model (0.5 day)
- Define `StreamSegment` interface (id, title, role, content, startedAt, lastTokenAt, tokenCount, status).
- Add selector `useStreamSegments(limit?: number)` that transforms raw buffers into ordered segments with computed properties.
- Include derived flags: `isCollapsible` (content length > threshold), `collapsedSummary` (first N characters + ellipsis), `isActive` (matches active stream id).
- Ensure selector memoization to avoid re-renders while streaming.

### 4.3 UI Component: StreamSegments (1 day)
- Build `StreamSegments` component using virtualized list or CSS max-height to prevent overflow.
- Provide controls per segment:
  - Expand/collapse toggle with smooth transition.
  - Copy button (hook into existing clipboard logic if available).
  - Status badge (active/completed/error) with animation for active.
- Implement “Show Earlier Updates” button when segments exceed default visible count.
- Add quick navigation buttons (scroll to top, scroll to active) pinned at panel header/footer.

### 4.4 UI Component: Summary Glance (0.5 day)
- Create `StreamSummaryGlance` component showing current action or latest token message in a glowing badge (gradient background + subtle pulse).
- Accept props: `statusLabel`, `phase`, `lastUpdated`, `activeAction`, `tokenCount`.
- Integrate into `PhaseInteractionPanel` header beneath status row; update automatically via `usePhaseInteraction` data.

### 4.5 Panel Integration (1 day)
- Replace inline message map in `PhaseInteractionPanel` with `StreamSummaryGlance` + `StreamSegments` sections.
- Ensure folding state persists across rerenders (e.g., keep open segments in component state keyed by segment id).
- Provide fallback placeholder when no segments exist (current message).
- Maintain existing footer with user input controls.

### 4.6 Transition & Animations (0.5 day)
- Use CSS transitions or Framer Motion for smooth expand/collapse.
- Add `max-height` + gradient fade for collapsed segments.
- Ensure performance acceptable while streaming (avoid layout thrashing by limiting animation scope).

### 4.7 Testing & QA (0.75 day)
- Component tests verifying collapsed vs expanded state, button labels, summary updates (React Testing Library).
- Snapshot tests (Jest or Storybook) for collapsed/expanded variants.
- Manual QA checklist:
  - Streaming long content auto-collapses older entries.
  - Expand retains scroll position reasonably.
  - Summary badge updates when `currentAction` or `activeStreamId` changes.
  - Copy/expand buttons accessible via keyboard.
  - Mobile view stacks gracefully and collapse controls remain reachable.

### 4.8 Documentation & Rollout (0.25 day)
- Update `docs/frontend` with stream panel UX guidelines.
- Note store selectors introduced and how to extend the summary case.
- Provide release note callout explaining new folding behavior and summary indicator.

## 5. Dependencies & Coordination
- Confirm store exposes necessary metadata (active stream id, timestamps, token counts) for summary glances.
- Coordinate with UX for exact animation styles, gradient colors, and microcopy (e.g., “展开完整内容”).
- Align with QA on sample long-session logs to validate folding.
- Ensure translation strings exist for new buttons (expand, collapse, copy summary).

## 6. Risks & Mitigations
- **Performance Impact**: Expensive DOM operations during streaming; mitigate with virtualization or throttled updates.
- **Accessibility**: Ensure collapsed content accessible to screen readers—use `aria-expanded`, provide hidden text for summary.
- **State Drift**: Collapsed state might reset on store updates; key state to stable ids and memoize selectors.
- **User Confusion**: Provide clear affordances (chevrons, hint text) indicating content is collapsed.

## 7. Success Criteria
- Sidebar handles long sessions without overwhelming scroll; collapsed segments reduce immediate height while preserving access.
- Summary glance reflects current action with a noticeable glow, mirroring Cursor inspiration.
- Users can quickly toggle segments, copy content, and jump to active stream.
- No regressions in streaming reliability or user input interactions.
- Documentation and QA artifacts updated, enabling future iterations on panel UX.
