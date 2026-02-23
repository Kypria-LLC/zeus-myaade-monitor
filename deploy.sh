#!/bin/bash
# ============================================================================
# ZEUS MYAADE MONITOR -- ONE-COMMAND DEPLOYMENT
# ============================================================================
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - .env file configured with MyAADE credentials
#
# Author: Kostas Kyprianos / Kypria Technologies
# Case: EPPO PP.00179/2026/EN | FBI IC3 | IRS CI Art. 26
# ============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "============================================================"
echo "  ZEUS MYAADE MONITOR -- DEPLOYMENT"
echo "  Justice for John Automation System"
echo "============================================================"
echo -e "${NC}"

# Check prerequisites
echo -e "${YELLOW}[1/6] Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker not found. Install Docker first.${NC}"
    echo "  https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}ERROR: Docker Compose not found.${NC}"
    exit 1
fi

echo -e "${GREEN}  Docker found: $(docker --version)${NC}"

# Check .env file
echo -e "${YELLOW}[2/6] Checking configuration...${NC}"

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}  .env not found. Creating from template...${NC}"
    cp .env.example .env
    echo -e "${RED}  IMPORTANT: Edit .env with your MyAADE credentials before starting!${NC}"
    echo -e "${RED}  Run: nano .env${NC}"
    exit 1
fi

# Verify credentials are set
if grep -q "your_taxisnet_username" .env 2>/dev/null; then
    echo -e "${RED}ERROR: .env still has default credentials.${NC}"
    echo -e "${RED}Edit .env with your actual MyAADE/TaxisNet credentials.${NC}"
    exit 1
fi

echo -e "${GREEN}  Configuration loaded.${NC}"

# Create data directories
echo -e "${YELLOW}[3/6] Creating data directories...${NC}"
mkdir -p data screenshots logs
echo -e "${GREEN}  Directories ready: data/ screenshots/ logs/${NC}"

# Stop existing container (if running)
echo -e "${YELLOW}[4/6] Stopping existing containers...${NC}"
docker compose down 2>/dev/null || docker-compose down 2>/dev/null || true
echo -e "${GREEN}  Clean state.${NC}"

# Build the container
echo -e "${YELLOW}[5/6] Building Docker image...${NC}"
docker compose build 2>/dev/null || docker-compose build
echo -e "${GREEN}  Image built successfully.${NC}"

# Start the monitor
echo -e "${YELLOW}[6/6] Starting Zeus Monitor...${NC}"
docker compose up -d 2>/dev/null || docker-compose up -d

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  ZEUS MONITOR IS NOW RUNNING${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "  Container: ${CYAN}zeus-myaade-monitor${NC}"
echo -e "  Logs:      ${CYAN}docker compose logs -f${NC}"
echo -e "  Stop:      ${CYAN}docker compose down${NC}"
echo -e "  Status:    ${CYAN}docker compose ps${NC}"
echo ""
echo -e "  Data stored in:"
echo -e "    Database:    ${CYAN}./data/myaade_monitor.db${NC}"
echo -e "    Screenshots: ${CYAN}./screenshots/${NC}"
echo -e "    Logs:        ${CYAN}./logs/${NC}"
echo ""
echo -e "${GREEN}  The PHAYLOS KYKLOS ends TODAY.${NC}"
echo -e "${GREEN}  Justice for John. \u2696\uFE0F${NC}"
echo ""
