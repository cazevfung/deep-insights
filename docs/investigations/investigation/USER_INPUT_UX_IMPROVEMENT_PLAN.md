# User Input Prompt UX Improvement Plan

## Current State Analysis

### Current Implementation

**Location**: `client/src/pages/ResearchAgentPage.tsx` (lines 209-271)

**Current Behavior**:
1. User input prompt appears at the **bottom** of the content area (after goals, plan, stream buffer, etc.)
2. When user clicks a choice button or sends input:
   - Input is sent via WebSocket (`research:user_input` message)
   - Input field is cleared (`setUserInput('')`)
   - **BUT**: The prompt block remains visible until backend clears `waitingForUser` state
3. No visual feedback that input was received/processed
4. No indication that workflow is moving to next phase
5. No animation or "magical" disappearance effect

**Current Code Structure**:
```tsx
{/* User Input Area - Currently at bottom */}
{researchAgentStatus.waitingForUser &&
  researchAgentStatus.userInputRequired && (
    <div className="bg-neutral-light-bg p-6 rounded-lg border-2 border-primary-300">
      {/* Prompt content */}
      {/* Choice buttons or text input */}
    </div>
  )}
```

### State Management

**Location**: `client/src/stores/workflowStore.ts`

**Current State Flow**:
1. Backend sends `research:user_input_required` message
2. `useWebSocket.ts` updates state: `waitingForUser: true, userInputRequired: {...}`
3. User sends response via `handleChoiceClick()` or `handleSendInput()`
4. Frontend sends `research:user_input` message to backend
5. Backend processes input and eventually clears the prompt
6. State updates: `waitingForUser: false, userInputRequired: null`

**Issue**: There's a delay between step 4 and step 6, during which the prompt remains visible with no feedback.

## User Requirements

1. ✅ **User prompts should always be at the top** - Currently at bottom
2. ✅ **Block should disappear in a "magical way"** - Currently just disappears instantly
3. ✅ **Tell user we're entering next phase** - Currently no feedback
4. ✅ **Give confidence message was sent** - Currently no confirmation

## Proposed Improvements

### 1. Move Prompt to Top

**Change**: Reorder components in `ResearchAgentPage.tsx` to render user input prompt first.

**Implementation**:
- Move the user input block to the top of the `space-y-6` div
- Ensure it appears before goals, plan, and other content
- Use CSS to ensure it stays visually prominent (sticky positioning optional)

**Benefits**:
- User immediately sees what action is required
- No scrolling needed to find the prompt
- Better UX flow: prompt → content → results

### 2. Optimistic UI Update with Animation

**Change**: Immediately hide/transform the prompt when user submits, before backend confirmation.

**Implementation Strategy**:
1. Add local state to track "submitting" status
2. When user clicks choice or sends input:
   - Set `isSubmitting: true` immediately
   - Trigger exit animation (fade out + slide up)
   - Show "Processing..." feedback
3. After animation completes (300-500ms), remove from DOM
4. Show success message: "已收到您的确认，正在进入下一阶段..."

**Animation Options**:
- **Fade + Slide Up**: `opacity: 1 → 0` + `transform: translateY(0) → translateY(-20px)`
- **Scale + Fade**: `scale(1) → scale(0.95)` + `opacity: 1 → 0`
- **Slide Out**: `transform: translateX(0) → translateX(-100%)` + fade

**Recommended**: Fade + Slide Up (feels natural, like content moving away)

### 3. Visual Feedback States

**Change**: Add multiple visual states to show progress.

**States**:
1. **Waiting for Input** (current state)
   - Visible prompt with border highlight
   - Buttons/input enabled

2. **Submitting** (new - immediate on click)
   - Prompt starts exit animation
   - Show spinner or loading indicator
   - Disable buttons/input

3. **Processing** (new - after animation)
   - Show success message: "✓ 已收到您的确认"
   - Show next phase message: "正在进入下一阶段..."
   - Optional: Show progress indicator

4. **Complete** (new - when backend confirms)
   - Fade out success message
   - Continue with normal workflow

### 4. Success Message Component

**Change**: Add a temporary success/feedback message after prompt disappears.

**Implementation**:
- Create a new component: `UserInputFeedback.tsx`
- Show after prompt animation completes
- Display: "✓ 已收到您的确认，正在进入下一阶段..."
- Auto-dismiss after 2-3 seconds or when backend confirms

**Design**:
- Green checkmark icon
- Subtle background (green-50 or primary-50)
- Smooth fade-in animation
- Positioned where prompt was (smooth transition)

## Technical Implementation Plan

### Phase 1: Reorder Components

**File**: `client/src/pages/ResearchAgentPage.tsx`

**Changes**:
1. Move user input block to top of content area
2. Keep all other content below

**Code Structure**:
```tsx
<div className="space-y-6">
  {/* User Input Area - NOW AT TOP */}
  {researchAgentStatus.waitingForUser && ...}
  
  {/* Other content below */}
  {researchAgentStatus.synthesizedGoal && ...}
  {researchAgentStatus.goals && ...}
  {researchAgentStatus.plan && ...}
  ...
</div>
```

### Phase 2: Add Animation System

**Dependencies**: 
- ✅ **Framer Motion is already installed** (`framer-motion: ^10.16.16`)
- The project already uses Framer Motion for page transitions (`AnimatedPage.tsx`, `App.tsx`)
- Tailwind CSS transitions are also available

**Recommendation**: Use **Framer Motion** for consistency with existing codebase patterns
- More powerful animation control
- Better performance (GPU-accelerated)
- Consistent with existing `AnimatedPage` component
- Easier to handle complex animations and exit animations

**Implementation** (using Framer Motion):
1. Wrap prompt in `motion.div` with `AnimatePresence`:
   ```tsx
   import { motion, AnimatePresence } from 'framer-motion'
   
   <AnimatePresence>
     {showPrompt && (
       <motion.div
         initial={{ opacity: 1, y: 0 }}
         animate={{ opacity: 1, y: 0 }}
         exit={{ opacity: 0, y: -20 }}
         transition={{ duration: 0.3, ease: 'easeOut' }}
       >
         {/* Prompt content */}
       </motion.div>
     )}
   </AnimatePresence>
   ```
2. On user input, set `showPrompt` to `false` - Framer Motion handles the exit animation automatically
3. Use `onAnimationComplete` callback to show feedback message after exit

### Phase 3: Add Feedback Message

**Implementation**:
1. Add state: `const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null)`
2. After prompt exits, show feedback:
   ```tsx
   if (promptState === 'hidden') {
     setFeedbackMessage('✓ 已收到您的确认，正在进入下一阶段...')
   }
   ```
3. Clear feedback when backend confirms (when `waitingForUser` becomes false)

### Phase 4: Handle Backend State Updates

**Current Issue**: Backend may take time to process and clear `waitingForUser`.

**Solution**: 
- Use optimistic UI (hide immediately)
- Still listen for backend state changes
- If backend clears `waitingForUser` while prompt is animating, ensure smooth transition
- If backend sends error, show error message and restore prompt

**Implementation**:
```tsx
useEffect(() => {
  // When backend clears waitingForUser, ensure prompt is hidden
  if (!researchAgentStatus.waitingForUser && promptState !== 'hidden') {
    setPromptState('hidden')
    // Show success feedback if not already shown
    if (!feedbackMessage) {
      setFeedbackMessage('✓ 已收到您的确认，正在进入下一阶段...')
    }
  }
}, [researchAgentStatus.waitingForUser])
```

## Animation Details

### Exit Animation (Using Framer Motion)

**Duration**: 300ms
**Easing**: `easeOut` (starts fast, ends slow)
**Properties**:
- `opacity`: `1 → 0`
- `y`: `0 → -20` (translateY)
- Optional: `scale`: `1 → 0.95` for subtle shrink effect

**Framer Motion Code**:
```tsx
<motion.div
  initial={{ opacity: 1, y: 0, scale: 1 }}
  animate={{ opacity: 1, y: 0, scale: 1 }}
  exit={{ opacity: 0, y: -20, scale: 0.95 }}
  transition={{ 
    duration: 0.3, 
    ease: 'easeOut',
    opacity: { duration: 0.25 },
    y: { duration: 0.3 }
  }}
>
  {/* Prompt content */}
</motion.div>
```

### Feedback Message Animation

**Duration**: 200ms fade-in
**Easing**: `easeIn`
**Properties**:
- `opacity`: `0 → 1`
- `y`: `10 → 0` (slide up)

**Framer Motion Code**:
```tsx
<motion.div
  initial={{ opacity: 0, y: 10 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.2, ease: 'easeIn' }}
  className="feedback-message"
>
  ✓ 已收到您的确认，正在进入下一阶段...
</motion.div>
```

## Component Structure (Proposed)

```tsx
import { motion, AnimatePresence } from 'framer-motion'

const ResearchAgentPage: React.FC = () => {
  const [showPrompt, setShowPrompt] = useState(true)
  const [showFeedback, setShowFeedback] = useState(false)
  const [userInput, setUserInput] = useState('')
  
  // Reset prompt state when new prompt arrives
  useEffect(() => {
    if (researchAgentStatus.waitingForUser && researchAgentStatus.userInputRequired) {
      setShowPrompt(true)
      setShowFeedback(false)
    }
  }, [researchAgentStatus.userInputRequired?.prompt_id])
  
  // Hide feedback when backend confirms (waitingForUser becomes false)
  useEffect(() => {
    if (!researchAgentStatus.waitingForUser && showFeedback) {
      // Delay hiding feedback to show success message
      const timer = setTimeout(() => setShowFeedback(false), 2000)
      return () => clearTimeout(timer)
    }
  }, [researchAgentStatus.waitingForUser, showFeedback])
  
  const handleChoiceClick = (choice: string) => {
    // ... existing send logic ...
    
    // Hide prompt immediately (triggers exit animation)
    setShowPrompt(false)
    
    // Show feedback after animation completes
    setTimeout(() => {
      setShowFeedback(true)
    }, 300)
  }
  
  const handleSendInput = () => {
    // ... existing send logic ...
    
    // Hide prompt immediately (triggers exit animation)
    setShowPrompt(false)
    
    // Show feedback after animation completes
    setTimeout(() => {
      setShowFeedback(true)
    }, 300)
  }
  
  return (
    <div className="max-w-6xl mx-auto">
      <Card>
        <div className="space-y-6">
          {/* User Input Prompt - AT TOP */}
          <AnimatePresence>
            {researchAgentStatus.waitingForUser &&
              researchAgentStatus.userInputRequired &&
              showPrompt && (
                <motion.div
                  initial={{ opacity: 1, y: 0, scale: 1 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -20, scale: 0.95 }}
                  transition={{ duration: 0.3, ease: 'easeOut' }}
                  className="bg-neutral-light-bg p-6 rounded-lg border-2 border-primary-300"
                >
                  {/* Prompt content */}
                </motion.div>
              )}
          </AnimatePresence>
          
          {/* Feedback Message */}
          <AnimatePresence>
            {showFeedback && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2, ease: 'easeIn' }}
                className="bg-primary-50 border border-primary-200 p-4 rounded-lg text-primary-800"
              >
                ✓ 已收到您的确认，正在进入下一阶段...
              </motion.div>
            )}
          </AnimatePresence>
          
          {/* Rest of content */}
          ...
        </div>
      </Card>
    </div>
  )
}
```

## Edge Cases to Handle

### 1. Rapid Multiple Clicks
- **Issue**: User clicks multiple times before animation completes
- **Solution**: Disable buttons immediately on first click, ignore subsequent clicks

### 2. Backend Error After Submission
- **Issue**: Backend fails to process input
- **Solution**: 
  - Show error message
  - Restore prompt (reverse animation)
  - Allow user to retry

### 3. New Prompt Arrives During Animation
- **Issue**: Backend sends new prompt while current one is animating out
- **Solution**: 
  - Cancel exit animation
  - Reset to 'visible' state
  - Show new prompt immediately

### 4. WebSocket Disconnection
- **Issue**: Connection lost after user submits
- **Solution**: 
  - Still show success feedback (optimistic)
  - Show connection warning separately
  - Reconnect and retry if needed

## Accessibility Considerations

1. **Screen Readers**: 
   - Announce when prompt appears/disappears
   - Announce feedback messages
   - Use `aria-live` regions for dynamic content

2. **Keyboard Navigation**:
   - Ensure focus management during animation
   - Focus should move to feedback message or next interactive element

3. **Reduced Motion**:
   - Respect `prefers-reduced-motion` media query
   - Use instant transitions if user prefers reduced motion

## Testing Checklist

- [ ] Prompt appears at top of content area
- [ ] Prompt disappears smoothly when user clicks choice
- [ ] Prompt disappears smoothly when user sends text input
- [ ] Feedback message appears after prompt disappears
- [ ] Feedback message shows correct text
- [ ] Multiple rapid clicks are handled gracefully
- [ ] Backend errors restore prompt correctly
- [ ] New prompt replaces old one correctly
- [ ] Animation works on slow devices
- [ ] Accessibility features work (screen readers, keyboard)
- [ ] Reduced motion preference is respected

## Performance Considerations

1. **Animation Performance**:
   - Framer Motion automatically uses GPU-accelerated properties (`transform`, `opacity`)
   - Avoid animating `height`, `width`, `margin`, `padding` (Framer Motion warns about this)
   - Framer Motion optimizes animations automatically

2. **State Management**:
   - Keep local state minimal (`showPrompt`, `showFeedback`)
   - Clean up timeouts on unmount
   - Use `AnimatePresence` for proper exit animations
   - Avoid unnecessary re-renders

3. **Bundle Size**:
   - ✅ Framer Motion is already in the project (no new dependencies)
   - Framer Motion is tree-shakeable, so only used features are included

## Implementation Priority

1. **High Priority** (Core UX):
   - Move prompt to top
   - Add exit animation
   - Add feedback message

2. **Medium Priority** (Polish):
   - Handle edge cases
   - Add accessibility features
   - Optimize animations

3. **Low Priority** (Nice to have):
   - Sticky positioning (keep prompt visible while scrolling)
   - Sound effects (optional)
   - More elaborate animations

## Estimated Implementation Time

- **Phase 1** (Reorder): 15 minutes
- **Phase 2** (Animation): 1-2 hours
- **Phase 3** (Feedback): 30 minutes
- **Phase 4** (State handling): 1 hour
- **Testing & Polish**: 1-2 hours

**Total**: 4-6 hours

## Dependencies

- ✅ **Framer Motion** (already installed: `^10.16.16`)
- ✅ React (existing)
- ✅ Zustand (existing)
- ✅ Tailwind CSS (existing)

**No new dependencies needed!**

## Conclusion

This plan addresses all user requirements:
1. ✅ Prompts at top
2. ✅ Magical disappearance (smooth animation)
3. ✅ Feedback about next phase
4. ✅ Confidence that input was received

The implementation uses optimistic UI patterns to provide immediate feedback while maintaining compatibility with backend state management. The animation system is lightweight and performant, using CSS transitions rather than heavy animation libraries.

