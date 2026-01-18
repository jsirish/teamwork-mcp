# Teamwork MCP Server
# Extends mcp-base for Teamwork.com integration

FROM mcp-base:2.2.0

LABEL org.opencontainers.image.source="https://github.com/dynamic/teamwork-mcp"
LABEL org.opencontainers.image.description="Teamwork MCP Server - Project management integration"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Copy Teamwork-specific files only (base already has core MCP deps)
COPY teamwork_mcp/ ./teamwork_mcp/

# Install Teamwork-specific dependencies
# Note: mcp-base already has fastmcp, so we only need Teamwork-specific packages
RUN pip install --no-cache-dir \
    requests>=2.31.0 \
    pydantic>=2.0.0

EXPOSE 3005

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:3005/health || exit 1

CMD ["python", "-m", "teamwork_mcp.server"]
