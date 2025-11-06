# Deep Research Agent Full Workflow Test

## Overview

This test (`test_research_agent_full.py`) provides a complete end-to-end test of the Deep Research Agent workflow using real scraped data.

## Test Structure

### Test Files Created

1. **`tests/test_research_agent_full.py`** - Main test file with three test cases:
   - `test_research_agent_full_workflow()` - Complete workflow with auto-selected goal
   - `test_research_agent_with_specific_goal()` - Test with specific goal ID selection
   - `test_research_agent_with_custom_topic()` - Test with custom user topic

2. **`research/ui/mock_interface.py`** - Mock UI interface for non-interactive testing

3. **`tests/results/reports/`** - Output directory for generated reports

## Modifications Made

### 1. Enhanced `DeepResearchAgent` (`research/agent.py`)
- Added optional `ui` parameter to accept custom UI interface
- Added `additional_output_dirs` parameter to save reports to multiple locations
- Reports are now saved to both:
  - Default: `data/research/reports/`
  - Additional: `tests/results/reports/`

### 2. Created `MockConsoleInterface` (`research/ui/mock_interface.py`)
- Non-interactive interface for automated testing
- Auto-selects goals and confirms plans
- Supports verbose logging for debugging

## Running the Test

### Prerequisites

1. **API Key**: Set `DASHSCOPE_API_KEY` environment variable
   ```bash
   # Linux/Mac
   export DASHSCOPE_API_KEY=your_key_here
   
   # Windows (PowerShell)
   $env:DASHSCOPE_API_KEY="your_key_here"
   
   # Windows (CMD)
   set DASHSCOPE_API_KEY=your_key_here
   ```

2. **Test Data**: Ensure `tests/results/run_251029_150500/` exists with JSON files

### Execution

```bash
# Option 1: Run with pytest
pytest tests/test_research_agent_full.py -v -s

# Option 2: Run directly
python tests/test_research_agent_full.py
```

## What the Test Does

1. **Phase 0 (Prepare)**
   - Loads all JSON files from `run_251029_150500/`
   - Creates abstracts for each content item
   - Assesses data quality

2. **Phase 1 (Discover)**
   - Generates 3 research goals based on the loaded data
   - Auto-selects first goal (or specified goal ID)

3. **Phase 2 (Plan)**
   - Creates a detailed research plan with steps
   - Auto-confirms plan execution

4. **Phase 3 (Execute)**
   - Executes each step of the plan
   - Extracts findings and insights from data
   - Updates scratchpad with results

5. **Phase 4 (Synthesize)**
   - Generates final research article/report
   - Saves to both default and test output locations

## Expected Output

### Report Files

1. **Default Location**: `data/research/reports/report_{session_id}.md`
2. **Test Location**: `tests/results/reports/report_{batch_id}_{session_id}.md`

### Report Content

- Research goal text
- Generation timestamp
- Batch ID
- Full markdown article with:
  - Introduction
  - Analysis sections
  - Findings
  - Conclusions
  - Sources/citations

## Test Assertions

The test verifies:
- ✅ All phases complete successfully
- ✅ Report file is created
- ✅ Report is saved to `tests/results/reports/`
- ✅ Report contains expected sections
- ✅ Report has substantial content (>500 chars)
- ✅ Selected goal is included in report
- ✅ Batch ID is included in report

## Customization

### Specify Goal ID

The test can be modified to select a specific goal:

```python
mock_ui = MockConsoleInterface(
    auto_select_goal_id="2",  # Select second goal
    auto_confirm_plan=True
)
```

### Custom User Topic

Provide a custom topic to guide goal generation:

```python
result = agent.run_research(
    batch_id=TEST_BATCH_ID,
    user_topic="游戏提取类型的未来发展趋势"
)
```

## Troubleshooting

### Test Skipped - No API Key
```
DASHSCOPE_API_KEY not set. Skipping live test.
```
**Solution**: Set the environment variable as shown above.

### Test Skipped - No Test Data
```
Test data directory not found: tests/results/run_251029_150500
```
**Solution**: Ensure the batch directory exists with JSON files.

### Test Failed - API Error
Check API key validity and network connectivity. Review logs for specific error messages.

## Next Steps

- Review generated reports in `tests/results/reports/`
- Compare reports across different goal selections
- Use as a baseline for future research agent improvements



