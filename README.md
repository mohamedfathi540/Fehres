# Fehres

A Retrieval-Augmented Generation (RAG) system for document-based question answering. Upload documents, process them into searchable chunks, and get AI-generated answers based on your content.

## Features

- **Multi-format Document Support**: PDF, TXT, Markdown, JSON, CSV, DOCX
- **Multiple LLM Providers**: OpenAI, Google Gemini, Cohere
- **Vector Database Options**: PostgreSQL with pgvector, Qdrant
- **RESTful API**: FastAPI backend with OpenAPI documentation
- **Monitoring**: Prometheus metrics and Grafana dashboards
- **Docker Ready**: Full containerized deployment with Docker Compose

## Architecture

```
                    ┌─────────────────┐
                    │   Streamlit UI  │
                    │   (Testing)     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │     Nginx       │
                    │  (Reverse Proxy)│
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    FastAPI      │
                    │   Application   │
                    └───┬────────┬────┘
                        │        │
         ┌──────────────┘        └──────────────┐
         │                                      │
┌────────▼────────┐                  ┌──────────▼──────────┐
│   PostgreSQL    │                  │   LLM Providers     │
│   (pgvector)    │                  │ OpenAI/Gemini/Cohere│
└─────────────────┘                  └─────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11.14+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Docker and Docker Compose (for containerized deployment)

### Local Development

1. Clone the repository

   ```bash
   git clone <repository-url>
   cd fehres
   ```

2. Set up environment

   ```bash
   cd SRC
   cp .env.example .env
   # Edit .env with your API keys and database credentials
   ```

3. Install dependencies

   ```bash
   uv sync
   # or: pip install -r requirements.txt
   ```

4. Run database migrations

   ```bash
   uv run python -m alembic upgrade head
   ```

5. Start the server

   ```bash
   uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

6. Access the API at `http://localhost:8000/docs`

### Docker Deployment

```bash
cd Docker
docker compose up -d
```

Services will be available at:

- API: http://localhost:8000
- API via Nginx: http://localhost
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090

See [Docker/README.md](Docker/README.md) for detailed Docker configuration.

## Usage

1. **Upload** a document via `/api/v1/data/upload/{project_id}`
2. **Process** the document into chunks via `/api/v1/data/process/{project_id}`
3. **Index** chunks to the vector database via `/api/v1/nlp/index/push/{project_id}`
4. **Ask** questions via `/api/v1/nlp/index/answer/{project_id}`

**Learning books corpus**: The project ID set by `LEARNING_BOOKS_PROJECT_ID` (default: 10) is reserved for the AI/Data Science references corpus (maths, statistics, coding, ML, DL, GenAI, system design). Use this fixed ID for upload, process, index, and search when using the learning assistant.

For full API documentation, see [API.md](API.md).

## Project Structure

```
fehres/
├── SRC/                    # Application source code
│   ├── main.py             # FastAPI application entry
│   ├── Routes/             # API endpoint definitions
│   ├── Controllers/        # Business logic
│   ├── Models/             # Data models and database schemas
│   ├── Stores/             # LLM and VectorDB integrations
│   └── Helpers/            # Configuration and utilities
├── Docker/                 # Docker configuration
├── streamlit_app/          # Testing frontend
├── API.md                  # API reference
└── README.md
```

## Configuration

Key environment variables (see `.env.example` for full list):

| Variable            | Description                                   |
| ------------------- | --------------------------------------------- |
| `GENRATION_BACKEND` | LLM provider: `OPENAI`, `GEMINI`, or `COHERE` |
| `EMBEDDING_BACKEND` | Embedding provider                            |
| `VECTORDB_BACKEND`  | Vector DB: `PGVECTOR` or `QDRANT`             |
| `POSTGRES_*`        | PostgreSQL connection settings                |
| `*_API_KEY`         | API keys for LLM providers                    |

## Testing

### Verify Server

```bash
uv run python verify.py
```

### Streamlit UI

```bash
cd streamlit_app
pip install -r requirements.txt
streamlit run app.py
```

See [streamlit_app/README.md](streamlit_app/README.md) for more details.

## License

Apache License 2.0 - see [LICENCE](LICENCE) for details.
