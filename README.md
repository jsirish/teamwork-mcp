# Teamwork MCP Server

Teamwork.com MCP server providing project management tools via the Teamwork API v3.

## Features

- Project management (list, get, create)
- Task management (list, get, create, update, complete)
- Time tracking (log time, get entries)
- People management (list, get details)

## Authentication

Authentication is handled by the MCP Gateway using OAuth 2.0. This server receives bearer tokens via the `Authorization` header.

## Usage

Run locally:
```bash
python server.py
```

Health check:
```bash
curl http://localhost:3005/health
```
