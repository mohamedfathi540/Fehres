#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────
# Fehres Development Environment
# Hybrid mode: Docker for infra, local for app
# ─────────────────────────────────────────────────────────

# Colors & formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="/tmp/fehres"
LOG_DIR="/tmp/fehres/logs"
BACKEND_PID="$PID_DIR/backend.pid"
FRONTEND_PID="$PID_DIR/frontend.pid"

# Ports
PORT_POSTGRES=5433
PORT_QDRANT=6333
PORT_BACKEND=8000
PORT_FRONTEND=5777

# Guard against repeated cleanup
CLEANING_UP=false

# ─────────────────────────────────────────────────────────
# ASCII Banner
# ─────────────────────────────────────────────────────────
banner() {
    echo ""
    echo -e "${MAGENTA}${BOLD}"
    echo "  ╔═══════════════════════════════════════════════╗"
    echo "  ║                                               ║"
    echo "  ║   ███████╗███████╗██╗  ██╗██████╗ ███████╗   ║"
    echo "  ║   ██╔════╝██╔════╝██║  ██║██╔══██╗██╔════╝   ║"
    echo "  ║   █████╗  █████╗  ███████║██████╔╝█████╗     ║"
    echo "  ║   ██╔══╝  ██╔══╝  ██╔══██║██╔══██╗██╔══╝     ║"
    echo "  ║   ██║     ███████╗██║  ██║██║  ██║███████╗   ║"
    echo "  ║   ╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝   ║"
    echo "  ║                                               ║"
    echo "  ║        🔥 Development Environment 🔥         ║"
    echo "  ╚═══════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
}

# ─────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────
step() {
    echo -e "\n${CYAN}${BOLD}▸ $1${NC}"
}

success() {
    echo -e "  ${GREEN}✓${NC} $1"
}

warn() {
    echo -e "  ${YELLOW}⚠${NC} $1"
}

fail() {
    echo -e "  ${RED}✗${NC} $1"
}

info() {
    echo -e "  ${DIM}$1${NC}"
}

# ─────────────────────────────────────────────────────────
# Kill any previous Fehres processes by PID file
# ─────────────────────────────────────────────────────────
kill_previous() {
    step "Cleaning up any previous sessions..."

    if [ -f "$BACKEND_PID" ]; then
        local bpid
        bpid=$(cat "$BACKEND_PID" 2>/dev/null || true)
        if [ -n "$bpid" ] && kill -0 "$bpid" 2>/dev/null; then
            kill "$bpid" 2>/dev/null || true
            kill -- -"$bpid" 2>/dev/null || true
            success "Killed previous backend (PID: $bpid)"
        fi
        rm -f "$BACKEND_PID"
    fi

    if [ -f "$FRONTEND_PID" ]; then
        local fpid
        fpid=$(cat "$FRONTEND_PID" 2>/dev/null || true)
        if [ -n "$fpid" ] && kill -0 "$fpid" 2>/dev/null; then
            kill "$fpid" 2>/dev/null || true
            kill -- -"$fpid" 2>/dev/null || true
            success "Killed previous frontend (PID: $fpid)"
        fi
        rm -f "$FRONTEND_PID"
    fi

    success "Clean slate ready"
}

# ─────────────────────────────────────────────────────────
# Cleanup handler (Ctrl+C) — runs only ONCE
# ─────────────────────────────────────────────────────────
cleanup() {
    # Guard: only run once
    if $CLEANING_UP; then
        exit 1
    fi
    CLEANING_UP=true

    # Ignore further signals during cleanup
    trap '' SIGINT SIGTERM

    echo ""
    step "Shutting down Fehres..."

    # Kill frontend
    if [ -f "$FRONTEND_PID" ]; then
        local fpid
        fpid=$(cat "$FRONTEND_PID" 2>/dev/null || true)
        if [ -n "$fpid" ] && kill -0 "$fpid" 2>/dev/null; then
            kill "$fpid" 2>/dev/null || true
            kill -- -"$fpid" 2>/dev/null || true
            success "Frontend stopped"
        fi
        rm -f "$FRONTEND_PID"
    fi

    # Kill backend
    if [ -f "$BACKEND_PID" ]; then
        local bpid
        bpid=$(cat "$BACKEND_PID" 2>/dev/null || true)
        if [ -n "$bpid" ] && kill -0 "$bpid" 2>/dev/null; then
            kill "$bpid" 2>/dev/null || true
            kill -- -"$bpid" 2>/dev/null || true
            success "Backend stopped"
        fi
        rm -f "$BACKEND_PID"
    fi

    # Stop Docker infra (only if Docker is truly available)
    if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
        docker compose -f "$SCRIPT_DIR/Docker/docker-compose.dev.yml" down 2>/dev/null || true
        success "Docker infra stopped"
    fi

    # Clean up logs
    rm -rf "$LOG_DIR" 2>/dev/null || true

    echo -e "\n${GREEN}${BOLD}  ✨ Fehres shut down cleanly. See you! ✨${NC}\n"
    exit 0
}

trap cleanup SIGINT SIGTERM

# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────
banner

# Create dirs
mkdir -p "$PID_DIR" "$LOG_DIR"

# 0. Kill previous sessions
kill_previous

# 1. Docker infrastructure (if Docker is truly available)
if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
    step "Starting Docker infrastructure (pgvector + qdrant)..."
    docker compose -f "$SCRIPT_DIR/Docker/docker-compose.dev.yml" up -d 2>&1 | while read -r line; do
        info "$line"
    done

    # Wait for PostgreSQL to be healthy
    echo -ne "  ${DIM}Waiting for PostgreSQL to be ready"
    for i in $(seq 1 30); do
        if docker exec pgvector pg_isready -U postgres &>/dev/null; then
            echo -e "${NC}"
            success "PostgreSQL (pgvector) is ready on port $PORT_POSTGRES"
            break
        fi
        echo -ne "."
        sleep 2
        if [ "$i" -eq 30 ]; then
            echo -e "${NC}"
            warn "PostgreSQL did not become ready — continuing anyway"
        fi
    done

    # Check Qdrant
    for i in $(seq 1 15); do
        if curl -sf --connect-timeout 2 http://localhost:$PORT_QDRANT/healthz &>/dev/null || \
           curl -sf --connect-timeout 2 http://localhost:$PORT_QDRANT/ &>/dev/null; then
            success "Qdrant is ready on port $PORT_QDRANT"
            break
        fi
        sleep 2
        if [ "$i" -eq 15 ]; then
            warn "Qdrant may not be ready yet — continuing anyway"
        fi
    done
else
    step "Docker not found — skipping infrastructure containers"
    warn "pgvector and qdrant will not be started"
    warn "Make sure they are running elsewhere, or install Docker"
    info "Backend will try to connect to PostgreSQL at localhost:$PORT_POSTGRES"
fi

# 2. Backend (FastAPI)
step "Starting FastAPI backend on port $PORT_BACKEND..."
cd "$SCRIPT_DIR/SRC"

# Activate venv or use uv
if command -v uv &>/dev/null; then
    nohup uv run uvicorn main:app --host 0.0.0.0 --port "$PORT_BACKEND" --reload \
        > "$LOG_DIR/backend.log" 2>&1 &
else
    # Fallback: use the local venv
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    fi
    nohup python -m uvicorn main:app --host 0.0.0.0 --port "$PORT_BACKEND" --reload \
        > "$LOG_DIR/backend.log" 2>&1 &
fi
echo $! > "$BACKEND_PID"
success "Backend starting (PID: $(cat "$BACKEND_PID"))"

# Wait for backend — use short curl timeout to avoid hanging
echo -ne "  ${DIM}Waiting for backend"
for i in $(seq 1 15); do
    # Check if "Application startup complete" appears in log
    if grep -q "Application startup complete" "$LOG_DIR/backend.log" 2>/dev/null; then
        echo -e "${NC}"
        success "Backend is up! → http://localhost:${PORT_BACKEND}/docs"
        break
    fi
    # Also check if the process died
    bpid=$(cat "$BACKEND_PID" 2>/dev/null || true)
    if [ -n "$bpid" ] && ! kill -0 "$bpid" 2>/dev/null; then
        echo -e "${NC}"
        fail "Backend process died! Check log:"
        tail -5 "$LOG_DIR/backend.log" 2>/dev/null | while read -r line; do
            info "$line"
        done
        break
    fi
    echo -ne "."
    sleep 2
    if [ "$i" -eq 15 ]; then
        echo -e "${NC}"
        warn "Backend not responding yet — check $LOG_DIR/backend.log"
    fi
done

# 3. Frontend (Vite)
step "Starting Vite frontend on port $PORT_FRONTEND..."
cd "$SCRIPT_DIR/frontend"

# Install deps if needed
if [ ! -d "node_modules" ]; then
    info "Installing frontend dependencies..."
    pnpm install --frozen-lockfile 2>&1 | tail -1
fi

nohup pnpm dev --host 0.0.0.0 > "$LOG_DIR/frontend.log" 2>&1 &
echo $! > "$FRONTEND_PID"
success "Frontend starting (PID: $(cat "$FRONTEND_PID"))"

# Wait for frontend — check log instead of curl
echo -ne "  ${DIM}Waiting for frontend"
for i in $(seq 1 10); do
    if grep -q "Local:" "$LOG_DIR/frontend.log" 2>/dev/null; then
        echo -e "${NC}"
        success "Frontend is up! → http://localhost:${PORT_FRONTEND}"
        break
    fi
    fpid=$(cat "$FRONTEND_PID" 2>/dev/null || true)
    if [ -n "$fpid" ] && ! kill -0 "$fpid" 2>/dev/null; then
        echo -e "${NC}"
        fail "Frontend process died! Check log:"
        tail -5 "$LOG_DIR/frontend.log" 2>/dev/null | while read -r line; do
            info "$line"
        done
        break
    fi
    echo -ne "."
    sleep 2
    if [ "$i" -eq 10 ]; then
        echo -e "${NC}"
        warn "Frontend not responding yet — check $LOG_DIR/frontend.log"
    fi
done

# ─────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}  ╔═══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}  ║         🚀 Fehres is LIVE! 🚀                ║${NC}"
echo -e "${GREEN}${BOLD}  ╠═══════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}${BOLD}  ║${NC}                                               ${GREEN}${BOLD}║${NC}"
echo -e "${GREEN}${BOLD}  ║${NC}  ${CYAN}Frontend${NC}     → ${WHITE}http://localhost:${PORT_FRONTEND}${NC}       ${GREEN}${BOLD}║${NC}"
echo -e "${GREEN}${BOLD}  ║${NC}  ${CYAN}Backend API${NC}  → ${WHITE}http://localhost:${PORT_BACKEND}/docs${NC}  ${GREEN}${BOLD}║${NC}"
echo -e "${GREEN}${BOLD}  ║${NC}  ${CYAN}PostgreSQL${NC}   → ${WHITE}localhost:${PORT_POSTGRES}${NC}             ${GREEN}${BOLD}║${NC}"
echo -e "${GREEN}${BOLD}  ║${NC}  ${CYAN}Qdrant${NC}       → ${WHITE}http://localhost:${PORT_QDRANT}${NC}       ${GREEN}${BOLD}║${NC}"
echo -e "${GREEN}${BOLD}  ║${NC}                                               ${GREEN}${BOLD}║${NC}"
echo -e "${GREEN}${BOLD}  ║${NC}                                               ${GREEN}${BOLD}║${NC}"
echo -e "${GREEN}${BOLD}  ╠═══════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}${BOLD}  ║${NC}  ${DIM}Press ${WHITE}Ctrl+C${NC}${DIM} to stop all services${NC}           ${GREEN}${BOLD}║${NC}"
echo -e "${GREEN}${BOLD}  ╚═══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "\n${CYAN}${BOLD}[ Medicine Scraper Instructions ]${NC}"
echo -e "  To update the medicine database from EDA:"
echo -e "  1. Run: ${WHITE}uv run python3 SRC/scripts/scrape_eda.py${NC}"
echo -e "  2. Open ${WHITE}captcha.jpg${NC} and type the code."
echo -e "  3. Result saved to ${WHITE}SRC/Assets/Files/eda_medicines.csv${NC}"

# ─────────────────────────────────────────────────────────
# Tail logs
# ─────────────────────────────────────────────────────────
step "Tailing logs (backend + frontend)..."
echo -e "  ${DIM}Backend log: $LOG_DIR/backend.log${NC}"
echo -e "  ${DIM}Frontend log: $LOG_DIR/frontend.log${NC}"
echo ""

tail -f "$LOG_DIR/backend.log" "$LOG_DIR/frontend.log" 2>/dev/null || wait
