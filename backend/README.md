# Research Tool Backend API

FastAPI backend for the Research Tool service.

## Architecture

This backend uses a **simplified architecture** that directly leverages the proven, working code from the `tests/` folder. Instead of re-implementing functionality, the backend:

1. **Uses test functions directly** - Imports and calls functions from `tests/test_full_workflow_integration.py`
2. **Adds WebSocket integration** - Thin adapters for real-time client updates
3. **Maintains simplicity** - No duplicate implementations, single source of truth

See `docs/planning/MIGRATION_PLAN_SIMPLIFY_BACKEND.md` for details.

## Getting Started

### Prerequisites

- Python 3.9+
- pip
- All dependencies from project root `requirements.txt`

### Installation

```bash
# Install backend dependencies
pip install -r requirements.txt

# Also ensure project root dependencies are installed
cd ..
pip install -r requirements.txt
```

### Running the Server

```bash
# Development mode
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using Python
python -m app.main

# Or using the run script
python run_server.py
```

The API will be available at `http://localhost:8000`

API documentation will be available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### Links
- `POST /api/links/format` - Format URLs and create batch
- `GET /api/links/batches/{batch_id}/status` - Get batch scraping status

### Workflow
- `POST /api/workflow/start` - Start workflow
- `GET /api/workflow/status/{workflow_id}` - Get workflow status
- `POST /api/workflow/cancel` - Cancel a running workflow

### Research
- `POST /api/research/user_input` - Submit user input during research

### Sessions
- `GET /api/sessions/{session_id}` - Get session data
- `GET /api/sessions/{session_id}/steps` - Get session steps

### WebSocket
- `WS /ws/{batch_id}` - WebSocket connection for real-time updates

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application
│   ├── routes/              # API routes
│   │   ├── links.py
│   │   ├── workflow.py
│   │   ├── research.py
│   │   └── session.py
│   ├── services/            # Business logic (thin adapters)
│   │   ├── link_formatter_service.py  # Uses utils/link_formatter.py
│   │   ├── workflow_service.py        # Uses tests/test_full_workflow_integration.py
│   │   ├── progress_service.py        # Progress tracking
│   │   └── websocket_ui.py            # UI adapter for research agent
│   └── websocket/           # WebSocket handlers
│       └── manager.py
├── lib/                     # Re-exports of working test functions
│   ├── __init__.py
│   └── workflow.py          # Re-exports from tests/
├── requirements.txt
├── run_server.py
└── README.md
```

## How It Works

### Workflow Service

The `WorkflowService` directly uses functions from `tests/test_full_workflow_integration.py`:

```python
from backend.lib import (
    run_all_scrapers,        # From tests/test_full_workflow_integration.py
    verify_scraper_results,  # From tests/test_full_workflow_integration.py
    run_research_agent,      # From tests/test_full_workflow_integration.py
)

# These functions are called with asyncio.to_thread() for async compatibility
# Progress callbacks are provided for real-time WebSocket updates
```

### Progress Updates

Progress updates flow through:
1. **Test functions** call progress callbacks (sync context)
2. **Callbacks queue messages** to a thread-safe queue
3. **Async task processes queue** and broadcasts via WebSocket
4. **Client receives real-time updates** via WebSocket connection

### Key Design Principles

1. **Single Source of Truth** - Test functions are the implementation
2. **Thin Adapters** - Backend services only add WebSocket integration
3. **No Duplication** - No re-implementation of working code
4. **Backwards Compatible** - Test scripts continue to work unchanged

## Development

### Adding New Features

1. **Implement in tests/** - Add functionality to test files first
2. **Test it works** - Verify with test scripts
3. **Add to backend** - Import and use in backend services
4. **Add WebSocket callbacks** - If real-time updates needed

### Testing

```bash
# Run test scripts directly
python tests/test_full_workflow_integration.py

# Run backend tests (if any)
pytest backend/tests/
```

## Migration Notes

This backend was simplified to use test functions directly. See:
- `docs/planning/MIGRATION_PLAN_SIMPLIFY_BACKEND.md` - Migration plan
- `docs/planning/PROGRESS_CALLBACKS_IMPLEMENTATION.md` - Progress callback details
- `docs/planning/MINIMAL_CHANGES_ANALYSIS.md` - Minimal changes analysis


