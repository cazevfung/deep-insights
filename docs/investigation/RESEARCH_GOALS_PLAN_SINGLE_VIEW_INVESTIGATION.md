# Research Goals & Plan Single View Investigation

## Problem Statement

The Research Agent page currently displays all research goals (研究目标) and research plan steps (研究计划) simultaneously in a vertical list. This creates visual clutter and makes it difficult to focus on individual items. The user wants to display only one block at a time.

## Current Implementation Analysis

### Location
- **File**: `client/src/pages/ResearchAgentPage.tsx`
- **Sections**:
  1. Research Goals (研究目标) - Lines 120-146
  2. Research Plan (研究计划) - Lines 149-191

### Current Behavior

#### Research Goals Section (Lines 120-146)
```tsx
{researchAgentStatus.goals && researchAgentStatus.goals.length > 0 && (
  <div className="bg-neutral-light-bg p-6 rounded-lg border border-neutral-300">
    <h3 className="text-lg font-semibold text-neutral-900 mb-3">研究目标</h3>
    <ul className="space-y-2">
      {researchAgentStatus.goals.map((goal) => (
        <li key={goal.id} className="flex items-start gap-3 p-3 bg-neutral-white rounded border border-neutral-200">
          <span className="text-primary-500 font-medium">{goal.id}.</span>
          <div className="flex-1">
            <p className="text-neutral-800">{goal.goal_text}</p>
            {goal.uses && goal.uses.length > 0 && (
              <p className="text-sm text-neutral-500 mt-1">用途: {goal.uses.join(', ')}</p>
            )}
          </div>
        </li>
      ))}
    </ul>
  </div>
)}
```

**Issues:**
- All goals are rendered simultaneously using `.map()`
- No navigation or selection mechanism
- All items are always visible, causing scroll/space issues

#### Research Plan Section (Lines 149-191)
```tsx
{researchAgentStatus.plan && researchAgentStatus.plan.length > 0 && (
  <div className="bg-neutral-light-bg p-6 rounded-lg border border-neutral-300">
    <h3 className="text-lg font-semibold text-neutral-900 mb-3">研究计划</h3>
    <div className="space-y-3">
      {researchAgentStatus.plan.map((step) => (
        <div key={step.step_id} className="p-4 bg-neutral-white rounded border border-neutral-200">
          <div className="flex items-start gap-3">
            <span className="text-primary-500 font-semibold">步骤 {step.step_id}</span>
            <div className="flex-1">
              <p className="font-medium text-neutral-900">{step.goal}</p>
              {step.required_data && (
                <p className="text-sm text-neutral-600 mt-1">
                  <span className="font-medium">需要数据:</span> {step.required_data}
                </p>
              )}
              {step.chunk_strategy && (
                <p className="text-sm text-neutral-600 mt-1">
                  <span className="font-medium">处理方式:</span> {step.chunk_strategy}
                </p>
              )}
              {step.notes && (
                <p className="text-sm text-neutral-500 mt-1 italic">{step.notes}</p>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  </div>
)}
```

**Issues:**
- All plan steps are rendered simultaneously using `.map()`
- No navigation or selection mechanism
- All items are always visible, causing scroll/space issues

### Data Structure

#### Research Goals
```typescript
goals: Array<{
  id: number
  goal_text: string
  uses?: string[]
}> | null
```

#### Research Plan
```typescript
plan: Array<{
  step_id: number
  goal: string
  required_data?: string
  chunk_strategy?: string
  notes?: string
}> | null
```

**Store Location**: `client/src/stores/workflowStore.ts`
- Goals: `researchAgentStatus.goals`
- Plan: `researchAgentStatus.plan`

## Similar Patterns in Codebase

### Phase3SessionPage Pattern
- **File**: `client/src/pages/Phase3SessionPage.tsx`
- **Pattern**: Expand/collapse with all items visible
- **Not suitable**: Still shows all items, just collapsed

### WorkflowStepper Pattern
- **File**: `client/src/components/workflow/WorkflowStepper.tsx`
- **Pattern**: Horizontal stepper with navigation
- **Relevance**: Shows navigation pattern but for page-level routing, not item-level

### Store Pattern for Current Step
- **File**: `client/src/stores/workflowStore.ts`
- **Pattern**: `currentStepId: number | null` for Phase 3 steps
- **Relevance**: Similar concept could be applied to goals/plan

## Proposed Solutions

### Option 1: Single View with Navigation Controls (Recommended)

**Approach**: Show one item at a time with Previous/Next buttons and a step indicator.

**Implementation**:
1. Add local state to track current index:
   ```tsx
   const [currentGoalIndex, setCurrentGoalIndex] = useState(0)
   const [currentPlanIndex, setCurrentPlanIndex] = useState(0)
   ```

2. Display only the current item:
   ```tsx
   const currentGoal = researchAgentStatus.goals?.[currentGoalIndex]
   const currentStep = researchAgentStatus.plan?.[currentPlanIndex]
   ```

3. Add navigation controls:
   - Previous/Next buttons
   - Step indicator (e.g., "1 of 8")
   - Optional: Jump to specific item via dropdown/selector

**Pros**:
- Clean, focused view
- Easy to implement
- Familiar UX pattern
- Reduces visual clutter

**Cons**:
- Requires navigation to see other items
- Less overview of all items

### Option 2: Single View with Sidebar/List Overview

**Approach**: Show one item in detail with a compact list/sidebar showing all items.

**Implementation**:
1. Split layout: Detail view (70%) + List view (30%)
2. Clicking an item in the list shows it in detail
3. Current item highlighted in list

**Pros**:
- Overview of all items
- Easy navigation
- Good for many items

**Cons**:
- More complex layout
- Takes more horizontal space

### Option 3: Accordion with Single Open Item

**Approach**: Show all items but only allow one to be expanded at a time.

**Implementation**:
1. Use accordion pattern
2. When one item expands, others collapse
3. Default: First item expanded

**Pros**:
- Shows all items (overview)
- Only one detailed view at a time
- Familiar pattern

**Cons**:
- Still shows all items (less focused)
- More scrolling if many items

### Option 4: Carousel/Slider Pattern

**Approach**: Use a carousel component to swipe/navigate through items.

**Implementation**:
1. Use a carousel library or custom implementation
2. Swipe/arrow navigation
3. Dots indicator for position

**Pros**:
- Modern, smooth UX
- Touch-friendly
- Good for mobile

**Cons**:
- Requires additional library or complex implementation
- May be overkill for this use case

## Recommended Solution: Option 1 (Single View with Navigation)

### Implementation Details

#### 1. Component State
```tsx
const [currentGoalIndex, setCurrentGoalIndex] = useState(0)
const [currentPlanIndex, setCurrentPlanIndex] = useState(0)
```

#### 2. Navigation Functions
```tsx
const goToNextGoal = () => {
  if (researchAgentStatus.goals) {
    setCurrentGoalIndex((prev) => 
      prev < researchAgentStatus.goals.length - 1 ? prev + 1 : prev
    )
  }
}

const goToPreviousGoal = () => {
  setCurrentGoalIndex((prev) => (prev > 0 ? prev - 1 : 0))
}

const goToGoal = (index: number) => {
  if (researchAgentStatus.goals && index >= 0 && index < researchAgentStatus.goals.length) {
    setCurrentGoalIndex(index)
  }
}
```

#### 3. UI Components Needed
- Navigation buttons (Previous/Next)
- Step indicator ("1 of 8")
- Optional: Dropdown/selector to jump to specific item
- Optional: Keyboard navigation (arrow keys)

#### 4. Reset Logic
- Reset indices when goals/plan change
- Use `useEffect` to sync with data changes

### UI Mockup Structure

```
┌─────────────────────────────────────────┐
│ 研究目标                                │
│ ┌─────────────────────────────────────┐ │
│ │ [< Prev]  目标 1 of 8  [Next >]    │ │
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ 1. Goal text here...                │ │
│ │    用途: transcript, comments       │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ 研究计划                                │
│ ┌─────────────────────────────────────┐ │
│ │ [< Prev]  步骤 1 of 5  [Next >]    │ │
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ 步骤 1                              │ │
│ │ Goal description...                 │ │
│ │ 需要数据: transcript                │ │
│ │ 处理方式: sequential                │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## Implementation Checklist

### Phase 1: Research Goals Single View
- [ ] Add `currentGoalIndex` state
- [ ] Implement navigation functions (next/prev/goTo)
- [ ] Update UI to show only current goal
- [ ] Add navigation controls (buttons + indicator)
- [ ] Add keyboard navigation (optional)
- [ ] Add dropdown selector (optional)
- [ ] Reset index when goals change
- [ ] Handle edge cases (empty, single item)

### Phase 2: Research Plan Single View
- [ ] Add `currentPlanIndex` state
- [ ] Implement navigation functions (next/prev/goTo)
- [ ] Update UI to show only current step
- [ ] Add navigation controls (buttons + indicator)
- [ ] Add keyboard navigation (optional)
- [ ] Add dropdown selector (optional)
- [ ] Reset index when plan changes
- [ ] Handle edge cases (empty, single item)

### Phase 3: Polish & UX
- [ ] Add smooth transitions between items
- [ ] Add loading states
- [ ] Improve accessibility (ARIA labels)
- [ ] Add tooltips/help text
- [ ] Test with various data sizes
- [ ] Responsive design considerations

## Edge Cases to Handle

1. **Empty arrays**: Hide navigation, show empty state
2. **Single item**: Disable navigation buttons, show "1 of 1"
3. **Data changes**: Reset to first item when goals/plan update
4. **Index out of bounds**: Validate indices before accessing
5. **Concurrent updates**: Handle rapid navigation clicks

## Accessibility Considerations

- Keyboard navigation (Arrow keys, Home/End)
- ARIA labels for navigation buttons
- Screen reader announcements for current item
- Focus management when navigating

## Testing Scenarios

1. Navigate through all goals/plan steps
2. Test with 1 item, 5 items, 20+ items
3. Test rapid navigation clicks
4. Test when data updates mid-navigation
5. Test keyboard navigation
6. Test on mobile devices

## Files to Modify

1. `client/src/pages/ResearchAgentPage.tsx` - Main implementation
2. Potentially create reusable component: `client/src/components/research/StepNavigator.tsx` (optional)

## Dependencies

- No new dependencies required
- Uses existing React hooks (useState, useEffect)
- Uses existing UI components (Button, Card)

## Alternative: Reusable Component

Consider creating a reusable `StepNavigator` component that can be used for both goals and plan:

```tsx
interface StepNavigatorProps<T> {
  items: T[]
  currentIndex: number
  onIndexChange: (index: number) => void
  renderItem: (item: T, index: number) => React.ReactNode
  getItemLabel: (item: T, index: number) => string
  sectionTitle: string
}
```

This would reduce code duplication and make the pattern reusable for future features.

## Conclusion

The recommended approach is **Option 1: Single View with Navigation Controls**. It provides:
- Clean, focused UI
- Simple implementation
- Familiar UX pattern
- Minimal code changes
- Good performance

The implementation should be straightforward and can be done incrementally (goals first, then plan).


