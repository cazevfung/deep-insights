# Full Workflow Integration Test

This test runs the complete research workflow from start to finish:

1. **Run All Scrapers**: Collects data from YouTube, Bilibili, Reddit, and article sources
2. **Verify Results**: Ensures transcripts and comments are saved in the results folder
3. **Run Research Agent**: Analyzes the gathered content using AI
4. **Generate Report**: Produces a research report saved in the reports folder

## Workflow Overview

```
test_links.json
    ↓
[STEP 1] Run All Scrapers → tests/results/run_{batch_id}/
    ↓
[STEP 2] Run Research Agent → tests/results/reports/report_{batch_id}_{session}.md
    ↓
[STEP 3] Verify Report
```

## Prerequisites

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set API key** (required for research agent):
   ```bash
   # Linux/Mac
   export DASHSCOPE_API_KEY=your_key_here
   
   # Windows
   set DASHSCOPE_API_KEY=your_key_here
   ```
   
   Or add to `config.yaml`:
   ```yaml
   qwen:
     api_key: 'your_key_here'
   ```

3. **Test data**: Ensure `tests/data/test_links.json` exists with valid links

## Usage

### Run the Integration Test

```bash
# From project root
python tests/test_full_workflow_integration.py
```

### What It Does

1. **Scrapers Phase**: 
   - Discovers and runs all `test_*.py` scripts in the tests folder
   - Collects content from YouTube, Bilibili, Reddit, and article sources
   - Saves transcripts and comments to `tests/results/run_{batch_id}/`

2. **Research Agent Phase**:
   - Loads collected data from the batch folder
   - Runs AI-powered analysis to discover research goals
   - Generates a comprehensive research report
   - Saves report to `tests/results/reports/`

3. **Verification Phase**:
   - Checks that all JSON files were generated
   - Verifies research report exists and has valid content
   - Displays summary statistics

## Output

### Scraper Results
- Location: `tests/results/run_{batch_id}/`
- Format: Individual JSON files per item
- Naming: `{batch_id}_{PLATFORM}_{link_id}_{type}.json`
  - Example: `251029_150500_YT_yt_req1_tsct.json` (transcript)
  - Example: `251029_150500_YT_yt_req1_cmts.json` (comments)
  - Example: `251029_150500_BILI_bili_req1_cmt.json` (Bilibili comments)

### Research Report
- Location: `tests/results/reports/`
- Format: Markdown (.md)
- Naming: `report_{batch_id}_{session_id}.md`
  - Example: `report_251029_150500_20251029_181530.md`

## Example Output

```
================================================================================
FULL WORKFLOW INTEGRATION TEST
================================================================================
Started: 2025-10-30 13:00:00

================================================================================
STEP 1: Running All Scrapers
================================================================================
[1/8] Running test_article_scraper.py
Finished test_article_scraper.py -> OK in 12.3s
[2/8] Running test_bilibili_comments.py
Finished test_bilibili_comments.py -> OK in 45.2s
...
Scrapers Summary: 7/8 passed

================================================================================
Verifying Scraper Results
================================================================================
✓ Found 25 JSON files in results directory

================================================================================
STEP 2: Running Research Agent
================================================================================
Initializing Deep Research Agent for batch: 251029_150500
Starting research workflow...
✓ Research workflow completed in 125.3s

================================================================================
STEP 3: Verifying Research Report
================================================================================
✓ All report checks passed

Report Details:
  - Path: tests/results/reports/report_251029_150500_20251030_130125.md
  - Size: 15,847 characters
  - Goal: 游戏提取类型的未来发展趋势...
  - Tokens: 45,230

================================================================================
✓ FULL WORKFLOW INTEGRATION TEST COMPLETED SUCCESSFULLY
================================================================================
Finished: 2025-10-30 13:02:30
```

## Troubleshooting

### Scrapers Fail
- Check internet connection
- Verify URLs in `test_links.json` are valid
- Some scrapers may fail due to rate limiting or network issues
- Test will continue if at least one scraper succeeds

### Research Agent Fails
- Verify API key is set correctly
- Check that scraper results exist in `tests/results/run_{batch_id}/`
- Ensure at least one JSON file was generated
- Check API quota/limits

### Report Verification Fails
- Ensure research agent completed successfully
- Check that report file exists in `tests/results/reports/`
- Verify report contains expected content (title, batch ID, etc.)

## Integration with CI/CD

This test can be used in continuous integration pipelines:

```yaml
# .github/workflows/integration-test.yml
name: Integration Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: |
          export DASHSCOPE_API_KEY=${{ secrets.DASHSCOPE_API_KEY }}
          python tests/test_full_workflow_integration.py
```

## Related Files

- `tests/test_all_scrapers_and_save_json.py` - Scraper runner
- `tests/test_research_agent_full.py` - Research agent test
- `tests/test_links_loader.py` - Test data loader
- `tests/data/test_links.json` - Test data configuration

## Notes

- The test runs all scrapers sequentially, which may take several minutes
- The research agent uses AI, which consumes API credits
- Browser-based scrapers (YouTube, Reddit) will open visible browser windows
- Results are saved to disk for inspection after the test completes







