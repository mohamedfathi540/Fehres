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

# Parse arguments
BUILD_FLAG=""
SERVICES=""

for arg in "$@"
do
    if [ "$arg" == "--build" ]; then
        BUILD_FLAG="--build"
    else
        SERVICES="$SERVICES $arg"
    fi
done

# 1. Prepare Environment Variables
echo -e "${BLUE}[1/3] Syncing environment configuration...${NC}"

# Sync env files using python script
if command -v python3 &> /dev/null; then
    python3 scripts/sync_env.py
elif command -v python &> /dev/null; then
    python scripts/sync_env.py
else
    echo -e "${RED}Python not found! Skipping env sync.${NC}"
fi

# 2. Build and Start
echo -e "${BLUE}[2/3] Starting services...${NC}"

if [ -n "$BUILD_FLAG" ]; then
    echo -e "${YELLOW}Build flag detected. Rebuilding images...${NC}"
fi

if [ -n "$SERVICES" ]; then
    echo -e "${YELLOW}Starting specific services: $SERVICES${NC}"
    COMPOSE_CMD="docker compose -f Docker/docker-compose.yml up -d $BUILD_FLAG $SERVICES"
else
    echo -e "${YELLOW}Starting all services...${NC}"
    COMPOSE_CMD="docker compose -f Docker/docker-compose.yml up -d $BUILD_FLAG"
fi

eval $COMPOSE_CMD

# 3. Follow Logs
echo -e "${BLUE}[3/3] Services started! Tailing logs...${NC}"
echo -e "${GREEN}Frontend:${NC} http://localhost:5173"
echo -e "${GREEN}Backend:${NC}  http://localhost:8000/docs"
echo -e "${GREEN}Grafana:${NC}  http://localhost:3000"

# Only tail logs if we started everything, or correct logs if specific services
if [ -n "$SERVICES" ]; then
     docker compose -f Docker/docker-compose.yml logs -f $SERVICES
else
     docker compose -f Docker/docker-compose.yml logs -f | grep --line-buffered -v "GET /kfgndfkk4464_fubfd555"
fi
