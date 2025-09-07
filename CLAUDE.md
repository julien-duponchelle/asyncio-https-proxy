# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Setup Development Environment:**
```bash
uv sync --dev
```

**Run Tests:**
```bash
uv run pytest tests/
```

**Run Specific Test:**
```bash
uv run pytest tests/test_<module_name>.py
```

**Linting and Formatting:**
```bash
uv run ruff check
uv run ruff format
```

**Type checking**
```bash
uv run pyright
```

**Documentation:**
```bash
# Serve docs locally with auto-reload
uv run mkdocs serve

# Build documentation
uv run mkdocs build
```

## Architecture Overview

This is an embeddable asyncio-based HTTPS forward proxy library designed for integration into Python applications rather than standalone use.

### Core Components

**Handler Pattern Architecture:**
- `HTTPSProxyHandler`: Base class that applications subclass to implement custom proxy behavior
- Each client connection creates a new handler instance 
- Key lifecycle methods: `on_client_connected()`, `on_request_received()`
- Handlers control request forwarding and response streaming

**TLS Certificate Management:**
- `TLSStore`: Manages dynamic certificate generation and signing for HTTPS interception
- Self-signed CA certificate system for SSL/TLS traffic interception
- Certificates generated on-demand for target hosts

**HTTP Processing Pipeline:**
- `HTTPRequest`: Parses incoming HTTP requests (method, URL, headers, body)
- `HTTPHeader`: Header parsing and manipulation utilities
- `server.py`: Main server orchestration and connection handling
- Request body streaming via async generators

**Key Integration Points:**
1. Applications create custom handler classes inheriting from `HTTPSProxyHandler`
2. Use `start_proxy_server()` with handler builder function and `TLSStore` instance
3. Handler methods receive parsed `HTTPRequest` objects and control response flow
4. Built-in support for both HTTP and HTTPS traffic interception

### Development Notes

- Python 3.13+ required
- Uses `uv` for dependency management (not pip/poetry)
- Pure asyncio implementation with streaming support
- Only external dependency: `cryptography` for TLS operations
- Test suite uses pytest with asyncio support
