#!/bin/bash

# Fehres - Development Startup Script
# Runs databases in Docker, backend and frontend locally

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create logs directory
mkdir -p logs
echo -e "${BLUE}Logs will be stored in ./logs/${NC}"

# Store child PIDs for cleanup
CHILD_PIDS=()

cleanup() {
    echo ""
    echo -e "${YELLOW}================================================${NC}"
    echo -e "${YELLOW}       Shutting down services...${NC}"
    echo -e "${YELLOW}================================================${NC}"
    
    # Kill tracked processes
    for pid in "${CHILD_PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            pkill -TERM -P "$pid" 2>/dev/null || true
            kill -TERM "$pid" 2>/dev/null || true
        fi
    done
    
    # Cleanup ports just in case
    for port in 8000 5173; do
        fuser -k "$port/tcp" 2>/dev/null || true
    done
    
    echo -e "${GREEN}All services stopped.${NC}"
    echo -e "${BLUE}Note: Docker infrastructure still running. Stop with:${NC}"
    echo -e "${BLUE}  docker compose -f Docker/docker-compose.dev.yml down${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}       Starting Fehres Development${NC}"
echo -e "${GREEN}================================================${NC}"

# 1. Start Infrastructure (Docker)
echo -e "${BLUE}[1/4] Checking Docker infrastructure...${NC}"
if ! docker ps | grep -q "fehres-pgvector"; then
    echo -e "${YELLOW}Starting Docker infrastructure...${NC}"
    docker compose -f Docker/docker-compose.dev.yml up -d
    echo -e "${YELLOW}Waiting for PostgreSQL to be healthy...${NC}"
    sleep 5
    # Wait for postgres to be ready
    until docker exec fehres-pgvector pg_isready -U postgres > /dev/null 2>&1; do
        echo -e "${YELLOW}Waiting for PostgreSQL...${NC}"
        sleep 2
    done
    echo -e "${GREEN}PostgreSQL is ready!${NC}"
else
    echo -e "${GREEN}Docker infrastructure already running.${NC}"
fi

# 1.5. Ensure database exists
echo -e "${BLUE}[1.5/4] Ensuring database exists...${NC}"
DB_EXISTS=$(docker exec fehres-pgvector psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='minirag'" 2>/dev/null || echo "")
if [ -z "$DB_EXISTS" ]; then
    echo -e "${YELLOW}Creating database 'minirag'...${NC}"
    docker exec fehres-pgvector psql -U postgres -c "CREATE DATABASE minirag;" > /dev/null 2>&1
    echo -e "${GREEN}Database created!${NC}"
else
    echo -e "${GREEN}Database already exists.${NC}"
fi

# 2. Run database migrations
echo -e "${BLUE}[2/4] Running database migrations...${NC}"
(cd SRC/Models/DB_Schemes/minirag && uv run alembic upgrade head)
echo -e "${GREEN}Migrations complete!${NC}"

# 3. Backend API
echo -e "${BLUE}[3/4] Starting Backend API (Port 8000)...${NC}"
(cd SRC && uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload) > logs/backend.log 2>&1 &
CHILD_PIDS+=($!)

# Wait a moment for backend to start
sleep 2

# 4. Frontend
echo -e "${BLUE}[4/4] Starting Frontend (Port 5173)...${NC}"
(cd frontend && pnpm run dev) > logs/frontend.log 2>&1 &
CHILD_PIDS+=($!)

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}       Services Started!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "  ${BLUE}Frontend:${NC}  http://localhost:5173"
echo -e "  ${BLUE}Backend:${NC}   http://localhost:8000/docs"
echo -e "  ${BLUE}PostgreSQL:${NC} localhost:5433"
echo -e "  ${BLUE}Qdrant:${NC}    localhost:6333"
echo ""
echo -e "${YELLOW}Tailing logs (Ctrl+C to stop all services)...${NC}"
echo -e "${YELLOW}================================================${NC}"
sleep 2
tail -f logs/*.log
