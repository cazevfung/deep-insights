# Path Configuration Migration Guide

## Overview

This migration moves hardcoded file paths to configurable values in `config.yaml`, enabling easier path management and moving batch directories from `tests/results/` to `data/research/batches/`.

**Migration Date:** 2025-01-XX  
**Status:** Planning  
**Impact:** Medium - Affects all file I/O operations for batches and reports

---

## Table of Contents

1. [Objectives](#objectives)
2. [Current State](#current-state)
3. [Target State](#target-state)
4. [Files to Modify](#files-to-modify)
5. [Implementation Steps](#implementation-steps)
6. [Configuration Changes](#configuration-changes)
7. [Dependency Verification](#dependency-verification)
8. [Testing Checklist](#testing-checklist)
9. [Rollback Plan](#rollback-plan)
10. [Post-Migration Tasks](#post-migration-tasks)

---

## Objectives

### Primary Goals

1. **Centralize Path Configuration**
   - Move all hardcoded paths to `config.yaml`
   - Enable easy path adjustments without code changes
   - Support different environments (dev, test, production)

2. **Reorganize Directory Structure**
   - Move batch run directories from `tests/results/run_{batch_id}/` to `data/research/batches/run_{batch_id}/`
   - Move reports from `tests/results/reports/` to `data/research/reports/`
   - Align with existing `data/research/` structure

3. **Maintain Backward Compatibility**
   - Support reading from old locations during transition
   - Preserve existing data access patterns
   - Minimize breaking changes

### Benefits

- **Easier Configuration**: Change paths via config file, no code changes needed
- **Better Organization**: All research data under `data/research/`
- **Environment Flexibility**: Different paths for dev/test/prod
- **Maintainability**: Single source of truth for paths

---

## Current State

### Hardcoded Paths

#### Batch Directories
- **Location**: `tests/results/run_{batch_id}/`
- **Used by**: Scrapers, workflow services, data loader
- **Files**: JSON files for transcripts, comments, metadata

#### Report Directories
- **Primary**: `tests/results/reports/report_{batch_id}_{session_id}.md`
- **Secondary**: `data/research/reports/report_{session_id}.md` (already exists)
- **Used by**: Research agent, reports API, history API

### Current File Locations

```
Project Root/
├── tests/
│   └── results/
│       ├── run_{batch_id}/          # Batch data (TO BE MOVED)
│       └── reports/                  # Reports (TO BE MOVED)
├── data/
│   └── research/
│       ├── batches/                  # NEW: Batch data location
│       ├── reports/                  # EXISTING: Reports location
│       └── sessions/                 # EXISTING: Session files
└── config.yaml                       # TO BE UPDATED
```

### Files with Hardcoded Paths

1. **Batch Directory References** (7 files):
   - `backend/app/services/workflow_service.py` (line 189)
   - `research/data_loader.py` (line 29)
   - `backend/lib/scraping_control_center.py` (line 58)
   - `backend/lib/workflow_direct.py` (line 489)
   - `research/phases/streaming_summarization_manager.py` (line 191)
   - `research/phases/streaming_summarization_manager_v2.py` (line 121)
   - Test files (multiple, may keep hardcoded for isolation)

2. **Report Directory References** (3 files):
   - `research/agent.py` (line 525)
   - `backend/app/routes/reports.py` (line 71)
   - `backend/app/routes/history.py` (line 24, 477)

---

## Target State

### New Directory Structure

```
Project Root/
├── tests/
│   └── results/                      # Only for test isolation
│       └── run_{batch_id}/           # Test-specific batches
├── data/
│   └── research/
│       ├── batches/                  # Production batch data
│       │   └── run_{batch_id}/
│       ├── reports/                  # All research reports
│       │   └── report_{session_id}.md
│       └── sessions/                 # Session files
└── config.yaml                       # Centralized path config
```

### Configuration Structure

```yaml
storage:
  base_dir: 'data/research'
  paths:
    batches_dir: 'data/research/batches'
    reports_dir: 'data/research/reports'
```

### Code Changes

- All path references use `Config.get_batches_dir()` and `Config.get_reports_dir()`
- Backward compatibility checks in read operations
- Consistent path usage across all modules

---

## Files to Modify

### 1. Configuration Files

#### `config.yaml`
**Action**: Add path configuration section

```yaml
storage:
  base_dir: 'data/research'
  format: 'json'
  save_metadata: true
  cache_enabled: true
  cache_dir: 'data/cache'
  # Path configuration
  paths:
    batches_dir: 'data/research/batches'  # Where batch run directories are saved
    reports_dir: 'data/research/reports'   # Where research reports are saved
```

#### `core/config.py`
**Action**: Add helper methods for path access

**New Methods**:
```python
def get_batches_dir(self) -> Path:
    """Get batches directory path."""
    project_root = find_project_root()
    batches_dir = self.get('storage.paths.batches_dir', 'data/research/batches')
    return project_root / batches_dir

def get_reports_dir(self) -> Path:
    """Get reports directory path."""
    project_root = find_project_root()
    reports_dir = self.get('storage.paths.reports_dir', 'data/research/reports')
    return project_root / reports_dir
```

### 2. Core Research Files

#### `research/agent.py`
**Line**: 525  
**Current**: 
```python
reports_dir = Path(__file__).parent.parent / "tests" / "results" / "reports"
```
**Change to**:
```python
from core.config import Config
config = Config()
reports_dir = config.get_reports_dir()
```

#### `research/data_loader.py`
**Line**: 29  
**Current**: 
```python
self.results_base_path = Path(__file__).parent.parent / "tests" / "results"
```
**Change to**:
```python
from core.config import Config
config = Config()
self.results_base_path = config.get_batches_dir()
```

**Also update**: Constructor parameter documentation (line 22)

### 3. Backend Service Files

#### `backend/app/services/workflow_service.py`
**Line**: 189  
**Current**: 
```python
output_dir = Path(__file__).parent.parent.parent.parent / "tests" / "results"
```
**Change to**:
```python
from core.config import Config
config = Config()
output_dir = config.get_batches_dir()
```

**Also check**: Line 1122 (uses `data_loader.results_base_path` - should be fine if data_loader uses config)

#### `backend/lib/scraping_control_center.py`
**Line**: 58  
**Current**: 
```python
output_dir = Path(__file__).parent.parent.parent / "tests" / "results"
```
**Change to**:
```python
from core.config import Config
config = Config()
output_dir = config.get_batches_dir()
```

#### `backend/lib/workflow_direct.py`
**Line**: 489  
**Current**: 
```python
output_dir = Path(__file__).parent.parent.parent / "tests" / "results"
```
**Change to**:
```python
from core.config import Config
config = Config()
output_dir = config.get_batches_dir()
```

### 4. Phase Management Files

#### `research/phases/streaming_summarization_manager.py`
**Line**: 191  
**Current**: 
```python
results_base_path = Path(__file__).parent.parent / "tests" / "results"
```
**Change to**:
```python
from core.config import Config
config = Config()
results_base_path = config.get_batches_dir()
```

#### `research/phases/streaming_summarization_manager_v2.py`
**Line**: 121  
**Current**: 
```python
self.batch_dir = Path(__file__).parent.parent.parent / "tests" / "results" / f"run_{batch_id}"
```
**Change to**:
```python
from core.config import Config
config = Config()
self.batch_dir = config.get_batches_dir() / f"run_{batch_id}"
```

### 5. API Route Files

#### `backend/app/routes/reports.py`
**Line**: 71  
**Current**: 
```python
test_reports_dir = project_root / "tests" / "results" / "reports"
```
**Change to**:
```python
from core.config import Config
config = Config()
# Check configured reports directory first
reports_dir = config.get_reports_dir()
# Keep backward compatibility check for old location
legacy_reports_dir = project_root / "tests" / "results" / "reports"
```

**Update `_find_report_file()` function**:
- Check configured `reports_dir` first
- Fall back to legacy location if not found
- Maintain existing priority logic

#### `backend/app/routes/history.py`
**Line**: 24 (already defined at top)  
**Current**: 
```python
reports_dir = project_root / "data" / "research" / "reports"
```
**Change to**:
```python
from core.config import Config
config = Config()
reports_dir = config.get_reports_dir()
```

**Line**: 477 (uses `reports_dir` variable)  
**Action**: No change needed if variable is updated at top

### 6. Test Files (Optional)

Test files may keep hardcoded paths for test isolation, or use test-specific config:

- `tests/test_*.py` files
- Consider: Create test config override or keep hardcoded for isolation

---

## Implementation Steps

### Phase 1: Configuration Setup

1. **Update `config.yaml`**
   - Add `storage.paths` section
   - Set default values to new locations
   - Document in comments

2. **Extend `core/config.py`**
   - Add `get_batches_dir()` method
   - Add `get_reports_dir()` method
   - Add error handling for missing config
   - Add unit tests

3. **Verify Config Loading**
   - Test config loading in isolation
   - Verify path resolution works correctly
   - Test with relative and absolute paths

### Phase 2: Core Research Module Updates

4. **Update `research/data_loader.py`**
   - Replace hardcoded path with config
   - Update constructor documentation
   - Test data loading from new location

5. **Update `research/agent.py`**
   - Replace hardcoded reports path
   - Test report generation to new location

6. **Update Phase Managers**
   - Update `streaming_summarization_manager.py`
   - Update `streaming_summarization_manager_v2.py`
   - Test summarization with new paths

### Phase 3: Backend Service Updates

7. **Update Workflow Services**
   - Update `workflow_service.py`
   - Update `scraping_control_center.py`
   - Update `workflow_direct.py`
   - Test batch directory creation

8. **Update API Routes**
   - Update `reports.py` with backward compatibility
   - Update `history.py`
   - Test report retrieval from both old and new locations

### Phase 4: Testing & Validation

9. **Create Test Batches**
   - Run scraper tests
   - Verify files saved to new location
   - Verify data loader can read from new location

10. **Test Report Generation**
    - Run full research workflow
    - Verify reports saved to new location
    - Verify reports API can find reports

11. **Test Backward Compatibility**
    - Verify old reports still accessible
    - Test migration of existing data (if needed)

### Phase 5: Data Migration (Optional)

12. **Migrate Existing Data** (if desired)
    - Use provided migration script: `scripts/migrate_paths.py`
    - First run with `--dry-run` to preview changes
    - Then run without flags to execute migration
    - Optionally use `--backup` to create backups of session files

---

## Configuration Changes

### config.yaml Addition

```yaml
storage:
  base_dir: 'data/research'
  format: 'json'
  save_metadata: true
  cache_enabled: true
  cache_dir: 'data/cache'
  
  # Path configuration for batch and report directories
  # These paths are relative to project root
  paths:
    batches_dir: 'data/research/batches'  # Where batch run directories (run_{batch_id}/) are saved
    reports_dir: 'data/research/reports'  # Where research reports (report_{session_id}.md) are saved
```

### core/config.py Addition

```python
def get_batches_dir(self) -> Path:
    """
    Get batches directory path where batch run directories are stored.
    
    Returns:
        Path object pointing to batches directory
    """
    project_root = find_project_root()
    batches_dir = self.get('storage.paths.batches_dir', 'data/research/batches')
    return project_root / batches_dir

def get_reports_dir(self) -> Path:
    """
    Get reports directory path where research reports are stored.
    
    Returns:
        Path object pointing to reports directory
    """
    project_root = find_project_root()
    reports_dir = self.get('storage.paths.reports_dir', 'data/research/reports')
    return project_root / reports_dir
```

---

## Dependency Verification

### Critical Dependencies

#### 1. Data Flow: Scrapers → Data Loader

**Path**: Scrapers save → Data loader reads

**Verification**:
- [ ] All scrapers use same `batches_dir` from config
- [ ] Data loader uses same `batches_dir` from config
- [ ] Batch directory structure unchanged (`run_{batch_id}/`)
- [ ] File naming convention unchanged

**Test**:
```python
# Test that scraper saves and loader can read
batch_id = "test_20250101_120000"
# Scraper saves to: config.get_batches_dir() / f"run_{batch_id}"
# Loader reads from: config.get_batches_dir() / f"run_{batch_id}"
```

#### 2. Report Flow: Agent → Reports API

**Path**: Agent saves → Reports API reads

**Verification**:
- [ ] Agent saves to `reports_dir` from config
- [ ] Reports API checks configured `reports_dir` first
- [ ] Reports API falls back to legacy location
- [ ] Report file naming consistent

**Test**:
```python
# Test that agent saves and API can find
session_id = "20250101_120000"
# Agent saves to: config.get_reports_dir() / f"report_{session_id}.md"
# API finds from: config.get_reports_dir() or legacy location
```

#### 3. Session Metadata

**Path**: Sessions reference report paths

**Verification**:
- [ ] New sessions store correct report paths
- [ ] Old sessions still have valid paths (if not migrated)
- [ ] History API can resolve report paths

**Test**:
- Create new session, verify report_path in metadata
- Load old session, verify backward compatibility

#### 4. Batch Directory Creation

**Path**: Multiple services create batch directories

**Verification**:
- [ ] All services use same `batches_dir`
- [ ] Directory creation is consistent
- [ ] Permissions are correct

**Test**:
- Create batch from workflow service
- Create batch from scraping control center
- Verify both use same base directory

### Dependency Map

```
┌─────────────────┐
│   config.yaml   │
│  (paths config) │
└────────┬────────┘
         │
         ├──► core/config.py (get_batches_dir, get_reports_dir)
         │
         ├──► Scrapers ──────┐
         │                   │
         ├──► Workflow ──────┼──► batches_dir/run_{batch_id}/
         │                   │
         └──► Data Loader ───┘
         
         └──► Research Agent ──► reports_dir/report_{session_id}.md
                                   │
                                   └──► Reports API ──► History API
```

---

## Testing Checklist

### Pre-Migration Testing

- [ ] **Config Loading**
  - [ ] Config loads correctly
  - [ ] Paths resolve to correct locations
  - [ ] Default values work if config missing

- [ ] **Directory Creation**
  - [ ] Batches directory created if missing
  - [ ] Reports directory created if missing
  - [ ] Permissions are correct

### Unit Tests

- [ ] **Config Module**
  - [ ] `get_batches_dir()` returns correct path
  - [ ] `get_reports_dir()` returns correct path
  - [ ] Handles missing config gracefully
  - [ ] Handles relative and absolute paths

- [ ] **Data Loader**
  - [ ] Loads batches from configured directory
  - [ ] Handles missing batch directories
  - [ ] File parsing unchanged

- [ ] **Research Agent**
  - [ ] Saves reports to configured directory
  - [ ] Report content unchanged
  - [ ] File naming correct

### Integration Tests

- [ ] **Full Workflow Test**
  - [ ] Run scraper → saves to new batches_dir
  - [ ] Run research agent → loads from new batches_dir
  - [ ] Generate report → saves to new reports_dir
  - [ ] Reports API → finds report in new reports_dir

- [ ] **Backward Compatibility Test**
  - [ ] Reports API finds reports in old location
  - [ ] Reports API finds reports in new location
  - [ ] Priority: new location > old location

- [ ] **Multiple Batch Test**
  - [ ] Create multiple batches
  - [ ] Verify all saved to same base directory
  - [ ] Verify no conflicts

### Manual Testing

- [ ] **Scraper Test**
  ```bash
  # Run scraper test
  python tests/test_youtube_scraper.py
  # Verify files in: data/research/batches/run_{batch_id}/
  ```

- [ ] **Research Workflow Test**
  ```bash
  # Run full research workflow
  python scripts/run_research.py
  # Verify report in: data/research/reports/report_{session_id}.md
  ```

- [ ] **API Test**
  ```bash
  # Start backend
  # Test reports API endpoint
  curl http://localhost:3001/api/reports/{batch_id}
  # Verify report content returned
  ```

### Regression Tests

- [ ] **Existing Functionality**
  - [ ] All existing tests pass
  - [ ] No breaking changes to APIs
  - [ ] UI still works correctly

- [ ] **Data Integrity**
  - [ ] No data loss during migration
  - [ ] File contents unchanged
  - [ ] Metadata preserved

---

## Rollback Plan

### Quick Rollback (Code Only)

If issues are discovered immediately:

1. **Revert Code Changes**
   ```bash
   git revert <commit-hash>
   # Or restore from backup branch
   ```

2. **Restore config.yaml**
   - Remove `storage.paths` section
   - Or set paths back to old values

3. **Verify System**
   - Test that old paths work
   - Verify no data corruption

### Data Rollback (If Data Migrated)

If data was moved and needs rollback:

1. **Move Data Back**
   ```bash
   # Move batches back
   mv data/research/batches/* tests/results/
   
   # Move reports back (if moved)
   # Note: Reports may have been created in new location only
   ```

2. **Update Session Metadata**
   - Update `report_path` in session files if needed
   - Or regenerate reports

### Partial Rollback

If only some components have issues:

1. **Keep Config, Revert Specific Files**
   - Revert problematic files to hardcoded paths
   - Keep config for other files
   - Document inconsistencies

2. **Gradual Migration**
   - Migrate one module at a time
   - Test after each migration
   - Rollback individual modules if needed

### Rollback Checklist

- [ ] Identify issue scope
- [ ] Determine rollback strategy
- [ ] Backup current state
- [ ] Execute rollback
- [ ] Verify system functionality
- [ ] Document lessons learned

---

## Post-Migration Tasks

### Immediate Tasks

1. **Verify All Systems**
   - [ ] All services using new paths
   - [ ] No hardcoded paths remain (except tests)
   - [ ] All tests passing

2. **Update Documentation**
   - [ ] Update README.md with new paths
   - [ ] Update API documentation
   - [ ] Update developer guides

3. **Monitor Logs**
   - [ ] Check for path-related errors
   - [ ] Monitor file creation
   - [ ] Verify no missing files

### Short-term Tasks (1 week)

4. **Data Migration** (Optional)
   - [ ] Decide if existing data should be moved
   - [ ] Run migration script with `--dry-run` to preview changes
   - [ ] Execute migration: `python scripts/migrate_paths.py [--backup]`
   - [ ] Verify data integrity
   - [ ] Check that all files moved correctly
   - [ ] Verify session JSON files updated correctly

5. **Cleanup**
   - [ ] Remove old test data if desired
   - [ ] Archive old reports if needed
   - [ ] Update .gitignore if needed

6. **Performance Monitoring**
   - [ ] Monitor file I/O performance
   - [ ] Check disk space usage
   - [ ] Verify no performance degradation

### Long-term Tasks (1 month)

7. **Documentation Updates**
   - [ ] Update all docs referencing old paths
   - [ ] Create path configuration guide
   - [ ] Update troubleshooting guides

8. **Code Cleanup**
   - [ ] Remove backward compatibility code (after transition period)
   - [ ] Clean up legacy path references
   - [ ] Refactor if needed

9. **Optimization**
   - [ ] Review path resolution performance
   - [ ] Optimize config loading if needed
   - [ ] Consider caching paths

---

## Risk Assessment

### Low Risk

- **Config Changes**: Adding new config section is low risk
- **Code Changes**: Replacing hardcoded paths with config calls is straightforward
- **Testing**: Can test in isolation before full deployment

### Medium Risk

- **Path Resolution**: Need to ensure paths resolve correctly across different environments
- **Backward Compatibility**: Must maintain compatibility during transition
- **Data Migration**: Moving existing data could cause issues if not careful

### High Risk

- **Breaking Changes**: If paths are wrong, entire system could fail
- **Data Loss**: If migration script has bugs, could lose data
- **Production Impact**: Changes affect all file I/O operations

### Mitigation Strategies

1. **Staged Rollout**: Migrate one module at a time
2. **Comprehensive Testing**: Test all scenarios before production
3. **Backup Strategy**: Backup all data before migration
4. **Rollback Plan**: Have clear rollback procedures
5. **Monitoring**: Monitor closely after deployment

---

## Success Criteria

### Must Have

- [ ] All hardcoded paths replaced with config
- [ ] New batches saved to `data/research/batches/`
- [ ] New reports saved to `data/research/reports/`
- [ ] All existing functionality works
- [ ] All tests pass

### Should Have

- [ ] Backward compatibility maintained
- [ ] Documentation updated
- [ ] No performance degradation
- [ ] Clean code (no hardcoded paths)

### Nice to Have

- [ ] Existing data migrated
- [ ] Performance improvements
- [ ] Additional path configuration options
- [ ] Environment-specific configs

---

## Timeline Estimate

### Phase 1: Configuration Setup (1-2 hours)
- Update config.yaml
- Extend core/config.py
- Write unit tests

### Phase 2: Core Module Updates (2-3 hours)
- Update research modules
- Test data loading
- Test report generation

### Phase 3: Backend Updates (2-3 hours)
- Update workflow services
- Update API routes
- Test batch creation
- Test report retrieval

### Phase 4: Testing (2-4 hours)
- Unit tests
- Integration tests
- Manual testing
- Fix issues

### Phase 5: Data Migration (Optional, 1-2 hours)
- Create migration script
- Execute migration
- Verify data

**Total Estimated Time**: 8-14 hours

---

## Related Documents

- [SERVER_MIGRATION_IMPLEMENTATION_GUIDE.md](./SERVER_MIGRATION_IMPLEMENTATION_GUIDE.md) - Similar migration patterns
- [config.yaml](../../config.yaml) - Current configuration file
- [RESEARCH_FOLDER_STRUCTURE.md](../implementation/RESEARCH_FOLDER_STRUCTURE.md) - Folder structure documentation

---

## Change Log

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-01-XX | 1.0 | Initial migration plan | - |

---

## Migration Script Usage

A migration script is provided at `scripts/migrate_paths.py` to automate the migration of existing files and session records.

### Running the Migration

1. **Preview Changes (Dry Run)**
   ```bash
   python scripts/migrate_paths.py --dry-run
   ```
   This will show what would be migrated without making any changes.

2. **Execute Migration**
   ```bash
   python scripts/migrate_paths.py
   ```
   This will:
   - Move batch directories from `tests/results/run_{batch_id}/` to `data/research/batches/run_{batch_id}/`
   - Move reports from `tests/results/reports/` to `data/research/reports/`
   - Update session JSON files to reference new paths

3. **With Backup**
   ```bash
   python scripts/migrate_paths.py --backup
   ```
   Creates timestamped backup copies of session files before updating them.

### What the Script Does

1. **Batch Migration**
   - Finds all `run_{batch_id}/` directories in `tests/results/`
   - Moves them to `data/research/batches/`
   - Skips if target already exists

2. **Report Migration**
   - Finds all `report_*.md` files in `tests/results/reports/`
   - Moves them to `data/research/reports/`
   - Skips if target already exists

3. **Session Updates**
   - Scans all `session_*.json` files in `data/research/sessions/`
   - Updates `report_path` in phase4 artifacts
   - Updates `additional_report_paths` arrays
   - Preserves all other session data

### Safety Features

- **Dry Run Mode**: Preview changes before executing
- **Backup Option**: Create backups of session files
- **Error Handling**: Continues on errors, logs all issues
- **Skip Existing**: Won't overwrite existing files
- **Detailed Logging**: Shows progress and results

### After Migration

1. Verify files are in new locations
2. Check that session files reference correct paths
3. Test that reports API can find reports
4. Test that data loader can find batches
5. Optionally clean up old empty directories

---

## Questions & Notes

### Open Questions

1. **Test Isolation**: Should test files keep hardcoded paths or use test config?
   - **Decision**: Keep hardcoded for test isolation, document in test files

2. **Data Migration**: Should existing data be moved automatically?
   - **Decision**: Optional, create script but don't auto-execute

3. **Backward Compatibility**: How long to maintain backward compatibility?
   - **Decision**: At least 1 release cycle, then remove legacy checks

### Implementation Notes

- Consider adding path validation in config methods
- Consider adding logging when paths are resolved
- Consider adding path existence checks with auto-creation
- Consider environment-specific configs (dev/test/prod)

---

**End of Migration Guide**

