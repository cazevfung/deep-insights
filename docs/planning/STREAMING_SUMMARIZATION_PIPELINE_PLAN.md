# Streaming Summarization Pipeline Plan

## Overview

Transform Phase 0 from a batch process to a streaming pipeline where:
1. **Scraping and Summarization run in tandem** - As soon as one item finishes scraping, it's immediately sent to summarization
2. **Phase 0 tracks completion** - Monitors both scraping and summarization progress
3. **Phase 0.5 waits** - Only starts when ALL items are scraped AND summarized

## Current Flow (Batch)

```
1. User submits links
2. Scraping starts (all items in parallel)
3. Scraping completes (all items done)
4. Phase 0 starts
   - Loads all scraped data
   - Summarizes all items (8 workers in parallel)
   - Creates abstracts
5. Phase 0.5 starts
```

## New Flow (Streaming Pipeline)

```
1. User submits links
2. Scraping starts (all items in parallel)
3. Phase 0 starts IMMEDIATELY (in parallel with scraping)
   - Sets up summarization queue
   - Waits for items to arrive
4. As each item finishes scraping:
   - Item data is immediately sent to Phase 0 summarization queue
   - Phase 0 worker picks it up and summarizes it
5. Phase 0 tracks:
   - Scraping completion status (per link_id)
   - Summarization completion status (per link_id)
6. When ALL items are scraped AND summarized:
   - Phase 0 creates abstracts from all summarized items
   - Phase 0 completes
7. Phase 0.5 starts
```

## Architecture Changes

### 1. Phase 0 Initialization Changes

**Current**: Phase 0 waits for scraping to complete, then loads all data at once.

**New**: Phase 0 starts immediately and:
- Creates a summarization queue
- Sets up worker pool (8 workers)
- Registers as a listener for `scraping:complete_link` events
- Tracks state: `{link_id: {'scraped': bool, 'summarized': bool}}`

### 2. Event-Driven Summarization

**New Component**: `StreamingSummarizationManager`

```python
class StreamingSummarizationManager:
    def __init__(self, client, config, ui, session):
        self.client = client
        self.config = config
        self.ui = ui
        self.session = session
        self.summarizer = ContentSummarizer(...)
        
        # State tracking
        self.item_states = {}  # {link_id: {'scraped': bool, 'summarized': bool, 'data': dict}}
        self.summarization_queue = Queue()
        self.expected_items = set()  # All link_ids we expect
        self.completed_lock = threading.Lock()
        
        # Worker pool
        self.workers = []
        self.num_workers = 8
        
    def register_expected_items(self, link_ids: List[str]):
        """Register all link_ids we expect to process."""
        self.expected_items = set(link_ids)
        for link_id in link_ids:
            self.item_states[link_id] = {
                'scraped': False,
                'summarized': False,
                'data': None
            }
    
    def on_scraping_complete(self, link_id: str, data: dict):
        """Called when an item finishes scraping."""
        with self.completed_lock:
            if link_id in self.item_states:
                self.item_states[link_id]['scraped'] = True
                self.item_states[link_id]['data'] = data
                # Add to summarization queue
                self.summarization_queue.put((link_id, data))
    
    def start_workers(self):
        """Start worker pool to process summarization queue."""
        # Start 8 workers that process items from queue
        # Similar to current implementation
    
    def wait_for_completion(self) -> bool:
        """Wait until all items are scraped AND summarized."""
        # Poll until: all scraped AND all summarized
        # Return True when complete
    
    def get_all_summarized_data(self) -> Dict[str, Any]:
        """Get all data with summaries attached."""
        return {link_id: state['data'] 
                for link_id, state in self.item_states.items() 
                if state['summarized']}
```

### 3. Workflow Service Integration

**Changes to `workflow_service.py`**:

1. **Start Phase 0 immediately** (don't wait for scraping):
   ```python
   # When scraping starts, also start Phase 0
   phase0_manager = StreamingSummarizationManager(...)
   phase0_manager.register_expected_items(all_link_ids)
   phase0_manager.start_workers()
   ```

2. **Route `scraping:complete_link` to Phase 0**:
   ```python
   # In message handler for 'scraping:complete_link'
   if phase0_manager:
       # Load the scraped data
       scraped_data = load_scraped_data_for_link(link_id, batch_id)
       phase0_manager.on_scraping_complete(link_id, scraped_data)
   ```

3. **Wait for Phase 0 completion**:
   ```python
   # After scraping completes, wait for Phase 0
   phase0_complete = phase0_manager.wait_for_completion()
   if phase0_complete:
       batch_data = phase0_manager.get_all_summarized_data()
       # Continue with Phase 0.5
   ```

### 4. Data Loading Changes

**Current**: `ResearchDataLoader.load_batch()` loads all data at once from files.

**New**: Need to load data incrementally:
- When `scraping:complete_link` arrives, load that specific item's data
- Store it in Phase 0's state tracker
- Queue it for summarization

**New Method**: `load_scraped_data_for_link(link_id, batch_id)` - loads single item's data

### 5. Phase 0 Execution Flow

**Modified `Phase0Prepare.execute()`**:

```python
def execute(self, batch_id: str, streaming_mode: bool = True) -> Dict[str, Any]:
    if streaming_mode:
        # Streaming mode: wait for items to arrive
        manager = StreamingSummarizationManager(...)
        manager.register_expected_items(expected_link_ids)
        manager.start_workers()
        
        # Wait for all items to be scraped and summarized
        manager.wait_for_completion()
        
        # Get all summarized data
        batch_data = manager.get_all_summarized_data()
        
        # Create abstracts from summarized data
        abstracts = self._create_abstracts_from_summarized_data(batch_data)
        
        # Quality assessment
        quality_assessment = self.data_loader.assess_data_quality(batch_data)
        
        return {
            "batch_id": batch_id,
            "data": batch_data,
            "abstracts": abstracts,
            "quality_assessment": quality_assessment
        }
    else:
        # Legacy batch mode (for backward compatibility)
        return self._execute_batch_mode(batch_id)
```

## Implementation Steps

### Step 1: Create StreamingSummarizationManager
- **File**: `research/phases/streaming_summarization_manager.py`
- **Features**:
  - Queue-based summarization (reuse current worker pool logic)
  - State tracking (scraped/summarized per link_id)
  - Event handlers for scraping completion
  - Completion detection

### Step 2: Modify Phase0Prepare
- **File**: `research/phases/phase0_prepare.py`
- **Changes**:
  - Add `streaming_mode` parameter
  - Integrate `StreamingSummarizationManager`
  - Modify `execute()` to support streaming
  - Keep batch mode for backward compatibility

### Step 3: Modify WorkflowService
- **File**: `backend/app/services/workflow_service.py`
- **Changes**:
  - Start Phase 0 immediately when scraping starts
  - Route `scraping:complete_link` messages to Phase 0 manager
  - Wait for Phase 0 completion before starting Phase 0.5
  - Handle edge cases (scraping fails, summarization fails)

### Step 4: Add Data Loading Helper
- **File**: `research/data_loader.py`
- **New Method**: `load_scraped_data_for_link(link_id, batch_id)`
- **Purpose**: Load single item's data from JSON file

### Step 5: Update Progress Tracking
- **File**: `backend/app/services/progress_service.py` (if needed)
- **Changes**:
  - Track summarization progress separately
  - Send progress updates for summarization
  - Combine scraping + summarization progress

## Benefits

1. **Faster Time-to-First-Result**: Users see summaries appearing as items finish scraping
2. **Better Resource Utilization**: Summarization starts immediately, no waiting
3. **Parallel Processing**: Scraping and summarization run in parallel
4. **Real-time Progress**: Users see both scraping and summarization progress
5. **Scalability**: Can handle large batches more efficiently

## Challenges & Solutions

### Challenge 1: Data Availability
**Problem**: How do we get scraped data when `scraping:complete_link` arrives?

**Solution**: 
- Scraping saves data to JSON files immediately
- Phase 0 loads from file when event arrives
- Or: Scraping sends data in the message (if not too large)

### Challenge 2: Error Handling
**Problem**: What if scraping fails but summarization is waiting?

**Solution**:
- Track failed items in state
- Mark as "scraped" (even if failed) so Phase 0 can complete
- Include error info in final batch_data

### Challenge 3: Ordering
**Problem**: Items might finish in different order

**Solution**:
- Use link_id as key, order doesn't matter
- Final abstracts can be ordered by link_id or original order

### Challenge 4: Backward Compatibility
**Problem**: Need to support both streaming and batch modes

**Solution**:
- Add `streaming_mode` flag (default: True)
- Keep batch mode code for fallback
- Can be toggled via config

## Testing Strategy

1. **Unit Tests**:
   - Test `StreamingSummarizationManager` state tracking
   - Test queue processing
   - Test completion detection

2. **Integration Tests**:
   - Test full flow: scraping → summarization → Phase 0.5
   - Test with various batch sizes
   - Test error scenarios

3. **Performance Tests**:
   - Compare streaming vs batch mode
   - Measure time-to-first-summary
   - Measure total completion time

## Configuration

Add to `config.yaml`:

```yaml
research:
  phase0:
    streaming_mode: true  # Enable streaming summarization
    summarization_workers: 8  # Number of parallel summarization workers
```

## Migration Path

1. **Phase 1**: Implement streaming mode alongside batch mode (feature flag)
2. **Phase 2**: Test with real data, compare performance
3. **Phase 3**: Make streaming mode default
4. **Phase 4**: Remove batch mode (or keep as fallback)

## Open Questions

1. **Data Transfer**: Should scraping send data in message or should Phase 0 load from file? Load from file (more reliable, handles large data)

2. **Progress Updates**: How to show combined scraping + summarization progress? Show both separately, plus combined percentage

3. **Failure Handling**: What if summarization fails for an item? Mark as failed, include in batch_data with error, continue

4. **Abstract Creation**: When to create abstracts? After all items summarized (current approach)

## Next Steps

1. Review and approve this plan
2. Implement `StreamingSummarizationManager`
3. Modify `Phase0Prepare` to use streaming mode
4. Update `WorkflowService` to coordinate scraping and summarization
5. Test with small batch
6. Test with large batch
7. Deploy and monitor

