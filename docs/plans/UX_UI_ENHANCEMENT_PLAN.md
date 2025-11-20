# UX/UI Enhancement Plan - Research Tool

## Overview
This document outlines the plan to enhance the web app's user experience with dynamic navigation, sequential step-based UI, smooth animations, and research history functionality.

## Current State Analysis

### Current Issues
1. **No Automatic Navigation**: Users remain on the scraping page even when research starts
2. **Tab-Based Navigation**: Sidebar shows tabs without sequential meaning
3. **No Progress-Based Navigation**: UI doesn't automatically guide users to current stage
4. **No Research History**: No way to view past research sessions

### Current Architecture
- **Pages**: LinkInputPage → ScrapingProgressPage → ResearchAgentPage → Phase3SessionPage → FinalReportPage
- **Navigation**: React Router with static routes
- **State Management**: Zustand stores (workflowStore, uiStore)
- **Progress Tracking**: WebSocket updates for real-time progress
- **Current Phase Tracking**: `currentPhase` in workflowStore

## Proposed Enhancements

---

## 1. Sequential Step-Based UI

### 1.1 Visual Design
Replace the sidebar navigation with a **horizontal step indicator** at the top of the page showing the workflow as sequential steps:

```
[Step 1: 链接输入] → [Step 2: 内容抓取] → [Step 3: 研究代理] → [Step 4: 深度研究] → [Step 5: 最终报告]
```

### 1.2 Step States
Each step can be in one of these states:
- **Not Started** (灰色, disabled): Future steps
- **In Progress** (蓝色, pulsing): Current active step
- **Completed** (绿色, checkmark): Finished steps
- **Error** (红色, warning icon): Failed steps

### 1.3 Implementation Details
- **Component**: `WorkflowStepper` component
- **Location**: Replace or supplement the current Header
- **Visual Style**:
  - Horizontal layout on desktop
  - Vertical/scrollable on mobile
  - Connector lines between steps
  - Icons for each step
  - Progress percentage for current step

### 1.4 Step Definitions
1. **链接输入** (Link Input)
   - Icon: 🔗
   - Route: `/`
   - Status: Based on `batchId` presence

2. **内容抓取** (Scraping)
   - Icon: 📥
   - Route: `/scraping`
   - Status: Based on `scrapingStatus.completed` vs `scrapingStatus.total`

3. **研究代理** (Research Agent)
   - Icon: 🔬
   - Route: `/research`
   - Status: Based on `researchAgentStatus.phase` and `researchAgentStatus.goals`

4. **深度研究** (Phase 3)
   - Icon: 📊
   - Route: `/phase3`
   - Status: Based on `phase3Steps` completion

5. **最终报告** (Final Report)
   - Icon: 📄
   - Route: `/report`
   - Status: Based on `finalReport.status`

---

## 2. Dynamic Navigation Based on Progress

### 2.1 Automatic Navigation Logic
Implement a **navigation manager** that automatically routes users to the appropriate page based on workflow progress:

**Navigation Rules:**
1. **Link Input → Scraping**: When `batchId` is set and workflow starts
2. **Scraping → Research**: When `scrapingStatus.completed + failed === total` AND not cancelled
3. **Research → Phase3**: When `researchAgentStatus.phase === '2'` AND plan is confirmed
4. **Phase3 → Report**: When all Phase3 steps are completed
5. **Report**: Final destination (no auto-navigation away)

### 2.2 Implementation Strategy
- **Hook**: `useProgressNavigation` hook
- **Location**: Global hook in App.tsx or Layout component
- **Logic**: 
  - Monitor `workflowStore` state changes
  - Determine current active phase based on progress
  - Navigate to appropriate route
  - Respect user's manual navigation (optional: allow manual override)

### 2.3 User Override Option
- **Option A**: Allow users to manually navigate to any completed step
- **Option B**: Lock navigation to current step only (stricter)
- **Recommendation**: Option A with visual indication of current step

### 2.4 Navigation Triggers
- WebSocket message: `research:phase_change`
- WebSocket message: `scraping:status` (when complete)
- WebSocket message: `phase3:step_complete` (when all steps done)
- WebSocket message: `phase4:report_ready`

---

## 3. Smooth Animation Transitions

### 3.1 Page Transition Animation
When navigating between steps, implement a **slide/slide-out animation**:

**Animation Style:**
- **Direction**: Slide left (moving forward) / Slide right (moving backward)
- **Duration**: 300-400ms
- **Easing**: `ease-in-out` or `cubic-bezier(0.4, 0, 0.2, 1)`
- **Effect**: Fade + translate combination

### 3.2 Implementation Approach
- **Option A**: CSS transitions with React Router
  - Use `Framer Motion` or `react-transition-group`
  - Animate route changes
- **Option B**: Custom animation hook
  - Use React state + CSS transitions
  - Manual animation control

**Recommendation**: Use **Framer Motion** for smoother animations and better performance

### 3.3 Animation Details

**Slide Animation:**
```typescript
// Forward (next step)
- Current page: slide out to left (-100%)
- Next page: slide in from right (+100%)

// Backward (previous step)
- Current page: slide out to right (+100%)
- Previous page: slide in from left (-100%)
```

**Fade Animation:**
- Opacity: 1 → 0 (outgoing)
- Opacity: 0 → 1 (incoming)

### 3.4 Step Indicator Animation
- **Progress Bar**: Animate width as steps complete
- **Active Step**: Pulse animation or glow effect
- **Completed Steps**: Checkmark fade-in animation
- **Step Connector Lines**: Animate color/width as steps complete

### 3.5 Performance Considerations
- Use CSS transforms (GPU-accelerated)
- Avoid animating layout properties
- Debounce rapid state changes
- Preserve scroll position where appropriate

---

## 4. Research History Feature

### 4.1 History Storage
- **Location**: Backend API endpoint for retrieving past sessions
- **Storage**: Each batch_id represents a research session
- **Metadata**: Store session metadata (batch_id, created_at, status, topic, etc.)

### 4.2 History UI Location
**Option A**: Sidebar Menu Item
- Add "研究历史" (Research History) item in sidebar
- Opens a modal or dedicated page

**Option B**: Header Dropdown
- History icon in header
- Dropdown menu with recent sessions

**Option C**: Dedicated Page
- New route: `/history`
- Full page with search/filter capabilities

**Recommendation**: **Option A + C** (Sidebar menu item that navigates to history page)

### 4.3 History Page Features

#### 4.3.1 History List View
- **Display**: List of past research sessions
- **Columns**:
  - Batch ID / Session Name
  - Date Created
  - Status (Completed, In Progress, Failed, Cancelled)
  - Topic/Summary (if available)
  - Number of URLs
  - Actions (View, Resume, Delete)

#### 4.3.2 Session Details
- View full session details
- Resume incomplete sessions
- View final report (if completed)
- Download/export results

#### 4.3.3 Filtering & Search
- Filter by status
- Filter by date range
- Search by batch_id or topic
- Sort by date, status, etc.

#### 4.3.4 Session Preview
- Show quick preview on hover/click
- Display key metrics (URLs processed, completion percentage)
- Show current phase for in-progress sessions

### 4.4 Backend API Requirements

**New Endpoints:**
```
GET /api/history
  - Returns list of all research sessions
  - Query params: status, date_from, date_to, limit, offset

GET /api/history/:batch_id
  - Returns full session details
  - Includes all phases data

POST /api/history/:batch_id/resume
  - Resume an incomplete session
  - Reconnect WebSocket
  - Restore workflow state

DELETE /api/history/:batch_id
  - Delete a session (optional)
```

### 4.5 State Restoration
When resuming a session:
1. Load session data from backend
2. Restore `workflowStore` state
3. Navigate to appropriate page based on progress
4. Reconnect WebSocket for that batch_id
5. Continue from where it left off

---

## 5. Implementation Plan

### Phase 1: Sequential Step UI
1. Create `WorkflowStepper` component
2. Replace sidebar navigation with stepper (or add alongside)
3. Integrate with workflowStore to show current step
4. Add step status indicators
5. Style with CSS/Tailwind

**Files to Create/Modify:**
- `client/src/components/workflow/WorkflowStepper.tsx` (new)
- `client/src/components/layout/Header.tsx` (modify)
- `client/src/components/layout/Sidebar.tsx` (optional: keep or remove)

### Phase 2: Dynamic Navigation
1. Create `useProgressNavigation` hook
2. Implement navigation logic based on workflow state
3. Add navigation triggers in WebSocket handler
4. Test navigation flow

**Files to Create/Modify:**
- `client/src/hooks/useProgressNavigation.ts` (new)
- `client/src/App.tsx` (modify)
- `client/src/hooks/useWebSocket.ts` (modify)

### Phase 3: Animation System
1. Install Framer Motion (or alternative)
2. Create animated route wrapper
3. Add page transition animations
4. Add step indicator animations
5. Test and refine animations

**Files to Create/Modify:**
- `client/src/components/common/AnimatedPage.tsx` (new)
- `client/src/App.tsx` (modify)
- `client/src/components/workflow/WorkflowStepper.tsx` (modify)

### Phase 4: Research History
1. Create History page component
2. Create History API service methods
3. Implement history list view
4. Add session detail view
5. Implement resume functionality
6. Add filtering and search

**Files to Create/Modify:**
- `client/src/pages/HistoryPage.tsx` (new)
- `client/src/services/api.ts` (modify)
- `client/src/components/layout/Sidebar.tsx` (modify)
- `client/src/App.tsx` (modify - add route)

**Backend Files (if needed):**
- `backend/api/history.py` (new) - History endpoints
- `backend/storage/session_storage.py` (modify) - Session metadata storage

---

## 6. Technical Specifications

### 6.1 Component Structure
```
components/
  workflow/
    WorkflowStepper.tsx      # Step indicator component
    StepIndicator.tsx        # Individual step component
  common/
    AnimatedPage.tsx         # Page transition wrapper
  history/
    HistoryPage.tsx          # History list page
    HistoryItem.tsx          # Individual history item
    HistoryFilters.tsx       # Filter/search component
```

### 6.2 Hook Structure
```
hooks/
  useProgressNavigation.ts   # Auto-navigation logic
  useWorkflowStep.ts         # Step status calculation
```

### 6.3 Store Updates
- **workflowStore**: Add `currentStep` computed property
- **uiStore**: Add `manualNavigationOverride` flag
- **historyStore** (new): Store history list and current session

### 6.4 Animation Library
**Recommendation**: **Framer Motion**
- Pros: Smooth, performant, easy to use
- Cons: Additional dependency (~50KB gzipped)

**Alternative**: `react-transition-group`
- Pros: Smaller, no external deps
- Cons: More manual setup required

---

## 7. User Experience Flow

### 7.1 New User Flow
1. User lands on Link Input page
2. Enters URLs and submits
3. **Auto-navigates** to Scraping page with slide animation
4. Step indicator shows Step 2 as active
5. When scraping completes, **auto-navigates** to Research page
6. Step indicator updates to show Step 3 active, Step 2 completed
7. Process continues through all steps
8. User can manually navigate to any completed step

### 7.2 Returning User Flow
1. User opens History page from sidebar
2. Sees list of past sessions
3. Clicks on a session to view details
4. Clicks "Resume" if incomplete, or "View Report" if complete
5. App restores state and navigates to appropriate page

### 7.3 Manual Navigation
- User can click on any completed step in the stepper
- Navigation animates appropriately (forward/backward)
- Current step is always highlighted

---

## 8. Design Considerations

### 8.1 Responsive Design
- **Desktop**: Horizontal stepper at top
- **Mobile**: Vertical stepper or collapsible
- **Tablet**: Horizontal with scroll if needed

### 8.2 Accessibility
- Keyboard navigation for steps
- ARIA labels for screen readers
- Focus management during transitions
- High contrast mode support

### 8.3 Performance
- Lazy load history data
- Debounce navigation triggers
- Optimize animation performance
- Cache session data

### 8.4 Error Handling
- Handle navigation errors gracefully
- Show error state in step indicator
- Allow manual recovery from errors

---

## 9. Testing Strategy

### 9.1 Unit Tests
- Step status calculation logic
- Navigation trigger conditions
- History filtering/search

### 9.2 Integration Tests
- Complete workflow navigation flow
- Session restoration
- Animation transitions

### 9.3 E2E Tests
- Full workflow from input to report
- History viewing and resuming
- Manual navigation between steps

---

## 10. Future Enhancements (Optional)

1. **Step Progress Persistence**: Save progress across browser sessions
2. **Step Bookmarks**: Allow users to bookmark specific steps
3. **Export Session**: Export session data as JSON
4. **Session Sharing**: Share session links with others
5. **Analytics Dashboard**: Show session statistics and trends
6. **Batch Operations**: Bulk actions on history items

---

## 11. Implementation Timeline Estimate

- **Phase 1 (Step UI)**: 1-2 days
- **Phase 2 (Dynamic Navigation)**: 1-2 days
- **Phase 3 (Animations)**: 1-2 days
- **Phase 4 (History)**: 2-3 days
- **Testing & Refinement**: 1-2 days

**Total**: ~1-2 weeks for complete implementation

---

## 12. Questions for Confirmation

1. **Navigation Override**: Should users be able to manually navigate to any step, or only to completed steps?
    ANSWER: user should be able to navigate to any steps that are either in progress or completed. for steps that are not in progress or not completed, the UI should hide them. when the steps status change to be in progress, the UI will show that sequential step, and the user can monitor its progress.
2. **Step Indicator Location**: Top of page, or keep in sidebar?
    ANSWER: let's change it to top of page, showing as a left to right interaction logic. you may also need to add minimalistic expand collapse logic for good UX.
3. **Animation Style**: Slide, fade, or both?
    ANSWER: it depends. you may need to use different approaches for different interactions.
4. **History Storage**: Should we store full session data or just metadata?
    ANSWER: we need to be able to retrieve--batch number, links from user input, approved goals of that batch, research results of each step, and the final research report.
5. **Mobile Experience**: How should the stepper work on mobile devices?
    ANSWER: let's ignore mobile for now and focus on the desktop experience.
6. **Session Deletion**: Should users be able to delete sessions, or keep all history?
    ANSWER: user should be able to delete sessions, but by default, all history are kept.

---

## Approval

Please review this plan and provide feedback on:
- Overall approach
- Design choices
- Implementation priorities
- Any additional requirements

Once approved, we can proceed with implementation.




