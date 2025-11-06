# Quick Reference: Using Test Code in Backend (Zero Changes Needed)

## ✅ Good News: **No Changes Required to Test Files!**

The test files are already structured correctly and can be imported directly.

---

## How to Use Test Functions in Backend

### 1. Import Functions Directly

```python
# backend/app/services/workflow_service.py
from tests.test_full_workflow_integration import (
    run_all_scrapers,
    verify_scraper_results,
    run_research_agent
)
from tests.test_links_loader import TestLinksLoader
```

### 2. Use Functions in Async Context

```python
import asyncio

async def run_workflow(self, batch_id: str):
    # Test functions are synchronous, so use asyncio.to_thread()
    scrapers_result = await asyncio.to_thread(run_all_scrapers)
    verified = await asyncio.to_thread(verify_scraper_results, batch_id)
    result = await asyncio.to_thread(run_research_agent, batch_id)
    return result
```

### 3. That's It!

**No changes needed to test files.** They continue to work exactly as before.

---

## Available Functions

### From `test_full_workflow_integration.py`

- `run_all_scrapers() -> Dict[str, Any]` - Run all scrapers
- `verify_scraper_results(batch_id: str) -> bool` - Verify scraper results
- `run_research_agent(batch_id: str) -> Optional[Dict]` - Run research agent
- `verify_research_report(result: Dict, batch_id: str) -> bool` - Verify report
- `check_api_key() -> Optional[str]` - Check API key

### From `test_all_scrapers_and_save_json.py`

- `test_all_scrapers_and_save() -> List[Dict]` - Run all scrapers in parallel

### From `test_links_loader.py`

- `TestLinksLoader` class - Load and manage test links
  - `get_batch_id() -> str`
  - `get_links(type: str) -> List[Dict]`
  - `iter_links(types: Optional[List[str]]) -> Iterator`

---

## Why No Changes Are Needed

1. **Functions are at module level** - Not inside `if __name__ == "__main__"` blocks
2. **Test files have dual purpose** - Work as both scripts and modules
3. **No test-specific dependencies** - Functions use standard Python, not pytest-specific features
4. **Already designed for reuse** - Functions are self-contained

---

## Example: Complete Backend Service

```python
# backend/app/services/workflow_service.py
import asyncio
from typing import Dict, Optional
from pathlib import Path

# Import working test functions
from tests.test_full_workflow_integration import (
    run_all_scrapers,
    verify_scraper_results,
    run_research_agent
)
from tests.test_links_loader import TestLinksLoader

class WorkflowService:
    """Simplified workflow service using proven test functions."""
    
    def __init__(self, websocket_manager):
        self.ws_manager = websocket_manager
    
    async def run_workflow(self, batch_id: str) -> Dict:
        """Run workflow using proven test functions."""
        try:
            # Step 1: Run all scrapers
            await self.ws_manager.broadcast(batch_id, {
                "type": "scraping:start",
                "message": "开始抓取内容..."
            })
            
            scrapers_result = await asyncio.to_thread(run_all_scrapers)
            
            # Step 2: Verify results
            verified = await asyncio.to_thread(verify_scraper_results, batch_id)
            if not verified:
                raise Exception("Scraper results verification failed")
            
            # Step 3: Run research agent
            await self.ws_manager.broadcast(batch_id, {
                "type": "research:start",
                "message": "开始研究代理..."
            })
            
            result = await asyncio.to_thread(run_research_agent, batch_id)
            
            if not result:
                raise Exception("Research agent failed")
            
            await self.ws_manager.broadcast(batch_id, {
                "type": "workflow:complete",
                "result": result
            })
            
            return result
            
        except Exception as e:
            await self.ws_manager.broadcast(batch_id, {
                "type": "error",
                "message": str(e)
            })
            raise
```

---

## Optional: Add Progress Callbacks (Future Enhancement)

If you want real-time progress updates, you could add optional callback parameters later:

```python
# Future enhancement (NOT required now)
def run_all_scrapers(progress_callback=None):
    if progress_callback:
        progress_callback({"type": "start", "message": "Running scrapers..."})
    else:
        print("STEP 1: Running All Scrapers")
    # ... rest of function
```

But this is **not necessary** to start - the functions work perfectly as-is.

---

## Summary

✅ **Zero changes needed** to test files  
✅ **Import and use directly** in backend  
✅ **Test scripts continue to work** unchanged  
✅ **No risk of breaking** existing functionality  

**Start using the functions right now - they're ready!**


