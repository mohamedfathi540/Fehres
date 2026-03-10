#!/bin/bash

# ═══════════════════════════════════════════════════════════════════
# Fehres — Stop Development Environment
# Stops all processes started by dev.sh
# ═══════════════════════════════════════════════════════════════════

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

CHECK="✅"
STOP="🛑"

PID_DIR="/tmp/fehres"
BACKEND_PID="$PID_DIR/backend.pid"
FRONTEND_PID="$PID_DIR/frontend.pid"
BACKEND_LOG="$PID_DIR/backend.log"
FRONTEND_LOG="$PID_DIR/frontend.log"
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_DEV="Docker/docker-compose.dev.yml"
COMPOSE_FULL="Docker/docker-compose.yml"

echo ""
echo -e "  ${YELLOW}${BOLD}"
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║         ${STOP}  Stopping Fehres Dev Env           ║"
echo "  ╚══════════════════════════════════════════════╝"
echo -e "  ${NC}"

# ── Helpers ────────────────────────────────────────────────────────
kill_pid_file() {
    local pidfile=$1
    local label=$2
    if [ -f "$pidfile" ]; then
        local pid
        pid=$(cat "$pidfile" 2>/dev/null)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            sleep 1
            kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null || true
            echo -e "    ${GREEN}${CHECK} $label stopped (PID $pid)${NC}"
        else
            echo -e "    ${DIM}$label was not running${NC}"
        fi
        rm -f "$pidfile"
    else
        echo -e "    ${DIM}$label — no PID file found${NC}"
    fi
}

free_port() {
    local port=$1
    lsof -ti ":$port" 2>/dev/null | xargs kill -9 2>/dev/null || true
    fuser -k "${port}/tcp" 2>/dev/null || true
}

# 1. Stop Frontend
echo -e "  ${CYAN}Stopping frontend...${NC}"
kill_pid_file "$FRONTEND_PID" "Frontend"
free_port 5173

# 2. Stop Backend
echo -e "  ${CYAN}Stopping backend...${NC}"
kill_pid_file "$BACKEND_PID" "Backend"
free_port 8000

# 3. Stop Docker infra — kill known containers first (handles zombie docker-proxy)
echo -e "  ${CYAN}Stopping Docker infrastructure...${NC}"
OLD_CONTAINERS="fastapi frontend nginx pgvector qdrant prometheus grafana postgres_exporter node_exporter fehres-pgvector fehres-qdrant"
for c in $OLD_CONTAINERS; do
    docker stop "$c" 2>/dev/null && docker rm "$c" 2>/dev/null || true
done
docker compose -f "$PROJECT_ROOT/$COMPOSE_DEV" down --remove-orphans 2>/dev/null && \
    echo -e "    ${GREEN}${CHECK} Dev Docker containers stopped${NC}" || \
    echo -e "    ${DIM}No dev Docker containers were running${NC}"

docker compose -f "$PROJECT_ROOT/$COMPOSE_FULL" down --remove-orphans 2>/dev/null && \
    echo -e "    ${GREEN}${CHECK} Full Docker stack stopped${NC}" || \
    echo -e "    ${DIM}No full Docker stack was running${NC}"

# 4. Cleanup temp files
rm -f "$BACKEND_LOG" "$FRONTEND_LOG"

# 5. Check if ports are actually free
echo ""
if ss -tlnH 2>/dev/null | grep -qE ':8000 |:5173 '; then
    echo -e "  ${YELLOW}⚠️  Some ports are still occupied (zombie docker-proxy).${NC}"
    echo -e "  ${YELLOW}   Run: ${BOLD}sudo systemctl restart docker${NC}${YELLOW} to clear them.${NC}"
else
    echo -e "  ${GREEN}${BOLD}${CHECK} All ports are free.${NC}"
fi

echo ""
echo -e "  ${GREEN}${BOLD}${CHECK} Fehres dev environment stopped.${NC}"
echo ""
echo -e "  ${DIM}To also remove Docker volumes (deletes all data):${NC}"
echo -e "    docker compose -f Docker/docker-compose.dev.yml down -v"
echo ""
