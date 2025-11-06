## Parallel Scraping Plan (Transcripts + Comments)

### Goals
- Maximize throughput when scraping many video links.
- Collect both transcripts and comments efficiently, reliably, and within rate limits.
- Be resilient to failures, transient network issues, and provider-side throttling.

### Scope
- Sources: YouTube, Bilibili (extendable to more providers).
- Artifacts: transcripts, comments (and basic metadata as needed for routing).

### Constraints & Assumptions
- Network-bound workloads dominate; parsing is light-to-moderate CPU.
- Some providers use APIs with rate limits; others require headless browser automation.
- We must be polite: honor robots, rate limits, and introduce jitter/backoff.
- Idempotent operations are required to safely retry and resume.

### High-Level Architecture
- Job-centric design with bounded parallelism:
  - Input: list of links → enqueue jobs.
  - For each link, create sub-jobs: `fetch_metadata`, `fetch_transcript`, `fetch_comments` (DAG: metadata → others if needed).
  - Workers execute sub-jobs in parallel within configured limits.
- Execution backends (selectable):
  - Local asyncio runner (default, simplest).
  - Queue-based with background workers (e.g., RQ/Celery) for scale.
  - Optional distributed execution later (e.g., Prefect/Arq/Celery on Redis/RabbitMQ).

### Concurrency Model
- Async I/O with per-domain semaphores:
  - `max_concurrency_global` (e.g., 64)
  - `max_concurrency_per_domain` (e.g., youtube.com=16, bilibili.com=16)
  - `max_concurrency_per_artifact` (transcripts=24, comments=24)
- Headless browser pool (when required):
  - Reuse browser contexts; cap at N browsers and M pages per browser.
  - Route tasks needing automation through the pool; others stay HTTP-only.
- CPU work (parsing/cleaning): use a small process/thread pool offloaded from the main event loop when necessary.

### Job Orchestration & Scheduling
- Build a DAG per link:
  - `fetch_metadata` → enables provider-specific routing.
  - `fetch_transcript` and `fetch_comments` can run in parallel once provider is known and pre-reqs fetched.
- Prioritization:
  - Short jobs first (transcripts) to increase perceived progress.
  - Respect user-provided priority or deadlines when present.
- Batching:
  - Batch API calls when allowed (e.g., comment pages in controlled parallelism).

### Rate Limiting & Politeness
- Token bucket per domain/provider with burst and refill rates.
- Exponential backoff with jitter on 429/5xx; circuit breaker after repeated errors.
- Identify and enforce provider-specific ceilings (QPS, concurrent connections).
- Randomize request order to avoid hotspotting specific channels/videos.

### Fault Tolerance & Idempotency
- Idempotent writes keyed by `(provider, video_id, artifact_type, page_token/offset)`.
- Checkpointing for paged comments (resume by next page token/offset).
- Retries with capped attempts; classify fatal vs transient errors.
- De-duplication by content hash and page key.

### Caching & Reuse
- HTTP cache with ETag/If-Modified-Since where supported.
- Local blob store for raw responses (HTML/JSON) to enable reprocessing.
- Normalized artifact store (cleaned transcripts/comments) for downstream reuse.

### Data Model (Conceptual)
- `jobs`: id, link, provider, status, created_at, priority.
- `sub_jobs`: job_id, type (metadata/transcript/comments), status, attempt, checkpoint.
- `artifacts`: job_id, type, content_ref, checksum, version.
- `runs`: run_id, config snapshot, metrics.

### Provider-Specific Notes
- YouTube:
  - Transcripts: prefer official API/library when available; fallback to scrape captions.
  - Comments: fetch pages by `pageToken`; parallelize multiple page tokens with a small window (e.g., 3–5 in flight) to avoid bans; prioritize top-level before replies or interleave controlled.
- Bilibili:
  - Transcripts: if present or generated; else rely on subtitles/CC data if available.
  - Comments (including danmaku): paginate by page or time; shard by time ranges; keep concurrency low-to-moderate; respect anti-bot protections.

### Resource Management
- Connection pools with tuned timeouts (connect/read total).
- Browser pool with cap and LRU for contexts; warm-up on start.
- Optional proxy rotation for high-volume runs; respect provider ToS.

### Observability
- Structured logs: correlation ids per job/sub-job.
- Metrics: QPS, success/error rates, retries, p95 latency, active semaphore counts, cache hit rate.
- Tracing spans per job and external call; flamegraph support for hotspots.
- Simple dashboard or CLI summaries per run.

### Configuration Knobs
- `max_concurrency_global`, `max_concurrency_per_domain`, `max_concurrency_per_artifact`.
- `max_browsers`, `max_pages_per_browser`.
- `request_timeout_s`, `retry_attempts`, `retry_backoff_base`.
- `comments_inflight_window`, `transcripts_priority_boost`.
- `enable_http_cache`, `enable_raw_capture`.

### CLI (Non-Implementing Examples)
- Scrape files from list with tuned concurrency:
  - `research scrape --links links.txt --max-concurrency 64 --domain youtube.com=16 --domain bilibili.com=16 --comments-window 4`
- Resume a failed run by run id:
  - `research scrape --resume run_20251030_123456`

### Testing Strategy
- Unit tests for rate limiter, backoff, and semaphores.
- Integration tests per provider with recorded fixtures and simulated 429/5xx.
- Soak tests with 1k+ links at low QPS to detect leaks and throttling behavior.
- Chaos tests: random failures, timeouts, browser crashes; ensure resumption works.

### Rollout Plan
- Phase 1: Local asyncio with semaphores and per-domain limits; basic caching.
- Phase 2: Introduce browser pool and artifact-level concurrency caps; add observability.
- Phase 3: External queue + workers for distributed runs; dashboarding and autoscaling.

### Security & Compliance
- No scraping behind logins unless explicitly permitted and configured.
- Rotate user-agents responsibly; avoid cloaking.
- Store PII (usernames/ids) per policy with access controls.

### Risks & Mitigations
- Provider bans: conservative concurrency + backoff + jitter + proxy pool.
- API changes: provider adapters with contract tests and version pinning.
- Browser instability: auto-restart crashing contexts; cap memory; watchdog.
- Data duplication: strong idempotency keys and content hashing.

### Acceptance Criteria
- Can process 1k links with both transcripts and comments under configured limits.
- Recoverable mid-run failures with resume producing no duplicates.
- Clear metrics and logs to analyze throughput and errors.
- Configurable knobs allow safe tuning without code changes.

### Revisions Based on Feedback (Confirmed Defaults)

- Only providers: YouTube and Bilibili.
- Default execution model: four parallel production lines running continuously:
  1) Bilibili Transcript, 2) Bilibili Comments, 3) YouTube Transcript, 4) YouTube Comments.
- Dynamic work-stealing: if any production line exhausts its queue (finishes early), it can pick up work from another line's queue while respecting per-domain/per-artifact limits.
- Progress tracking: each video and each artifact page (e.g., comment page token/time-slice) is tracked with durable checkpoints to prevent crashes/dupes and to allow safe resume.

#### Detailed Scheduling Model (Production Lines)
- Work Queues:
  - Maintain four logical queues: `bili_transcripts_q`, `bili_comments_q`, `yt_transcripts_q`, `yt_comments_q`.
  - Each queue feeds a worker group capped by `max_concurrency_per_artifact` and `max_concurrency_per_domain`.
- Work-Stealing:
  - When a queue becomes empty, its idle workers attempt to steal from the other non-empty queues with the least backlog.
  - Stealing respects: per-domain concurrency caps, token buckets, and politeness. Example: Bilibili workers may steal from YouTube queues only if YouTube domain caps are not exceeded.
- Fairness & Backpressure:
  - Prioritize transcript tasks first when queues are balanced to increase early completeness.
  - If comments create sustained pressure, shrink comments concurrency slightly to keep transcripts flowing.
- Failure Isolation:
  - Errors in one line do not halt others. Use per-line circuit breakers; if Bilibili comments line hits repeated 429s, it backs off without impacting transcripts or YouTube.

#### Checkpointing & Idempotency (Progress Safety)
- Transcripts:
  - Idempotent key: `(provider, video_id, artifact=transcript, version)`.
  - On success, mark transcript done and store checksum; on retry, skip if up-to-date.
- Comments:
  - Idempotent key per page/slice: `(provider, video_id, artifact=comments, page_token|time_slice)`.
  - Checkpoint next page token (YouTube) or next time offset (Bilibili) and persist after each successful page to allow exact resume.
- Resume Semantics:
  - On restart, repopulate queues from the checkpoint store. Already completed items are skipped via idempotency keys.

#### Defaults (Concrete Values)
- Global concurrency: `max_concurrency_global = 64`.
- Per domain: `youtube.com = 16`, `bilibili.com = 16` (tunable).
- Per artifact: `transcripts = 24` total across providers, `comments = 24` total across providers.
- Comments inflight window: 3–5 pages per video concurrently (provider-tuned; start with 3).
- Retries: 3 attempts, exponential backoff base 1.5 with jitter, cap at 60s.

#### Test Runner Implications (Planning Only)
- Current script (sequential):
```1:80:tests/test_all_scrapers_and_save.py
"""Discover and run all test_*.py scripts directly under the tests folder."""
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Ensure project root is on path (in case individual tests rely on it)
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_all_scrapers_and_save():
    """Auto-discover test scripts in tests/ and run them sequentially."""
    print("\n" + "=" * 80)
    print("Discovering and Running Scraper Test Scripts in tests/")
    print("=" * 80)

    tests_dir = Path(__file__).parent
    runner_name = Path(__file__).name

    # Only scripts directly under tests folder matching test_*_scraper.py
    scripts = [p for p in tests_dir.glob("test_*_scraper.py")]

    if not scripts:
        print("No test_*_scraper.py scripts found directly under tests/.")
        return []

    # Preferred execution order
    preferred_order = [
        "test_bilibili_scraper.py",
        "test_bilibili_comments_scraper.py",
        "test_youtube_scraper.py",
        "test_youtube_comments_scraper.py",
        "test_reddit_scraper.py",
        "test_article_scraper.py",
    ]

    scripts_by_name = {p.name: p for p in scripts}
    ordered_scripts = [scripts_by_name[name] for name in preferred_order if name in scripts_by_name]
    remaining_scripts = sorted([p for p in scripts if p.name not in preferred_order], key=lambda p: p.name)
    scripts = ordered_scripts + remaining_scripts

    run_results = []
    total = len(scripts)
    for idx, script in enumerate(scripts, 1):
        print("\n" + "-" * 80)
        print(f"[{idx}/{total}] Running {script.name}")
        print("-" * 80)

        start_ts = datetime.now()
        completed = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(tests_dir),
            shell=False,
        )
        end_ts = datetime.now()

        duration_s = (end_ts - start_ts).total_seconds()
        status_text = "OK" if completed.returncode == 0 else f"FAIL ({completed.returncode})"
        print(f"Finished {script.name} -> {status_text} in {duration_s:.1f}s")

        run_results.append({
            "script": script.name,
            "returncode": completed.returncode,
            "duration_seconds": duration_s,
        })

    # Summary
    print("\n" + "=" * 80)
    print("Test Scripts Summary")
    print("=" * 80)
    num_ok = sum(1 for r in run_results if r["returncode"] == 0)
    print(f"Passed: {num_ok}/{total}")
    for r in run_results:
        status = "OK" if r["returncode"] == 0 else f"FAIL ({r['returncode']})"
        print(f"- {r['script']}: {status} in {r['duration_seconds']:.1f}s")

    return run_results

if __name__ == '__main__':
    test_all_scrapers_and_save()
```
- Planned changes (not implementing now):
  - Allow grouping into four logical suites: `bili_transcript`, `bili_comments`, `yt_transcript`, `yt_comments`.
  - Run these four suites in parallel via a small process pool, while tests inside each suite may remain sequential or lightly parallelized.
  - Replace fixed preferred order with dynamic scheduling: if one suite finishes early, optionally borrow tests from another suite’s tail (work-stealing for tests).
  - Persist intermediate artifacts per test to avoid reruns on crash; summarize at the end by scanning outputs.

#### Clarifications in Plain Terms
- Browser Pool (what it means):
  - Some pages require a real browser (e.g., headless Chrome) to load dynamic content. A "browser pool" means we pre-launch a limited number of browsers and reuse them for multiple pages to avoid slow startups and keep memory stable. If your current scrapers are HTTP-only and work fine, you can keep this disabled.
- Proxy Rotation (what it means):
  - Using a set of outbound IPs and cycling them to reduce throttling/bans when volume is high. If you’re scraping at modest scale within limits, you do not need proxies. This remains optional.
- Job/Run/Artifact Schema (simple explanation):
  - "Job" = one video to scrape.
  - "Sub-job" = a piece of that video’s work (transcript, comments page 1, comments page 2, ...).
  - "Run" = one end-to-end execution with a config snapshot (so we can reproduce).
  - "Artifact" = the saved outputs (transcripts, comments) and where they live on disk.
  - You do not have to change your existing data layout to adopt this model; it’s a naming convention to make retries/resume/dedup consistent.

#### Acceptance Criteria (Updated)
- Four production lines run in parallel by default with dynamic work-stealing.
- Checkpoints ensure no duplicate pages and allow resume after crash.
- Sequential test harness can be switched to a four-suite parallel runner without hardcoded order.
- Provider scope limited to YouTube and Bilibili; all knobs are configurable but sensible defaults work out of the box.
