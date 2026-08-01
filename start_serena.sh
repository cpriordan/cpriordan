#!/bin/bash

# Serena MCP Server Startup Script for Fintests Project
# This script starts the Serena MCP server with the appropriate configuration

# Set up environment
export PATH="$HOME/.local/bin:$PATH"
cd /home/ubuntu/projects/fintests

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Serena MCP Server for Fintests Project${NC}"
echo "======================================================="

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv is not installed. Please install uv first.${NC}"
    echo "Run: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if configuration exists
if [ ! -f "serena_config.yml" ]; then
    echo -e "${YELLOW}Warning: serena_config.yml not found. Using default configuration.${NC}"
fi

if [ ! -f ".serena/project.yml" ]; then
    echo -e "${YELLOW}Warning: .serena/project.yml not found. Using default project settings.${NC}"
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Function to start MCP server
start_mcp_server() {
    echo -e "${GREEN}Starting Serena MCP Server...${NC}"
    
    # Default to stdio transport unless specified
    TRANSPORT=${1:-stdio}
    
    if [ "$TRANSPORT" = "stdio" ]; then
        echo "Transport: Standard I/O (for Claude Code integration)"
        uvx --from git+https://github.com/oraios/serena serena start-mcp-server --transport stdio
    elif [ "$TRANSPORT" = "sse" ]; then
        echo "Transport: Server-Sent Events (HTTP-based)"
        echo "Server will be available at: http://localhost:8002"
        uvx --from git+https://github.com/oraios/serena serena start-mcp-server --transport sse --port 8002
    else
        echo -e "${RED}Error: Invalid transport type. Use 'stdio' or 'sse'.${NC}"
        exit 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [transport_type]"
    echo ""
    echo "Transport types:"
    echo "  stdio  - Standard I/O transport (default, for Claude Code)"
    echo "  sse    - Server-Sent Events transport (HTTP-based)"
    echo ""
    echo "Examples:"
    echo "  $0         # Start with stdio transport"
    echo "  $0 stdio   # Start with stdio transport"
    echo "  $0 sse     # Start with SSE transport"
}

# Function to check dependencies
check_dependencies() {
    echo -e "${YELLOW}Checking language server dependencies...${NC}"
    
    # Check Python language server
    if ! command -v pylsp &> /dev/null; then
        echo -e "${YELLOW}Python Language Server (pylsp) not found. Installing...${NC}"
        pip install python-lsp-server
    fi
    
    # Note: Other language servers would be installed as needed
    # For now, we'll start with Python support for the Playwright tests
    
    echo -e "${GREEN}Dependencies check complete.${NC}"
}

# Handle command line arguments
case "$1" in
    -h|--help)
        show_usage
        exit 0
        ;;
    "")
        check_dependencies
        start_mcp_server "stdio"
        ;;
    stdio|sse)
        check_dependencies
        start_mcp_server "$1"
        ;;
    *)
        echo -e "${RED}Error: Invalid argument '$1'${NC}"
        show_usage
        exit 1
        ;;
esac