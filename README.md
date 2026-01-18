# My First RAG Project

This project is a Retrieval-Augmented Generation (RAG) system built with FastAPI, LangChain, and Vector Databases (like Qdrant/pgvector). It provides an API to upload documents, process them into chunks, index them, and ask questions based on the document context.

## Prerequisites

Before seeking to run the project, ensure you have the following installed:

*   **Python**: version 3.11.14 or higher
*   **uv**: A fast Python package installer and resolver.
*   **Docker** (Optional but recommended for running DB services like Postgres/Qdrant)

## Installation

1.  **Clone the repository** (if you haven't already).

2.  **Initialize the virtual environment**:

    ```bash
    uv init
    uv sync
    ```

3.  **Verify Python Version**:

    ```bash
    uv run python --version
    # Should be 3.11.14 or compatible
    ```

4.  **Install Requirements**:

    ```bash
    uv pip install -r requirements.txt
    ```

## Configuration

1.  **Environment Variables**:
    Copy the example environment file to create your own `.env` file:

    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file**:
    Open `.env` and fill in the necessary details. Key variables usually include:
    *   `OPENAI_API_KEY`: For LLM generation and embeddings (if using OpenAI).
    *   `POSTGRES_*`: Database connection details.
    *   `VECTORDB_*`: Vector Database configuration.

## Running the Application

To start the API server, use the following command:

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 5000
```

The API will be available at `http://0.0.0.0:5000`.

## Testing & Verification

### 1. Automated Verification Script
We have included a `verify.py` script to quickly check if the server is up and running.

**Make sure the server is running in a separate terminal**, then run:

```bash
uv run python verify.py
```

If successful, you should see:
> ✅ Health check passed!

### 2. Manual Testing via API Docs
Open your browser and navigate to:
[http://0.0.0.0:5000/docs](http://0.0.0.0:5000/docs)

This uses Swagger UI to let you interactively test the API endpoints.

### 3. Step-by-Step Usage (Example)
1.  **Health Check**: GET `/api/v1/`
2.  **Upload File**: POST `/api/v1/data/upload/{project_id}`
3.  **Process File**: POST `/api/v1/data/process/{project_id}`
4.  **Index Data**: POST `/api/v1/nlp/index/push/{project_id}`
5.  **Search/Ask**: POST `/api/v1/nlp/index/search/{project_id}` or `/api/v1/nlp/index/answer/{project_id}`

## Project Structure
*   `main.py`: Entry point of the application.
*   `Routes`: API definitions.
*   `Controllers`: Business logic.
*   `Models`: Data models and schemas.
*   `Stores`: LLM and VectorDB integrations.
*   `Helpers`: Utility functions and configuration.

## Activation of the virtual environment

```bash
source .venv/bin/activate
```

### 4. Migrate the Database
```bash
uv run python -m alembic upgrade head
```