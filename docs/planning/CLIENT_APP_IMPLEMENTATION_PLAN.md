# Client App Implementation Plan

## Overview

This document outlines the comprehensive plan for building a client application that runs the entire research tool service. The app will provide a modern, Cursor-inspired UI with real-time progress tracking throughout all phases of the research workflow, using the provided Design System for color palette and typography.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Technology Stack](#technology-stack)
3. [Design System Integration](#design-system-integration)
4. [Application Structure](#application-structure)
5. [Workflow Integration](#workflow-integration)
6. [UI Components & Views](#ui-components--views)
7. [State Management](#state-management)
8. [Real-Time Communication](#real-time-communication)
9. [Implementation Phases](#implementation-phases)
10. [Technical Details](#technical-details)

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Client Application                    │
│  ┌───────────────────────────────────────────────────┐  │
│  │         Frontend (React/Vue + WebSocket)         │  │
│  │  - Link Input & Formatting UI                   │  │
│  │  - Progress Tracking (Phase 0-4)                 │  │
│  │  - Interactive Research Agent UI                 │  │
│  │  - Session Data Visualization                    │  │
│  │  - Final Report Display                          │  │
│  └───────────────────────────────────────────────────┘  │
│                        ↕ WebSocket/HTTP                  │
│  ┌───────────────────────────────────────────────────┐  │
│  │         Backend API Server (FastAPI)             │  │
│  │  - Link Formatting Service                       │  │
│  │  - Batch Management                              │  │
│  │  - Workflow Orchestration                        │  │
│  │  - Research Agent Integration                    │  │
│  │  - Progress Broadcasting                         │  │
│  └───────────────────────────────────────────────────┘  │
│                        ↕                                 │
│  ┌───────────────────────────────────────────────────┐  │
│  │         Existing Research Tool Services          │  │
│  │  - link_formatter.py                             │  │
│  │  - test_full_workflow_integration.py             │  │
│  │  - DeepResearchAgent                              │  │
│  │  - Session JSON Management                        │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Cursor-Inspired UX**: Clean, minimal interface with focus on content and workflow
2. **Real-Time Feedback**: WebSocket-based progress updates throughout all phases
3. **Phase-Aware UI**: Different UI layouts optimized for each workflow phase
4. **Responsive Design**: Support for different screen sizes while maintaining desktop-first approach
5. **Design System Compliance**: Strict adherence to provided color palette and typography

---

## Technology Stack

### Frontend

**Primary Framework:**
- **React 18+** with TypeScript
  - Modern, component-based architecture
  - Excellent ecosystem for real-time updates
  - Type safety for complex state management
  - Strong community support

**Alternative Consideration:**
- **Vue 3** with Composition API (if team preference)
  - Simpler learning curve
  - Good performance
  - Excellent TypeScript support

**State Management:**
- **Zustand** or **Redux Toolkit**
  - Lightweight state management
  - Excellent for real-time updates
  - Simple API for complex workflows

**Real-Time Communication:**
- **WebSocket** (via `socket.io-client` or native WebSocket)
  - Bidirectional communication
  - Real-time progress updates
  - Event-driven architecture

**UI Framework:**
- **Tailwind CSS** (custom configuration)
  - Utility-first approach
  - Easy customization to match Design System
  - Responsive design utilities
  - Custom color palette from Design System

**Additional Libraries:**
- **React Router** - Navigation between phases/pages
- **React Markdown** - Render final report markdown
- **React JSON Viewer** - Beautiful JSON data visualization
- **Framer Motion** - Smooth animations and transitions
- **Axios** - HTTP requests for API calls
- **date-fns** - Date formatting and manipulation

### Backend

**API Framework:**
- **FastAPI**
  - Modern Python async framework
  - Built-in WebSocket support
  - Automatic API documentation
  - Type hints and validation
  - Excellent performance

**WebSocket Management:**
- **Python-SocketIO** or native FastAPI WebSocket
  - Real-time bidirectional communication
  - Room/namespace support for multiple sessions
  - Event-driven architecture

**Integration Layer:**
- **Existing Services Integration**
  - Wrap `link_formatter.py` logic
  - Integrate `test_full_workflow_integration.py` workflow
  - Connect to `DeepResearchAgent` with progress callbacks
  - Read/write session JSON files

**Background Tasks:**
- **Celery** (optional, for long-running tasks)
  - Async task processing
  - Progress tracking
  - Task queuing
- **Alternative**: FastAPI BackgroundTasks (simpler, for single instance)

### Development Tools

- **Vite** - Fast build tool and dev server
- **TypeScript** - Type safety
- **ESLint + Prettier** - Code quality
- **Vitest** - Unit testing
- **Playwright** - E2E testing (optional)

---

## Design System Integration

### Color Palette Application

#### Main Theme Colors
- **Primary Dark Blue** (`#002A54`): 
  - Primary buttons, active states, main navigation
  - Headers and important UI elements
  
- **Secondary Dark Red** (`#B02A2A`): 
  - Error states, warnings, critical actions
  - Accent elements requiring attention
  
- **Neutrals** (`#5D87A1`): 
  - Secondary text, borders, dividers
  - Muted UI elements
  
- **Background Colors**:
  - `#F8F7F9` (Light BG): Main application background
  - `#E7E7E8` (Grey BG): Card backgrounds, panels
  - `#FFFFFF` (White): Content areas, modals

#### Primary Color Shades (Blue)
- **600** (`#000F1F`): Dark mode text, deepest shadows
- **500** (`#002A54`): Primary actions, brand color
- **400** (`#005CB8`): Hover states, links
- **300** (`#52A8FF`): Active/focus states
- **200** (`#B8DBFF`): Light backgrounds, subtle highlights
- **100** (`#EBF5FF`): Very light backgrounds, disabled states

#### Secondary Color Shades (Red/Pink)
- **600** (`#882137`): Error borders, critical alerts
- **500** (`#AF2A47`): Error text, delete actions
- **400** (`#DA6780`): Warning states
- **300** (`#E490A2`): Hover states on error elements
- **200** (`#F5D6DD`): Light error backgrounds
- **100** (`#FCEEF1`): Very light error backgrounds

#### Neutral Colors
- **Black** (`#031C34`): Primary text color
- **500** (`#5D87A1`): Secondary text, icons
- **400** (`#9EB7C7`): Tertiary text, placeholders
- **300** (`#DFE7EC`): Borders, dividers
- **Grey BG** (`#E7E7E8`): Panel backgrounds
- **Light BG** (`#F8F7F9`): Main background
- **White** (`#FFFFFF`): Content areas

#### Supportive Colors
- Use sparingly for:
  - Status indicators (Green: `#2FB66A` for success)
  - Info states (Blue: `#00B7F1`)
  - Special highlights (Orange: `#E9853C`)

### Typography

#### English Font: Myriad Pro
- **Weights**: Regular, Semibold, Bold
- **Usage**: 
  - Primary UI text (English content)
  - Headers and titles
  - Body text
- **Fallback**: System sans-serif (Arial, Helvetica)

#### Chinese Fonts
- **華康儷中宋 (DFLiSong-B5)**: Headlines, titles
  - Use for Chinese headings and important text
  - Fallback: SimSun, serif
  
- **蒙納黑體 (Monotype Hei)**: Body text
  - Use for Chinese body content
  - Weights: Light, Medium, Bold
  - Fallback: SimHei, Microsoft YaHei, sans-serif

#### Typography Scale

**Headlines:**
- Headline XL (80pt): Landing page hero text
- Headline 1 (60pt, Bold): Main page titles
- Headline 2 (60pt, Semibold): Section headers
- Headline 3 (52pt, Bold): Subsection headers
- Headline 4 (52pt, Semibold): Card titles
- Headline 5 (40pt, Bold): Panel headers
- Headline 6 (40pt, Semibold): Small headers

**Body Text:**
- Title 1-3 (24pt): Section labels, important text
- Body (16pt): Primary body text
- Body Small (12pt): Secondary text, captions
- Number (20pt): Numerical data, metrics

### UI Component Styles

#### Cursor-Inspired Design Elements

1. **Sidebar Navigation**: 
   - Left sidebar with collapsible sections
   - Dark background (`#031C34` or `#002A54`)
   - Icon-based navigation
   - Smooth transitions

2. **Content Area**:
   - Clean, spacious layout
   - Maximum content width (~1200px)
   - Generous whitespace
   - Subtle shadows and borders

3. **Code/Data Display**:
   - Monospace font for JSON/data
   - Syntax highlighting
   - Collapsible sections
   - Copy-to-clipboard functionality

4. **Progress Indicators**:
   - Minimal, clean progress bars
   - Step-by-step indicators
   - Real-time status updates
   - Smooth animations

5. **Button Styles**:
   - Primary: Dark blue background (`#002A54`)
   - Secondary: Outlined with blue border
   - Danger: Red accent (`#AF2A47`)
   - Ghost: Transparent with hover state

---

## Application Structure

### Directory Structure

```
client/
├── src/
│   ├── components/           # Reusable UI components
│   │   ├── common/          # Buttons, inputs, cards
│   │   ├── layout/          # Header, sidebar, footer
│   │   ├── progress/        # Progress bars, step indicators
│   │   ├── data-display/   # JSON viewer, markdown renderer
│   │   └── phase-specific/ # Phase-specific components
│   ├── pages/               # Page components
│   │   ├── LinkInputPage.tsx
│   │   ├── ScrapingProgressPage.tsx
│   │   ├── ResearchAgentPage.tsx
│   │   ├── Phase3SessionPage.tsx
│   │   └── FinalReportPage.tsx
│   ├── stores/              # State management
│   │   ├── workflowStore.ts
│   │   ├── sessionStore.ts
│   │   └── uiStore.ts
│   ├── services/            # API and WebSocket services
│   │   ├── api.ts
│   │   ├── websocket.ts
│   │   └── types.ts
│   ├── hooks/               # Custom React hooks
│   │   ├── useWebSocket.ts
│   │   ├── useProgress.ts
│   │   └── useSession.ts
│   ├── utils/               # Utility functions
│   │   ├── formatters.ts
│   │   ├── validators.ts
│   │   └── constants.ts
│   ├── styles/              # Global styles and Tailwind config
│   │   ├── globals.css
│   │   └── tailwind.config.js
│   ├── types/               # TypeScript types
│   │   ├── workflow.ts
│   │   ├── session.ts
│   │   └── api.ts
│   └── App.tsx              # Main app component
├── public/                  # Static assets
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js

backend/
├── app/
│   ├── main.py              # FastAPI application
│   ├── routes/              # API routes
│   │   ├── links.py
│   │   ├── workflow.py
│   │   ├── research.py
│   │   └── session.py
│   ├── services/            # Business logic
│   │   ├── link_formatter_service.py
│   │   ├── workflow_service.py
│   │   ├── research_agent_service.py
│   │   └── session_service.py
│   ├── websocket/           # WebSocket handlers
│   │   ├── manager.py
│   │   └── events.py
│   ├── models/              # Data models
│   │   ├── workflow.py
│   │   ├── session.py
│   │   └── batch.py
│   └── utils/               # Utilities
│       ├── config.py
│       └── helpers.py
├── requirements.txt
└── README.md
```

---

## Workflow Integration

### Workflow Steps Mapping

#### Step 1: Link Input & Formatting
**UI Component**: `LinkInputPage`
**Backend Service**: `link_formatter_service.py`
**Integration**: Wrap `utils/link_formatter.py` logic

**Flow:**
1. User pastes URLs in textarea or inputs one by one
2. Click "开始研究" button
3. Frontend sends URLs to `/api/links/format` endpoint
4. Backend calls `build_items()` from `link_formatter.py`
5. Backend generates/retrieves batch ID
6. Backend saves to `tests/data/test_links.json`
7. Backend returns batch ID and formatted items
8. Frontend navigates to progress page with batch ID

#### Step 2: Batch Creation & Workflow Start
**UI Component**: `ScrapingProgressPage` (Phase 0)
**Backend Service**: `workflow_service.py`
**Integration**: Wrap `test_full_workflow_integration.py` logic

**Flow:**
1. Frontend receives batch ID
2. Frontend calls `/api/workflow/start` with batch ID
3. Backend starts workflow in background task
4. WebSocket connection established for progress updates
5. Backend runs `run_all_scrapers()` equivalent
6. Progress updates sent via WebSocket:
   - Scraper status (started, in-progress, completed, failed)
   - Individual URL processing status
   - Overall progress percentage
7. UI displays real-time scraper progress

#### Step 3: Research Agent Entry
**UI Component**: `ResearchAgentPage` (Phase 0.5-2)
**Backend Service**: `research_agent_service.py`
**Integration**: Wrap `DeepResearchAgent` with progress callbacks

**Flow:**
1. Scraping completes, backend verifies results
2. WebSocket event: `research_agent_starting`
3. Frontend slides to `ResearchAgentPage`
4. Backend initializes `DeepResearchAgent`
5. Progress updates for Phase 0.5-2:
   - Phase 0.5: Role generation
   - Phase 1: Goal discovery and user interaction
   - Phase 2: Research plan synthesis

#### Step 4: Phase 3 Session Display
**UI Component**: `Phase3SessionPage`
**Backend Service**: `session_service.py`
**Integration**: Read and parse session JSON files

**Flow:**
1. Phase 3 starts, backend begins step execution
2. For each step, backend:
   - Executes research step
   - Updates session JSON file
   - Sends WebSocket event with step data
3. Frontend receives step data
4. Frontend displays step as a column
5. Columns scroll horizontally if too many
6. Each column shows:
   - Step ID and goal
   - Findings summary
   - Key claims and evidence
   - Insights
   - Confidence score
   - Timestamp

#### Step 5: Phase 4 Final Report
**UI Component**: `FinalReportPage`
**Backend Service**: `research_agent_service.py`
**Integration**: Read final report from session JSON

**Flow:**
1. Phase 3 completes all steps
2. Phase 4 starts, backend generates final report
3. WebSocket event: `final_report_ready`
4. Frontend receives report markdown
5. Frontend displays report in pinned right column
6. Phase 3 columns remain visible on left
7. UI shows hierarchical importance (report is primary)

---

## UI Components & Views

### 1. Link Input Page (`LinkInputPage`)

**Purpose**: Initial URL input and formatting

**Layout**:
- Centered card on light background
- Large textarea for URL input
- "开始研究" button (primary blue)
- Optional: URL validation feedback

**Features**:
- Multi-line URL input
- Real-time URL validation
- Format hints/help text
- Loading state during formatting
- Error display for invalid URLs

**Design Elements**:
- Card background: `#FFFFFF`
- Input border: `#DFE7EC`
- Primary button: `#002A54`
- Focus state: `#52A8FF`

### 2. Scraping Progress Page (`ScrapingProgressPage`)

**Purpose**: Show progress during Phase 0 (scraping)

**Layout**:
- Header with batch ID and overall progress
- List of URLs with individual status
- Progress bar at top
- Status indicators (success, error, in-progress)

**Features**:
- Real-time progress updates via WebSocket
- Individual URL status tracking
- Success/error counts
- Expandable error details
- Auto-navigate to research page when complete

**Design Elements**:
- Progress bar: Primary blue gradient
- Success indicator: Green (`#2FB66A`)
- Error indicator: Red (`#AF2A47`)
- In-progress: Animated spinner

### 3. Research Agent Page (`ResearchAgentPage`)

**Purpose**: Interactive research agent (Phase 0.5-2)

**Layout**:
- Left: AI response display area
- Right: User input area (when needed)
- Bottom: Progress indicator showing current phase

**Phase 0.5 - Role Generation**:
- Display: Streaming AI response for role generation
- User Input: None (automatic)

**Phase 1 - Goal Discovery**:
- Display: Generated goals with descriptions
- User Input: 
  - Goal selection buttons
  - Optional: Text input for custom goal
  - "确认" and "修改" buttons

**Phase 2 - Research Plan**:
- Display: Research plan steps with descriptions
- User Input:
  - "确认计划" button
  - Optional: Step modification interface
  - "开始研究" button

**Features**:
- Streaming text display (typewriter effect)
- Interactive buttons at appropriate times
- Phase indicator in header
- Smooth transitions between phases

**Design Elements**:
- AI response area: White background, monospace font
- User input area: Light grey background (`#F8F7F9`)
- Buttons: Primary blue with hover states
- Phase indicator: Color-coded badges

### 4. Phase 3 Session Page (`Phase3SessionPage`)

**Purpose**: Display session data for each research step

**Layout**:
- Horizontal scrolling column layout
- Each column represents one step
- Column width: ~400px
- Vertical scroll for long content

**Column Structure** (per step):
```
┌─────────────────────────┐
│ Step {id}               │
│ {goal_text}             │
├─────────────────────────┤
│ Findings Summary       │
│ {summary_text}          │
├─────────────────────────┤
│ Key Claims             │
│ • Claim 1              │
│ • Claim 2              │
├─────────────────────────┤
│ Evidence               │
│ • Evidence 1            │
│ • Evidence 2            │
├─────────────────────────┤
│ Insights               │
│ {insights_text}        │
├─────────────────────────┤
│ Confidence: {score}%    │
│ Timestamp: {time}      │
└─────────────────────────┘
```

**Features**:
- Real-time column addition as steps complete
- Horizontal scroll for many columns
- Vertical scroll within columns
- Expandable sections for detailed data
- JSON viewer for raw data (optional)
- Copy-to-clipboard for findings
- Search/filter steps

**Design Elements**:
- Column background: `#FFFFFF`
- Column border: `#DFE7EC`
- Header: Primary blue background
- Confidence badge: Color-coded (green/yellow/red)
- Subtle shadows for depth

### 5. Final Report Page (`FinalReportPage`)

**Purpose**: Display final report alongside Phase 3 steps

**Layout**:
- Left: Phase 3 columns (scrollable, narrower)
- Right: Pinned final report column (wider, fixed)
- Split: ~40% / ~60% or ~30% / ~70%

**Report Column Structure**:
```
┌─────────────────────────────────────┐
│ Final Report                       │
│ (Pinned, Sticky)                   │
├─────────────────────────────────────┤
│ {markdown content rendered}        │
│                                     │
│ - Headers                           │
│ - Sections                          │
│ - Lists                             │
│ - Code blocks (if any)              │
│                                     │
│ [Scrollable content]                │
├─────────────────────────────────────┤
│ Actions:                            │
│ [Export PDF] [Export Markdown]      │
│ [Copy Link]                         │
└─────────────────────────────────────┘
```

**Features**:
- Markdown rendering with syntax highlighting
- Sticky/pinned report column
- Export options (PDF, Markdown, JSON)
- Table of contents (auto-generated)
- Section navigation
- Print-friendly styling

**Design Elements**:
- Report column: Elevated with shadow
- Background: `#FFFFFF`
- Typography: Body text (16pt) for content
- Headers: Bold, larger sizes
- Hierarchical importance: Report is visually dominant

### 6. Common UI Components

#### Progress Bar
- Horizontal bar with percentage
- Color-coded by phase
- Smooth animation
- Optional: Step indicators

#### Status Badge
- Color-coded (success, error, warning, info)
- Icon + text
- Rounded corners

#### JSON Viewer
- Collapsible tree structure
- Syntax highlighting
- Copy buttons for values
- Search functionality

#### Markdown Renderer
- Styled markdown output
- Syntax highlighting for code blocks
- Table styling
- Link handling

#### Button Components
- Primary: Blue background
- Secondary: Outlined
- Danger: Red
- Ghost: Transparent
- Loading states
- Disabled states

---

## State Management

### Store Structure

#### Workflow Store (`workflowStore.ts`)

```typescript
interface WorkflowState {
  // Current workflow state
  currentPhase: 'input' | 'scraping' | 'research' | 'phase3' | 'phase4' | 'complete';
  batchId: string | null;
  workflowId: string | null;
  
  // Progress tracking
  overallProgress: number; // 0-100
  currentStep: string | null;
  stepProgress: number; // 0-100
  
  // Scraping phase
  scrapingStatus: {
    total: number;
    completed: number;
    failed: number;
    inProgress: number;
    items: Array<{
      url: string;
      status: 'pending' | 'in-progress' | 'completed' | 'failed';
      error?: string;
    }>;
  };
  
  // Research agent phase
  researchAgentStatus: {
    phase: '0.5' | '1' | '2';
    currentAction: string | null;
    waitingForUser: boolean;
    userInputRequired: {
      type: 'goal_selection' | 'plan_confirmation' | 'custom_input';
      data: any;
    } | null;
  };
  
  // Phase 3
  phase3Steps: Array<SessionStep>;
  currentStepId: number | null;
  
  // Phase 4
  finalReport: {
    content: string;
    generatedAt: string;
    status: 'generating' | 'ready' | 'error';
  } | null;
  
  // Error handling
  errors: Array<{
    phase: string;
    message: string;
    timestamp: string;
  }>;
}

// Actions
- setBatchId(batchId: string)
- setCurrentPhase(phase: string)
- updateProgress(progress: number)
- updateScrapingStatus(status: ScrapingStatus)
- updateResearchAgentStatus(status: ResearchAgentStatus)
- addPhase3Step(step: SessionStep)
- setFinalReport(report: FinalReport)
- addError(error: Error)
```

#### Session Store (`sessionStore.ts`)

```typescript
interface SessionState {
  sessionId: string | null;
  sessionData: SessionData | null;
  
  // Session metadata
  metadata: {
    created_at: string;
    batch_id: string;
    selected_goal: string | null;
    research_plan: any;
    status: string;
  };
  
  // Quality assessment
  qualityAssessment: QualityAssessment | null;
  
  // Research role
  researchRole: ResearchRole | null;
  
  // Synthesized goal
  synthesizedGoal: SynthesizedGoal | null;
  
  // Component goals
  componentGoals: Array<ComponentGoal>;
  
  // Scratchpad (step data)
  scratchpad: Record<string, StepData>;
  
  // Final report
  finalReport: string | null;
}

// Actions
- loadSession(sessionId: string)
- updateSessionData(data: SessionData)
- updateStep(stepId: string, stepData: StepData)
```

#### UI Store (`uiStore.ts`)

```typescript
interface UIState {
  // Navigation
  currentPage: string;
  sidebarOpen: boolean;
  
  // Theme
  theme: 'light' | 'dark';
  
  // View preferences
  viewPreferences: {
    showRawJson: boolean;
    columnWidth: number;
    fontSize: number;
  };
  
  // Notifications
  notifications: Array<Notification>;
}

// Actions
- setCurrentPage(page: string)
- toggleSidebar()
- setTheme(theme: string)
- addNotification(notification: Notification)
- removeNotification(id: string)
```

---

## Real-Time Communication

### WebSocket Events

#### Client → Server Events

```typescript
// Start workflow
'workflow:start' {
  batchId: string;
}

// User interaction during research
'research:user_input' {
  type: 'goal_selection' | 'plan_confirmation' | 'custom_input';
  data: any;
}

// Request session update
'session:request_update' {
  sessionId: string;
}
```

#### Server → Client Events

```typescript
// Workflow progress
'workflow:progress' {
  phase: string;
  progress: number;
  currentStep: string;
  message: string;
}

// Scraping updates
'scraping:status' {
  total: number;
  completed: number;
  failed: number;
  items: Array<ScrapingItem>;
}

'scraping:item_update' {
  url: string;
  status: 'in-progress' | 'completed' | 'failed';
  error?: string;
}

// Research agent updates
'research:phase_change' {
  phase: '0.5' | '1' | '2';
  message: string;
}

'research:stream_start' {
  type: 'role' | 'goal' | 'plan' | 'step';
}

'research:stream_token' {
  token: string;
}

'research:stream_end' {
  data: any; // Parsed response
}

'research:user_input_required' {
  type: 'goal_selection' | 'plan_confirmation' | 'custom_input';
  data: any;
}

// Phase 3 updates
'phase3:step_start' {
  stepId: number;
  goal: string;
}

'phase3:step_complete' {
  stepId: number;
  stepData: SessionStep;
}

// Phase 4 updates
'phase4:report_generating' {
  progress: number;
}

'phase4:report_ready' {
  report: string;
  sessionId: string;
}

// Errors
'error' {
  phase: string;
  message: string;
  details?: any;
}
```

### WebSocket Connection Management

```typescript
// Connection lifecycle
- Connect on workflow start
- Reconnect on disconnect
- Room/namespace per batch ID
- Clean disconnect on page unload
- Heartbeat/ping to maintain connection
```

---

## Implementation Phases

### Phase 1: Foundation Setup (Week 1-2)

**Goals:**
- Set up project structure
- Configure build tools
- Implement Design System in Tailwind
- Create base UI components
- Set up state management

**Tasks:**
1. Initialize React + TypeScript project with Vite
2. Configure Tailwind CSS with Design System colors
3. Set up typography (Myriad Pro + Chinese fonts)
4. Create base layout components (Header, Sidebar)
5. Implement common UI components (Button, Card, Input)
6. Set up state management stores
7. Create routing structure

**Deliverables:**
- Working dev environment
- Design System integrated
- Base components library
- Routing structure

### Phase 2: Backend API Setup (Week 2-3)

**Goals:**
- Create FastAPI backend
- Integrate existing services
- Set up WebSocket infrastructure
- Create API endpoints

**Tasks:**
1. Set up FastAPI project structure
2. Create link formatter service wrapper
3. Create workflow service wrapper
4. Integrate DeepResearchAgent with callbacks
5. Set up WebSocket manager
6. Create API routes (links, workflow, research, session)
7. Implement progress broadcasting
8. Add error handling and logging

**Deliverables:**
- Working FastAPI backend
- Integrated services
- WebSocket infrastructure
- API documentation

### Phase 3: Link Input & Scraping UI (Week 3-4)

**Goals:**
- Implement link input page
- Create scraping progress page
- Real-time progress updates
- Error handling

**Tasks:**
1. Build LinkInputPage component
2. Implement URL validation
3. Create ScrapingProgressPage component
4. Set up WebSocket connection
5. Implement real-time progress updates
6. Add error display and handling
7. Auto-navigation on completion

**Deliverables:**
- Link input page functional
- Scraping progress with real-time updates
- Error handling

### Phase 4: Research Agent UI (Week 4-5)

**Goals:**
- Implement research agent page
- Streaming text display
- Interactive user input
- Phase transitions

**Tasks:**
1. Build ResearchAgentPage component
2. Implement streaming text display
3. Create goal selection interface
4. Create plan confirmation interface
5. Implement user input handling
6. Add phase transitions and animations
7. Integrate with backend WebSocket events

**Deliverables:**
- Research agent page functional
- Streaming display working
- User interactions working

### Phase 5: Phase 3 Session Display (Week 5-6)

**Goals:**
- Implement session data visualization
- Column layout with scrolling
- Real-time step updates
- JSON data display

**Tasks:**
1. Build Phase3SessionPage component
2. Implement horizontal scrolling column layout
3. Create step column component
4. Implement JSON viewer
5. Add real-time step updates
6. Implement search/filter
7. Add copy-to-clipboard functionality

**Deliverables:**
- Phase 3 page with column layout
- Real-time step updates
- Beautiful data visualization

### Phase 6: Final Report Display (Week 6-7)

**Goals:**
- Implement final report page
- Markdown rendering
- Pinned column layout
- Export functionality

**Tasks:**
1. Build FinalReportPage component
2. Implement split layout (columns + report)
3. Add markdown renderer
4. Implement export functionality (PDF, Markdown)
5. Add table of contents
6. Styling for hierarchical importance
7. Print-friendly styles

**Deliverables:**
- Final report page functional
- Export functionality
- Beautiful report display

### Phase 7: Polish & Testing (Week 7-8)

**Goals:**
- UI/UX refinements
- Performance optimization
- Error handling improvements
- Testing

**Tasks:**
1. UI/UX polish (animations, transitions)
2. Performance optimization
3. Comprehensive error handling
4. Unit tests for critical components
5. E2E testing (optional)
6. Browser compatibility testing
7. Documentation

**Deliverables:**
- Polished application
- Test coverage
- Documentation

---

## Technical Details

### Backend Service Integration

#### Link Formatter Service

```python
# app/services/link_formatter_service.py

from utils.link_formatter import build_items, current_batch_id
from pathlib import Path
import json

class LinkFormatterService:
    def format_links(self, urls: List[str]) -> Dict:
        """Format URLs and create batch."""
        items = build_items(urls)
        batch_id = current_batch_id()
        
        # Save to test_links.json
        target_file = Path("tests/data/test_links.json")
        payload = {
            "batchId": batch_id,
            "createdAt": iso_timestamp(),
            "links": items,
        }
        target_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        return {
            "batch_id": batch_id,
            "items": items,
            "total": len(items)
        }
```

#### Workflow Service

```python
# app/services/workflow_service.py

from tests.test_full_workflow_integration import (
    run_all_scrapers,
    verify_scraper_results,
    run_research_agent
)
from app.websocket.manager import WebSocketManager

class WorkflowService:
    def __init__(self, websocket_manager: WebSocketManager):
        self.ws_manager = websocket_manager
    
    async def run_workflow(self, batch_id: str):
        """Run full workflow with progress updates."""
        # Step 1: Run scrapers
        await self.ws_manager.broadcast("scraping:start", {"batch_id": batch_id})
        
        scrapers_result = run_all_scrapers()
        
        # Send progress updates
        for item in scrapers_result:
            await self.ws_manager.broadcast("scraping:item_update", {
                "url": item["url"],
                "status": "completed" if item["returncode"] == 0 else "failed",
                "error": item.get("error")
            })
        
        # Step 2: Verify results
        if not verify_scraper_results(batch_id):
            await self.ws_manager.broadcast("error", {
                "phase": "scraping",
                "message": "Scraper results verification failed"
            })
            return
        
        # Step 3: Run research agent
        await self.ws_manager.broadcast("research:start", {"batch_id": batch_id})
        
        # Create UI with WebSocket callbacks
        ui = WebSocketUI(self.ws_manager)
        
        agent = DeepResearchAgent(
            api_key=api_key,
            ui=ui,
            additional_output_dirs=[str(output_dir)]
        )
        
        result = agent.run_research(
            batch_id=batch_id,
            user_topic=None
        )
        
        return result
```

#### WebSocket UI Adapter

```python
# app/services/websocket_ui.py

class WebSocketUI:
    """Adapter to convert DeepResearchAgent UI calls to WebSocket events."""
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.ws_manager = websocket_manager
    
    def display_message(self, message: str, level: str = "info"):
        """Send message via WebSocket."""
        self.ws_manager.broadcast("workflow:progress", {
            "message": message,
            "level": level
        })
    
    def display_stream(self, token: str):
        """Stream token via WebSocket."""
        self.ws_manager.broadcast("research:stream_token", {
            "token": token
        })
    
    def prompt_user(self, prompt: str, choices: Optional[list] = None) -> str:
        """Request user input via WebSocket."""
        # This will need to wait for user response
        # Implementation depends on async approach
        pass
```

### Frontend WebSocket Integration

```typescript
// src/services/websocket.ts

class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  
  connect(batchId: string): void {
    const wsUrl = `ws://localhost:8000/ws/${batchId}`;
    this.ws = new WebSocket(wsUrl);
    
    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    };
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    this.ws.onclose = () => {
      this.handleReconnect(batchId);
    };
  }
  
  private handleMessage(data: any): void {
    // Dispatch to appropriate store/handler
    switch (data.type) {
      case 'workflow:progress':
        workflowStore.updateProgress(data);
        break;
      case 'scraping:item_update':
        workflowStore.updateScrapingItem(data);
        break;
      case 'research:stream_token':
        workflowStore.appendStreamToken(data.token);
        break;
      case 'phase3:step_complete':
        workflowStore.addPhase3Step(data.stepData);
        break;
      // ... more cases
    }
  }
  
  send(event: string, data: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: event, ...data }));
    }
  }
  
  private handleReconnect(batchId: string): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => this.connect(batchId), 1000 * this.reconnectAttempts);
    }
  }
  
  disconnect(): void {
    this.ws?.close();
    this.ws = null;
  }
}
```

### Session Data Parsing

```typescript
// src/utils/sessionParser.ts

interface SessionStep {
  step_id: number;
  findings: {
    summary: string;
    points_of_interest: {
      key_claims: Array<{
        claim: string;
        supporting_evidence: string;
      }>;
      notable_evidence: Array<{
        evidence_type: string;
        description: string;
      }>;
    };
    analysis_details: {
      five_whys: string[];
      assumptions: string[];
      uncertainties: string[];
    };
  };
  insights: string;
  confidence: number;
  timestamp: string;
}

function parseSessionData(sessionJson: any): {
  metadata: SessionMetadata;
  steps: SessionStep[];
  finalReport: string | null;
} {
  const steps: SessionStep[] = [];
  
  // Parse scratchpad
  if (sessionJson.scratchpad) {
    Object.keys(sessionJson.scratchpad).forEach((key) => {
      const stepData = sessionJson.scratchpad[key];
      steps.push({
        step_id: stepData.step_id,
        findings: stepData.findings,
        insights: stepData.insights,
        confidence: stepData.confidence,
        timestamp: stepData.timestamp,
      });
    });
  }
  
  // Sort by step_id
  steps.sort((a, b) => a.step_id - b.step_id);
  
  return {
    metadata: sessionJson.metadata,
    steps,
    finalReport: sessionJson.metadata?.final_report || null,
  };
}
```

---

## Additional Considerations

### Error Handling

- **Network Errors**: Retry logic, user-friendly error messages
- **API Errors**: Display error details, suggest solutions
- **WebSocket Disconnection**: Auto-reconnect, show connection status
- **Validation Errors**: Inline validation feedback
- **Service Errors**: Graceful degradation, error logging

### Performance Optimization

- **Lazy Loading**: Load components on demand
- **Virtual Scrolling**: For long lists of steps/items
- **Memoization**: React.memo for expensive components
- **Debouncing**: For search/filter inputs
- **Code Splitting**: Route-based code splitting
- **Image Optimization**: Optimize any images/assets

### Accessibility

- **Keyboard Navigation**: Full keyboard support
- **Screen Reader Support**: ARIA labels and roles
- **Color Contrast**: Ensure Design System colors meet WCAG AA
- **Focus Management**: Visible focus indicators
- **Alternative Text**: For icons and images

### Browser Compatibility

- **Modern Browsers**: Chrome, Firefox, Safari, Edge (latest 2 versions)
- **Polyfills**: For older browser support if needed
- **Progressive Enhancement**: Core functionality works without JS

### Deployment

- **Development**: Local development server
- **Production**: Build static assets, serve via FastAPI or separate web server
- **Packaging**: Consider Electron for desktop app (future)
- **Docker**: Containerize for easy deployment

---

## Future Enhancements

1. **Dark Mode**: Support for dark theme
2. **Export Options**: More export formats (Word, HTML)
3. **Session History**: View past research sessions
4. **Collaboration**: Share sessions with team members
5. **Customization**: User preferences for UI layout
6. **Offline Support**: Work offline with cached data
7. **Mobile App**: React Native mobile version
8. **Desktop App**: Electron wrapper for native app

---

## Conclusion

This plan provides a comprehensive roadmap for building a modern, Cursor-inspired client application that integrates seamlessly with the existing research tool workflow. The architecture supports real-time progress tracking, beautiful data visualization, and an intuitive user experience throughout all phases of the research process.

The Design System integration ensures visual consistency, while the component-based architecture allows for maintainable and extensible code. The WebSocket-based real-time communication provides immediate feedback and keeps users engaged throughout the potentially long-running research process.

**Next Steps:**
1. Review and confirm this plan
2. Set up development environment
3. Begin Phase 1 implementation
4. Iterate based on feedback

