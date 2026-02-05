#!/bin/bash

# Fehres - Stop Development Infrastructure
# Stops Docker containers started by dev.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${YELLOW}Stopping Fehres development infrastructure...${NC}"

# Stop Docker infrastructure
docker compose -f Docker/docker-compose.dev.yml down

echo -e "${GREEN}Infrastructure stopped.${NC}"
echo ""
echo -e "${BLUE}To remove volumes (delete all data):${NC}"
echo -e "  docker compose -f Docker/docker-compose.dev.yml down -v"
