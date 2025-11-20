# Documentation

Unified directory structure organized by document type. Start here for the latest highlights and navigation help.

---

## ✨ AI Content Editor Feature (2025-11-19)

Interactive content editing feature that allows users to highlight and edit any phase content (Phase 1-4) through AI-powered conversations using Qwen-Plus.

### Quick Start

1. **[AI_CONTENT_EDITOR_EXECUTION_PLAN.md](./plans/AI_CONTENT_EDITOR_EXECUTION_PLAN.md)** *Original Plan*  
   Complete implementation plan with architecture, API specs, and rollout strategy.

2. **[EDITOR_SELECTION_MAPPING_FIX_PLAN.md](./plans/EDITOR_SELECTION_MAPPING_FIX_PLAN.md)** *🔴 CRITICAL FIX*  
   Fix plan for selection mapping issues. **Current implementation has data corruption risks for Phase 1/2.**

**Key capabilities:** Text selection → AI chat → Apply changes → Real-time updates. Works across all research phases with context-aware editing.

**⚠️ Status**: Initial implementation complete, but critical fixes needed for Phase 1/2 editing (see fix plan).

---

## 🚨 Prompt System Improvement Plan (2025-11-12)

Comprehensive plan to improve the research tool's prompt system-addressing rigidity, over-complication, and insufficient user intent prioritization.

### Quick Start

1. **[PROMPT_IMPROVEMENTS_SUMMARY.md](./reference/PROMPT_IMPROVEMENTS_SUMMARY.md)** *START HERE* (5 min read)  
   Executive summary, impact, and decision framework.
2. **[PROMPT_IMPROVEMENT_PLAN.md](./plans/PROMPT_IMPROVEMENT_PLAN.md)** (25 pages)  
   Strategy, root causes, and detailed improvements.
3. **[PROMPT_IMPROVEMENTS_VISUAL_COMPARISON.md](./reference/PROMPT_IMPROVEMENTS_VISUAL_COMPARISON.md)** (20 pages)  
   Before/after walkthroughs with concrete examples.
4. **[PROMPT_IMPROVEMENT_IMPLEMENTATION_GUIDE.md](./guides/prompts/PROMPT_IMPROVEMENT_IMPLEMENTATION_GUIDE.md)** (30 pages)  
   Step-by-step rollout, testing, and rollback guidance.

**Key findings:** 60% complexity reduction required. Lead with user intent. Phase 3 must shrink from 132->50 lines.

---

## 🚀 Server Migration Program (2025-01-XX)

End-to-end migration plan for moving the Research Tool into a multi-user, cloud-hosted environment.

### Quick Start

1. **[SERVER_MIGRATION_SUMMARY.md](./reference/SERVER_MIGRATION_SUMMARY.md)** *START HERE* (10 min read)  
   Goals, phases, and migration checklist.
2. **[SERVER_MIGRATION_PLAN.md](./plans/SERVER_MIGRATION_PLAN.md)** (40+ pages)  
   Architecture, data model, authN/Z, rollout risks.
3. **[SERVER_MIGRATION_IMPLEMENTATION_GUIDE.md](./guides/migrations/SERVER_MIGRATION_IMPLEMENTATION_GUIDE.md)** (30+ pages)  
   Execution playbook, database steps, frontend integration, deployment.

**Key capabilities:** JWT auth, per-user isolation, configurable sharing modes, PostgreSQL + Redis, Dockerized deployment, layered security controls.

---

## Structure Overview

- `overview/` - project-wide orientation docs.
- `plans/` - strategic and tactical plans (formerly `planning/` plus standalone plan docs).
- `guides/` - implementation, setup, frontend, browser, and solution guides.  
  - Subfolders: `implementation/`, `installation/`, `frontend/`, `browser/`, `solutions/`, plus topical pods (`setup/`, `prompts/`, `migrations/`, `summarization/`, `research/`).
- `investigations/` - investigations, analyses, feasibility studies, and debugging case files.
- `fixes/` - documented bug fixes and patch notes.
- `workflows/` - operational runbooks, progress reporting, and testing playbooks.
- `prompts/` - prompt libraries and prompt-engineering specs.
- `scrapers/` - scraper-specific instructions (bilibili, reddit, etc.).
- `reference/` - summaries, comparisons, scenario catalogs, completion reports.

---

## Quick Index

### Overview
- `overview/PROJECT_ORGANIZATION.md`

### Plans
- `plans/EDITOR_SELECTION_MAPPING_FIX_PLAN.md` - **NEW** - Fix plan for editor selection mapping issues
- `plans/AI_CONTENT_EDITOR_EXECUTION_PLAN.md` - AI-powered content editor for interactive phase editing
- `plans/DEEP_RESEARCH_PLAN.md`
- `plans/DEEP_RESEARCH_PLAN_SUMMARY.md`
- `plans/RIGHT_COLUMN_CHAT_EXECUTION_PLAN.md`
- `plans/SERVER_MIGRATION_PLAN.md`
- `plans/SUMMARIZATION_PROGRESS_IMPROVEMENT_PLAN.md`
- `plans/WRITING_STYLE_SELECTION_PLAN.md`

### Guides
- `guides/setup/OSS_MANUAL_SETUP_GUIDE.md`
- `guides/setup/OSS_SETUP_FOR_PUBLIC_REPORTS.md`
- `guides/migrations/SERVER_MIGRATION_IMPLEMENTATION_GUIDE.md`
- `guides/migrations/SUMMARIZATION_MANAGER_V2_MIGRATION.md`
- `guides/migrations/PATH_CONFIGURATION_MIGRATION.md` - Path configuration and directory reorganization
- `guides/summarization/SUMMARIZATION_V2_QUICKSTART.md`
- `guides/summarization/SCRAPE_SUMMARIZATION_WORKFLOW_V3.md`
- `guides/prompts/PROMPT_IMPROVEMENT_IMPLEMENTATION_GUIDE.md`
- `guides/research/RESEARCH_ROLE_IMPLEMENTATION.md`

### Investigations
- `investigations/EDITOR_SELECTION_TO_JSON_MAPPING_DETAILED.md` - **NEW** - Critical analysis of AI editor selection mapping issues
- `investigations/EDITOR_SELECTION_MAPPING_ISSUES.md` - Initial editor selection mapping analysis
- `investigations/EDITOR_PHASE3_RERUN_LOGIC_ANALYSIS.md` - Phase 3 rerun trigger logic analysis
- `investigations/RACE_CONDITION_INVESTIGATION.md`
- `investigations/DEBUG_USER_INPUT_ISSUE.md`
- `investigations/V2_DEBUG_SOURCE_TYPES.md`
- `investigations/analysis/*`, `investigations/feasibility/*`, `investigations/debug/*`

### Fixes
- `fixes/CONVERSATION_MODE_BUG_FIX.md`
- `fixes/RACE_CONDITION_FIXES_IMPLEMENTED.md`
- `fixes/V2_CRITICAL_FIX_DATA_MERGER.md`
- `fixes/LOCK_CONTENTION_FIX.md`
- `fixes/research_agent_running_status_fix.md`

### Workflows
- `workflows/progress/PROGRESS_TRACKING.md`
- `workflows/testing/QUICK_TEST.md`
- `workflows/testing/RUN_REDDIT_TEST.md`
- `workflows/testing/integration/TEST_RESEARCH_AGENT_README.md`

### Reference
- `reference/PROMPT_IMPROVEMENTS_SUMMARY.md`
- `reference/SERVER_MIGRATION_SUMMARY.md`
- `reference/SUMMARIZATION_V1_VS_V2_COMPARISON.md`
- `reference/V2_INTEGRATION_COMPLETE.md`
- `reference/USER_INPUT_SCENARIOS.md`

### Prompts & Scrapers
- `prompts/` - prompt instruction sets for every phase.
- `scrapers/bilibili/*`, `scrapers/reddit/*` - scraper-specific instructions and upgrades.

Use this README as the jumping-off point. If a document spans multiple categories, check its front-matter tags or the `reference/` summaries for related links.
