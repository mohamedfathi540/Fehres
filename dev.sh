#!/bin/bash

# Fehres - Development Startup Script (Full Docker)
# Runs everything in Docker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}================================================${NC}"
    echo -e "${YELLOW}       Shutting down services...${NC}"
    echo -e "${YELLOW}================================================${NC}"
    docker compose -f Docker/docker-compose.yml down
    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}       Starting Fehres (Full Docker)${NC}"
echo -e "${GREEN}================================================${NC}"

# 1. Prepare Environment Variables
echo -e "${BLUE}[1/3] Preparing environment configuration...${NC}"
mkdir -p Docker/env

# Read SRC/.env and translate for Docker
# We need to change localhost -> pgvector and port 5433 -> 5432 for internal docker comms
if [ -f "SRC/.env" ]; then
    echo -e "${YELLOW}Translating SRC/.env to Docker/env/.env.app...${NC}"
    sed -e 's/POSTGRES_HOST[[:space:]]*=[[:space:]]*"localhost"/POSTGRES_HOST = "pgvector"/g' \
        -e 's/POSTGRES_PORT[[:space:]]*=[[:space:]]*"5433"/POSTGRES_PORT = "5432"/g' \
        SRC/.env > Docker/env/.env.app
else
    echo -e "${RED}Error: SRC/.env not found! Please create it from SRC/.env.example${NC}"
    exit 1
fi

# 2. Build and Start
echo -e "${BLUE}[2/3] Building and starting services...${NC}"
echo -e "${YELLOW}This might take a while on first run...${NC}"

docker compose -f Docker/docker-compose.yml up --build -d

# 3. Follow Logs
echo -e "${BLUE}[3/3] Services started! Tailing logs...${NC}"
echo -e "${GREEN}Frontend:${NC} http://localhost:5173"
echo -e "${GREEN}Backend:${NC}  http://localhost:8000/docs"
echo -e "${GREEN}Grafana:${NC}  http://localhost:3000"

docker compose -f Docker/docker-compose.yml logs -f
