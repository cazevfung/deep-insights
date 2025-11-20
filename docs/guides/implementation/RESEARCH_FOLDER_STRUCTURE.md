# Deep Research Agent - Folder Structure

## Proposed Structure

Yes, we should create a dedicated `research/` folder to organize all deep research agent scripts and modules.

## Directory Layout

```
research_tool/
├── research/                        # Main research agent module
│   ├── __init__.py                 # Package initialization, exports main classes
│   │
│   ├── agent.py                    # Main DeepResearchAgent orchestrator class
│   │                               # Coordinates all phases and manages workflow
│   │
│   ├── client.py                   # QwenStreamingClient - API integration
│   │                               # Handles streaming API calls to Qwen3-max
│   │
│   ├── data_loader.py              # ResearchDataLoader - Data preparation
│   │                               # Loads and normalizes scraped batch data
│   │
│   ├── progress_tracker.py        # ProgressTracker - Execution tracking
│   │                               # Tracks step completion, displays progress
│   │
│   ├── session.py                  # ResearchSession - Session management
│   │                               # Manages scratchpad, saves/loads sessions
│   │
│   ├── config.py                   # ResearchConfig - Configuration
│   │                               # Research-specific settings
│   │
│   ├── phases/                     # Phase implementations
│   │   ├── __init__.py
│   │   ├── base_phase.py           # Abstract base class for all phases
│   │   ├── phase0_prepare.py       # Phase 0: Data loading & preparation
│   │   ├── phase1_discover.py      # Phase 1: Goal generation
│   │   ├── phase2_plan.py          # Phase 2: Plan creation
│   │   ├── phase3_execute.py       # Phase 3: Execution loop
│   │   └── phase4_synthesize.py   # Phase 4: Report generation
│   │
│   └── ui/                         # User interface components
│       ├── __init__.py
│       ├── console_interface.py    # Console-based UI with streaming display
│       ├── formatters.py           # Output formatting (progress bars, etc.)
│       └── prompts.py              # User interaction prompts
│
├── tests/
│   └── research/                   # Tests for research agent
│       ├── __init__.py
│       ├── test_client.py          # Test QwenStreamingClient
│       ├── test_data_loader.py     # Test ResearchDataLoader
│       ├── test_phases.py          # Test phase implementations
│       ├── test_session.py          # Test session management
│       └── test_integration.py     # End-to-end integration tests
│
├── scripts/
│   └── run_research.py             # CLI entry point for research agent
│                                   # Usage: python scripts/run_research.py <batch_id>
│
└── data/
    └── research/                   # Research-specific data storage
        ├── sessions/               # Saved research sessions
        └── reports/                # Generated reports
```

## File Responsibilities

### Core Module Files (`research/`)

#### `research/__init__.py`
- Exports main classes: `DeepResearchAgent`, `QwenStreamingClient`, etc.
- Makes imports cleaner: `from research import DeepResearchAgent`

#### `research/agent.py`
- `DeepResearchAgent` class - Main orchestrator
- Manages the 4-phase workflow
- Coordinates between phases
- Handles error recovery

#### `research/client.py`
- `QwenStreamingClient` class
- Handles API authentication
- Manages streaming requests
- Parses JSON from streams
- Tracks token usage

#### `research/data_loader.py`
- `ResearchDataLoader` class
- Loads batch data from `tests/results/run_{batch_id}/`
- Normalizes different data formats (YouTube, Bilibili, Reddit)
- Creates data abstracts
- Chunks data based on strategies

#### `research/progress_tracker.py`
- `ProgressTracker` class
- Tracks step completion
- Calculates progress percentage
- Updates UI callbacks

#### `research/session.py`
- `ResearchSession` class
- Manages scratchpad dictionary
- Saves/loads research sessions
- Persists to JSON files

#### `research/config.py`
- `ResearchConfig` class
- Research-specific settings
- Chunk sizes, sample sizes, etc.
- Loads from `config.yaml`

### Phase Files (`research/phases/`)

#### `research/phases/base_phase.py`
- Abstract base class for all phases
- Common functionality: logging, error handling
- Standard interface for phase execution

#### `research/phases/phase0_prepare.py`
- `Phase0Prepare` class
- Loads and prepares data
- Creates abstracts

#### `research/phases/phase1_discover.py`
- `Phase1Discover` class
- Generates research goals
- Uses streaming API

#### `research/phases/phase2_plan.py`
- `Phase2Plan` class
- Creates detailed research plan
- Uses streaming API

#### `research/phases/phase3_execute.py`
- `Phase3Execute` class
- Executes plan steps
- Updates scratchpad
- Uses streaming API per step

#### `research/phases/phase4_synthesize.py`
- `Phase4Synthesize` class
- Generates final report
- Uses streaming API

### UI Files (`research/ui/`)

#### `research/ui/console_interface.py`
- `ConsoleInterface` class
- Handles user input/output
- Displays streaming text
- Shows progress bars
- Interactive prompts

#### `research/ui/formatters.py`
- Progress bar formatting
- Text formatting utilities
- Markdown helpers

### Test Files (`tests/research/`)

All test files follow standard pytest patterns.

## Example Usage

```python
# From project root or scripts/
from research import DeepResearchAgent
from research.ui.console_interface import ConsoleInterface

# Initialize
agent = DeepResearchAgent()
ui = ConsoleInterface()

# Run research
agent.run_research(
    batch_id="251029_150500",
    ui_callback=ui.display_stream
)
```

Or via CLI:
```bash
python scripts/run_research.py 251029_150500
```

## Benefits of This Structure

1. **Clear Separation**: Research agent is isolated from scrapers
2. **Modularity**: Each phase is a separate module
3. **Testability**: Easy to test individual components
4. **Maintainability**: Easy to find and update code
5. **Scalability**: Easy to add new phases or features
6. **Consistency**: Matches existing project structure (`scrapers/`, `core/`)

## Integration with Existing Code

The research agent will:
- **Use**: Existing `core/config.py` for base config
- **Read**: Scraped data from `tests/results/run_{batch_id}/`
- **Output**: Reports to `data/research/reports/`
- **Log**: To existing logging system

## Next Steps

1. Create `research/` folder structure
2. Create `__init__.py` files
3. Implement `client.py` first (QwenStreamingClient)
4. Implement `data_loader.py` next
5. Implement phase classes one by one
6. Create main `agent.py` orchestrator
7. Add tests incrementally

