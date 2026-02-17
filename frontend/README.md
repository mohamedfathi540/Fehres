# Fehres Frontend

A modern, accessible React SPA for the Fehres RAG (Retrieval-Augmented Generation) system.

## Features

- **Chat Interface**: RAG Q&A with AI-generated answers
- **Upload & Process**: File upload, chunking, and indexing workflow
- **Semantic Search**: Natural language search on indexed documents
- **Index Info**: Vector database statistics dashboard
- **Settings**: API configuration and preferences

## Tech Stack

- React 18 + TypeScript
- Vite (build tool)
- React Aria Components (accessible UI primitives)
- Tailwind CSS (styling)
- TanStack Query (server state management)
- Zustand (client state management)
- React Router (SPA routing)

## Getting Started

### Prerequisites

- Node.js 18+ or pnpm
- Running Fehres API backend

### Installation

```bash
# Install dependencies
pnpm install

# Start development server
pnpm run dev
```

The development server will start at `http://localhost:5173`.

### Environment Variables

Copy `.env.example` to `.env` and configure as needed:

```bash
cp .env.example .env
```

| Variable       | Description         | Default                        |
| -------------- | ------------------- | ------------------------------ |
| `VITE_API_URL` | Fehres API base URL | `http://localhost:8000/api/v1` |

### Building for Production

```bash
pnpm build
```

The built files will be in the `dist/` directory.

### Docker

Build and run with Docker:

```bash
docker build -t fehres-frontend .
docker run -p 80:80 fehres-frontend
```

## Project Structure

```
frontend/
├── src/
│   ├── api/          # API clients and types
│   ├── components/   # React components
│   │   ├── ui/       # Base UI components
│   │   ├── layout/   # Layout components
│   │   └── features/ # Feature-specific components
│   ├── pages/        # Page components
│   ├── stores/       # Zustand stores
│   └── utils/        # Utility functions
├── public/           # Static assets
└── ...
```

## API Integration

The frontend communicates with the Fehres API at `http://localhost:8000/api/v1` by default. This can be changed in the Settings page.

Available endpoints:

- `GET /` - Health check
- `POST /data/upload/{project_id}` - Upload files
- `POST /data/process/{project_id}` - Process files into chunks
- `POST /nlp/index/push/{project_id}` - Push chunks to vector DB
- `GET /nlp/index/info/{project_id}` - Get index info
- `POST /nlp/index/search/{project_id}` - Semantic search
- `POST /nlp/index/answer/{project_id}` - RAG Q&A

## License

Same as the main Fehres project.
