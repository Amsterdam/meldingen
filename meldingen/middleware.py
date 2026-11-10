from starlette.types import ASGIApp, Message, Receive, Scope, Send


class ContentSizeLimitMiddleware:
    _app: ASGIApp
    _max_size: int

    def __init__(self, app: ASGIApp, max_size: int) -> None:
        self._app = app
        self._max_size = max_size

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self._app(scope, receive, send)
            return

        received = 0

        async def handle() -> Message:
            nonlocal received

            message = await receive()

            received += len(message.get("body", b""))
            if received > self._max_size:
                await send(
                    {"type": "http.response.start", "status": 413, "headers": [[b"content-type", b"application/json"]]}
                )
                await send({"type": "http.response.body", "body": b'{"detail":"Allowed content size exceeded"}'})

            return message

        await self._app(scope, handle, send)
