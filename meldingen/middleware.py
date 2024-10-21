from fastapi import FastAPI
from starlette.types import Message, Receive, Scope, Send


class ContentSizeLimitMiddleware:
    _app: FastAPI
    _max_size: int

    def __init__(self, app: FastAPI, max_size: int):
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
