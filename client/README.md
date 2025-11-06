# Research Tool Client

Client application for the Research Tool service.

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn/pnpm

### Installation

```bash
npm install
```

### Development

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

### Build

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
client/
├── src/
│   ├── components/     # Reusable UI components
│   ├── pages/          # Page components
│   ├── stores/          # State management (Zustand)
│   ├── services/        # API and WebSocket services
│   ├── hooks/           # Custom React hooks
│   ├── utils/           # Utility functions
│   ├── styles/          # Global styles and Tailwind config
│   └── types/           # TypeScript types
├── public/              # Static assets
└── package.json
```

## Features

- Real-time progress tracking via WebSocket
- Phase-aware UI for different workflow stages
- Design System integration (colors and typography)
- Responsive design with mobile support

## Tech Stack

- React 18 + TypeScript
- Vite
- Tailwind CSS
- Zustand (state management)
- React Router
- Axios (HTTP client)
- React Markdown (markdown rendering)



