# Project Organization

This document describes the project structure after reorganization.

## Directory Structure

```
research-tool/
├── README.md                    # Main project documentation
├── config.yaml                  # Configuration file
├── requirements.txt             # Python dependencies
│
├── core/                        # Core functionality
│   ├── __init__.py
│   └── config.py                # Configuration management
│
├── scrapers/                    # Scraper implementations
│   ├── __init__.py
│   ├── base_scraper.py          # Base scraper class
│   ├── youtube_scraper.py       # YouTube scraper
│   ├── bilibili_scraper.py      # Bilibili scraper
│   ├── reddit_scraper.py        # Reddit scraper
│   └── article_scraper.py       # Article scraper
│
├── tests/                       # Test files
│   ├── __init__.py
│   ├── test_all_scrapers.py     # Test all scrapers
│   ├── test_youtube_scraper.py  # YouTube tests
│   ├── test_bilibili_snapany.py # Bilibili snapany tests
│   ├── test_bilibili_simple.py  # Bilibili simple tests
│   ├── test_reddit_scraper.py   # Reddit tests
│   ├── test_article_scraper.py  # Article tests
│   └── test_snapany_download.py # Snapany download tests
│
├── utils/                       # Utility scripts
│   └── convert_mp4_to_mp3.py    # MP4 to audio converter
│
├── scripts/                      # Batch and shell scripts
│   ├── run_test.bat             # Run tests
│   ├── run_test_with_python313.bat  # Run tests with Python 3.13
│   └── debug-install-ffmpeg.ps1 # FFmpeg installation helper
│
├── docs/                        # Documentation
│   ├── QUICK_TEST.md            # Quick testing guide
│   │
│   ├── implementation/          # Implementation documentation
│   │   ├── BILIBILI_SNAPANY_IMPLEMENTATION.md
│   │   ├── IMPLEMENTATION_SUMMARY.md
│   │   ├── REFINED_PLAN_SUMMARY.md
│   │   └── RESEARCH_TOOL_SCRAPER_PLAN.md
│   │
│   ├── solutions/               # Solution documentation
│   │   ├── AUDIO_CONVERSION_SOLUTION.md
│   │   ├── CONVERSION_PLAN.md
│   │   ├── MP4_TO_MP3_CONVERSION_PLAN.md
│   │   └── PATH_EXPLANATION.md
│   │
│   ├── installation/            # Installation guides
│   │   ├── INSTALL_MOVIEPY.md
│   │   ├── INSTALL_PACKAGES.md
│   │   └── VERIFY_DOWNLOAD.md
│   │
│   └── debug/                   # Debug notes
│       ├── BILIBILI_FFMPEG_ISSUE.md
│       ├── CODE_IMPROVEMENTS.md
│       └── QUICK_FIX_FFMPEG.md
│
├── data/                        # Data storage
│   ├── cache/                   # Cache files
│   └── research/                # Research outputs
│
├── downloads/                   # Downloaded media files
│   └── [video and audio files]
│
├── storage/                     # Content storage (empty)
│
└── web/                        # Web interface
    ├── static/                 # Static assets
    │   ├── css/
    │   └── js/
    └── templates/              # HTML templates
```

## What Changed

### Documentation Organization
- All markdown documentation files moved to `docs/` with subdirectories:
  - `docs/implementation/` - Implementation plans and summaries
  - `docs/solutions/` - Technical solutions and conversion plans
  - `docs/installation/` - Installation and setup guides
  - `docs/debug/` - Debug notes and troubleshooting

### Test Files
- Test files moved from root to `tests/` directory
- Updated batch files in `scripts/` to reference tests in `tests/`

### Utility Files
- `convert_mp4_to_mp3.py` moved to `utils/` directory
- Updated `bilibili_scraper.py` to reference the new location

### Scripts
- Batch files moved to `scripts/` directory
- Debug PowerShell script renamed to `debug-install-ffmpeg.ps1`

### Clean Root Directory
- Root now only contains essential files:
  - `README.md`
  - `config.yaml`
  - `requirements.txt`

## Updated References

The following files were updated to reflect new paths:
- `scrapers/bilibili_scraper.py` - Updated path to `convert_mp4_to_mp3.py`
- `scripts/run_test.bat` - Updated path to test files
- `scripts/run_test_with_python313.bat` - Updated path to test files
- `README.md` - Updated project structure section

## Benefits

1. **Cleaner root directory** - Only essential files at the top level
2. **Better organization** - Related files grouped together
3. **Easier navigation** - Clear separation of concerns
4. **Professional structure** - Following Python project conventions







