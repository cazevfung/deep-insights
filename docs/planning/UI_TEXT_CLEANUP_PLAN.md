# UI Text Cleanup Plan

## Overview
This plan addresses two UI improvements:
1. Remove the default "等待AI响应..." text that always appears even when not needed
2. Move the "Research Tool v0.1.0" version marker from the bottom of the sidebar to the top of the page

---

## Issue 1: Remove Default "等待AI响应..." Text

### Current Behavior
- Location: `client/src/pages/ResearchAgentPage.tsx` (line 196)
- Current code:
  ```tsx
  {researchAgentStatus.streamBuffer || '等待AI响应...'}
  ```
- Problem: The text "等待AI响应..." always appears when `streamBuffer` is empty or falsy, even when the AI is not waiting for a response or when no AI interaction is happening.

### Proposed Solution
**Option A: Conditional Rendering (Recommended)**
- Only show the AI Response Display section when there's actual content to display
- Hide the section entirely when `streamBuffer` is empty and no AI interaction is active

**Option B: Empty State**
- Show an empty div or placeholder when no content is available
- Remove the default text entirely

**Implementation Steps:**
1. Modify `ResearchAgentPage.tsx` to conditionally render the AI Response Display section
2. Only display the section when:
   - `researchAgentStatus.streamBuffer` has content, OR
   - There's an active AI operation (can be determined by checking phase status or other indicators)
3. Remove the fallback text `'等待AI响应...'` entirely

### Files to Modify
- `client/src/pages/ResearchAgentPage.tsx`

### Specific Changes
- Line 193-198: Modify the AI Response Display section to conditionally render
- Remove the `|| '等待AI响应...'` fallback
- Add logic to determine if AI interaction is active (check phase, streamBuffer, or other status indicators)

---

## Issue 2: Move Version Marker to Top

### Current Behavior
- Location: `client/src/components/layout/Sidebar.tsx` (line 88-93)
- Current position: Bottom footer of the sidebar
- Code:
  ```tsx
  <div className="p-4 border-t border-neutral-500">
    <p className="text-xs text-neutral-400 text-center">
      Research Tool v0.1.0
    </p>
  </div>
  ```

### Proposed Solution
**Move to Header Component**
- Remove the version text from the Sidebar footer
- Add the version text to the Header component (top of the page)
- Position it appropriately (likely in the right side of the header)

### Implementation Steps:
1. **Remove from Sidebar:**
   - Delete or comment out the footer section (lines 88-93) in `Sidebar.tsx`
   - Remove the border-top styling if it's only used for the footer

2. **Add to Header:**
   - Modify `Header.tsx` to include the version text
   - Position it in the right side actions area (currently empty at line 39-41)
   - Style it appropriately (small text, subtle color)

### Files to Modify
- `client/src/components/layout/Sidebar.tsx` - Remove footer section
- `client/src/components/layout/Header.tsx` - Add version text to top

### Specific Changes

**Sidebar.tsx:**
- Remove lines 88-93 (footer div with version text)
- Optionally adjust padding/spacing if the footer was providing visual balance

**Header.tsx:**
- Add version text to the right side actions area (line 39-41)
- Style: `text-xs text-neutral-400` or similar subtle styling
- Position: Right side of header, aligned with other header content

---

## Design Considerations

### For Issue 1 (AI Response Text):
- Consider if there are other states where we should show something (e.g., "No AI response yet" vs completely hidden)
- Ensure the UI doesn't look broken when the section is hidden
- Consider adding a loading indicator if we want to show activity status

### For Issue 2 (Version Marker):
- Header version text should be subtle and not interfere with main content
- Consider if version should be clickable (e.g., show changelog or about dialog)
- Ensure responsive design: version text should work on mobile and desktop
- Consider positioning: top-right is standard, but could also be top-left or center

---

## Testing Checklist

### Issue 1 Testing:
- [ ] Verify "等待AI响应..." text doesn't appear when no AI interaction is active
- [ ] Verify AI response section appears when streamBuffer has content
- [ ] Verify AI response section appears when AI is actively processing
- [ ] Test with empty state (no research session active)
- [ ] Test with active research session but no current stream buffer
- [ ] Test with streaming content to ensure display works correctly

### Issue 2 Testing:
- [ ] Verify version text appears in header (top of page)
- [ ] Verify version text removed from sidebar footer
- [ ] Test responsive design (mobile and desktop)
- [ ] Verify header layout doesn't break with version text added
- [ ] Test on all pages to ensure version is visible everywhere

---

## Implementation Order

1. **First:** Move version marker (Issue 2) - simpler change, less risk
2. **Second:** Remove default AI response text (Issue 1) - requires more careful consideration of states

---

## Notes

- The version marker move is straightforward and low-risk
- The AI response text removal requires understanding all states where the section should/shouldn't appear
- Consider creating a constant for the version number if it's used in multiple places
- Both changes are cosmetic and don't affect functionality




