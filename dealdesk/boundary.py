"""HTTP boundary for the loopback-only, single-user synthetic demo."""

from urllib.parse import urlsplit

from starlette.responses import JSONResponse

MAX_BODY_BYTES = 16_384


class LocalDemoBoundary:
    def __init__(self, app, host: str):
        self.app = app
        self.hosts = {host.lower(), "localhost", "127.0.0.1", "::1"}

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))

        async def reject(status, detail):
            await JSONResponse({"detail": detail}, status_code=status)(scope, receive, send)

        try:
            authority = headers.get(b"host", b"").decode("ascii")
            parsed = urlsplit("//" + authority)
            valid_host = (parsed.hostname in self.hosts and parsed.username is None
                          and parsed.password is None and not parsed.path
                          and not parsed.query and not parsed.fragment)
            parsed.port  # Reject malformed ports as well as malformed IPv6.
        except (ValueError, UnicodeError):
            valid_host = False
        if not valid_host:
            return await reject(400, "This demo accepts local Host names only.")
        origin = headers.get(b"origin")
        expected = f"{scope.get('scheme', 'http')}://{authority}".encode("ascii")
        if origin is not None and origin != expected:
            return await reject(403, "A browser request must come from this demo's origin.")
        # CLI/agent calls omit Origin; browsers also provide Fetch Metadata.
        top_navigation = (scope.get("method") in ("GET", "HEAD") and origin is None
                          and headers.get(b"sec-fetch-mode") == b"navigate"
                          and headers.get(b"sec-fetch-dest") == b"document")
        if headers.get(b"sec-fetch-site") in (b"cross-site", b"same-site") and not top_navigation:
            return await reject(403, "Cross-origin browser access is refused.")
        try:
            length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            return await reject(400, "Invalid request length.")
        if length < 0 or length > MAX_BODY_BYTES:
            return await reject(413, "Request body exceeds the 16 KiB demo limit.")
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > MAX_BODY_BYTES:
                return await reject(413, "Request body exceeds the 16 KiB demo limit.")
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, replay, send)
