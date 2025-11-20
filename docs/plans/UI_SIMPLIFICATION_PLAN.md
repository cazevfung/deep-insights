# UI Simplification Plan

## 1. Motivation & Problem Statement
- Current product surfaces multiple nested headings, stacked CTAs, and dense info blocks on several key screens (`StreamDisplay`, `AgentConsole`, `DatasetConfig`), exhausting visual hierarchy and burying primary workflows.
- User feedback from Nov 2025 usability sessions flagged cognitive overload: participants needed >3 hints to locate the main action in 4/7 tasks, and session heatmaps show scanning back-and-forth across panel borders.
- Cross-platform audits (web + embedded desktop shell) reveal inconsistent component scales, iconography repetition, and redundant section titles that compete with contextual hints.
- We need a structured simplification effort that preserves functionality, emphasizes primary flows, and reduces attention tax without triggering feature regression.

## 2. North Star Goals
1. **Clarity first**: Every screen exposes one primary goal and ≤2 supportive actions.
2. **Progressive disclosure**: Secondary information appears on demand (collapsible, tooltips, drawers) rather than inline blocks.
3. **Consistent hierarchy**: Shared typography and spacing tokens guarantee predictable visual rhythm.
4. **Measurable calm**: Quantifiable drop (≥25%) in glance time to primary action and headline readability scores ≥70 on UX baseline tests.

## 3. Scope & Deliverables
- **Design system alignment**: Update tokens, component variants, and layout patterns in `client` to enforce simpler hierarchies.
- **Screen-by-screen simplification**: Streamline high-impact surfaces (Streaming dashboard, Research session logs, Dataset configuration, Integrations wizard, Admin controls).
- **Content & microcopy refresh**: Replace verbose headings with single-line intents; prune redundant CTA labels.
- **Instrumentation update**: Track user focus and CTA usage post-simplification for validation.
- **Rollout playbook**: Provide migration guidance and QA checklist for multidisciplinary teams.

## 4. Guiding Principles
- **Fewer layers, stronger cues**: Maximum of three hierarchy levels per view (title, section, inline label).
- **Action priority**: Only one primary button per logical section; convert siblings to secondary or menu actions.
- **Information scent**: Replace dense bullet blocks with succinct summaries (<100 characters) linked to detail drawers.
- **Component reuse**: Favor existing layout primitives (`Stack`, `Card`, `Accordion`) instead of bespoke wrappers.
- **Responsive parity**: Ensure simplification applies across breakpoints; avoid reintroducing clutter on small screens.

## 5. Current State Audit
- **Inventory mapping**: Catalogue all headings, CTAs, info blocks per screen; score severity (High = >3 headings above fold, >2 CTAs same level).
- **UX debt tags**: Annotate components with `ui:simplify` flags in Figma + Storybook for traceability.
- **Redundancy matrix**: Identify repeated informational modules (e.g., duplicate “Stream summary” cards) and propose consolidation.
- **Data capture**: Capture baseline analytics (click depth, time-to-primary action, bounce) before changes.

## 6. Simplification Framework
1. **Assess** (Design + PM)
   - Run heuristic evaluation against guiding principles.
   - Prioritize screens based on user frequency and severity scores.
2. **Design Direction** (Design system team)
   - Produce low-fidelity wireframes demonstrating reduced hierarchy.
   - Codify updated typographic scale (e.g., `Title` → `Headline`, `Section` → `Subheadline`) and CTA styles.
3. **Content Pass** (Content strategy)
   - Draft concise titles and microcopy list per screen with voice/tone alignment.
   - Provide tooltip text for deferred details.
4. **Implementation Blueprints** (Design + Frontend leads)
   - Map wireframes to component updates; identify refactors vs. toggles.
   - Document layout rules in `docs/frontend/style-guide.md`.
5. **Engineering Preparation** (Frontend squads)
   - Create feature flags / environment toggles to test simplified layouts per route.
   - Update Storybook stories for key components with simplified variants.
6. **Validation** (UX research + QA)
   - Conduct A/B or hallway tests measuring task completion time and reported clarity.
   - Verify responsiveness, accessibility (focus order, heading levels, color contrast).

## 7. Workstreams & Responsibilities
- **Design System Overhaul**
  - Owners: Design system lead + frontend infrastructure.
  - Deliver: token adjustments, component variant guidelines, Storybook documentation.
- **High-Traffic Screens**
  - Owners: Streaming squad, Research agent squad.
  - Deliver: simplified `StreamDisplay`, `AgentConsole`, `SessionInsights` flows.
- **Configuration & Admin**
  - Owners: Data platform squad.
  - Deliver: decluttered dataset/integration setup screens, flattened admin panels.
- **Content & Localization**
  - Owners: Content strategist + localization vendor.
  - Deliver: streamlined headings, CTA labels, updated translation keys.
- **Research & Analytics**
  - Owners: UX research + data analytics.
  - Deliver: baselines, experiment plans, post-launch dashboards.

## 8. Milestones & Timeline (tentative)
- **M0 – Audit & Principles (Week 1)**
  - Complete UI inventory and severity scoring.
  - Publish guiding principle doc + design tokens proposal.
- **M1 – Design Directions (Week 2)**
  - Wireframes for top 3 screens.
  - Content drafts delivered for review.
- **M2 – Component Updates (Week 3)**
  - Merge design token changes.
  - Ship Storybook updates and developer documentation.
- **M3 – Screen Implementation (Weeks 4-5)**
  - Feature-flagged simplified layouts for streaming, agent, configuration flows.
  - Run QA + accessibility review.
- **M4 – Validation & Rollout (Week 6)**
  - Execute user tests, compare metrics vs. baseline.
  - Decide on full rollout; update release notes and runbooks.

## 9. Metrics & Success Criteria
- **Primary action discoverability**: Average time-to-primary CTA reduced by ≥25% on instrumented flows.
- **Heading density**: ≤2 top-level headings per viewport on audited screens.
- **CTA clarity**: NPS-style question on clarity improves by ≥0.5 points in post-task surveys.
- **Info block reduction**: 40% drop in concurrent info blocks rendered above fold (tracked via DOM instrumentation).
- **Accessibility**: All updated pages meet WCAG 2.1 AA headings structure and focus order guidelines.

## 10. Risks & Mitigations
- **Stakeholder pushback**: Teams may fear loss of informational depth. Mitigate with progressive disclosure prototypes and stakeholder walkthroughs.
- **Scope creep**: Simplification could prompt unrelated redesign requests. Mitigate via clear intake process and backlog triage.
- **Regression risk**: Removing CTAs may hide advanced workflows. Mitigate with user testing, data-driven gating, and fallback entry points in overflow menus.
- **Localization drift**: Shorter copy may desync with existing translations. Mitigate by coordinating translation updates before rollout.
- **Measurement noise**: Analytics may be confounded by simultaneous feature launches. Mitigate with feature flags and targeted experiment windows.

## 11. Implementation Guardrails (Engineering-Focused)
- Introduce reusable `SectionHeader` component enforcing single-line, truncated headings with tooltip fallback.
- Standardize padding/margin tokens (`space-16`, `space-24`) to enforce breathing room without creating new wrappers.
- Provide utility to collapse info blocks into expandable `InfoSummary` component with default closed state.
- Ensure component API docs include guidance on CTA tier usage (`primary`, `secondary`, `tertiary`, `icon-only`).
- Add lint rule or Storybook check to flag multiple `primary` buttons within the same layout container.

## 12. Communication & Change Management
- Weekly sync across squads to unblock design/engineering dependencies and reconcile scope adjustments.
- Publish changelog entries in `docs/frontend/changelog.md` for every merged simplification batch.
- Share living checklist in project tracker covering audit status, design review, implementation, QA sign-off for each screen.
- Partner with support team to update knowledge base screenshots and scripts once simplified UI ships.

## 13. Next Steps
1. Kick off audit workshop and assign screen owners by end of current sprint.
2. Spin up Figma project with shared components and annotate existing flows with clutter hotspots.
3. Prepare analytics dashboards (instrumented events, funnels) ready before M1 deliverables.
4. Schedule user validation sessions aligned with M3 deployments.

