### Scraping → Summarization Workflow Manager v3 (No-Race-Condition Design)

This document describes the v3 workflow manager for the scraping → summarization pipeline.  
The design assumes **a single authoritative workflow manager** that:
- Maintains item state (`idle` → `scraping` → `scraped` → `summarizing` → `completed`)
- Enforces the **max 8 concurrent scrapes** rule
- Serializes all state transitions (via a single event loop or equivalent locking) to avoid race conditions.

### High-Level Flowchart (Mermaid)

```mermaid
flowchart TD
    %% ========= Legend / Concurrency Notes =========
    subgraph Legend
      L1[State Box] --> L2{Decision}
      L3[[Async Worker]] --> L4[(Persistent Storage)]
    end

    %% ========= Start & Initialization =========
    START([Start Process])
    INIT[Initialize workflow, load items, set idle states, active_scrapes = 0, max_scrapes = 8]

    START --> INIT

    %% ========= Main Control Loop =========
    MAIN_LOOP[Main workflow loop - single manager & serialized events]
    INIT --> MAIN_LOOP

    MAIN_LOOP --> CHECK_DONE{Any items NOT 'completed'?}
    CHECK_DONE -- No --> PROCESS_DONE[Mark process finished]
    PROCESS_DONE --> PHASE_HALF([Start Phase 0.5])
    PHASE_HALF --> END([End])

    CHECK_DONE -- Yes --> CHECK_START_SCRAPE{Can start new scrape? active_scrapes < max_scrapes AND any idle item}

    %% ========= Start Scraping (Atomic Claim) =========
    CHECK_START_SCRAPE -- Yes --> CLAIM_ITEM[Atomically select and claim next idle item; set status = 'scraping'; active_scrapes++]
    CLAIM_ITEM --> START_SCRAPE[Start scrape worker for claimed item]

    %% If we can't start a new scrape, just wait on events and re-loop
    CHECK_START_SCRAPE -- No --> WAIT_EVENTS[Wait for events: scrape_finished, summary_partial, summary_finished] --> MAIN_LOOP

    %% Scrape worker is async; it only emits an event
    START_SCRAPE --> SCRAPE_DONE_EVENT([Emit scrape_finished event with item_id and raw data])

    %% ========= Event Handling: Scrape Finished =========
    SCRAPE_DONE_EVENT --> HANDLE_SCRAPE_DONE[Handle scrape_finished event in manager; active_scrapes--; status = 'scraped'; save scraped JSON]
    HANDLE_SCRAPE_DONE --> START_SUMMARY[Start AI summarization worker streaming; set status = 'summarizing']
    START_SUMMARY --> SUMMARY_STREAM_EVENT([Emit streaming events: summary_partial / summary_finished])

    %% ========= Event Handling: Summarization Streaming =========
    SUMMARY_STREAM_EVENT --> HANDLE_SUMMARY_EVENTS{Summarization event type}

    HANDLE_SUMMARY_EVENTS -- summary_partial --> APPLY_PARTIAL[Update in-progress summary in JSON; status remains 'summarizing']
    APPLY_PARTIAL --> MAIN_LOOP

    HANDLE_SUMMARY_EVENTS -- summary_finished --> APPLY_FINAL[Write final summary to JSON; set status = 'completed']
    APPLY_FINAL --> MAIN_LOOP
```

 ### Main Loop Behavior (How New Scrapes Keep Starting)
 
 - The `MAIN_LOOP` is a true loop in the workflow manager (e.g., `while process_not_finished:`).
 - On each iteration, it:
   - Checks whether all items are `completed`. If yes, it finishes and starts Phase 0.5.
   - If not finished, it evaluates `CHECK_START_SCRAPE`:
     - If `active_scrapes < max_scrapes` **and** there is at least one `idle` item, it immediately claims a new item and starts a scrape worker.
     - Otherwise, it executes `WAIT_EVENTS`, which:
       - Blocks until there is at least one event **or** a short timeout (e.g., 100–500 ms).
       - Returns control to `MAIN_LOOP`, which again re-checks `CHECK_START_SCRAPE`.
 - This means the manager is **continuously re-evaluating** whether it can start new scrapes—either in response to events (like `scrape_finished`) or periodic wake-ups—so it never gets stuck in a "wait and nothing happens" state as long as there are idle items available.
 
 ### Race-Condition Avoidance (Key Rules)

- **Single owner of state**: All changes to item status, `active_scrapes`, and JSON metadata happen **only in the workflow manager**, never directly inside workers.
- **Atomic claim for scraping**: When starting a scrape, the manager:
  - Selects exactly one `idle` item (e.g., `SELECT ... FOR UPDATE`, or in-memory lock).
  - Immediately marks it `scraping` and increments `active_scrapes` before launching the worker.
  - Persists this change so no second manager instance can claim the same item.
- **Serialized event handling**:
  - `scrape_finished`, `summary_partial`, and `summary_finished` events are processed **one at a time** by the manager (via a single-threaded loop, queue, or equivalent locking).
  - Each event handler re-checks the current item state (idempotent updates) before applying changes.
- **No direct cross-talk between workers**:
  - Scrape workers only emit `scrape_finished` events.
  - Summarization workers only emit streaming / final events.
  - Workers never modify `active_scrapes` or item lifecycle flags.
- **Termination is safe**:
  - The process completes only when **all items are `completed`** and no further events are pending.
  - After that, the manager marks the entire process finished and **starts Phase 0.5**.

### Summary of Required States per Item

- **`idle`**: Not yet scraped, eligible to be claimed if `active_scrapes < 8`.
- **`scraping`**: A scrape worker is running for this item. It cannot be claimed again.
- **`scraped`**: Scrape finished, JSON saved; item is ready for summarization.
- **`summarizing`**: Summarization is active and may be streaming partial results.
- **`completed`**: Final summary written to JSON; item fully done.

This diagram and state model are designed so that once implemented with a single authoritative manager (or a strongly-consistent lock around its responsibilities), **no race conditions** should occur in the scraping → summarization process.


