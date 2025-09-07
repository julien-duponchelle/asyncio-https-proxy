# Advanced Usage

This guide covers advanced usage of asyncio-https-proxy using the lower-level `HTTPSProxyHandler` for complete control over request handling and forwarding logic.

## When to Use HTTPSProxyHandler

Use the base `HTTPSProxyHandler` when you need:

- **Complete control** over request forwarding logic
- **Custom HTTP client implementations** (using httpx, aiohttp, curl_cffi, ...)
- **Fine-grained error handling** and retry logic

For most use cases, [HTTPSForwardProxyHandler](reference/https_forward_proxy_handler.md) with automatic forwarding is recommended. See the [Getting Started](getting-started.md) guide.

## HTTPSProxyHandler Overview

The `HTTPSProxyHandler` is the base class that provides:

- Request parsing and lifecycle hooks
- Response writing utilities
- Request body reading capabilities
- **No automatic forwarding** - you implement all logic yourself

## Basic HTTPSProxyHandler Example

Here's a complete example using `HTTPSProxyHandler` with httpx for request forwarding:

```python title="base_usage.py"
--8<-- "examples/base_usage.py"
```


## Handler Lifecycle Methods

The `HTTPSProxyHandler` provides these lifecycle hooks:

### `on_client_connected()`
Called when a client connects and sends a request. This is where you implement your main request handling logic.

### `on_request_received()` 
Called after the request is fully parsed. Use for logging or request inspection.

### Helper Methods

- `self.read_request_body()` - Async generator for request body chunks
- `self.write_response(data)` - Write response data to client
- `self.flush_response()` - Flush response data to client

## Error Handling Best Practices

```python
async def on_client_connected(self):
    try:
        await self._handle_request()
    except httpx.ConnectTimeout:
        await self._send_error(504, "Gateway Timeout")
    except httpx.ConnectError:
        await self._send_error(502, "Bad Gateway") 
    except Exception as e:
        print(f"Unexpected error: {e}")
        await self._send_error(500, "Internal Server Error")

async def _send_error(self, code: int, message: str):
    """Send standardized error response."""
    body = f"Proxy Error: {code} {message}".encode()
    response = (
        f"HTTP/1.1 {code} {message}\\r\\n"
        f"Content-Type: text/plain\\r\\n"
        f"Content-Length: {len(body)}\\r\\n"
        f"\\r\\n"
    ).encode() + body
    
    self.write_response(response)
    await self.flush_response()
```