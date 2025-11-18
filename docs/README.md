# Documentation

This folder is organized for quick navigation. Start here.

---

## 🚨 **NEW: Prompt System Improvement Plan** (2025-11-12)

Comprehensive plan to improve the research tool's prompt system - addressing rigidity, over-complication, and insufficient user intent prioritization.

### Quick Start

1. **[PROMPT_IMPROVEMENTS_SUMMARY.md](./PROMPT_IMPROVEMENTS_SUMMARY.md)** ⭐ **START HERE** (5 min read)
   - Executive summary of the problem and solution
   - Expected impact and quick decision framework

2. **[PROMPT_IMPROVEMENT_PLAN.md](./PROMPT_IMPROVEMENT_PLAN.md)** (25 pages)
   - Complete strategic analysis and root cause analysis
   - Detailed improvement plans for each phase
   - Risk mitigation and success metrics

3. **[PROMPT_IMPROVEMENTS_VISUAL_COMPARISON.md](./PROMPT_IMPROVEMENTS_VISUAL_COMPARISON.md)** (20 pages)
   - Side-by-side before/after comparisons for each phase
   - Concrete examples showing improvements

4. **[PROMPT_IMPROVEMENT_IMPLEMENTATION_GUIDE.md](./PROMPT_IMPROVEMENT_IMPLEMENTATION_GUIDE.md)** (30 pages)
   - Step-by-step implementation with specific file changes
   - Testing protocols and rollback procedures
   - Complete implementation checklist

**Key Findings:** 60% complexity reduction needed. User intent should be first, not buried. Phase 3 needs major simplification (132→50 lines).

---

## 🚀 **NEW: Server Migration Plan** (2025-01-XX)

Comprehensive plan to migrate the Research Tool from a local file-based system to a cloud-hosted, multi-user platform with authentication, authorization, and report sharing capabilities.

### Quick Start

1. **[SERVER_MIGRATION_SUMMARY.md](./SERVER_MIGRATION_SUMMARY.md)** ⭐ **START HERE** (10 min read)
   - Quick overview of migration goals and phases
   - Key components and architecture decisions
   - Migration checklist and timeline

2. **[SERVER_MIGRATION_PLAN.md](./SERVER_MIGRATION_PLAN.md)** (40+ pages)
   - Complete migration strategy and architecture design
   - Database schema and API specifications
   - Authentication, authorization, and report sharing systems
   - Security considerations and deployment strategy
   - Risk assessment and testing strategy

3. **[SERVER_MIGRATION_IMPLEMENTATION_GUIDE.md](./SERVER_MIGRATION_IMPLEMENTATION_GUIDE.md)** (30+ pages)
   - Step-by-step implementation with code examples
   - Database setup and migration scripts
   - Authentication and authorization implementation
   - Report sharing implementation
   - Frontend integration examples
   - Deployment configuration

**Key Features:**
- User authentication with JWT tokens and refresh tokens
- User isolation (users only see their own reports)
- Report sharing with multiple share types (public, unlisted, private, password-protected)
- PostgreSQL database with Redis cache
- Cloud deployment with Docker containers
- Comprehensive security measures

---

## Structure

- planning/ — Research plans, summaries, upgrades
- testing/ — Integration and scraper test docs
  - integration/ — Full workflow and research agent tests
- scrapers/ — Per-scraper guides
  - bilibili/
  - reddit/
- browser/ — Chrome/CDP connection and startup guides
- progress/ — Progress tracking docs
- overview/ — High-level project organization
- analysis/, implementation/, installation/, solutions/, debug/ — Existing detailed docs

### Implementation Plans
- implementation/USER_GUIDANCE_EARLY_COLLECTION_PLAN.md — Move user guidance collection before link input

### Frontend Design
- frontend/USER_GUIDANCE_PAGE_REDESIGN.md — UI redesign for User Guidance Page (question-focused with circular button)

## Index

### Overview
- overview/PROJECT_ORGANIZATION.md

### Planning
- planning/DEEP_RESEARCH_PLAN.md
- planning/DEEP_RESEARCH_PLAN_SUMMARY.md
- planning/DEEP_RESEARCH_PLAN_ENHANCED.md
- planning/REFINED_PLAN_SUMMARY.md
- planning/TRANSCRIPTION_UPGRADE_SUMMARY.md

### Testing
- testing/integration/INTEGRATION_TEST_CREATED.md
- testing/integration/INTEGRATION_TEST_SUMMARY.md
- testing/integration/TEST_RESEARCH_AGENT_README.md
- testing/SCRAPER_TEST_SUMMARY.md
- testing/RUN_REDDIT_TEST.md
- testing/QUICK_TEST.md

### Scrapers
- scrapers/bilibili/BILIBILI_COMMENTS_PLANNING_SUMMARY.md
- scrapers/bilibili/BILIBILI_COMMENTS_QUICK_REFERENCE.md
- scrapers/reddit/REDDIT_SCRAPER_INSTRUCTIONS.md
- scrapers/reddit/REDDIT_SCRAPER_IMPROVEMENTS.md
- scrapers/reddit/START_CHROME_FOR_REDDIT.md

### Browser
- browser/HOW_TO_START_CHROME_WITH_DEBUGGING.md
- browser/AUTO_CHROME_STARTUP.md
- browser/BROWSER_CONNECTION_SUMMARY.md
- browser/CHROME_CONNECTION_MODE.md

### Progress
- progress/PROGRESS_TRACKING.md
- progress/PROGRESS_TRACKING_IMPLEMENTATION.md








